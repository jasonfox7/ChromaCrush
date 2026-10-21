/// Bot player service — drives a server-side bot through the backend API.
///
/// Timer-driven: each tick dispatches work to a **separate Dart isolate** that
/// handles HTTP calls and JSON parsing, keeping the main isolate free for
/// rendering and audio. Only lightweight score/state results cross back.
///
/// **Rival Mode**: 80% of matches (scaling with ELO), the bot rubber-bands its
/// move selection to keep scores close, creating exciting neck-and-neck games.
/// The remaining matches are "unleashed" — bot plays optimally (stomps).
///
/// Authentication uses per-match Bearer JWT tokens provided by the server
/// when matching against a bot opponent.
library;

import 'dart:async';
import 'dart:convert';
import 'dart:isolate';
import 'dart:math';

import 'package:http/http.dart' as http;

import '../config/game_config.dart';
import 'debug_logger.dart';
import 'event_bus.dart';

/// Abstract interface for testability.
abstract class BotPlayerServiceBase {
  void startPlaying({
    required String matchId,
    required int totalMoves,
    required String bearerToken,
    String difficulty = 'medium',
    int elo = 1000,
    int initialScore = 0,
  });
  void stop();
  int get currentScore;
  int get movesMade;
  void dispose();
}

/// Difficulty determines base move quality when not rubber-banding.
enum BotDifficulty {
  easy, // Random move from all hints
  medium, // Random from top 3
  hard, // Always best move
}

// ---------------------------------------------------------------------------
// Isolate communication types
// ---------------------------------------------------------------------------

/// Parameters sent to the bot move isolate.
class _BotMoveParams {
  const _BotMoveParams({
    required this.baseUrl,
    required this.bearerToken,
    required this.matchId,
    required this.difficulty,
    required this.randomSeed,
    this.rivalMode = false,
    this.rivalTightness = 0.10,
    this.sprintMoves = 5,
    this.botMovesRemaining = 30,
  });
  final String baseUrl;
  final String bearerToken;
  final String matchId;
  final String difficulty;
  final int randomSeed;

  /// True = rubber-band to keep scores close. False = play at full strength.
  final bool rivalMode;

  /// Max acceptable score gap fraction before sandbagging kicks in.
  final double rivalTightness;

  /// Last N moves: always play best regardless of rival mode.
  final int sprintMoves;

  /// Bot's remaining moves (for sprint detection).
  final int botMovesRemaining;
}

/// Lightweight result from the bot move isolate — no cascade data.
class _BotMoveResult {
  const _BotMoveResult({
    this.valid = false,
    this.scoreGained = 0,
    this.movesRemaining = 0,
    this.matchCompleted = false,
    this.matchesFound = 0,
    this.cascades = 0,
    this.skipped = false,
    this.fatal = false,
    this.reason,
  });
  final bool valid;
  final int scoreGained;
  final int movesRemaining;
  final bool matchCompleted;
  final int matchesFound;
  final int cascades;
  final bool skipped;

  /// True when the error is permanent (4xx) — bot should stop, not retry.
  final bool fatal;
  final String? reason;
}

// ---------------------------------------------------------------------------
// Rival mode move selection
// ---------------------------------------------------------------------------

