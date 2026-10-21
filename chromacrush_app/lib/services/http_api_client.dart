/// Concrete HTTP API client for backend communication.
///
/// Implements Phase 1 endpoints: auth, energy, matchmaking, match, health.
/// Non-Phase-1 methods throw UnimplementedError (inherited from StubApiClient).
library;

import 'dart:convert';
import 'dart:io';
import 'dart:isolate';

import 'package:http/http.dart' as http;

import '../config.dart';
import '../models/app_error.dart';
import '../models/backend_contract.dart';
import 'api_client.dart';
import 'session_manager.dart';
import 'token_storage.dart';

// ---------------------------------------------------------------------------
// Isolate entry point — parses MoveResultResponse off the main thread
// ---------------------------------------------------------------------------

/// Parses a move result JSON response in a separate isolate.
///
/// The player's move response includes full cascade step data (removals,
/// drops, spawns, activations, attractions) which can be large after
/// chain reactions. Parsing this off the main thread prevents frame drops
/// and audio glitches.
ApiResponse<MoveResultResponse> _parseMoveResultInIsolate(
  (String body, int statusCode) args,
) {
  final (responseBody, statusCode) = args;
  final body = jsonDecode(responseBody) as Map<String, dynamic>;

  if (statusCode >= 200 && statusCode < 300) {
    final data = body['data'] != null
        ? MoveResultResponse.fromJson(body['data'] as Map<String, dynamic>)
        : null;
    return ApiResponse<MoveResultResponse>(
      success: body['success'] as bool? ?? true,
      data: data,
      meta: body['meta'] != null
          ? ResponseMeta.fromJson(body['meta'] as Map<String, dynamic>)
          : null,
    );
  }

  // Error — return failed response (caller handles gracefully).
  return const ApiResponse<MoveResultResponse>(success: false);
}

class HttpApiClient extends ApiClientBase {
  HttpApiClient({
    http.Client? client,
    required this.tokenStorage,
    required this.sessionManager,
  }) : _client = client ?? http.Client();

  final http.Client _client;
  final TokenStorage tokenStorage;
  final SessionManager sessionManager;

  /// In-memory access token cache (avoids async read on every request).
  String? _accessToken;

  /// Prevents concurrent token refresh attempts.
  bool _refreshInProgress = false;

  // ---------------------------------------------------------------------------
  // Auth
  // ---------------------------------------------------------------------------

  @override
  Future<ApiResponse<RegisterResponse>> register(
    RegisterRequest request,
  ) async {
    final response = await _post('/auth/register', request.toJson());
    return _parse(response, RegisterResponse.fromJson);
  }

  @override
  Future<ApiResponse<LoginResponse>> login(LoginRequest request) async {
    final response = await _post('/auth/login', request.toJson());
    final result = _parse(response, LoginResponse.fromJson);
    if (result.success && result.data != null) {
      await _saveTokens(result.data!);
    }
    return result;
  }

  @override
  Future<ApiResponse<RegisterResponse>> appleLogin(
    AppleLoginRequest request,
  ) async {
    final response = await _post('/auth/apple', request.toJson());
    final result = _parse(response, RegisterResponse.fromJson);
    if (result.success && result.data != null) {
      await _saveTokens(result.data!.auth);
    }
    return result;
  }

  @override
  Future<ApiResponse<LoginResponse>> refreshToken(
    RefreshRequest request,
  ) async {
    final response = await _post('/auth/refresh', request.toJson());
    final result = _parse(response, LoginResponse.fromJson);
    if (result.success && result.data != null) {
      await _saveTokens(result.data!);
    }
    return result;
  }

  @override
  Future<ApiResponse<void>> logout() async {
    final response = await _post('/auth/logout', {});
    await tokenStorage.clearTokens();
    _accessToken = null;
    return _parseVoid(response);
  }

  // ---------------------------------------------------------------------------
  // Energy
  // ---------------------------------------------------------------------------

  @override
  Future<ApiResponse<EnergyResponse>> getEnergy() async {
    final response = await _get('/energy');
    return _parse(response, EnergyResponse.fromJson);
  }

  @override
  Future<ApiResponse<EnergyResponse>> consumeEnergy() async {
    final response = await _post('/energy/consume', {});
    return _parse(response, EnergyResponse.fromJson);
  }

