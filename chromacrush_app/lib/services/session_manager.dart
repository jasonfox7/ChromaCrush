/// Session manager — player state that persists across screens.
///
/// Extends ChangeNotifier so Flutter widgets rebuild on state changes.
/// Populated from backend API responses. Server is truth.
library;

import 'package:flutter/foundation.dart';

import '../models/backend_contract.dart';

class SessionManager extends ChangeNotifier {
  // -- Auth state --
  String? _accessToken;
  String? _refreshToken;
  PlayerResponse? _player;

  String? get accessToken => _accessToken;
  String? get refreshToken => _refreshToken;
  PlayerResponse? get player => _player;
  bool get isLoggedIn => _accessToken != null;

  void setAuth(LoginResponse auth, PlayerResponse player) {
    _accessToken = auth.accessToken;
    _refreshToken = auth.refreshToken;
    _player = player;
    notifyListeners();
  }

  void updateTokens(LoginResponse auth) {
    _accessToken = auth.accessToken;
    _refreshToken = auth.refreshToken;
    notifyListeners();
  }

  void clearAuth() {
    _accessToken = null;
    _refreshToken = null;
    _player = null;
    _energy = null;
    _gold = null;
    _ownedCards = null;
    _equippedLoadout = null;
    notifyListeners();
  }

  void updateUsername(String newUsername) {
    if (_player != null) {
      _player = PlayerResponse(
        playerId: _player!.playerId,
        username: newUsername,
        playerType: _player!.playerType,
        eloRating: _player!.eloRating,
        createdAt: _player!.createdAt,
      );
      notifyListeners();
    }
  }

  // -- Gold state --
  GoldResponse? _gold;
  GoldResponse? get gold => _gold;
  int get goldBalance => _gold?.balance ?? 0;

  void updateGold(GoldResponse gold) {
    _gold = gold;
    notifyListeners();
  }

  void updateGoldBalance(int newBalance) {
    if (_gold != null) {
      _gold = GoldResponse(
        balance: newBalance,
        lifetimeEarned: _gold!.lifetimeEarned,
        lifetimeSpent: _gold!.lifetimeSpent,
      );
    } else {
      _gold = GoldResponse(
        balance: newBalance,
        lifetimeEarned: 0,
        lifetimeSpent: 0,
      );
    }
    notifyListeners();
  }

  // -- Energy state --
  EnergyResponse? _energy;
  EnergyResponse? get energy => _energy;

  /// Client-side countdown seconds until next heart regenerates.
  int? _regenSecondsRemaining;
  int? get regenSecondsRemaining => _regenSecondsRemaining;

  void updateEnergy(EnergyResponse energy) {
    _energy = energy;
    // Sync client-side countdown from server value.
    _regenSecondsRemaining = energy.isFull ? null : energy.secondsToNextHeart;
    notifyListeners();
  }

  /// Tick the client-side regen countdown by 1 second.
  /// Returns true if the timer is still active.
  bool tickRegenTimer() {
    if (_regenSecondsRemaining == null || _regenSecondsRemaining! <= 0) {
      _regenSecondsRemaining = null;
      return false;
    }
    _regenSecondsRemaining = _regenSecondsRemaining! - 1;
    notifyListeners();
    return _regenSecondsRemaining! > 0;
  }

  // -- Active match --
  String? _activeMatchId;
  String? get activeMatchId => _activeMatchId;

  void setActiveMatch(String matchId) {
    _activeMatchId = matchId;
    notifyListeners();
  }

  void clearActiveMatch() {
    _activeMatchId = null;
    notifyListeners();
  }

  // -- Ad-free status --
  bool _isAdFree = false;
  bool get isAdFree => _isAdFree;

  void setAdFree(bool value) {
    _isAdFree = value;
    notifyListeners();
  }

  // -- Card state --
  List<PlayerCardResponse>? _ownedCards;
  EquippedLoadoutResponse? _equippedLoadout;

  List<PlayerCardResponse>? get ownedCards => _ownedCards;
  EquippedLoadoutResponse? get equippedLoadout => _equippedLoadout;

  void updateOwnedCards(List<PlayerCardResponse> cards) {
    _ownedCards = cards;
    notifyListeners();
  }

  void updateEquippedLoadout(EquippedLoadoutResponse loadout) {
    _equippedLoadout = loadout;
    notifyListeners();
  }

  void clearCards() {
    _ownedCards = null;
    _equippedLoadout = null;
    notifyListeners();
  }
}