/// Pick a move index from the ranked hints list using rival mode logic.
///
/// In rival mode, the bot adjusts its move quality based on the score gap:
/// - Far ahead  → pick from worst moves (sandbag)
/// - Slightly ahead → pick from middle
/// - Close game → top 3 (competitive)
/// - Behind → best move (catch up)
/// - Sprint finish → always best (exciting ending)
///
/// In unleashed mode, falls back to standard difficulty-based selection.
int _pickMoveIndex({
  required int numMoves,
  required String difficulty,
  required bool rivalMode,
  required double rivalTightness,
  required int sprintMoves,
  required int botScore,
  required int playerScore,
  required int movesRemaining,
  required Random rng,
}) {
  // Unleashed mode or sprint finish: standard difficulty selection.
  if (!rivalMode || movesRemaining <= sprintMoves) {
    return switch (difficulty) {
      'hard' => 0,
      'medium' => rng.nextInt(min(3, numMoves)),
      _ => rng.nextInt(numMoves),
    };
  }

  // Rival mode: rubber-band based on score gap.
  final totalScore = botScore + playerScore;
  final gap = totalScore > 0 ? (botScore - playerScore) / totalScore : 0.0;

  if (gap > rivalTightness) {
    // Bot ahead too much — sandbag (pick from bottom half).
    final start = numMoves ~/ 2;
    return start + rng.nextInt(numMoves - start);
  } else if (gap > rivalTightness * 0.5) {
    // Bot slightly ahead — coast (middle of the list).
    final start = numMoves ~/ 4;
    final end = min(numMoves, (numMoves * 3) ~/ 4);
    return start + rng.nextInt(max(1, end - start));
  } else if (gap > -rivalTightness * 0.5) {
    // Close game — competitive (top 3).
    return rng.nextInt(min(3, numMoves));
  } else {
    // Bot behind — catch up (best move).
    return 0;
  }
}

// ---------------------------------------------------------------------------
// Isolate entry point — runs entirely off the main thread
// ---------------------------------------------------------------------------

/// Executes a full bot move cycle in a separate isolate.
///
/// 1. GET match state with bot hints
/// 2. Pick a move based on difficulty + rival mode
/// 3. POST the move
/// 4. Return ONLY lightweight results (skip cascade_steps parsing entirely)
Future<_BotMoveResult> _executeBotMoveInIsolate(_BotMoveParams params) async {
  final client = http.Client();
  try {
    final headers = {
      'Accept': 'application/json',
      'Authorization': 'Bearer ${params.bearerToken}',
    };

    // 1. GET match state with bot hints.
    final stateResp = await client.get(
      Uri.parse('${params.baseUrl}/matches/${params.matchId}/state'),
      headers: headers,
    );
    if (stateResp.statusCode < 200 || stateResp.statusCode >= 300) {
      return _BotMoveResult(
        skipped: true,
        reason: 'State fetch HTTP ${stateResp.statusCode}',
      );
    }

    final stateBody = jsonDecode(stateResp.body) as Map<String, dynamic>;
    final stateData = stateBody['data'] as Map<String, dynamic>?;
    if (stateData == null) {
      return const _BotMoveResult(skipped: true, reason: 'No state data');
    }

    final botHintsJson = stateData['bot_hints'] as Map<String, dynamic>?;
    if (botHintsJson == null) {
      return const _BotMoveResult(skipped: true, reason: 'No bot hints');
    }

    final bestMovesJson = botHintsJson['best_moves'] as List<dynamic>? ?? [];
    if (bestMovesJson.isEmpty) {
      return const _BotMoveResult(skipped: true, reason: 'No best moves');
    }

    // 2. Pick a move based on difficulty + rival mode rubber-banding.
    final rng = Random(params.randomSeed);
    final botScore = stateData['my_score'] as int? ?? 0;
    final playerScore = stateData['opponent_score'] as int? ?? 0;

    final moveIndex = _pickMoveIndex(
      numMoves: bestMovesJson.length,
      difficulty: params.difficulty,
      rivalMode: params.rivalMode,
      rivalTightness: params.rivalTightness,
      sprintMoves: params.sprintMoves,
      botScore: botScore,
      playerScore: playerScore,
      movesRemaining: params.botMovesRemaining,
      rng: rng,
    );
    final moveJson = bestMovesJson[moveIndex] as Map<String, dynamic>;
    final moveData = moveJson['move'] as Map<String, dynamic>;

    // 3. Submit the move.
    final moveResp = await client.post(
      Uri.parse('${params.baseUrl}/matches/${params.matchId}/move'),
      headers: {...headers, 'Content-Type': 'application/json'},
      body: jsonEncode({
        'from_row': moveData['from_row'],
        'from_col': moveData['from_col'],
        'to_row': moveData['to_row'],
        'to_col': moveData['to_col'],
        'timestamp_ms': DateTime.now().millisecondsSinceEpoch,
      }),
    );
    if (moveResp.statusCode < 200 || moveResp.statusCode >= 300) {
      return _BotMoveResult(
        skipped: true,
        fatal: moveResp.statusCode >= 400 && moveResp.statusCode < 500,
        reason: 'Move HTTP ${moveResp.statusCode}',
      );
    }

    final resultBody = jsonDecode(moveResp.body) as Map<String, dynamic>;
    final resultData = resultBody['data'] as Map<String, dynamic>?;
    if (resultData == null) {
      return const _BotMoveResult(skipped: true, reason: 'No move result');
    }

    // 4. Extract ONLY lightweight fields — cascade_steps never parsed.
    return _BotMoveResult(
      valid: resultData['valid'] as bool? ?? false,
      scoreGained: resultData['score_gained'] as int? ?? 0,
      movesRemaining: resultData['moves_remaining'] as int? ?? 0,
      matchCompleted: resultData['match_completed'] as bool? ?? false,
      matchesFound: resultData['matches_found'] as int? ?? 0,
      cascades: resultData['cascades'] as int? ?? 0,
    );
  } finally {
    client.close();
  }
}

