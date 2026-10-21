/// MatchViewModel — coordinates match lifecycle between API and game scene.
///
/// States: idle → matchmaking → loading → playing → ended.
/// Subscribes to EventBus for game scene events. Updates SessionManager.
library;

import 'dart:async';

import 'package:flutter/widgets.dart';

import '../models/backend_contract.dart';
import '../models/view_state.dart';
import '../services/api_client.dart';
import '../services/bot_player_service.dart';
import '../services/event_bus.dart';
import '../services/session_manager.dart';

/// Match lifecycle state.
enum MatchState { idle, matchmaking, loading, playing, ended }

class MatchViewModel extends ChangeNotifier {
  MatchViewModel({
    required this.apiClient,
    required this.eventBus,
    required this.sessionManager,
    this.botPlayerService,
  }) {
    _subscribeToEvents();
  }

  final ApiClientBase apiClient;
  final EventBus eventBus;
  final SessionManager sessionManager;
  final BotPlayerServiceBase? botPlayerService;

  // -- Observable state --
  MatchState state = MatchState.idle;
  String? matchId;
  int myScore = 0;
  int opponentScore = 0;
  int movesRemaining = 0;
  String? opponentName;
  String? opponentPlayerId;
  bool? opponentIsBot;
  MatchOutcome? matchResult;
  CardRaidResultResponse? raidResult;
  MatchRewardResponse? rewardResult;
  List<({int cardId, String rarity})> opponentCards = const [];
  String? errorMessage;
  bool isSinglePlayer = false;

  // -- Board state for the game scene --
  BoardStateResponse? currentBoard;

  // -- Computed post-match properties --

  /// Absolute score difference between player and opponent.
  int get scoreDifferential => (myScore - opponentScore).abs();

  /// True when the player lost by a narrow margin (< 15% of combined score).
  bool get isNearMiss {
    if (matchResult != MatchOutcome.loss) return false;
    final totalScore = myScore + opponentScore;
    if (totalScore == 0) return false;
    return scoreDifferential / totalScore < 0.15;
  }

  // -- Event subscriptions --
  final List<StreamSubscription<dynamic>> _subscriptions = [];

  void _subscribeToEvents() {
    _subscriptions.add(
      eventBus.on<ScoreUpdatedEvent>().listen((event) {
        myScore += event.delta;
        notifyListeners();
      }),
    );

    _subscriptions.add(
      eventBus.on<MovesUpdatedEvent>().listen((event) {
        movesRemaining = event.movesRemaining;
        notifyListeners();
      }),
    );

    _subscriptions.add(
      eventBus.on<BotScoreUpdatedEvent>().listen((event) {
        opponentScore = event.botScore;
        notifyListeners();
      }),
    );

    _subscriptions.add(
      eventBus.on<MatchEndedEvent>().listen((_) {
        _onMatchEnded();
      }),
    );
  }

  // ---------------------------------------------------------------------------
  // Match lifecycle
  // ---------------------------------------------------------------------------

  /// Start a single-player match: auto-register guest → queue → bot match → play.
  Future<void> startSinglePlayer() async {
    isSinglePlayer = true;
    await _startMatchFlow();
  }

  /// Start a versus match (requires prior auth): queue → match → play.
  Future<void> startMatch() async {
    isSinglePlayer = false;
    await _startMatchFlow();
  }

