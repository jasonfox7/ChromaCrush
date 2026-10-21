/// Lightweight HTTP client for bot API calls.
///
/// Authenticates via `Authorization: Bearer` header (per-match JWT).
/// Only needs two methods: get match state (with bot hints) and submit move.
library;

import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;

import '../models/app_error.dart';
import '../models/backend_contract.dart';

/// Abstract interface for testability.
abstract class BotApiClientBase {
  Future<MatchStateResponse> getMatchState(String matchId);
  Future<MoveResultResponse> submitMove(String matchId, MoveRequest request);
}

/// Concrete bot API client using Bearer token authentication.
class BotApiClient implements BotApiClientBase {
  BotApiClient({
    required this.baseUrl,
    required this.bearerToken,
    http.Client? client,
  }) : _client = client ?? http.Client();

  final String baseUrl;
  final String bearerToken;
  final http.Client _client;

  @override
  Future<MatchStateResponse> getMatchState(String matchId) async {
    final response = await _get('/matches/$matchId/state');
    return _parse(response, MatchStateResponse.fromJson);
  }

  @override
  Future<MoveResultResponse> submitMove(
    String matchId,
    MoveRequest request,
  ) async {
    final response = await _post('/matches/$matchId/move', request.toJson());
    return _parse(response, MoveResultResponse.fromJson);
  }

  // -- HTTP helpers --

  Map<String, String> _headers({bool contentType = false}) {
    final headers = <String, String>{
      'Accept': 'application/json',
      'Authorization': 'Bearer $bearerToken',
    };
    if (contentType) {
      headers['Content-Type'] = 'application/json';
    }
    return headers;
  }

  Future<http.Response> _get(String path) async {
    final url = Uri.parse('$baseUrl$path');
    try {
      return await _client.get(url, headers: _headers());
    } on SocketException {
      throw const NetworkError(message: 'No internet connection');
    } on HttpException catch (e) {
      throw NetworkError(message: e.message);
    }
  }

  Future<http.Response> _post(String path, Map<String, dynamic> body) async {
    final url = Uri.parse('$baseUrl$path');
    try {
      return await _client.post(
        url,
        headers: _headers(contentType: true),
        body: jsonEncode(body),
      );
    } on SocketException {
      throw const NetworkError(message: 'No internet connection');
    } on HttpException catch (e) {
      throw NetworkError(message: e.message);
    }
  }

  T _parse<T>(
    http.Response response,
    T Function(Map<String, dynamic>) fromJson,
  ) {
    final body = jsonDecode(response.body) as Map<String, dynamic>;

    if (response.statusCode >= 200 && response.statusCode < 300) {
      final data = body['data'] as Map<String, dynamic>?;
      if (data == null) {
        throw const NetworkError(message: 'Empty response data');
      }
      return fromJson(data);
    }

    final errorBody = body['error'] as Map<String, dynamic>? ?? body;
    final correlationId =
        (body['meta'] as Map<String, dynamic>?)?['correlation_id'] as String?;
    throw parseApiError(
      response.statusCode,
      errorBody,
      correlationId: correlationId,
    );
  }
}