  @override
  Future<ApiResponse<LoginStreakResponse>> recordLogin() async {
    final response = await _post('/energy/login', {});
    return _parse(response, LoginStreakResponse.fromJson);
  }

  @override
  Future<ApiResponse<StreakResponse>> getStreak() async {
    final response = await _get('/energy/streak');
    return _parse(response, StreakResponse.fromJson);
  }

  // ---------------------------------------------------------------------------
  // Matchmaking
  // ---------------------------------------------------------------------------

  @override
  Future<ApiResponse<QueueEntryResponse>> joinQueue(
    JoinQueueRequest request,
  ) async {
    final response = await _post('/matchmaking/queue', request.toJson());
    return _parse(response, QueueEntryResponse.fromJson);
  }

  @override
  Future<ApiResponse<void>> leaveQueue() async {
    final response = await _delete('/matchmaking/queue');
    return _parseVoid(response);
  }

  @override
  Future<ApiResponse<QueueStatusResponse>> getQueueStatus() async {
    final response = await _get('/matchmaking/queue/status');
    return _parse(response, QueueStatusResponse.fromJson);
  }

  @override
  Future<ApiResponse<PoolStatsResponse>> getPoolStats() async {
    final response = await _get('/matchmaking/pools');
    return _parse(response, PoolStatsResponse.fromJson);
  }

  @override
  Future<ApiResponse<MatchStateResponse>> quickMatch({
    QuickMatchRequest? request,
  }) async {
    final body = request?.toJson() ?? {};
    final response = await _post('/matchmaking/quick-match', body);
    return _parse(response, MatchStateResponse.fromJson);
  }

  // ---------------------------------------------------------------------------
  // Match
  // ---------------------------------------------------------------------------

  @override
  Future<ApiResponse<List<MatchStateResponse>>> getActiveMatches() async {
    final response = await _get('/matches/active');
    // Backend wraps list inside {"matches": [...]}, not a bare array.
    final body = jsonDecode(response.body) as Map<String, dynamic>;
    if (response.statusCode >= 200 && response.statusCode < 300) {
      final dataMap = body['data'] as Map<String, dynamic>? ?? {};
      final items =
          (dataMap['matches'] as List<dynamic>?)
              ?.map(
                (e) => MatchStateResponse.fromJson(e as Map<String, dynamic>),
              )
              .toList() ??
          <MatchStateResponse>[];
      return ApiResponse<List<MatchStateResponse>>(
        success: body['success'] as bool? ?? true,
        data: items,
      );
    }
    final errorBody = body['error'] as Map<String, dynamic>? ?? body;
    throw parseApiError(response.statusCode, errorBody);
  }

  @override
  Future<ApiResponse<MatchStateResponse>> getMatch(String matchId) async {
    final response = await _get('/matches/$matchId');
    return _parse(response, MatchStateResponse.fromJson);
  }

  @override
  Future<ApiResponse<MatchStateResponse>> getMatchState(String matchId) async {
    final response = await _get('/matches/$matchId/state');
    return _parse(response, MatchStateResponse.fromJson);
  }

  @override
  Future<ApiResponse<BoardStateResponse>> getBoard(String matchId) async {
    final response = await _get('/matches/$matchId/board');
    return _parse(response, BoardStateResponse.fromJson);
  }

  @override
  Future<ApiResponse<MoveResultResponse>> submitMove(
    String matchId,
    MoveRequest request,
  ) async {
    final response = await _post('/matches/$matchId/move', request.toJson());
    // Parse the large cascade JSON in a separate isolate to keep the
    // main thread free for rendering and audio.
    final responseBody = response.body;
    final statusCode = response.statusCode;
    return Isolate.run(
      () => _parseMoveResultInIsolate((responseBody, statusCode)),
    );
  }

  @override
  Future<ApiResponse<MatchStateResponse>> forfeitMatch(String matchId) async {
    final response = await _post('/matches/$matchId/forfeit', {});
    return _parse(response, MatchStateResponse.fromJson);
  }