  Future<void> _startMatchFlow() async {
    // Full reset for new match.
    botPlayerService?.stop();
    matchId = null;
    currentBoard = null;
    movesRemaining = 0;
    matchResult = null;
    raidResult = null;
    rewardResult = null;
    opponentName = null;
    opponentPlayerId = null;
    opponentIsBot = null;
    opponentCards = const [];
    errorMessage = null;
    myScore = 0;
    opponentScore = 0;
    state = MatchState.matchmaking;
    // Defer to avoid setState-during-build when called from initState.
    WidgetsBinding.instance.addPostFrameCallback((_) => notifyListeners());

    try {
      MatchStateResponse? match;

      if (isSinglePlayer) {
        // Single-player: instant bot match via quick-match endpoint.
        // Server picks a random bot from the pool.
        final result = await apiClient.quickMatch();
        match = result.data;
      } else {
        // Versus: join matchmaking queue and poll for match assignment.
        await apiClient.joinQueue(const JoinQueueRequest());

        for (var i = 0; i < 30; i++) {
          await Future<void>.delayed(const Duration(seconds: 1));

          final status = await apiClient.getQueueStatus();
          if (status.data != null && !status.data!.inQueue) {
            final active = await apiClient.getActiveMatches();
            if (active.data != null && active.data!.isNotEmpty) {
              match = active.data!.first;
              break;
            }
          }
        }
      }

      if (match == null) {
        state = MatchState.idle;
        errorMessage = isSinglePlayer
            ? 'Failed to create match'
            : 'Matchmaking timed out';
        notifyListeners();
        return;
      }

      // Load match state.
      state = MatchState.loading;
      matchId = match.matchId;
      sessionManager.setActiveMatch(match.matchId);
      notifyListeners();

      // Determine opponent info from server response.
      opponentName = match.player2.username;
      opponentPlayerId = match.player2.playerId;
      opponentIsBot = match.opponentIsBot || match.player2.isBot;

      // Fetch opponent's equipped cards for preview.
      try {
        final opCards = await apiClient.getPlayerEquippedCards(
          match.player2.playerId,
        );
        if (opCards.success && opCards.data != null) {
          opponentCards = opCards.data!.cards
              .map(
                (c) =>
                    (cardId: c.definition.cardId, rarity: c.definition.rarity),
              )
              .toList();
        }
      } catch (_) {
        // Non-critical — preview just won't show cards.
      }

      // Fetch board.
      final boardResponse = await apiClient.getBoard(match.matchId);
      if (boardResponse.data == null) {
        state = MatchState.idle;
        errorMessage = 'Failed to load board';
        notifyListeners();
        return;
      }

      currentBoard = boardResponse.data;
      movesRemaining = boardResponse.data!.movesRemaining;
      myScore = boardResponse.data!.score;

      state = MatchState.playing;
      notifyListeners();

      // Start the bot opponent if server provided a per-match bot token.
      // Difficulty scales with the player's elo rating.
      final botToken = match.botToken;
      if (botToken != null && botPlayerService != null && matchId != null) {
        final elo = sessionManager.player?.eloRating ?? 1000;
        final difficulty = elo >= 1300
            ? 'hard'
            : elo >= 1100
            ? 'medium'
            : 'easy';
        botPlayerService!.startPlaying(
          matchId: matchId!,
          totalMoves: movesRemaining,
          bearerToken: botToken,
          difficulty: difficulty,
          elo: elo,
        );
      }
    } catch (e) {
      state = MatchState.idle;
      errorMessage = e.toString();
      notifyListeners();
    }
  }

  /// Forfeit the current match.
  Future<void> forfeit() async {
    if (matchId == null) return;
    botPlayerService?.stop();

    try {
      final result = await apiClient.forfeitMatch(matchId!);
      matchResult = MatchOutcome.loss;

      // Read final scores, raid, and reward data from forfeit response.
      if (result.data != null) {
        final data = result.data!;
        myScore = data.myScore;
        opponentScore = data.opponentScore;
        raidResult = data.raidResult;
        rewardResult = data.rewardResult;
      }

      state = MatchState.ended;
      sessionManager.clearActiveMatch();
      notifyListeners();
    } catch (e) {
      errorMessage = e.toString();
      notifyListeners();
    }
  }

