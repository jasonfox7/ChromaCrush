/// API client for all backend communication.
///
/// Abstract interface defined here. Concrete HTTP implementation in Phase 1.
/// Covers all 55 backend REST endpoints grouped by domain.
library;

import '../models/backend_contract.dart';

/// Abstract API client interface. All methods return typed responses
/// wrapped in the backend's ApiResponse envelope.
abstract class ApiClientBase {
  // -- Auth --
  Future<ApiResponse<RegisterResponse>> register(RegisterRequest request);
  Future<ApiResponse<LoginResponse>> login(LoginRequest request);
  Future<ApiResponse<RegisterResponse>> appleLogin(AppleLoginRequest request);
  Future<ApiResponse<LoginResponse>> refreshToken(RefreshRequest request);
  Future<ApiResponse<void>> logout();

  // -- Player --
  Future<ApiResponse<PlayerProfileResponse>> getProfile();
  Future<ApiResponse<PlayerProfileResponse>> updateProfile(
    PlayerUpdateRequest request,
  );
  Future<ApiResponse<UsernameCheckResponse>> checkUsername(String username);
  Future<ApiResponse<PlayerStatsResponse>> getPlayerStats(String playerId);
  Future<ApiResponse<LeaderboardResponse>> getLeaderboard({
    int limit = 50,
    int offset = 0,
    String sortBy = 'elo',
  });

  // -- Energy --
  Future<ApiResponse<EnergyResponse>> getEnergy();
  Future<ApiResponse<EnergyResponse>> consumeEnergy();
  Future<ApiResponse<LoginStreakResponse>> recordLogin();
  Future<ApiResponse<StreakResponse>> getStreak();

  // -- Matchmaking --
  Future<ApiResponse<QueueEntryResponse>> joinQueue(JoinQueueRequest request);
  Future<ApiResponse<void>> leaveQueue();
  Future<ApiResponse<QueueStatusResponse>> getQueueStatus();
  Future<ApiResponse<PoolStatsResponse>> getPoolStats();
  Future<ApiResponse<MatchStateResponse>> quickMatch({
    QuickMatchRequest? request,
  });

  // -- Match --
  Future<ApiResponse<List<MatchStateResponse>>> getActiveMatches();
  Future<ApiResponse<MatchStateResponse>> getMatch(String matchId);
  Future<ApiResponse<MatchStateResponse>> getMatchState(String matchId);
  Future<ApiResponse<BoardStateResponse>> getBoard(String matchId);
  Future<ApiResponse<MoveResultResponse>> submitMove(
    String matchId,
    MoveRequest request,
  );
  Future<ApiResponse<MatchStateResponse>> forfeitMatch(String matchId);
  Future<ApiResponse<List<MoveHistoryEntry>>> getMoveHistory(String matchId);
  Future<ApiResponse<List<MatchSummaryResponse>>> getMatchHistory({
    int limit = 20,
    int offset = 0,
  });

  // -- Vault --
  Future<ApiResponse<List<ArtifactResponse>>> getArtifacts();
  Future<ApiResponse<ArtifactResponse>> getArtifact(String artifactId);
  Future<ApiResponse<ShieldResponse>> getShieldStatus();
  Future<ApiResponse<ShieldResponse>> activateShield(ShieldRequest request);
  Future<ApiResponse<RaidResponse>> attemptRaid(RaidRequest request);
  Future<ApiResponse<CollectionProgressResponse>> getCollectionProgress(
    String setName,
  );
  Future<ApiResponse<List<RaidTargetResponse>>> getRaidTargets();

  // -- Events --
  Future<ApiResponse<List<EventResponse>>> getEvents();
  Future<ApiResponse<EventResponse>> getEvent(String eventId);
  Future<ApiResponse<EventParticipantResponse>> joinEvent(String eventId);
  Future<ApiResponse<void>> leaveEvent(String eventId);
  Future<ApiResponse<EventLeaderboardResponse>> getEventLeaderboard(
    String eventId,
  );
  Future<ApiResponse<PlayerEventStatusResponse>> getEventStatus(String eventId);