  @override
  Future<ApiResponse<List<MoveHistoryEntry>>> getMoveHistory(
    String matchId,
  ) async {
    final response = await _get('/matches/$matchId/moves');
    return _parseList(response, MoveHistoryEntry.fromJson);
  }

  @override
  Future<ApiResponse<List<MatchSummaryResponse>>> getMatchHistory({
    int limit = 20,
    int offset = 0,
  }) async {
    final response = await _get('/matches/history?limit=$limit&offset=$offset');
    return _parseList(response, MatchSummaryResponse.fromJson);
  }

  // ---------------------------------------------------------------------------
  // Campaign
  // ---------------------------------------------------------------------------

  @override
  Future<ApiResponse<CampaignLevelsResponse>> getCampaignLevels() async {
    final response = await _get('/campaign/levels');
    return _parse(response, CampaignLevelsResponse.fromJson);
  }

  @override
  Future<ApiResponse<CampaignLevelResponse>> getCampaignLevel(
    int levelNumber,
  ) async {
    final response = await _get('/campaign/levels/$levelNumber');
    return _parse(response, CampaignLevelResponse.fromJson);
  }

  @override
  Future<ApiResponse<CampaignProgressResponse>> getCampaignProgress() async {
    final response = await _get('/campaign/progress');
    return _parse(response, CampaignProgressResponse.fromJson);
  }

  @override
  Future<ApiResponse<CampaignAttemptResponse>> startCampaignAttempt(
    int levelNumber,
  ) async {
    final response = await _post(
      '/campaign/attempts',
      {'level_number': levelNumber},
    );
    return _parse(response, CampaignAttemptResponse.fromJson);
  }

  @override
  Future<ApiResponse<CampaignMoveResponse>> submitCampaignMove(
    String attemptId,
    MoveRequest move,
  ) async {
    final response = await _post(
      '/campaign/attempts/$attemptId/move',
      move.toJson(),
    );
    return _parse(response, CampaignMoveResponse.fromJson);
  }

  @override
  Future<ApiResponse<CampaignAbandonResponse>> abandonCampaignAttempt(
    String attemptId,
  ) async {
    final response = await _post(
      '/campaign/attempts/$attemptId/abandon',
      {},
    );
    return _parse(response, CampaignAbandonResponse.fromJson);
  }

  @override
  Future<ApiResponse<CampaignMoveResponse>> activateCampaignMega(
    String attemptId,
    MegaActivationRequest request,
  ) async {
    final response = await _post(
      '/campaign/attempts/$attemptId/mega',
      request.toJson(),
    );
    return _parse(response, CampaignMoveResponse.fromJson);
  }

  // ---------------------------------------------------------------------------
  // Health
  // ---------------------------------------------------------------------------

  @override
  Future<ApiResponse<HealthResponse>> getHealth() async {
    final response = await _get('/health');
    return _parse(response, HealthResponse.fromJson);
  }

  // ---------------------------------------------------------------------------
  // Player (Phase 1 — basic implementations)
  // ---------------------------------------------------------------------------

  @override
  Future<ApiResponse<PlayerProfileResponse>> getProfile() async {
    final response = await _get('/players/me');
    return _parse(response, PlayerProfileResponse.fromJson);
  }

  @override
  Future<ApiResponse<PlayerProfileResponse>> updateProfile(
    PlayerUpdateRequest request,
  ) async {
    final response = await _patch('/players/me', request.toJson());
    return _parse(response, PlayerProfileResponse.fromJson);
  }

  @override
  Future<ApiResponse<UsernameCheckResponse>> checkUsername(
    String username,
  ) async {
    final response = await _get(
      '/players/check-username?username=${Uri.encodeComponent(username)}',
    );
    return _parse(response, UsernameCheckResponse.fromJson);
  }

  @override
  Future<ApiResponse<PlayerStatsResponse>> getPlayerStats(
    String playerId,
  ) async {
    final response = await _get('/players/$playerId/stats');
    return _parse(response, PlayerStatsResponse.fromJson);
  }

  @override
  Future<ApiResponse<LeaderboardResponse>> getLeaderboard({
    int limit = 50,
    int offset = 0,
    String sortBy = 'elo',
  }) async {
    final response = await _get(
      '/players/leaderboard?limit=$limit&offset=$offset&sort_by=$sortBy',
    );
    return _parse(response, LeaderboardResponse.fromJson);
  }

