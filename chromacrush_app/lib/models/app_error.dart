/// Typed application errors mapped from backend error codes.
///
/// Backend error taxonomy defined in `deprecated/guidance/interface-contracts.md` Section 2.
sealed class AppError implements Exception {
  const AppError({
    required this.code,
    required this.message,
    this.correlationId,
  });
  final String code;
  final String message;
  final String? correlationId;

  @override
  String toString() => '[$code] $message';
}

// -- Network errors (client-side) --

class NetworkError extends AppError {
  const NetworkError({required super.message, super.correlationId})
    : super(code: 'NETWORK_ERROR');
}

class TimeoutError extends AppError {
  const TimeoutError({super.correlationId})
    : super(code: 'TIMEOUT', message: 'Request timed out');
}

// -- Validation errors (400) --

class ValidationError extends AppError {
  const ValidationError({
    required super.code,
    required super.message,
    super.correlationId,
  });
}

// -- Not found errors (404) --

class NotFoundError extends AppError {
  const NotFoundError({
    required super.code,
    required super.message,
    super.correlationId,
  });
}

// -- Auth errors (401) --

class AuthError extends AppError {
  const AuthError({
    required super.code,
    required super.message,
    super.correlationId,
  });
}

// -- Forbidden errors (403) --

class ForbiddenError extends AppError {
  const ForbiddenError({
    required super.code,
    required super.message,
    super.correlationId,
  });
}

// -- Conflict errors (409) --

class ConflictError extends AppError {
  const ConflictError({
    required super.code,
    required super.message,
    super.correlationId,
  });
}

// -- Rate limit errors (429) --

class RateLimitError extends AppError {
  const RateLimitError({
    required super.code,
    required super.message,
    super.correlationId,
    this.retryAfter,
  });
  final int? retryAfter;
}

// -- Server errors (500) --

class ServerError extends AppError {
  const ServerError({
    required super.code,
    required super.message,
    super.correlationId,
  });
}

/// Parse a backend error response into a typed [AppError].
AppError parseApiError(
  int statusCode,
  Map<String, dynamic> errorBody, {
  String? correlationId,
}) {
  final code = errorBody['code'] as String? ?? 'UNKNOWN';
  final message = errorBody['message'] as String? ?? 'Unknown error';
  final cid = correlationId ?? errorBody['correlation_id'] as String?;

  return switch (statusCode) {
    400 => ValidationError(code: code, message: message, correlationId: cid),
    401 => AuthError(code: code, message: message, correlationId: cid),
    403 => ForbiddenError(code: code, message: message, correlationId: cid),
    404 => NotFoundError(code: code, message: message, correlationId: cid),
    409 => ConflictError(code: code, message: message, correlationId: cid),
    429 => RateLimitError(code: code, message: message, correlationId: cid),
    _ => ServerError(code: code, message: message, correlationId: cid),
  };
}