  // -- Ads --
  Future<ApiResponse<AdFreeStatusResponse>> getAdFreeStatus();
  Future<ApiResponse<InterstitialResponse>> requestInterstitial(
    InterstitialRequest request,
  );
  Future<ApiResponse<RewardedVideoResponse>> requestRewardedVideo(
    String rewardType,
  );
  Future<ApiResponse<RewardedVideoCompleteResponse>> completeRewardedVideo(
    String adRequestId,
    bool completed,
    int watchedDurationMs,
  );

  // -- Payments --
  Future<ApiResponse<PurchaseIntentResponse>> initiatePurchase(
    InitiatePurchaseRequest request,
  );
  Future<ApiResponse<PurchaseResultResponse>> validatePurchase(
    ValidatePurchaseRequest request,
  );
  Future<ApiResponse<PurchaseStatusResponse>> getPurchaseStatus();

  // -- Inventory --
  Future<ApiResponse<MegaInventoryResponse>> getMegaInventory();
  Future<ApiResponse<MoveResultResponse>> activateMega(
    String matchId,
    MegaActivationRequest request,
  );

  // -- Cards --
  Future<ApiResponse<List<CardDefinitionResponse>>> getCardDefinitions();
  Future<ApiResponse<CardDefinitionResponse>> getCardDefinition(int cardId);
  Future<ApiResponse<PlayerCardsResponse>> getPlayerCards({
    int limit = 50,
    int offset = 0,
  });
  Future<ApiResponse<EquippedLoadoutResponse>> getEquippedCards();
  Future<ApiResponse<EquippedLoadoutResponse>> getPlayerEquippedCards(
    String playerId,
  );
  Future<ApiResponse<EquippedLoadoutResponse>> equipCard(
    CardEquipRequest request,
  );
  Future<ApiResponse<EquippedLoadoutResponse>> unequipCard(
    CardUnequipRequest request,
  );
  Future<ApiResponse<PlayerCardResponse>> reorderCard(
    CardReorderRequest request,
  );
  Future<ApiResponse<MergeResultResponse>> mergeCards();

  // -- Economy --
  Future<ApiResponse<GoldResponse>> getGold();
  Future<ApiResponse<SellCardsResponse>> sellEquippedCards();
  Future<ApiResponse<BuyItemResponse>> buyItem(BuyItemRequest request);
  Future<ApiResponse<MarketplaceListResponse>> getMarketplace();

  // -- Campaign --
  Future<ApiResponse<CampaignLevelsResponse>> getCampaignLevels();
  Future<ApiResponse<CampaignLevelResponse>> getCampaignLevel(int levelNumber);
  Future<ApiResponse<CampaignProgressResponse>> getCampaignProgress();
  Future<ApiResponse<CampaignAttemptResponse>> startCampaignAttempt(
    int levelNumber,
  );
  Future<ApiResponse<CampaignMoveResponse>> submitCampaignMove(
    String attemptId,
    MoveRequest move,
  );
  Future<ApiResponse<CampaignAbandonResponse>> abandonCampaignAttempt(
    String attemptId,
  );
  Future<ApiResponse<CampaignMoveResponse>> activateCampaignMega(
    String attemptId,
    MegaActivationRequest request,
  );

  // -- Health --
  Future<ApiResponse<HealthResponse>> getHealth();
}