  // ---------------------------------------------------------------------------
  // Cards
  // ---------------------------------------------------------------------------

  @override
  Future<ApiResponse<List<CardDefinitionResponse>>> getCardDefinitions() async {
    final response = await _get('/cards/definitions');
    return _parseList(response, CardDefinitionResponse.fromJson);
  }

  @override
  Future<ApiResponse<CardDefinitionResponse>> getCardDefinition(
    int cardId,
  ) async {
    final response = await _get('/cards/definitions/$cardId');
    return _parse(response, CardDefinitionResponse.fromJson);
  }

  @override
  Future<ApiResponse<PlayerCardsResponse>> getPlayerCards({
    int limit = 50,
    int offset = 0,
  }) async {
    final response = await _get('/cards/mine?limit=$limit&offset=$offset');
    return _parse(response, PlayerCardsResponse.fromJson);
  }

  @override
  Future<ApiResponse<EquippedLoadoutResponse>> getEquippedCards() async {
    final response = await _get('/cards/equipped');
    return _parse(response, EquippedLoadoutResponse.fromJson);
  }

  @override
  Future<ApiResponse<EquippedLoadoutResponse>> getPlayerEquippedCards(
    String playerId,
  ) async {
    final response = await _get('/cards/equipped/$playerId');
    return _parse(response, EquippedLoadoutResponse.fromJson);
  }

  @override
  Future<ApiResponse<EquippedLoadoutResponse>> equipCard(
    CardEquipRequest request,
  ) async {
    final response = await _post('/cards/equip', request.toJson());
    return _parse(response, EquippedLoadoutResponse.fromJson);
  }

  @override
  Future<ApiResponse<EquippedLoadoutResponse>> unequipCard(
    CardUnequipRequest request,
  ) async {
    final response = await _post('/cards/unequip', request.toJson());
    return _parse(response, EquippedLoadoutResponse.fromJson);
  }

  @override
  Future<ApiResponse<PlayerCardResponse>> reorderCard(
    CardReorderRequest request,
  ) async {
    final response = await _post('/cards/reorder', request.toJson());
    return _parse(response, PlayerCardResponse.fromJson);
  }

  @override
  Future<ApiResponse<MergeResultResponse>> mergeCards() async {
    final response = await _post('/cards/merge', {});
    return _parse(response, MergeResultResponse.fromJson);
  }

  // ---------------------------------------------------------------------------
  // Inventory
  // ---------------------------------------------------------------------------

  @override
  Future<ApiResponse<MegaInventoryResponse>> getMegaInventory() async {
    final response = await _get('/inventory/mega');
    return _parse(response, MegaInventoryResponse.fromJson);
  }

  @override
  Future<ApiResponse<MoveResultResponse>> activateMega(
    String matchId,
    MegaActivationRequest request,
  ) async {
    final response = await _post('/matches/$matchId/mega', request.toJson());
    // Reuse isolate parsing — mega activation returns the same cascade data as moves.
    final responseBody = response.body;
    final statusCode = response.statusCode;
    return Isolate.run(
      () => _parseMoveResultInIsolate((responseBody, statusCode)),
    );
  }

  // ---------------------------------------------------------------------------
  // Economy
  // ---------------------------------------------------------------------------

  @override
  Future<ApiResponse<GoldResponse>> getGold() async {
    final response = await _get('/economy/gold');
    return _parse(response, GoldResponse.fromJson);
  }

  @override
  Future<ApiResponse<SellCardsResponse>> sellEquippedCards() async {
    final response = await _post('/economy/sell-cards', {});
    return _parse(response, SellCardsResponse.fromJson);
  }

  @override
  Future<ApiResponse<BuyItemResponse>> buyItem(BuyItemRequest request) async {
    final response = await _post('/economy/buy', request.toJson());
    return _parse(response, BuyItemResponse.fromJson);
  }

  @override
  Future<ApiResponse<MarketplaceListResponse>> getMarketplace() async {
    final response = await _get('/economy/marketplace');
    return _parse(response, MarketplaceListResponse.fromJson);
  }