// ---------------------------------------------------------------------------
// BotPlayerService
// ---------------------------------------------------------------------------

/// Concrete bot player that dispatches moves to a separate Dart isolate.
///
/// All HTTP communication and JSON parsing happens off the main thread.
/// Only lightweight results (score, moves remaining, match status) cross
/// back to the main isolate for EventBus dispatch.
class BotPlayerService implements BotPlayerServiceBase {
  BotPlayerService({
    required String baseUrl,
    required EventBus eventBus,
    required DebugLogger debugLogger,
  }) : _baseUrl = baseUrl,
       _eventBus = eventBus,
       _log = debugLogger;

  final String _baseUrl;
  final EventBus _eventBus;
  final DebugLogger _log;
  final _random = Random();

  Timer? _timer;
  String? _matchId;
  String? _bearerToken;
  int _movesRemaining = 0;
  int _currentScore = 0;
  int _movesMade = 0;
  BotDifficulty _difficulty = BotDifficulty.medium;
  bool _busy = false; // Prevents overlapping isolate dispatches.

  // Rival mode state — decided at match start.
  bool _rivalMode = false;
  double _rivalTightness = 0.10;
  int _sprintMoves = 5;

  @override
  int get currentScore => _currentScore;

  @override
  int get movesMade => _movesMade;

  @override
  void startPlaying({
    required String matchId,
    required int totalMoves,
    required String bearerToken,
    String difficulty = 'medium',
    int elo = 1000,
    int initialScore = 0,
  }) {
    stop();
    _matchId = matchId;
    _bearerToken = bearerToken;
    _movesRemaining = totalMoves;
    _currentScore = initialScore;
    _movesMade = 0;
    _busy = false;
    _difficulty = switch (difficulty) {
      'easy' => BotDifficulty.easy,
      'hard' => BotDifficulty.hard,
      _ => BotDifficulty.medium,
    };

    // Rival mode: rubber-band probability and tightness scale with ELO.
    //   Low ELO  (<1100): 90% rival, loose (0.20), sprint last 3
    //   Mid ELO  (1100-1300): 80% rival, medium (0.10), sprint last 5
    //   High ELO (>1300): 60% rival, tight (0.05), sprint last 7
    final unleashChance = elo >= 1300
        ? 0.40
        : elo >= 1100
        ? 0.20
        : 0.10;
    _rivalMode = _random.nextDouble() >= unleashChance;
    _rivalTightness = elo >= 1300
        ? 0.05
        : elo >= 1100
        ? 0.10
        : 0.20;
    _sprintMoves = elo >= 1300
        ? 7
        : elo >= 1100
        ? 5
        : 3;

    _log.logApiRequest(
      '/bot/start',
      'BOT',
      matchId: matchId,
      body: {
        'totalMoves': totalMoves,
        'difficulty': difficulty,
        'elo': elo,
        'rivalMode': _rivalMode,
        'rivalTightness': _rivalTightness,
        'sprintMoves': _sprintMoves,
      },
    );
    _scheduleNext();
  }

