/// Persistent token storage using SharedPreferences.
///
/// Tokens survive app restarts. On iOS this uses NSUserDefaults,
/// on Windows the Windows registry. For banking-grade security
/// swap to flutter_secure_storage (iOS Keychain) later.
library;

import 'package:shared_preferences/shared_preferences.dart';

class TokenStorage {
  static const _accessTokenKey = 'access_token';
  static const _refreshTokenKey = 'refresh_token';

  SharedPreferences? _prefs;

  Future<SharedPreferences> get _preferences async {
    return _prefs ??= await SharedPreferences.getInstance();
  }

  Future<String?> get accessToken async {
    final prefs = await _preferences;
    return prefs.getString(_accessTokenKey);
  }

  Future<String?> get refreshToken async {
    final prefs = await _preferences;
    return prefs.getString(_refreshTokenKey);
  }

  Future<void> saveTokens({
    required String accessToken,
    required String refreshToken,
  }) async {
    final prefs = await _preferences;
    await prefs.setString(_accessTokenKey, accessToken);
    await prefs.setString(_refreshTokenKey, refreshToken);
  }

  Future<void> clearTokens() async {
    final prefs = await _preferences;
    await prefs.remove(_accessTokenKey);
    await prefs.remove(_refreshTokenKey);
  }
}
