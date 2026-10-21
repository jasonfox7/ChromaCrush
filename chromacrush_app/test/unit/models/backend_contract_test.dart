import 'package:flutter_test/flutter_test.dart';
import 'package:chromacrush_app/models/backend_contract.dart';

void main() {
  group('ApiResponse', () {
    test('success envelope round-trips correctly', () {
      final response = ApiResponse<Map<String, dynamic>>(
        success: true,
        data: {'key': 'value'},
        meta: const ResponseMeta(
          correlationId: 'abc-123',
          timestamp: '2026-01-01T00:00:00Z',
          version: '1.0.0',
        ),
      );

      expect(response.success, isTrue);
      expect(response.data, {'key': 'value'});
      expect(response.error, isNull);
      expect(response.meta!.correlationId, 'abc-123');
    });

    test('error envelope carries error detail', () {
      const response = ApiResponse<Object>(
        success: false,
        error: ErrorDetail(
          code: 'MATCH_NOT_FOUND',
          message: 'No match with that ID',
        ),
      );

      expect(response.success, isFalse);
      expect(response.data, isNull);
      expect(response.error!.code, 'MATCH_NOT_FOUND');
      expect(response.error!.message, 'No match with that ID');
    });
  });

  group('ResponseMeta', () {
    test('fromJson parses all fields', () {
      final json = {
        'correlation_id': 'cid-456',
        'timestamp': '2026-02-01T12:00:00Z',
        'version': '1.0.0',
      };

      final meta = ResponseMeta.fromJson(json);
      expect(meta.correlationId, 'cid-456');
      expect(meta.timestamp, '2026-02-01T12:00:00Z');
      expect(meta.version, '1.0.0');
    });

    test('fromJson handles null fields', () {
      final meta = ResponseMeta.fromJson(<String, dynamic>{});
      expect(meta.correlationId, isNull);
      expect(meta.timestamp, isNull);
      expect(meta.version, isNull);
    });
  });

  group('ErrorDetail', () {
    test('fromJson parses with details map', () {
      final json = {
        'code': 'VALIDATION_ERROR',
        'message': 'Invalid input',
        'details': {'field': 'username'},
      };

      final error = ErrorDetail.fromJson(json);
      expect(error.code, 'VALIDATION_ERROR');
      expect(error.message, 'Invalid input');
      expect(error.details, {'field': 'username'});
    });
  });

  group('BoardStateResponse', () {
    test('fromJson parses 8x8 board', () {
      final cells = List.generate(
        8,
        (r) => List.generate(8, (c) => (r + c) % 6 + 1),
      );
      final json = {
        'cells': cells,
        'size': 8,
        'moves_made': 3,
        'moves_remaining': 27,
        'score': 450,
        'has_valid_moves': true,
      };

      final board = BoardStateResponse.fromJson(json);
      expect(board.cells.length, 8);
      expect(board.cells[0].length, 8);
      expect(board.size, 8);
      expect(board.movesMade, 3);
      expect(board.movesRemaining, 27);
      expect(board.score, 450);
      expect(board.hasValidMoves, isTrue);
    });

    test('fromJson defaults size to 8 when absent', () {
      final json = {
        'cells': List.generate(8, (_) => List.generate(8, (_) => 1)),
        'moves_made': 0,
        'moves_remaining': 30,
        'score': 0,
        'has_valid_moves': true,
      };

      final board = BoardStateResponse.fromJson(json);
      expect(board.size, 8);
    });
  });

  group('MoveResultResponse', () {
    test('fromJson parses valid move with new board', () {
      final boardJson = {
        'cells': List.generate(8, (_) => List.generate(8, (_) => 1)),
        'size': 8,
        'moves_made': 1,
        'moves_remaining': 29,
        'score': 100,
        'has_valid_moves': true,
      };

      final json = {
        'valid': true,
        'score_gained': 100,
        'new_board': boardJson,
        'matches_found': 3,
        'cascades': 1,
        'special_gems_created': 0,
        'match_completed': false,
        'match_status': 'in_progress',
        'moves_remaining': 29,
        'move_number': 1,
      };

      final result = MoveResultResponse.fromJson(json);
      expect(result.valid, isTrue);
      expect(result.scoreGained, 100);
      expect(result.newBoard, isNotNull);
      expect(result.newBoard!.score, 100);
      expect(result.matchesFound, 3);
      expect(result.cascades, 1);
      expect(result.specialGemsCreated, 0);
      expect(result.matchCompleted, isFalse);
      expect(result.matchStatus, 'in_progress');
      expect(result.moveNumber, 1);
    });

    test('fromJson handles null new_board', () {
      final json = {
        'valid': false,
        'score_gained': 0,
        'new_board': null,
        'matches_found': 0,
        'cascades': 0,
        'special_gems_created': 0,
        'match_completed': false,
        'match_status': 'in_progress',
        'moves_remaining': 30,
        'move_number': 0,
      };

      final result = MoveResultResponse.fromJson(json);
      expect(result.valid, isFalse);
      expect(result.newBoard, isNull);
    });
  });

  group('AppliedModifierResponse', () {
    test('fromJson parses all fields', () {
      final json = {
        'card_id': 7,
        'card_name': 'Flame Surge',
        'hook': 'on_match_scored',
        'description': '+10% fire matches',
      };

      final mod = AppliedModifierResponse.fromJson(json);
      expect(mod.cardId, 7);
      expect(mod.cardName, 'Flame Surge');
      expect(mod.hook, 'on_match_scored');
      expect(mod.description, '+10% fire matches');
    });
  });

  group('MoveResultResponse with applied_modifiers', () {
    test('fromJson parses applied_modifiers list', () {
      final json = {
        'valid': true,
        'score_gained': 150,
        'new_board': null,
        'matches_found': 2,
        'cascades': 1,
        'special_gems_created': 0,
        'match_completed': false,
        'match_status': 'in_progress',
        'moves_remaining': 28,
        'move_number': 2,
        'applied_modifiers': [
          {
            'card_id': 3,
            'card_name': 'Crystal Focus',
            'hook': 'on_cascade_step',
            'description': '+5% cascade bonus',
          },
          {
            'card_id': 12,
            'card_name': 'Storm Caller',
            'hook': 'on_match_scored',
            'description': '+15 lightning',
          },
        ],
      };

      final result = MoveResultResponse.fromJson(json);
      expect(result.appliedModifiers.length, 2);
      expect(result.appliedModifiers[0].cardId, 3);
      expect(result.appliedModifiers[0].cardName, 'Crystal Focus');
      expect(result.appliedModifiers[1].cardId, 12);
    });

    test('fromJson defaults to empty list when absent', () {
      final json = {
        'valid': true,
        'score_gained': 50,
        'new_board': null,
        'matches_found': 1,
        'cascades': 0,
        'special_gems_created': 0,
        'match_completed': false,
        'match_status': 'in_progress',
        'moves_remaining': 29,
        'move_number': 1,
      };

      final result = MoveResultResponse.fromJson(json);
      expect(result.appliedModifiers, isEmpty);
    });
  });

  group('MoveRequest', () {
    test('toJson produces correct snake_case keys', () {
      const move = MoveRequest(
        fromRow: 2,
        fromCol: 3,
        toRow: 2,
        toCol: 4,
        timestampMs: 1706000000000,
      );

      final json = move.toJson();
      expect(json['from_row'], 2);
      expect(json['from_col'], 3);
      expect(json['to_row'], 2);
      expect(json['to_col'], 4);
      expect(json['timestamp_ms'], 1706000000000);
    });
  });

  group('MatchStateResponse', () {
    test('fromJson parses nested player states', () {
      final json = {
        'match_id': 'm-123',
        'status': 'in_progress',
        'match_type': 'standard',
        'player1': {
          'player_id': 'p1',
          'username': 'alice',
          'score': 200,
          'moves_made': 5,
          'moves_remaining': 25,
        },
        'player2': {
          'player_id': 'p2',
          'username': 'bob',
          'score': 150,
          'moves_made': 4,
          'moves_remaining': 26,
        },
        'is_my_turn': true,
        'my_score': 200,
        'opponent_score': 150,
        'turns_remaining': 25,
      };

      final state = MatchStateResponse.fromJson(json);
      expect(state.matchId, 'm-123');
      expect(state.status, 'in_progress');
      expect(state.player1.username, 'alice');
      expect(state.player2.username, 'bob');
      expect(state.isMyTurn, isTrue);
      expect(state.turnsRemaining, 25);
    });
  });

  group('LoginResponse', () {
    test('fromJson parses auth tokens', () {
      final json = {
        'access_token': 'at-xyz',
        'refresh_token': 'rt-xyz',
        'token_type': 'Bearer',
        'expires_in': 3600,
      };

      final auth = LoginResponse.fromJson(json);
      expect(auth.accessToken, 'at-xyz');
      expect(auth.refreshToken, 'rt-xyz');
      expect(auth.tokenType, 'Bearer');
      expect(auth.expiresIn, 3600);
    });
  });

  group('RegisterRequest', () {
    test('toJson includes optional email when present', () {
      const req = RegisterRequest(
        username: 'alice',
        password: 'secret',
        email: 'a@b.com',
      );
      final json = req.toJson();
      expect(json['username'], 'alice');
      expect(json['password'], 'secret');
      expect(json['email'], 'a@b.com');
    });

    test('toJson omits email when null', () {
      const req = RegisterRequest(username: 'alice', password: 'secret');
      final json = req.toJson();
      expect(json.containsKey('email'), isFalse);
    });
  });

  group('EnergyResponse', () {
    test('fromJson parses full energy state', () {
      final json = {
        'current_hearts': 3,
        'max_hearts': 5,
        'seconds_to_next_heart': 600,
        'next_heart_at': '2026-02-01T12:10:00Z',
        'is_full': false,
        'daily_streak': 7,
      };

      final energy = EnergyResponse.fromJson(json);
      expect(energy.currentHearts, 3);
      expect(energy.maxHearts, 5);
      expect(energy.secondsToNextHeart, 600);
      expect(energy.isFull, isFalse);
      expect(energy.dailyStreak, 7);
    });
  });

  group('Enums', () {
    test('MatchStatus.fromValue maps backend strings', () {
      expect(MatchStatus.fromValue('in_progress'), MatchStatus.inProgress);
      expect(MatchStatus.fromValue('completed'), MatchStatus.completed);
      expect(MatchStatus.fromValue('pending'), MatchStatus.pending);
      expect(MatchStatus.fromValue('abandoned'), MatchStatus.abandoned);
    });

    test('MatchType.fromValue maps backend strings', () {
      expect(MatchType.fromValue('standard'), MatchType.standard);
      expect(MatchType.fromValue('competitive'), MatchType.competitive);
      expect(MatchType.fromValue('casual'), MatchType.casual);
      expect(MatchType.fromValue('tutorial'), MatchType.tutorial);
    });

    test('PlayerType.fromValue maps backend strings', () {
      expect(PlayerType.fromValue('human'), PlayerType.human);
      expect(PlayerType.fromValue('bot'), PlayerType.bot);
    });

    test('unknown enum value falls back to default', () {
      expect(MatchStatus.fromValue('xyz'), MatchStatus.pending);
      expect(MatchType.fromValue('xyz'), MatchType.standard);
      expect(PlayerType.fromValue('xyz'), PlayerType.human);
    });
  });

  group('RaidResponse', () {
    test('fromJson parses nested artifact list', () {
      final json = {
        'success': true,
        'artifacts_stolen': [
          {
            'artifact_id': 'a1',
            'artifact_type_id': 'at1',
            'rarity': 'rare',
            'artifact_set': 'ancient',
            'name': 'Golden Idol',
            'description': 'A shiny artifact',
            'acquired_at': '2026-01-15T00:00:00Z',
            'source': 'raid',
          },
        ],
        'defender_id': 'd1',
        'message': 'Raid successful',
      };

      final raid = RaidResponse.fromJson(json);
      expect(raid.success, isTrue);
      expect(raid.artifactsStolen.length, 1);
      expect(raid.artifactsStolen[0].name, 'Golden Idol');
      expect(raid.defenderId, 'd1');
    });
  });

  group('PlayerStatsResponse', () {
    test('fromJson parses win_rate as double', () {
      final json = {
        'player_id': 'p1',
        'matches_played': 100,
        'matches_won': 60,
        'matches_lost': 30,
        'matches_drawn': 10,
        'total_score': 50000,
        'highest_score': 1200,
        'longest_chain': 8,
        'total_gems_matched': 25000,
        'win_rate': 0.6,
      };

      final stats = PlayerStatsResponse.fromJson(json);
      expect(stats.winRate, 0.6);
      expect(stats.matchesPlayed, 100);
    });
  });
}