/// Stub implementation that throws UnimplementedError for all methods.
/// Replaced by real HTTP implementation in Phase 1.
class StubApiClient extends ApiClientBase {
  @override
  Future<ApiResponse<RegisterResponse>> register(RegisterRequest request) =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<LoginResponse>> login(LoginRequest request) =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<RegisterResponse>> appleLogin(AppleLoginRequest request) =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<LoginResponse>> refreshToken(RefreshRequest request) =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<void>> logout() => throw UnimplementedError();
  @override
  Future<ApiResponse<PlayerProfileResponse>> getProfile() =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<PlayerProfileResponse>> updateProfile(
    PlayerUpdateRequest request,
  ) => throw UnimplementedError();
  @override
  Future<ApiResponse<UsernameCheckResponse>> checkUsername(String username) =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<PlayerStatsResponse>> getPlayerStats(String playerId) =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<LeaderboardResponse>> getLeaderboard({
    int limit = 50,
    int offset = 0,
    String sortBy = 'elo',
  }) => throw UnimplementedError();
  @override
  Future<ApiResponse<EnergyResponse>> getEnergy() => throw UnimplementedError();
  @override
  Future<ApiResponse<EnergyResponse>> consumeEnergy() =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<LoginStreakResponse>> recordLogin() =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<StreakResponse>> getStreak() => throw UnimplementedError();
  @override
  Future<ApiResponse<QueueEntryResponse>> joinQueue(JoinQueueRequest request) =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<void>> leaveQueue() => throw UnimplementedError();
  @override
  Future<ApiResponse<QueueStatusResponse>> getQueueStatus() =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<PoolStatsResponse>> getPoolStats() =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<MatchStateResponse>> quickMatch({
    QuickMatchRequest? request,
  }) => throw UnimplementedError();
  @override
  Future<ApiResponse<List<MatchStateResponse>>> getActiveMatches() =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<MatchStateResponse>> getMatch(String matchId) =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<MatchStateResponse>> getMatchState(String matchId) =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<BoardStateResponse>> getBoard(String matchId) =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<MoveResultResponse>> submitMove(
    String matchId,
    MoveRequest request,
  ) => throw UnimplementedError();
  @override
  Future<ApiResponse<MatchStateResponse>> forfeitMatch(String matchId) =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<List<MoveHistoryEntry>>> getMoveHistory(String matchId) =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<List<MatchSummaryResponse>>> getMatchHistory({
    int limit = 20,
    int offset = 0,
  }) => throw UnimplementedError();
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
  ) => throw UnimplementedError();
  @override
  Future<ApiResponse<PurchaseStatusResponse>> getPurchaseStatus() =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<MegaInventoryResponse>> getMegaInventory() =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<MoveResultResponse>> activateMega(
    String matchId,
    MegaActivationRequest request,
  ) => throw UnimplementedError();
  @override
  Future<ApiResponse<List<CardDefinitionResponse>>> getCardDefinitions() =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<CardDefinitionResponse>> getCardDefinition(int cardId) =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<PlayerCardsResponse>> getPlayerCards({
    int limit = 50,
    int offset = 0,
  }) => throw UnimplementedError();
  @override
  Future<ApiResponse<EquippedLoadoutResponse>> getEquippedCards() =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<EquippedLoadoutResponse>> getPlayerEquippedCards(
    String playerId,
  ) => throw UnimplementedError();
  @override
  Future<ApiResponse<EquippedLoadoutResponse>> equipCard(
    CardEquipRequest request,
  ) => throw UnimplementedError();
  @override
  Future<ApiResponse<EquippedLoadoutResponse>> unequipCard(
    CardUnequipRequest request,
  ) => throw UnimplementedError();
  @override
  Future<ApiResponse<PlayerCardResponse>> reorderCard(
    CardReorderRequest request,
  ) => throw UnimplementedError();
  @override
  Future<ApiResponse<MergeResultResponse>> mergeCards() =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<GoldResponse>> getGold() => throw UnimplementedError();
  @override
  Future<ApiResponse<SellCardsResponse>> sellEquippedCards() =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<BuyItemResponse>> buyItem(BuyItemRequest request) =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<MarketplaceListResponse>> getMarketplace() =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<CampaignLevelsResponse>> getCampaignLevels() =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<CampaignLevelResponse>> getCampaignLevel(
    int levelNumber,
  ) => throw UnimplementedError();
  @override
  Future<ApiResponse<CampaignProgressResponse>> getCampaignProgress() =>
      throw UnimplementedError();
  @override
  Future<ApiResponse<CampaignAttemptResponse>> startCampaignAttempt(
    int levelNumber,
  ) => throw UnimplementedError();
  @override
  Future<ApiResponse<CampaignMoveResponse>> submitCampaignMove(
    String attemptId,
    MoveRequest move,
  ) => throw UnimplementedError();
  @override
  Future<ApiResponse<CampaignAbandonResponse>> abandonCampaignAttempt(
    String attemptId,
  ) => throw UnimplementedError();
  @override
  Future<ApiResponse<CampaignMoveResponse>> activateCampaignMega(
    String attemptId,
    MegaActivationRequest request,
  ) => throw UnimplementedError();
  @override
  Future<ApiResponse<HealthResponse>> getHealth() => throw UnimplementedError();
}