  // ---------------------------------------------------------------------------
  // Stubs — not yet implemented (Phase 2+)
  // ---------------------------------------------------------------------------

  @override
  Future<ApiResponse<List<ArtifactResponse>>> getArtifacts() =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<ArtifactResponse>> getArtifact(String artifactId) =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<ShieldResponse>> getShieldStatus() =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<ShieldResponse>> activateShield(ShieldRequest request) =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<RaidResponse>> attemptRaid(RaidRequest request) =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<CollectionProgressResponse>> getCollectionProgress(
    String setName,
  ) => throw UnimplementedError();
  @override
  Future<ApiResponse<List<RaidTargetResponse>>> getRaidTargets() =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<List<EventResponse>>> getEvents() =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<EventResponse>> getEvent(String eventId) =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<EventParticipantResponse>> joinEvent(String eventId) =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<void>> leaveEvent(String eventId) =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<EventLeaderboardResponse>> getEventLeaderboard(
    String eventId,
  ) => throw UnimplementedError();
  @override
  Future<ApiResponse<PlayerEventStatusResponse>> getEventStatus(
    String eventId,
  ) => throw UnimplementedError();
  @override
  Future<ApiResponse<AdFreeStatusResponse>> getAdFreeStatus() =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<InterstitialResponse>> requestInterstitial(
    InterstitialRequest request,
  ) => throw UnimplementedError();
  @override
  Future<ApiResponse<RewardedVideoResponse>> requestRewardedVideo(
    String rewardType,
  ) => throw UnimplementedError();
  @override
  Future<ApiResponse<RewardedVideoCompleteResponse>> completeRewardedVideo(
    String adRequestId,
    bool completed,
    int watchedDurationMs,
  ) => throw UnimplementedError();
  @override
  Future<ApiResponse<PurchaseIntentResponse>> initiatePurchase(
    InitiatePurchaseRequest request,
  ) => throw UnimplementedError();
  @override
  Future<ApiResponse<PurchaseResultResponse>> validatePurchase(
    ValidatePurchaseRequest request,
  ) async {
    final response = await _post(
      '/payments/purchase/validate',
      request.toJson(),
    );
    return _parse(response, PurchaseResultResponse.fromJson);
  }

  @override
  Future<ApiResponse<PurchaseStatusResponse>> getPurchaseStatus() =>
      throw UnimplementedError();

  // ---------------------------------------------------------------------------
  // HTTP helpers
  // ---------------------------------------------------------------------------

  /// Attempt to refresh the access token using the stored refresh token.
  /// Returns true if refresh succeeded and tokens were updated.
  Future<bool> _attemptTokenRefresh() async {
    if (_refreshInProgress) return false;
    final refresh = sessionManager.refreshToken;
    if (refresh == null || refresh.isEmpty) return false;

    _refreshInProgress = true;
    try {
      final url = Uri.parse('${AppConfig.apiUrl}/auth/refresh');
      final response = await _client.post(
        url,
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({'refresh_token': refresh}),
      );
      if (response.statusCode >= 200 && response.statusCode < 300) {
        final body = jsonDecode(response.body) as Map<String, dynamic>;
        final data = body['data'] as Map<String, dynamic>?;
        if (data != null) {
          final auth = LoginResponse.fromJson(data);
          await _saveTokens(auth);
          sessionManager.updateTokens(auth);
          return true;
        }
      }
      // Refresh failed — clear auth so user goes to login.
      sessionManager.clearAuth();
      _accessToken = null;
      await tokenStorage.clearTokens();
      return false;
    } catch (_) {
      return false;
    } finally {
      _refreshInProgress = false;
    }
  }

  Future<http.Response> _get(String path) async {
    final url = Uri.parse('${AppConfig.apiUrl}$path');
    try {
      var response = await _client.get(url, headers: await _headers());
      if (response.statusCode == 401 && await _attemptTokenRefresh()) {
        response = await _client.get(url, headers: await _headers());
      }
      return response;
    } on SocketException {
      throw const NetworkError(message: 'No internet connection');
    } on HttpException catch (e) {
      throw NetworkError(message: e.message);
    }
  }

