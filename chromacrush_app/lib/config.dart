/// Application configuration.
///
/// API base URL and feature flags. In production, these would be
/// loaded from environment or remote config.
class AppConfig {
  const AppConfig._();

  /// Backend API base URL.
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000',
  );

  /// API version prefix.
  static const String apiPrefix = '/api/v1';

  /// Full API URL (base + prefix).
  static String get apiUrl => '$apiBaseUrl$apiPrefix';
}