  /// Rejoin an active match (e.g. after app disconnect).
  Future<void> rejoinMatch(String activeMatchId) async {
    botPlayerService?.stop();
    matchId = activeMatchId;
    currentBoard = null;
    movesRemaining = 0;
    matchResult = null;
    raidResult = null;
    rewardResult = null;
    opponentName = null;
    opponentPlayerId = null;
    opponentIsBot = null;
    opponentCards = const [];
    errorMessage = null;
    myScore = 0;
    opponentScore = 0;
    state = MatchState.loading;
    notifyListeners();

    try {
      // Fetch match state to restore opponent info + scores.
      final matchState = await apiClient.getMatchState(activeMatchId);
      if (matchState.data == null) {
        // Match no longer exists or already ended — clear and bail.
        state = MatchState.idle;
        errorMessage = 'Match no longer active';
        sessionManager.clearActiveMatch();
        notifyListeners();
        return;
      }

      final match = matchState.data!;
      if (match.status == 'completed' || match.status == 'cancelled') {
        state = MatchState.idle;
        errorMessage = 'Match already ended';
        sessionManager.clearActiveMatch();
        notifyListeners();
        return;
      }

      opponentName = match.player2.username;
      opponentPlayerId = match.player2.playerId;
      opponentIsBot = match.opponentIsBot || match.player2.isBot;
      myScore = match.myScore;
      opponentScore = match.opponentScore;

      // Fetch opponent's equipped cards for preview.
      try {
        final opCards = await apiClient.getPlayerEquippedCards(
          match.player2.playerId,
        );
        if (opCards.success && opCards.data != null) {
          opponentCards = opCards.data!.cards
              .map(
                (c) =>
                    (cardId: c.definition.cardId, rarity: c.definition.rarity),
              )
              .toList();
        }
      } catch (_) {}

      // Fetch board.
      final boardResponse = await apiClient.getBoard(activeMatchId);
      if (boardResponse.data == null) {
        state = MatchState.idle;
        errorMessage = 'Failed to load board';
        sessionManager.clearActiveMatch();
        notifyListeners();
        return;
      }

      currentBoard = boardResponse.data;
      movesRemaining = boardResponse.data!.movesRemaining;
      myScore = boardResponse.data!.score;

      state = MatchState.playing;
      sessionManager.setActiveMatch(activeMatchId);
      notifyListeners();

      // Emit initial bot score so UI shows opponent's score immediately.
      if (opponentScore > 0) {
        eventBus.fire(BotScoreUpdatedEvent(botScore: opponentScore, delta: 0));
      }

      // Start the bot opponent if applicable.
      final botToken = match.botToken;
      if (botToken != null && botPlayerService != null) {
        final elo = sessionManager.player?.eloRating ?? 1000;
        final difficulty = elo >= 1300
            ? 'hard'
            : elo >= 1100
            ? 'medium'
            : 'easy';
        botPlayerService!.startPlaying(
          matchId: activeMatchId,
          totalMoves: match.player2.movesRemaining,
          bearerToken: botToken,
          difficulty: difficulty,
          elo: elo,
          initialScore: opponentScore,
        );
      }
    } catch (e) {
      state = MatchState.idle;
      errorMessage = e.toString();
      sessionManager.clearActiveMatch();
      notifyListeners();
    }
  }

  /// Play again — start a new match (preserves game mode).
  /// _startMatchFlow handles the full reset internally.
  Future<void> playAgain() async {
    await _startMatchFlow();
  }

  // ---------------------------------------------------------------------------
  // Internal
  // ---------------------------------------------------------------------------

  Future<void> _onMatchEnded() async {
    if (matchId == null) return;
    final endingMatchId = matchId!;

    // Stop the bot.
    botPlayerService?.stop();

    try {
      // When playing against a bot, forfeit on behalf of the bot to mark the
      // backend match as completed. This prevents stale in_progress matches.
      if (opponentIsBot == true) {
        try {
          await apiClient.forfeitMatch(endingMatchId);
        } catch (_) {
          // Best-effort — match may already be completed.
        }
      }

      // Fetch final match state to determine win/loss and raid result.
      final matchState = await apiClient.getMatchState(endingMatchId);
      if (matchState.data != null) {
        final data = matchState.data!;
        opponentScore = data.opponentScore;
        myScore = data.myScore;

        // Use backend winner_id as source of truth (handles instant-win cards
        // like Lucky Rabbit where the winner may have 0 score).
        final myPlayerId = sessionManager.player?.playerId;
        if (data.winnerId != null && myPlayerId != null) {
          matchResult = data.winnerId == myPlayerId
              ? MatchOutcome.win
              : MatchOutcome.loss;
        } else if (data.winnerId == null &&
            data.status == 'completed') {
          matchResult = MatchOutcome.draw;
        } else {
          // Fallback to score comparison for older matches without winner_id.
          if (myScore > opponentScore) {
            matchResult = MatchOutcome.win;
          } else if (myScore < opponentScore) {
            matchResult = MatchOutcome.loss;
          } else {
            matchResult = MatchOutcome.draw;
          }
        }

        // Read raid and reward results from match state (persisted on match record).
        raidResult = data.raidResult;
        rewardResult = data.rewardResult;
      }
    } catch (_) {
      // Fall back to local score comparison.
      if (myScore > opponentScore) {
        matchResult = MatchOutcome.win;
      } else if (myScore < opponentScore) {
        matchResult = MatchOutcome.loss;
      } else {
        matchResult = MatchOutcome.draw;
      }
    }

    state = MatchState.ended;
    sessionManager.clearActiveMatch();
    notifyListeners();
  }

  @override
  void dispose() {
    for (final sub in _subscriptions) {
      sub.cancel();
    }
    super.dispose();
  }
}