  Future<http.Response> _post(String path, Map<String, dynamic> body) async {
    final url = Uri.parse('${AppConfig.apiUrl}$path');
    final encoded = jsonEncode(body);
    try {
      var response = await _client.post(
        url,
        headers: await _headers(contentType: true),
        body: encoded,
      );
      if (response.statusCode == 401 && await _attemptTokenRefresh()) {
        response = await _client.post(
          url,
          headers: await _headers(contentType: true),
          body: encoded,
        );
      }
      return response;
    } on SocketException {
      throw const NetworkError(message: 'No internet connection');
    } on HttpException catch (e) {
      throw NetworkError(message: e.message);
    }
  }

  Future<http.Response> _patch(String path, Map<String, dynamic> body) async {
    final url = Uri.parse('${AppConfig.apiUrl}$path');
    final encoded = jsonEncode(body);
    try {
      var response = await _client.patch(
        url,
        headers: await _headers(contentType: true),
        body: encoded,
      );
      if (response.statusCode == 401 && await _attemptTokenRefresh()) {
        response = await _client.patch(
          url,
          headers: await _headers(contentType: true),
          body: encoded,
        );
      }
      return response;
    } on SocketException {
      throw const NetworkError(message: 'No internet connection');
    } on HttpException catch (e) {
      throw NetworkError(message: e.message);
    }
  }

  Future<http.Response> _delete(String path) async {
    final url = Uri.parse('${AppConfig.apiUrl}$path');
    try {
      var response = await _client.delete(url, headers: await _headers());
      if (response.statusCode == 401 && await _attemptTokenRefresh()) {
        response = await _client.delete(url, headers: await _headers());
      }
      return response;
    } on SocketException {
      throw const NetworkError(message: 'No internet connection');
    } on HttpException catch (e) {
      throw NetworkError(message: e.message);
    }
  }

  Future<Map<String, String>> _headers({bool contentType = false}) async {
    final headers = <String, String>{'Accept': 'application/json'};
    if (contentType) {
      headers['Content-Type'] = 'application/json';
    }
    final token = _accessToken ?? await tokenStorage.accessToken;
    if (token != null) {
      _accessToken = token;
      headers['Authorization'] = 'Bearer $token';
    }
    return headers;
  }

  Future<void> _saveTokens(LoginResponse auth) async {
    _accessToken = auth.accessToken;
    await tokenStorage.saveTokens(
      accessToken: auth.accessToken,
      refreshToken: auth.refreshToken,
    );
  }

  /// Set the in-memory access token (used after login/register in SessionManager).
  void setAccessToken(String? token) {
    _accessToken = token;
  }

  // ---------------------------------------------------------------------------
  // Response parsing
  // ---------------------------------------------------------------------------

  ApiResponse<T> _parse<T>(
    http.Response response,
    T Function(Map<String, dynamic>) fromJson,
  ) {
    final body = jsonDecode(response.body) as Map<String, dynamic>;

    if (response.statusCode >= 200 && response.statusCode < 300) {
      final data = body['data'] != null
          ? fromJson(body['data'] as Map<String, dynamic>)
          : null;
      return ApiResponse<T>(
        success: body['success'] as bool? ?? true,
        data: data,
        meta: body['meta'] != null
            ? ResponseMeta.fromJson(body['meta'] as Map<String, dynamic>)
            : null,
      );
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

  ApiResponse<List<T>> _parseList<T>(
    http.Response response,
    T Function(Map<String, dynamic>) fromJson,
  ) {
    final body = jsonDecode(response.body) as Map<String, dynamic>;

    if (response.statusCode >= 200 && response.statusCode < 300) {
      final items =
          (body['data'] as List<dynamic>?)
              ?.map((e) => fromJson(e as Map<String, dynamic>))
              .toList() ??
          <T>[];
      return ApiResponse<List<T>>(
        success: body['success'] as bool? ?? true,
        data: items,
        meta: body['meta'] != null
            ? ResponseMeta.fromJson(body['meta'] as Map<String, dynamic>)
            : null,
      );
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

  ApiResponse<void> _parseVoid(http.Response response) {
    if (response.statusCode >= 200 && response.statusCode < 300) {
      return const ApiResponse<void>(success: true);
    }

    final body = jsonDecode(response.body) as Map<String, dynamic>;
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