  @override
  void stop() {
    final wasActive = _matchId != null;
    _timer?.cancel();
    _timer = null;
    if (wasActive) {
      _log.logApiRequest(
        '/bot/stop',
        'BOT',
        matchId: _matchId,
        body: {
          'movesMade': _movesMade,
          'score': _currentScore,
          'movesRemaining': _movesRemaining,
        },
      );
    }
    _matchId = null;
    _bearerToken = null;
    _movesRemaining = 0;
  }

  @override
  void dispose() {
    stop();
  }

  /// Schedule the next move with a randomized delay based on difficulty.
  void _scheduleNext() {
    if (_movesRemaining <= 0 || _matchId == null) return;
    // Easy bot: 3-5s, medium: 2-4s, hard: 1.5-3s.
    final delayMs = switch (_difficulty) {
      BotDifficulty.easy =>
        kBotEasyDelayMinMs + _random.nextInt(kBotEasyDelayRangeMs),
      BotDifficulty.medium =>
        kBotMediumDelayMinMs + _random.nextInt(kBotMediumDelayRangeMs),
      BotDifficulty.hard =>
        kBotHardDelayMinMs + _random.nextInt(kBotHardDelayRangeMs),
    };
    _log.logApiRequest(
      '/bot/schedule',
      'BOT',
      matchId: _matchId,
      body: {'delayMs': delayMs, 'movesRemaining': _movesRemaining},
    );
    _timer = Timer(Duration(milliseconds: delayMs), _playMove);
  }

  /// Dispatch bot move to a separate isolate, process lightweight result.
  Future<void> _playMove() async {
    if (_busy ||
        _matchId == null ||
        _bearerToken == null ||
        _movesRemaining <= 0) {
      _log.logError(
        'Bot _playMove skipped: busy=$_busy matchId=$_matchId movesRemaining=$_movesRemaining',
      );
      return;
    }
    _busy = true;
    final matchId = _matchId!;

    try {
      final params = _BotMoveParams(
        baseUrl: _baseUrl,
        bearerToken: _bearerToken!,
        matchId: matchId,
        difficulty: _difficulty.name,
        randomSeed: _random.nextInt(1 << 32),
        rivalMode: _rivalMode,
        rivalTightness: _rivalTightness,
        sprintMoves: _sprintMoves,
        botMovesRemaining: _movesRemaining,
      );

      // All HTTP + JSON parsing happens in a separate isolate.
      final result = await Isolate.run(() => _executeBotMoveInIsolate(params));

      if (result.skipped) {
        _log.logError('Bot move skipped: ${result.reason}', matchId: matchId);
        _busy = false;
        if (result.fatal) {
          _log.logError('Bot stopping — fatal error', matchId: matchId);
          stop();
        } else {
          _scheduleNext();
        }
        return;
      }

      _log.logMoveResponse(
        valid: result.valid,
        scoreGained: result.scoreGained,
        matchesFound: result.matchesFound,
        cascades: result.cascades,
        movesRemaining: result.movesRemaining,
        matchId: matchId,
      );

      // Accumulate score and update state.
      if (result.valid) {
        final delta = result.scoreGained;
        _currentScore += delta;
        _movesMade++;
        _movesRemaining = result.movesRemaining;

        // Fire event on bus (main isolate — lightweight).
        _eventBus.fire(
          BotScoreUpdatedEvent(botScore: _currentScore, delta: delta),
        );
      } else {
        _log.logError('Bot move INVALID', matchId: matchId);
      }

      // Check if match is over.
      if (result.matchCompleted || _movesRemaining <= 0) {
        _log.logApiRequest(
          '/bot/finished',
          'BOT',
          matchId: matchId,
          body: {
            'matchCompleted': result.matchCompleted,
            'movesRemaining': _movesRemaining,
            'finalScore': _currentScore,
            'totalMoves': _movesMade,
          },
        );
        _busy = false;
        stop();
        return;
      }
    } catch (e, st) {
      _log.logError(
        'Bot move ERROR: $e',
        matchId: matchId,
        context: {'stackTrace': st.toString().split('\n').take(5).toList()},
      );
    }

    _busy = false;
    _scheduleNext();
  }
}
