/// Debug logger for end-to-end move tracing (frontend side).
///
/// Produces structured JSON events with epoch_ms timestamps that can be
/// correlated with backend debug logs. Controlled by a debug flag passed
/// at construction. When disabled, all methods are no-ops.
library;

import 'dart:convert';
import 'dart:io';

/// Debug event categories matching the backend's DebugCategory.
enum DebugCategory { board, move, match, cascade, sync, api, error }

class DebugLogger {
  DebugLogger({required bool enabled}) : _enabled = enabled {
    if (_enabled) {
      _initLogFile();
    }
  }

  final bool _enabled;
  static const int _maxEvents = 500;
  final List<Map<String, dynamic>> _events = [];
  IOSink? _logSink;
  String? _logFilePath;

  bool get enabled => _enabled;
  String? get logFilePath => _logFilePath;

  void _initLogFile() {
    try {
      final dir = Directory('logs');
      if (!dir.existsSync()) {
        dir.createSync(recursive: true);
      }
      final ts = DateTime.now()
          .toUtc()
          .toIso8601String()
          .replaceAll(':', '-')
          .split('.')
          .first;
      _logFilePath = 'logs/debug_frontend_$ts.jsonl';
      _logSink = File(_logFilePath!).openWrite(mode: FileMode.append);
    } catch (_) {
      // Running in browser or no filesystem access — console only.
    }
  }

  // ---------------------------------------------------------------------------
  // Core
  // ---------------------------------------------------------------------------

  void _log(
    DebugCategory category,
    String action,
    Map<String, dynamic> data, {
    String? matchId,
    String? playerId,
  }) {
    if (!_enabled) return;

    final event = <String, dynamic>{
      'ts': DateTime.now().toUtc().toIso8601String(),
      'epoch_ms': DateTime.now().millisecondsSinceEpoch,
      'cat': category.name.toUpperCase(),
      'action': action,
      'side': 'FRONTEND',
      'match_id': ?matchId,
      'player_id': ?playerId,
      ...data,
    };

    _events.add(event);
    if (_events.length > _maxEvents) {
      _events.removeRange(0, _events.length - _maxEvents);
    }

    // Write to file if available
    try {
      _logSink?.writeln(jsonEncode(event));
    } catch (_) {}

    // Console output for immediate visibility
    // ignore: avoid_print
    print('[FE:${category.name.toUpperCase()}] $action');
  }

  // ---------------------------------------------------------------------------
  // Board state
  // ---------------------------------------------------------------------------

  void logBoardState(String label, List<List<int>> cells, {String? matchId}) {
    if (!_enabled) return;

    final ascii = _boardToAscii(cells);
    _log(DebugCategory.board, 'board_state:$label', {
      'board': cells,
      'ascii': ascii,
    }, matchId: matchId);

    for (final row in ascii) {
      // ignore: avoid_print
      print('  $row');
    }
  }

  // ---------------------------------------------------------------------------
  // Move
  // ---------------------------------------------------------------------------

  void logMoveAttempt(
    int fromRow,
    int fromCol,
    int toRow,
    int toCol,
    List<List<int>> boardBefore, {
    String? matchId,
  }) {
    if (!_enabled) return;

    final fromGem = boardBefore[fromRow][fromCol];
    final toGem = boardBefore[toRow][toCol];

    _log(DebugCategory.move, 'move_attempt', {
      'from': [fromRow, fromCol],
      'to': [toRow, toCol],
      'from_gem': fromGem,
      'to_gem': toGem,
      'board_before': boardBefore,
    }, matchId: matchId);

    // ignore: avoid_print
    print(
      '  Swap ($fromRow,$fromCol)[gem=$fromGem] -> ($toRow,$toCol)[gem=$toGem]',
    );
  }

  void logMoveResponse({
    required bool valid,
    required int scoreGained,
    required int matchesFound,
    required int cascades,
    required int movesRemaining,
    List<List<int>>? newBoard,
    String? matchId,
    String? error,
  }) {
    if (!_enabled) return;

    _log(DebugCategory.move, 'move_response', {
      'valid': valid,
      'score_gained': scoreGained,
      'matches_found': matchesFound,
      'cascades': cascades,
      'moves_remaining': movesRemaining,
      'new_board': ?newBoard,
      'error': ?error,
    }, matchId: matchId);

    final status = valid ? 'VALID' : 'INVALID';
    // ignore: avoid_print
    print(
      '  Response: $status score=$scoreGained matches=$matchesFound cascades=$cascades',
    );
    if (newBoard != null) {
      for (final row in _boardToAscii(newBoard)) {
        // ignore: avoid_print
        print('  $row');
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Sync
  // ---------------------------------------------------------------------------

  void logBoardSync(String label, List<List<int>> cells, {String? matchId}) {
    if (!_enabled) return;

    _log(DebugCategory.sync, 'board_sync:$label', {
      'board': cells,
      'ascii': _boardToAscii(cells),
    }, matchId: matchId);
  }

  // ---------------------------------------------------------------------------
  // API
  // ---------------------------------------------------------------------------

  void logApiRequest(
    String endpoint,
    String method, {
    String? matchId,
    Map<String, dynamic>? body,
  }) {
    if (!_enabled) return;

    _log(DebugCategory.api, '$method $endpoint', {
      'body': ?body,
    }, matchId: matchId);
  }

  void logApiResponse(
    String endpoint,
    bool success, {
    String? matchId,
    String? error,
  }) {
    if (!_enabled) return;

    _log(DebugCategory.api, 'response:$endpoint', {
      'success': success,
      'error': ?error,
    }, matchId: matchId);
  }

  // ---------------------------------------------------------------------------
  // Error
  // ---------------------------------------------------------------------------

  void logError(
    String message, {
    String? matchId,
    Map<String, dynamic>? context,
  }) {
    if (!_enabled) return;

    _log(DebugCategory.error, message, {'context': ?context}, matchId: matchId);
  }

  // ---------------------------------------------------------------------------
  // Query / export
  // ---------------------------------------------------------------------------

  List<Map<String, dynamic>> getEvents({
    DebugCategory? category,
    String? matchId,
  }) {
    var results = _events.toList();
    if (category != null) {
      results = results
          .where((e) => e['cat'] == category.name.toUpperCase())
          .toList();
    }
    if (matchId != null) {
      results = results.where((e) => e['match_id'] == matchId).toList();
    }
    return results;
  }

  void clear() {
    _events.clear();
  }

  void dispose() {
    _logSink?.close();
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  static const _gemChars = {
    0: '.',
    1: 'R',
    2: 'B',
    3: 'G',
    4: 'Y',
    5: 'P',
    6: 'O',
  };

  static List<String> _boardToAscii(List<List<int>> cells) {
    return [
      for (var r = 0; r < cells.length; r++)
        '$r: ${cells[r].map((v) => _gemChars[v] ?? '?').join(' ')}',
    ];
  }
}
