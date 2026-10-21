import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:chromacrush_app/services/http_api_client.dart';
import 'package:chromacrush_app/services/session_manager.dart';
import 'package:chromacrush_app/services/token_storage.dart';
import 'package:chromacrush_app/models/backend_contract.dart';
import 'package:chromacrush_app/models/app_error.dart';

/// In-memory token storage for tests.
class _FakeTokenStorage extends TokenStorage {
  String? _accessToken;
  String? _refreshToken;

  _FakeTokenStorage();

  @override
  Future<String?> get accessToken async => _accessToken;
  @override
  Future<String?> get refreshToken async => _refreshToken;

  @override
  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    _accessToken = accessToken;
    _refreshToken = refreshToken;
  }

  @override
  Future<void> clearTokens() async {
    _accessToken = null;
    _refreshToken = null;
  }
}

HttpApiClient _createClient(http.Client mockHttp) {
  return HttpApiClient(
    client: mockHttp,
    tokenStorage: _FakeTokenStorage(),
    sessionManager: SessionManager(),
  );
}

void main() {
  group('HttpApiClient', () {
    test('login parses LoginResponse and saves tokens', () async {
      final mockHttp = MockClient((_) async {
        return http.Response(
          jsonEncode({
            'success': true,
            'data': {
              'access_token': 'at-123',
              'refresh_token': 'rt-456',
              'token_type': 'Bearer',
              'expires_in': 3600,
            },
          }),
          200,
        );
      });

      final client = _createClient(mockHttp);
      final result = await client.login(
        const LoginRequest(username: 'alice', password: 'pass123'),
      );

      expect(result.success, isTrue);
      expect(result.data, isNotNull);
      expect(result.data!.accessToken, 'at-123');
      expect(result.data!.refreshToken, 'rt-456');
      expect(result.data!.expiresIn, 3600);
    });

    test('register parses RegisterResponse', () async {
      final mockHttp = MockClient((_) async {
        return http.Response(
          jsonEncode({
            'success': true,
            'data': {
              'player': {
                'player_id': 'p-1',
                'username': 'alice',
                'player_type': 'human',
                'elo_rating': 1000,
                'created_at': '2026-01-01T00:00:00Z',
              },
              'auth': {
                'access_token': 'at-1',
                'refresh_token': 'rt-1',
                'token_type': 'Bearer',
                'expires_in': 3600,
              },
            },
          }),
          200,
        );
      });

      final client = _createClient(mockHttp);
      final result = await client.register(
        const RegisterRequest(username: 'alice', password: 'pass123'),
      );

      expect(result.success, isTrue);
      expect(result.data!.player.username, 'alice');
      expect(result.data!.auth.accessToken, 'at-1');
    });

    test('getBoard parses BoardStateResponse with 8x8 grid', () async {
      final cells = List.generate(
        8,
        (r) => List.generate(8, (c) => ((r + c) % 6) + 1),
      );
      final mockHttp = MockClient((_) async {
        return http.Response(
          jsonEncode({
            'success': true,
            'data': {
              'cells': cells,
              'size': 8,
              'moves_made': 3,
              'moves_remaining': 17,
              'score': 450,
              'has_valid_moves': true,
            },
          }),
          200,
        );
      });

      final client = _createClient(mockHttp);
      final result = await client.getBoard('match-1');

      expect(result.success, isTrue);
      expect(result.data!.cells.length, 8);
      expect(result.data!.cells[0].length, 8);
      expect(result.data!.movesRemaining, 17);
      expect(result.data!.score, 450);
    });

    test('submitMove parses MoveResultResponse', () async {
      final mockHttp = MockClient((_) async {
        return http.Response(
          jsonEncode({
            'success': true,
            'data': {
              'valid': true,
              'score_gained': 150,
              'matches_found': 1,
              'cascades': 0,
              'special_gems_created': 0,
              'match_completed': false,
              'match_status': 'in_progress',
              'moves_remaining': 16,
              'move_number': 4,
              'new_board': {
                'cells': List.generate(8, (_) => List.generate(8, (_) => 1)),
                'size': 8,
                'moves_made': 4,
                'moves_remaining': 16,
                'score': 600,
                'has_valid_moves': true,
              },
            },
          }),
          200,
        );
      });

      final client = _createClient(mockHttp);
      final result = await client.submitMove(
        'match-1',
        const MoveRequest(
          fromRow: 0,
          fromCol: 0,
          toRow: 0,
          toCol: 1,
          timestampMs: 1000,
        ),
      );

      expect(result.success, isTrue);
      expect(result.data!.valid, isTrue);
      expect(result.data!.scoreGained, 150);
      expect(result.data!.newBoard, isNotNull);
      expect(result.data!.movesRemaining, 16);
    });

    test('getEnergy parses EnergyResponse', () async {
      final mockHttp = MockClient((_) async {
        return http.Response(
          jsonEncode({
            'success': true,
            'data': {
              'current_hearts': 3,
              'max_hearts': 5,
              'is_full': false,
              'daily_streak': 7,
            },
          }),
          200,
        );
      });

      final client = _createClient(mockHttp);
      final result = await client.getEnergy();

      expect(result.success, isTrue);
      expect(result.data!.currentHearts, 3);
      expect(result.data!.maxHearts, 5);
    });

    test('getHealth parses HealthResponse', () async {
      final mockHttp = MockClient((_) async {
        return http.Response(
          jsonEncode({
            'success': true,
            'data': {'status': 'healthy', 'timestamp': '2026-02-08T00:00:00Z'},
          }),
          200,
        );
      });

      final client = _createClient(mockHttp);
      final result = await client.getHealth();

      expect(result.success, isTrue);
      expect(result.data!.status, 'healthy');
    });

    test('4xx error throws typed AppError', () async {
      final mockHttp = MockClient((_) async {
        return http.Response(
          jsonEncode({
            'success': false,
            'error': {
              'code': 'VALIDATION_INVALID_GEM_SWAP',
              'message': 'Gems are not adjacent',
            },
          }),
          400,
        );
      });

      final client = _createClient(mockHttp);
      expect(() => client.getHealth(), throwsA(isA<ValidationError>()));
    });

    test('401 error throws AuthError', () async {
      final mockHttp = MockClient((_) async {
        return http.Response(
          jsonEncode({
            'success': false,
            'error': {'code': 'AUTH_TOKEN_EXPIRED', 'message': 'Token expired'},
          }),
          401,
        );
      });

      final client = _createClient(mockHttp);
      expect(() => client.getProfile(), throwsA(isA<AuthError>()));
    });

    test('getActiveMatches parses list response', () async {
      final mockHttp = MockClient((_) async {
        return http.Response(
          jsonEncode({
            'success': true,
            'data': {
              'matches': [
                {
                  'match_id': 'm-1',
                  'status': 'in_progress',
                  'match_type': 'standard',
                  'player1': {
                    'player_id': 'p-1',
                    'username': 'alice',
                    'score': 0,
                    'moves_made': 0,
                    'moves_remaining': 20,
                  },
                  'player2': {
                    'player_id': 'p-2',
                    'username': 'bot_7741',
                    'score': 0,
                    'moves_made': 0,
                    'moves_remaining': 20,
                  },
                  'is_my_turn': true,
                  'my_score': 0,
                  'opponent_score': 0,
                },
              ],
            },
          }),
          200,
        );
      });

      final client = _createClient(mockHttp);
      final result = await client.getActiveMatches();

      expect(result.success, isTrue);
      expect(result.data!.length, 1);
      expect(result.data!.first.matchId, 'm-1');
    });

    test('joinQueue parses QueueEntryResponse', () async {
      final mockHttp = MockClient((_) async {
        return http.Response(
          jsonEncode({
            'success': true,
            'data': {
              'player_id': 'p-1',
              'pool_type': 'mixed',
              'elo_rating': 1000,
              'position': 1,
              'joined_at': '2026-02-08T00:00:00Z',
            },
          }),
          200,
        );
      });

      final client = _createClient(mockHttp);
      final result = await client.joinQueue(const JoinQueueRequest());

      expect(result.success, isTrue);
      expect(result.data!.poolType, 'mixed');
      expect(result.data!.position, 1);
    });

    test('sends auth header when token is set', () async {
      String? authHeader;
      final mockHttp = MockClient((request) async {
        authHeader = request.headers['Authorization'];
        return http.Response(
          jsonEncode({
            'success': true,
            'data': {'status': 'healthy', 'timestamp': '2026-02-08T00:00:00Z'},
          }),
          200,
        );
      });

      final client = _createClient(mockHttp);
      client.setAccessToken('test-token');
      await client.getHealth();

      expect(authHeader, 'Bearer test-token');
    });
  });
}
