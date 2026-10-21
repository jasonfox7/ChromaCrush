import 'package:flutter_test/flutter_test.dart';
import 'package:chromacrush_app/services/session_manager.dart';
import 'package:chromacrush_app/models/backend_contract.dart';

void main() {
  group('SessionManager', () {
    late SessionManager session;

    setUp(() {
      session = SessionManager();
    });

    test('starts with no auth', () {
      expect(session.isLoggedIn, isFalse);
      expect(session.accessToken, isNull);
      expect(session.player, isNull);
    });

    test('setAuth updates auth state', () {
      const auth = LoginResponse(
        accessToken: 'at-1',
        refreshToken: 'rt-1',
        tokenType: 'Bearer',
        expiresIn: 3600,
      );
      const player = PlayerResponse(
        playerId: 'p-1',
        username: 'alice',
        playerType: 'human',
        eloRating: 1200,
        createdAt: '2026-01-01T00:00:00Z',
      );

      session.setAuth(auth, player);

      expect(session.isLoggedIn, isTrue);
      expect(session.accessToken, 'at-1');
      expect(session.player!.username, 'alice');
    });

    test('clearAuth resets all auth state', () {
      const auth = LoginResponse(
        accessToken: 'at-1',
        refreshToken: 'rt-1',
        tokenType: 'Bearer',
        expiresIn: 3600,
      );
      const player = PlayerResponse(
        playerId: 'p-1',
        username: 'alice',
        playerType: 'human',
        eloRating: 1200,
        createdAt: '2026-01-01T00:00:00Z',
      );

      session.setAuth(auth, player);
      session.clearAuth();

      expect(session.isLoggedIn, isFalse);
      expect(session.accessToken, isNull);
      expect(session.player, isNull);
      expect(session.energy, isNull);
    });

    test('updateEnergy updates energy state', () {
      const energy = EnergyResponse(
        currentHearts: 3,
        maxHearts: 5,
        isFull: false,
        dailyStreak: 7,
      );

      session.updateEnergy(energy);

      expect(session.energy, isNotNull);
      expect(session.energy!.currentHearts, 3);
      expect(session.energy!.maxHearts, 5);
    });

    test('setActiveMatch and clearActiveMatch', () {
      expect(session.activeMatchId, isNull);

      session.setActiveMatch('m-123');
      expect(session.activeMatchId, 'm-123');

      session.clearActiveMatch();
      expect(session.activeMatchId, isNull);
    });

    test('setAdFree updates ad-free status', () {
      expect(session.isAdFree, isFalse);

      session.setAdFree(true);
      expect(session.isAdFree, isTrue);

      session.setAdFree(false);
      expect(session.isAdFree, isFalse);
    });

    test('notifyListeners fires on setAuth', () {
      int notifyCount = 0;
      session.addListener(() => notifyCount++);

      const auth = LoginResponse(
        accessToken: 'at-1',
        refreshToken: 'rt-1',
        tokenType: 'Bearer',
        expiresIn: 3600,
      );
      const player = PlayerResponse(
        playerId: 'p-1',
        username: 'alice',
        playerType: 'human',
        eloRating: 1200,
        createdAt: '2026-01-01T00:00:00Z',
      );

      session.setAuth(auth, player);
      expect(notifyCount, 1);
    });

    test('notifyListeners fires on clearAuth', () {
      int notifyCount = 0;
      session.addListener(() => notifyCount++);

      session.clearAuth();
      expect(notifyCount, 1);
    });

    test('notifyListeners fires on updateEnergy', () {
      int notifyCount = 0;
      session.addListener(() => notifyCount++);

      const energy = EnergyResponse(
        currentHearts: 5,
        maxHearts: 5,
        isFull: true,
        dailyStreak: 1,
      );
      session.updateEnergy(energy);
      expect(notifyCount, 1);
    });

    test('notifyListeners fires on setActiveMatch', () {
      int notifyCount = 0;
      session.addListener(() => notifyCount++);

      session.setActiveMatch('m-1');
      expect(notifyCount, 1);

      session.clearActiveMatch();
      expect(notifyCount, 2);
    });

    test('notifyListeners fires on setAdFree', () {
      int notifyCount = 0;
      session.addListener(() => notifyCount++);

      session.setAdFree(true);
      expect(notifyCount, 1);
    });
  });
}
