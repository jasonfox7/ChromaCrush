/// Backend contract — Dart data classes matching all backend API schemas.
///
/// Generated from backend `src/modules/api/schemas/*.py` files.
/// Every field name matches the backend JSON key exactly.
///
/// Source docs:
/// - `docs/architecture/architecture.md` — module map, 55 endpoints
/// - `deprecated/guidance/interface-contracts.md` — type registry, error taxonomy
/// - `src/modules/api/schemas/` — Pydantic v2 request/response models
library;

// ==========================================================================
// Enums
// ==========================================================================

/// Match lifecycle status. Backend: `src/modules/match/types.py` MatchStatus.
enum MatchStatus {
  pending('pending'),
  inProgress('in_progress'),
  completed('completed'),
  abandoned('abandoned');

  const MatchStatus(this.value);
  final String value;

  static MatchStatus fromValue(String v) => MatchStatus.values.firstWhere(
    (e) => e.value == v,
    orElse: () => MatchStatus.pending,
  );
}

/// Match type / rule set. Backend: `src/modules/match/types.py` MatchType.
enum MatchType {
  standard('standard'),
  competitive('competitive'),
  casual('casual'),
  tutorial('tutorial');

  const MatchType(this.value);
  final String value;

  static MatchType fromValue(String v) => MatchType.values.firstWhere(
    (e) => e.value == v,
    orElse: () => MatchType.standard,
  );
}

/// Player account type. Backend: `src/core/types/player.py` PlayerType.
enum PlayerType {
  human('human'),
  bot('bot');

  const PlayerType(this.value);
  final String value;

  static PlayerType fromValue(String v) => PlayerType.values.firstWhere(
    (e) => e.value == v,
    orElse: () => PlayerType.human,
  );
}

// ==========================================================================
// Common envelope — wraps every API response
// ==========================================================================

/// Backend: `src/modules/api/schemas/common.py` ResponseMeta.
class ResponseMeta {
  const ResponseMeta({this.correlationId, this.timestamp, this.version});

  factory ResponseMeta.fromJson(Map<String, dynamic> json) => ResponseMeta(
    correlationId: json['correlation_id'] as String?,
    timestamp: json['timestamp'] as String?,
    version: json['version'] as String?,
  );

  final String? correlationId;
  final String? timestamp;
  final String? version;
}

/// Backend: `src/modules/api/schemas/common.py` ErrorDetail.
class ErrorDetail {
  const ErrorDetail({required this.code, required this.message, this.details});

  factory ErrorDetail.fromJson(Map<String, dynamic> json) => ErrorDetail(
    code: json['code'] as String,
    message: json['message'] as String,
    details: json['details'] as Map<String, dynamic>?,
  );

  final String code;
  final String message;
  final Map<String, dynamic>? details;
}

/// Backend: `src/modules/api/schemas/common.py` ApiResponse[T].
///
/// Every backend response is wrapped in this envelope.
class ApiResponse<T> {
  const ApiResponse({required this.success, this.data, this.error, this.meta});

  final bool success;
  final T? data;
  final ErrorDetail? error;
  final ResponseMeta? meta;
}

// ==========================================================================
// Auth schemas — `src/modules/api/schemas/auth.py`
// ==========================================================================

class RegisterRequest {
  const RegisterRequest({
    required this.username,
    required this.password,
    this.email,
  });

  Map<String, dynamic> toJson() => {
    'username': username,
    'password': password,
    if (email != null) 'email': email,
  };

  final String username;
  final String password;
  final String? email;
}

class LoginRequest {
  const LoginRequest({required this.username, required this.password});

  Map<String, dynamic> toJson() => {'username': username, 'password': password};

  final String username;
  final String password;
}

class AppleLoginRequest {
  const AppleLoginRequest({
    required this.identityToken,
    this.authorizationCode,
    this.displayName,
  });

  Map<String, dynamic> toJson() => {
    'identity_token': identityToken,
    if (authorizationCode != null) 'authorization_code': authorizationCode,
    if (displayName != null) 'display_name': displayName,
  };

  final String identityToken;
  final String? authorizationCode;
  final String? displayName;
}

class RefreshRequest {
  const RefreshRequest({required this.refreshToken});

  Map<String, dynamic> toJson() => {'refresh_token': refreshToken};

  final String refreshToken;
}

class LoginResponse {
  const LoginResponse({
    required this.accessToken,
    required this.refreshToken,
    required this.tokenType,
    required this.expiresIn,
  });

  factory LoginResponse.fromJson(Map<String, dynamic> json) => LoginResponse(
    accessToken: json['access_token'] as String,
    refreshToken: json['refresh_token'] as String,
    tokenType: json['token_type'] as String? ?? 'Bearer',
    expiresIn: json['expires_in'] as int,
  );

  final String accessToken;
  final String refreshToken;
  final String tokenType;
  final int expiresIn;
}

class PlayerResponse {
  const PlayerResponse({
    required this.playerId,
    required this.username,
    required this.playerType,
    required this.eloRating,
    required this.createdAt,
  });

  factory PlayerResponse.fromJson(Map<String, dynamic> json) => PlayerResponse(
    playerId: json['player_id'] as String,
    username: json['username'] as String,
    playerType: json['player_type'] as String,
    eloRating: json['elo_rating'] as int,
    createdAt: json['created_at'] as String,
  );

  final String playerId;
  final String username;
  final String playerType;
  final int eloRating;
  final String createdAt;
}

class RegisterResponse {
  const RegisterResponse({
    required this.player,
    required this.auth,
    this.isNewPlayer = false,
  });

  factory RegisterResponse.fromJson(Map<String, dynamic> json) =>
      RegisterResponse(
        player: PlayerResponse.fromJson(json['player'] as Map<String, dynamic>),
        auth: LoginResponse.fromJson(json['auth'] as Map<String, dynamic>),
        isNewPlayer: json['is_new_player'] as bool? ?? false,
      );

  final PlayerResponse player;
  final LoginResponse auth;
  final bool isNewPlayer;
}

class ApiKeyResponse {
  const ApiKeyResponse({
    required this.keyId,
    required this.apiKey,
    required this.createdAt,
    this.description,
  });

  factory ApiKeyResponse.fromJson(Map<String, dynamic> json) => ApiKeyResponse(
    keyId: json['key_id'] as String,
    apiKey: json['api_key'] as String,
    createdAt: json['created_at'] as String,
    description: json['description'] as String?,
  );

  final String keyId;
  final String apiKey;
  final String createdAt;
  final String? description;
}

class ApiKeyListItem {
  const ApiKeyListItem({
    required this.keyId,
    required this.prefix,
    required this.createdAt,
    required this.isRevoked,
    this.description,
  });

  factory ApiKeyListItem.fromJson(Map<String, dynamic> json) => ApiKeyListItem(
    keyId: json['key_id'] as String,
    description: json['description'] as String?,
    prefix: json['prefix'] as String,
    createdAt: json['created_at'] as String,
    isRevoked: json['is_revoked'] as bool,
  );

  final String keyId;
  final String? description;
  final String prefix;
  final String createdAt;
  final bool isRevoked;
}

// ==========================================================================
// Player schemas — `src/modules/api/schemas/player.py`
// ==========================================================================

class PlayerUpdateRequest {
  const PlayerUpdateRequest({this.username, this.email});

  Map<String, dynamic> toJson() => {
    if (username != null) 'username': username,
    if (email != null) 'email': email,
  };

  final String? username;
  final String? email;
}

class PlayerProfileResponse {
  const PlayerProfileResponse({
    required this.playerId,
    required this.username,
    required this.playerType,
    required this.eloRating,
    required this.createdAt,
    this.email,
  });

  factory PlayerProfileResponse.fromJson(Map<String, dynamic> json) =>
      PlayerProfileResponse(
        playerId: json['player_id'] as String,
        username: json['username'] as String,
        playerType: json['player_type'] as String,
        eloRating: json['elo_rating'] as int,
        createdAt: json['created_at'] as String,
        email: json['email'] as String?,
      );

  final String playerId;
  final String username;
  final String playerType;
  final int eloRating;
  final String createdAt;
  final String? email;
}

class UsernameCheckResponse {
  const UsernameCheckResponse({
    required this.available,
    required this.valid,
    this.error,
  });

  factory UsernameCheckResponse.fromJson(Map<String, dynamic> json) =>
      UsernameCheckResponse(
        available: json['available'] as bool,
        valid: json['valid'] as bool,
        error: json['error'] as String?,
      );

  final bool available;
  final bool valid;
  final String? error;
}

class PlayerStatsResponse {
  const PlayerStatsResponse({
    required this.playerId,
    required this.matchesPlayed,
    required this.matchesWon,
    required this.matchesLost,
    required this.matchesDrawn,
    required this.totalScore,
    required this.highestScore,
    required this.longestChain,
    required this.totalGemsMatched,
    required this.winRate,
  });

  factory PlayerStatsResponse.fromJson(Map<String, dynamic> json) =>
      PlayerStatsResponse(
        playerId: json['player_id'] as String,
        matchesPlayed: json['matches_played'] as int,
        matchesWon: json['matches_won'] as int,
        matchesLost: json['matches_lost'] as int,
        matchesDrawn: json['matches_drawn'] as int,
        totalScore: json['total_score'] as int,
        highestScore: json['highest_score'] as int,
        longestChain: json['longest_chain'] as int,
        totalGemsMatched: json['total_gems_matched'] as int,
        winRate: (json['win_rate'] as num).toDouble(),
      );

  final String playerId;
  final int matchesPlayed;
  final int matchesWon;
  final int matchesLost;
  final int matchesDrawn;
  final int totalScore;
  final int highestScore;
  final int longestChain;
  final int totalGemsMatched;
  final double winRate;
}

class LeaderboardEntry {
  const LeaderboardEntry({
    required this.rank,
    required this.playerId,
    required this.username,
    required this.eloRating,
    this.highestScore,
  });

  factory LeaderboardEntry.fromJson(Map<String, dynamic> json) =>
      LeaderboardEntry(
        rank: json['rank'] as int,
        playerId: json['player_id'] as String,
        username: json['username'] as String,
        eloRating: json['elo_rating'] as int,
        highestScore: json['highest_score'] as int?,
      );

  final int rank;
  final String playerId;
  final String username;
  final int eloRating;
  final int? highestScore;
}

class LeaderboardResponse {
  const LeaderboardResponse({
    required this.entries,
    required this.total,
    required this.limit,
    required this.offset,
  });

  factory LeaderboardResponse.fromJson(Map<String, dynamic> json) =>
      LeaderboardResponse(
        entries: (json['entries'] as List<dynamic>)
            .map((e) => LeaderboardEntry.fromJson(e as Map<String, dynamic>))
            .toList(),
        total: json['total'] as int,
        limit: json['limit'] as int,
        offset: json['offset'] as int,
      );

  final List<LeaderboardEntry> entries;
  final int total;
  final int limit;
  final int offset;
}

// ==========================================================================
// Energy schemas — `src/modules/api/schemas/energy.py`
// ==========================================================================

class EnergyResponse {
  const EnergyResponse({
    required this.currentHearts,
    required this.maxHearts,
    required this.isFull,
    required this.dailyStreak,
    this.secondsToNextHeart,
    this.nextHeartAt,
  });

  factory EnergyResponse.fromJson(Map<String, dynamic> json) => EnergyResponse(
    currentHearts: json['current_hearts'] as int,
    maxHearts: json['max_hearts'] as int,
    secondsToNextHeart: json['seconds_to_next_heart'] as int?,
    nextHeartAt: json['next_heart_at'] as String?,
    isFull: json['is_full'] as bool,
    dailyStreak: json['daily_streak'] as int,
  );

  final int currentHearts;
  final int maxHearts;
  final int? secondsToNextHeart;
  final String? nextHeartAt;
  final bool isFull;
  final int dailyStreak;
}

class StreakResponse {
  const StreakResponse({
    required this.currentStreak,
    required this.nextRewardThreshold,
    required this.daysUntilReward,
    required this.rewardHearts,
    this.lastLoginDate,
  });

  factory StreakResponse.fromJson(Map<String, dynamic> json) => StreakResponse(
    currentStreak: json['current_streak'] as int,
    lastLoginDate: json['last_login_date'] as String?,
    nextRewardThreshold: json['next_reward_threshold'] as int,
    daysUntilReward: json['days_until_reward'] as int,
    rewardHearts: json['reward_hearts'] as int,
  );

  final int currentStreak;
  final String? lastLoginDate;
  final int nextRewardThreshold;
  final int daysUntilReward;
  final int rewardHearts;
}

class LoginStreakResponse {
  const LoginStreakResponse({
    required this.streakDay,
    required this.streakContinued,
    required this.streakBroken,
    required this.bonusHeartsGranted,
    required this.energy,
  });

  factory LoginStreakResponse.fromJson(Map<String, dynamic> json) =>
      LoginStreakResponse(
        streakDay: json['streak_day'] as int,
        streakContinued: json['streak_continued'] as bool,
        streakBroken: json['streak_broken'] as bool,
        bonusHeartsGranted: json['bonus_hearts_granted'] as int,
        energy: EnergyResponse.fromJson(json['energy'] as Map<String, dynamic>),
      );

  final int streakDay;
  final bool streakContinued;
  final bool streakBroken;
  final int bonusHeartsGranted;
  final EnergyResponse energy;
}

// ==========================================================================
// Matchmaking schemas — `src/modules/api/schemas/matchmaking.py`
// ==========================================================================

class JoinQueueRequest {
  const JoinQueueRequest({this.poolType = 'mixed'});

  Map<String, dynamic> toJson() => {'pool_type': poolType};

  final String poolType;
}

class QueueEntryResponse {
  const QueueEntryResponse({
    required this.playerId,
    required this.poolType,
    required this.eloRating,
    required this.position,
    required this.joinedAt,
    this.estimatedWaitSeconds,
  });

  factory QueueEntryResponse.fromJson(Map<String, dynamic> json) =>
      QueueEntryResponse(
        playerId: json['player_id'] as String,
        poolType: json['pool_type'] as String,
        eloRating: json['elo_rating'] as int,
        position: json['position'] as int,
        estimatedWaitSeconds: json['estimated_wait_seconds'] as int?,
        joinedAt: json['joined_at'] as String,
      );

  final String playerId;
  final String poolType;
  final int eloRating;
  final int position;
  final int? estimatedWaitSeconds;
  final String joinedAt;
}

class QueueStatusResponse {
  const QueueStatusResponse({
    required this.inQueue,
    this.position,
    this.poolType,
    this.estimatedWaitSeconds,
    this.joinedAt,
  });

  factory QueueStatusResponse.fromJson(Map<String, dynamic> json) =>
      QueueStatusResponse(
        inQueue: json['in_queue'] as bool,
        position: json['position'] as int?,
        poolType: json['pool_type'] as String?,
        estimatedWaitSeconds: json['estimated_wait_seconds'] as int?,
        joinedAt: json['joined_at'] as String?,
      );

  final bool inQueue;
  final int? position;
  final String? poolType;
  final int? estimatedWaitSeconds;
  final String? joinedAt;
}

class QuickMatchRequest {
  const QuickMatchRequest({this.botPlayerId});

  Map<String, dynamic> toJson() => {
    if (botPlayerId != null) 'bot_player_id': botPlayerId,
  };

  final String? botPlayerId;
}

class PoolStatsResponse {
  const PoolStatsResponse({
    required this.poolType,
    required this.playerCount,
    this.averageWaitSeconds,
  });

  factory PoolStatsResponse.fromJson(Map<String, dynamic> json) =>
      PoolStatsResponse(
        poolType: json['pool_type'] as String,
        playerCount: json['player_count'] as int,
        averageWaitSeconds: json['average_wait_seconds'] as int?,
      );

  final String poolType;
  final int playerCount;
  final int? averageWaitSeconds;
}

// ==========================================================================
// Match schemas — `src/modules/api/schemas/match.py`
// ==========================================================================

class MoveRequest {
  const MoveRequest({
    required this.fromRow,
    required this.fromCol,
    required this.toRow,
    required this.toCol,
    required this.timestampMs,
  });

  Map<String, dynamic> toJson() => {
    'from_row': fromRow,
    'from_col': fromCol,
    'to_row': toRow,
    'to_col': toCol,
    'timestamp_ms': timestampMs,
  };

  final int fromRow;
  final int fromCol;
  final int toRow;
  final int toCol;
  final int timestampMs;
}

class PlayerMatchStateResponse {
  const PlayerMatchStateResponse({
    required this.playerId,
    required this.username,
    required this.score,
    required this.movesMade,
    required this.movesRemaining,
    this.isBot = false,
  });

  factory PlayerMatchStateResponse.fromJson(Map<String, dynamic> json) =>
      PlayerMatchStateResponse(
        playerId: json['player_id'] as String,
        username: json['username'] as String,
        score: json['score'] as int,
        movesMade: json['moves_made'] as int,
        movesRemaining: json['moves_remaining'] as int,
        isBot: json['is_bot'] as bool? ?? false,
      );

  final String playerId;
  final String username;
  final int score;
  final int movesMade;
  final int movesRemaining;
  final bool isBot;
}

class MatchStateResponse {
  const MatchStateResponse({
    required this.matchId,
    required this.status,
    required this.matchType,
    required this.player1,
    required this.player2,
    required this.isMyTurn,
    required this.myScore,
    required this.opponentScore,
    this.turnsRemaining,
    this.botHints,
    this.raidResult,
    this.rewardResult,
    this.botToken,
    this.botPlayerId,
    this.opponentIsBot = false,
    this.winnerId,
  });

  factory MatchStateResponse.fromJson(Map<String, dynamic> json) =>
      MatchStateResponse(
        matchId: json['match_id'] as String,
        status: json['status'] as String,
        matchType: json['match_type'] as String,
        player1: PlayerMatchStateResponse.fromJson(
          json['player1'] as Map<String, dynamic>,
        ),
        player2: PlayerMatchStateResponse.fromJson(
          json['player2'] as Map<String, dynamic>,
        ),
        isMyTurn: json['is_my_turn'] as bool,
        myScore: json['my_score'] as int,
        opponentScore: json['opponent_score'] as int,
        turnsRemaining: json['turns_remaining'] as int?,
        botHints: json['bot_hints'] as Map<String, dynamic>?,
        raidResult: json['raid_result'] != null
            ? CardRaidResultResponse.fromJson(
                json['raid_result'] as Map<String, dynamic>,
              )
            : null,
        rewardResult: json['reward_result'] != null
            ? MatchRewardResponse.fromJson(
                json['reward_result'] as Map<String, dynamic>,
              )
            : null,
        botToken: json['bot_token'] as String?,
        botPlayerId: json['bot_player_id'] as String?,
        opponentIsBot: json['opponent_is_bot'] as bool? ?? false,
        winnerId: json['winner_id'] as String?,
      );

  final String matchId;
  final String status;
  final String matchType;
  final PlayerMatchStateResponse player1;
  final PlayerMatchStateResponse player2;
  final bool isMyTurn;
  final int myScore;
  final int opponentScore;
  final int? turnsRemaining;
  final Map<String, dynamic>? botHints;
  final CardRaidResultResponse? raidResult;
  final MatchRewardResponse? rewardResult;
  final String? botToken;
  final String? botPlayerId;
  final bool opponentIsBot;
  final String? winnerId;
}

class MatchSummaryResponse {
  const MatchSummaryResponse({
    required this.matchId,
    required this.status,
    required this.matchType,
    required this.opponentId,
    required this.opponentUsername,
    required this.playerScore,
    required this.opponentScore,
    required this.createdAt,
    this.won,
    this.completedAt,
  });

  factory MatchSummaryResponse.fromJson(Map<String, dynamic> json) =>
      MatchSummaryResponse(
        matchId: json['match_id'] as String,
        status: json['status'] as String,
        matchType: json['match_type'] as String,
        opponentId: json['opponent_id'] as String,
        opponentUsername: json['opponent_username'] as String,
        playerScore: json['player_score'] as int,
        opponentScore: json['opponent_score'] as int,
        won: json['won'] as bool?,
        createdAt: json['created_at'] as String,
        completedAt: json['completed_at'] as String?,
      );

  final String matchId;
  final String status;
  final String matchType;
  final String opponentId;
  final String opponentUsername;
  final int playerScore;
  final int opponentScore;
  final bool? won;
  final String createdAt;
  final String? completedAt;
}

/// Board state from backend. Two parallel grids: `cells` (colors 0-6) and
/// `functions` (gem abilities 0-4, where 0 = neutral).
class BoardStateResponse {
  const BoardStateResponse({
    required this.cells,
    required this.functions,
    required this.size,
    required this.movesMade,
    required this.movesRemaining,
    required this.score,
    required this.hasValidMoves,
  });

  factory BoardStateResponse.fromJson(Map<String, dynamic> json) {
    final cells = (json['cells'] as List<dynamic>)
        .map((row) => (row as List<dynamic>).map((v) => v as int).toList())
        .toList();
    final functionsJson = json['functions'] as List<dynamic>?;
    final functions = functionsJson != null
        ? functionsJson
              .map(
                (row) => (row as List<dynamic>).map((v) => v as int).toList(),
              )
              .toList()
        : List.generate(
            cells.length,
            (_) => List<int>.filled(cells.isEmpty ? 0 : cells[0].length, 0),
          );
    return BoardStateResponse(
      cells: cells,
      functions: functions,
      size: json['size'] as int? ?? 8,
      movesMade: json['moves_made'] as int? ?? 0,
      movesRemaining: json['moves_remaining'] as int? ?? 0,
      score: json['score'] as int? ?? 0,
      hasValidMoves: json['has_valid_moves'] as bool? ?? true,
    );
  }

  final List<List<int>> cells;
  final List<List<int>> functions;
  final int size;
  final int movesMade;
  final int movesRemaining;
  final int score;
  final bool hasValidMoves;
}

/// A special gem that was triggered during a cascade step.
class SpecialActivationResponse {
  const SpecialActivationResponse({
    required this.gemType,
    required this.row,
    required this.col,
    required this.affected,
    this.isMega = false,
    this.megaFunc,
  });

  factory SpecialActivationResponse.fromJson(Map<String, dynamic> json) {
    final affectedJson = json['affected'] as List<dynamic>? ?? [];
    return SpecialActivationResponse(
      gemType: json['gem_type'] as int,
      row: json['row'] as int,
      col: json['col'] as int,
      affected: affectedJson.map((a) {
        final m = a as Map<String, dynamic>;
        return (row: m['row'] as int, col: m['col'] as int);
      }).toList(),
      isMega: json['is_mega'] as bool? ?? false,
      megaFunc: json['mega_func'] as int?,
    );
  }

  final int gemType;
  final int row;
  final int col;
  final List<({int row, int col})> affected;
  final bool isMega;
  final int? megaFunc;
}

/// Two special gems attracted toward a center gem, forming a mega gem.
class SpecialAttractionResponse {
  const SpecialAttractionResponse({
    required this.posARow,
    required this.posACol,
    required this.posBRow,
    required this.posBCol,
    required this.centerRow,
    required this.centerCol,
    required this.funcA,
    required this.funcB,
    required this.megaFunc,
  });

  factory SpecialAttractionResponse.fromJson(Map<String, dynamic> json) =>
      SpecialAttractionResponse(
        posARow: json['pos_a_row'] as int,
        posACol: json['pos_a_col'] as int,
        posBRow: json['pos_b_row'] as int,
        posBCol: json['pos_b_col'] as int,
        centerRow: json['center_row'] as int,
        centerCol: json['center_col'] as int,
        funcA: json['func_a'] as int,
        funcB: json['func_b'] as int,
        megaFunc: json['mega_func'] as int,
      );

  final int posARow;
  final int posACol;
  final int posBRow;
  final int posBCol;
  final int centerRow;
  final int centerCol;
  final int funcA;
  final int funcB;
  final int megaFunc;
}

/// One step in the cascade animation buffer (detect → clear → gravity → fill).
class CascadeStepResponse {
  const CascadeStepResponse({
    required this.stepNumber,
    required this.removals,
    required this.drops,
    required this.spawns,
    this.specialGemCreated,
    this.specialActivations = const [],
    this.specialAttractions = const [],
    this.injectedSpecial,
    this.injectedActivation,
    this.injectedDrops = const [],
    this.injectedSpawns = const [],
  });

  factory CascadeStepResponse.fromJson(Map<String, dynamic> json) {
    final removalsJson = json['removals'] as List<dynamic>? ?? [];
    final dropsJson = json['drops'] as List<dynamic>? ?? [];
    final spawnsJson = json['spawns'] as List<dynamic>? ?? [];
    final specialJson = json['special_gem_created'] as Map<String, dynamic>?;
    final activationsJson = json['special_activations'] as List<dynamic>? ?? [];
    final attractionsJson = json['special_attractions'] as List<dynamic>? ?? [];
    final injectedJson = json['injected_special'] as Map<String, dynamic>?;
    final injectedActJson =
        json['injected_activation'] as Map<String, dynamic>?;
    final injectedDropsJson = json['injected_drops'] as List<dynamic>? ?? [];
    final injectedSpawnsJson = json['injected_spawns'] as List<dynamic>? ?? [];

    return CascadeStepResponse(
      stepNumber: json['step_number'] as int,
      removals: removalsJson.map((r) {
        final m = r as Map<String, dynamic>;
        return (row: m['row'] as int, col: m['col'] as int);
      }).toList(),
      drops: dropsJson.map((d) {
        final m = d as Map<String, dynamic>;
        return (
          gemType: m['gem_type'] as int,
          fromRow: m['from_row'] as int,
          fromCol: m['from_col'] as int,
          toRow: m['to_row'] as int,
          toCol: m['to_col'] as int,
        );
      }).toList(),
      spawns: spawnsJson.map((s) {
        final m = s as Map<String, dynamic>;
        return (
          gemType: m['gem_type'] as int,
          row: m['row'] as int,
          col: m['col'] as int,
        );
      }).toList(),
      specialGemCreated: specialJson != null
          ? (
              row: specialJson['row'] as int,
              col: specialJson['col'] as int,
              gemType: specialJson['gem_type'] as int,
              color: specialJson['color'] as int? ?? 0,
            )
          : null,
      specialActivations: activationsJson
          .map(
            (a) =>
                SpecialActivationResponse.fromJson(a as Map<String, dynamic>),
          )
          .toList(),
      specialAttractions: attractionsJson
          .map(
            (a) =>
                SpecialAttractionResponse.fromJson(a as Map<String, dynamic>),
          )
          .toList(),
      injectedSpecial: injectedJson != null
          ? (
              row: injectedJson['row'] as int,
              col: injectedJson['col'] as int,
              function: injectedJson['function'] as int,
            )
          : null,
      injectedActivation: injectedActJson != null
          ? SpecialActivationResponse.fromJson(injectedActJson)
          : null,
      injectedDrops: injectedDropsJson.map((d) {
        final m = d as Map<String, dynamic>;
        return (
          gemType: m['gem_type'] as int,
          fromRow: m['from_row'] as int,
          fromCol: m['from_col'] as int,
          toRow: m['to_row'] as int,
          toCol: m['to_col'] as int,
        );
      }).toList(),
      injectedSpawns: injectedSpawnsJson.map((s) {
        final m = s as Map<String, dynamic>;
        return (
          gemType: m['gem_type'] as int,
          row: m['row'] as int,
          col: m['col'] as int,
        );
      }).toList(),
    );
  }

  final int stepNumber;
  final List<({int row, int col})> removals;
  final List<({int gemType, int fromRow, int fromCol, int toRow, int toCol})>
  drops;
  final List<({int gemType, int row, int col})> spawns;
  final ({int row, int col, int gemType, int color})? specialGemCreated;
  final List<SpecialActivationResponse> specialActivations;
  final List<SpecialAttractionResponse> specialAttractions;
  final ({int row, int col, int function})? injectedSpecial;
  final SpecialActivationResponse? injectedActivation;
  final List<({int gemType, int fromRow, int fromCol, int toRow, int toCol})>
  injectedDrops;
  final List<({int gemType, int row, int col})> injectedSpawns;
}

/// A card modifier that was applied during a move.
class AppliedModifierResponse {
  const AppliedModifierResponse({
    required this.cardId,
    required this.cardName,
    required this.hook,
    required this.description,
  });

  factory AppliedModifierResponse.fromJson(Map<String, dynamic> json) =>
      AppliedModifierResponse(
        cardId: json['card_id'] as int,
        cardName: json['card_name'] as String,
        hook: json['hook'] as String,
        description: json['description'] as String,
      );

  final int cardId;
  final String cardName;
  final String hook;
  final String description;
}

/// Card raid result from post-match finalization.
class CardRaidResultResponse {
  const CardRaidResultResponse({
    required this.occurred,
    this.stolenCardId,
    this.stolenCardName,
    this.wasShielded = false,
    this.cardUnequipped = false,
    this.blockedByCard = false,
    this.blockedByCardName,
  });

  factory CardRaidResultResponse.fromJson(Map<String, dynamic> json) =>
      CardRaidResultResponse(
        occurred: json['occurred'] as bool,
        stolenCardId: json['stolen_card_id'] as int?,
        stolenCardName: json['stolen_card_name'] as String?,
        wasShielded: json['was_shielded'] as bool? ?? false,
        cardUnequipped: json['card_unequipped'] as bool? ?? false,
        blockedByCard: json['blocked_by_card'] as bool? ?? false,
        blockedByCardName: json['blocked_by_card_name'] as String?,
      );

  final bool occurred;
  final int? stolenCardId;
  final String? stolenCardName;
  final bool wasShielded;
  final bool cardUnequipped;
  final bool blockedByCard;
  final String? blockedByCardName;
}

class RewardCardEntry {
  const RewardCardEntry({
    required this.cardId,
    required this.name,
    required this.rarity,
  });

  factory RewardCardEntry.fromJson(Map<String, dynamic> json) =>
      RewardCardEntry(
        cardId: json['card_id'] as int,
        name: json['name'] as String,
        rarity: json['rarity'] as String,
      );

  final int cardId;
  final String name;
  final String rarity;
}

class MatchRewardResponse {
  const MatchRewardResponse({
    required this.awarded,
    required this.cards,
    required this.tier,
  });

  factory MatchRewardResponse.fromJson(Map<String, dynamic> json) =>
      MatchRewardResponse(
        awarded: json['awarded'] as bool,
        cards: (json['cards'] as List<dynamic>)
            .map((c) => RewardCardEntry.fromJson(c as Map<String, dynamic>))
            .toList(),
        tier: json['tier'] as String,
      );

  final bool awarded;
  final List<RewardCardEntry> cards;
  final String tier;
}

class MoveResultResponse {
  const MoveResultResponse({
    required this.valid,
    required this.scoreGained,
    required this.matchesFound,
    required this.cascades,
    required this.specialGemsCreated,
    required this.matchCompleted,
    required this.matchStatus,
    required this.movesRemaining,
    required this.moveNumber,
    this.newBoard,
    this.cascadeSteps = const [],
    this.appliedModifiers = const [],
    this.raidResult,
    this.rewardResult,
  });

  factory MoveResultResponse.fromJson(
    Map<String, dynamic> json,
  ) => MoveResultResponse(
    valid: json['valid'] as bool,
    scoreGained: json['score_gained'] as int,
    newBoard: json['new_board'] != null
        ? BoardStateResponse.fromJson(json['new_board'] as Map<String, dynamic>)
        : null,
    matchesFound: json['matches_found'] as int,
    cascades: json['cascades'] as int,
    specialGemsCreated: json['special_gems_created'] as int,
    matchCompleted: json['match_completed'] as bool,
    matchStatus: json['match_status'] as String,
    movesRemaining: json['moves_remaining'] as int,
    moveNumber: json['move_number'] as int,
    cascadeSteps:
        (json['cascade_steps'] as List<dynamic>?)
            ?.map(
              (s) => CascadeStepResponse.fromJson(s as Map<String, dynamic>),
            )
            .toList() ??
        const [],
    appliedModifiers:
        (json['applied_modifiers'] as List<dynamic>?)
            ?.map(
              (m) =>
                  AppliedModifierResponse.fromJson(m as Map<String, dynamic>),
            )
            .toList() ??
        const [],
    raidResult: json['raid_result'] != null
        ? CardRaidResultResponse.fromJson(
            json['raid_result'] as Map<String, dynamic>,
          )
        : null,
    rewardResult: json['reward_result'] != null
        ? MatchRewardResponse.fromJson(
            json['reward_result'] as Map<String, dynamic>,
          )
        : null,
  );

  final bool valid;
  final int scoreGained;
  final BoardStateResponse? newBoard;
  final int matchesFound;
  final int cascades;
  final int specialGemsCreated;
  final bool matchCompleted;
  final String matchStatus;
  final int movesRemaining;
  final int moveNumber;
  final List<CascadeStepResponse> cascadeSteps;
  final List<AppliedModifierResponse> appliedModifiers;
  final CardRaidResultResponse? raidResult;
  final MatchRewardResponse? rewardResult;
}

class MoveHistoryEntry {
  const MoveHistoryEntry({
    required this.moveNumber,
    required this.playerId,
    required this.fromRow,
    required this.fromCol,
    required this.toRow,
    required this.toCol,
    required this.scoreGained,
    required this.timestamp,
  });

  factory MoveHistoryEntry.fromJson(Map<String, dynamic> json) =>
      MoveHistoryEntry(
        moveNumber: json['move_number'] as int,
        playerId: json['player_id'] as String,
        fromRow: json['from_row'] as int,
        fromCol: json['from_col'] as int,
        toRow: json['to_row'] as int,
        toCol: json['to_col'] as int,
        scoreGained: json['score_gained'] as int,
        timestamp: json['timestamp'] as String,
      );

  final int moveNumber;
  final String playerId;
  final int fromRow;
  final int fromCol;
  final int toRow;
  final int toCol;
  final int scoreGained;
  final String timestamp;
}

// ==========================================================================
// Vault schemas — `src/modules/api/schemas/vault.py`
// ==========================================================================

class ShieldRequest {
  const ShieldRequest({this.durationHours});

  Map<String, dynamic> toJson() => {
    if (durationHours != null) 'duration_hours': durationHours,
  };

  final int? durationHours;
}

class RaidRequest {
  const RaidRequest({required this.defenderId});

  Map<String, dynamic> toJson() => {'defender_id': defenderId};

  final String defenderId;
}

class ArtifactResponse {
  const ArtifactResponse({
    required this.artifactId,
    required this.artifactTypeId,
    required this.rarity,
    required this.artifactSet,
    required this.name,
    required this.description,
    required this.acquiredAt,
    required this.source,
  });

  factory ArtifactResponse.fromJson(Map<String, dynamic> json) =>
      ArtifactResponse(
        artifactId: json['artifact_id'] as String,
        artifactTypeId: json['artifact_type_id'] as String,
        rarity: json['rarity'] as String,
        artifactSet: json['artifact_set'] as String,
        name: json['name'] as String,
        description: json['description'] as String,
        acquiredAt: json['acquired_at'] as String,
        source: json['source'] as String,
      );

  final String artifactId;
  final String artifactTypeId;
  final String rarity;
  final String artifactSet;
  final String name;
  final String description;
  final String acquiredAt;
  final String source;
}

class ShieldResponse {
  const ShieldResponse({
    required this.isActive,
    this.expiresAt,
    this.remainingHours,
  });

  factory ShieldResponse.fromJson(Map<String, dynamic> json) => ShieldResponse(
    isActive: json['is_active'] as bool,
    expiresAt: json['expires_at'] as String?,
    remainingHours: (json['remaining_hours'] as num?)?.toDouble(),
  );

  final bool isActive;
  final String? expiresAt;
  final double? remainingHours;
}

class RaidResponse {
  const RaidResponse({
    required this.success,
    required this.artifactsStolen,
    required this.defenderId,
    required this.message,
  });

  factory RaidResponse.fromJson(Map<String, dynamic> json) => RaidResponse(
    success: json['success'] as bool,
    artifactsStolen: (json['artifacts_stolen'] as List<dynamic>)
        .map((e) => ArtifactResponse.fromJson(e as Map<String, dynamic>))
        .toList(),
    defenderId: json['defender_id'] as String,
    message: json['message'] as String,
  );

  final bool success;
  final List<ArtifactResponse> artifactsStolen;
  final String defenderId;
  final String message;
}

class CollectionProgressResponse {
  const CollectionProgressResponse({
    required this.setName,
    required this.totalInSet,
    required this.collected,
    required this.completionPercentage,
    required this.missingArtifacts,
  });

  factory CollectionProgressResponse.fromJson(Map<String, dynamic> json) =>
      CollectionProgressResponse(
        setName: json['set_name'] as String,
        totalInSet: json['total_in_set'] as int,
        collected: json['collected'] as int,
        completionPercentage: (json['completion_percentage'] as num).toDouble(),
        missingArtifacts: (json['missing_artifacts'] as List<dynamic>)
            .map((e) => e as String)
            .toList(),
      );

  final String setName;
  final int totalInSet;
  final int collected;
  final double completionPercentage;
  final List<String> missingArtifacts;
}

class RaidTargetResponse {
  const RaidTargetResponse({
    required this.playerId,
    required this.username,
    required this.vaultSize,
    required this.isProtected,
  });

  factory RaidTargetResponse.fromJson(Map<String, dynamic> json) =>
      RaidTargetResponse(
        playerId: json['player_id'] as String,
        username: json['username'] as String,
        vaultSize: json['vault_size'] as int,
        isProtected: json['is_protected'] as bool,
      );

  final String playerId;
  final String username;
  final int vaultSize;
  final bool isProtected;
}

// ==========================================================================
// Event schemas — `src/modules/api/schemas/events.py`
// ==========================================================================

class EventResponse {
  const EventResponse({
    required this.eventId,
    required this.name,
    required this.eventType,
    required this.status,
    required this.startTime,
    required this.endTime,
    required this.currentParticipants,
    this.maxParticipants,
    this.description,
  });

  factory EventResponse.fromJson(Map<String, dynamic> json) => EventResponse(
    eventId: json['event_id'] as String,
    name: json['name'] as String,
    eventType: json['event_type'] as String,
    status: json['status'] as String,
    startTime: json['start_time'] as String,
    endTime: json['end_time'] as String,
    maxParticipants: json['max_participants'] as int?,
    currentParticipants: json['current_participants'] as int,
    description: json['description'] as String?,
  );

  final String eventId;
  final String name;
  final String eventType;
  final String status;
  final String startTime;
  final String endTime;
  final int? maxParticipants;
  final int currentParticipants;
  final String? description;
}

class EventParticipantResponse {
  const EventParticipantResponse({
    required this.eventId,
    required this.playerId,
    required this.score,
    required this.matchesPlayed,
    required this.joinedAt,
    this.rank,
  });

  factory EventParticipantResponse.fromJson(Map<String, dynamic> json) =>
      EventParticipantResponse(
        eventId: json['event_id'] as String,
        playerId: json['player_id'] as String,
        score: json['score'] as int,
        rank: json['rank'] as int?,
        matchesPlayed: json['matches_played'] as int,
        joinedAt: json['joined_at'] as String,
      );

  final String eventId;
  final String playerId;
  final int score;
  final int? rank;
  final int matchesPlayed;
  final String joinedAt;
}

class EventLeaderboardEntryResponse {
  const EventLeaderboardEntryResponse({
    required this.rank,
    required this.playerId,
    required this.username,
    required this.score,
    required this.matchesPlayed,
  });

  factory EventLeaderboardEntryResponse.fromJson(Map<String, dynamic> json) =>
      EventLeaderboardEntryResponse(
        rank: json['rank'] as int,
        playerId: json['player_id'] as String,
        username: json['username'] as String,
        score: json['score'] as int,
        matchesPlayed: json['matches_played'] as int,
      );

  final int rank;
  final String playerId;
  final String username;
  final int score;
  final int matchesPlayed;
}

class EventLeaderboardResponse {
  const EventLeaderboardResponse({
    required this.eventId,
    required this.entries,
    required this.totalParticipants,
    this.playerRank,
  });

  factory EventLeaderboardResponse.fromJson(Map<String, dynamic> json) =>
      EventLeaderboardResponse(
        eventId: json['event_id'] as String,
        entries: (json['entries'] as List<dynamic>)
            .map(
              (e) => EventLeaderboardEntryResponse.fromJson(
                e as Map<String, dynamic>,
              ),
            )
            .toList(),
        totalParticipants: json['total_participants'] as int,
        playerRank: json['player_rank'] as int?,
      );

  final String eventId;
  final List<EventLeaderboardEntryResponse> entries;
  final int totalParticipants;
  final int? playerRank;
}

class PlayerEventStatusResponse {
  const PlayerEventStatusResponse({
    required this.eventId,
    required this.playerId,
    required this.score,
    required this.matchesPlayed,
    required this.isActive,
    this.rank,
  });

  factory PlayerEventStatusResponse.fromJson(Map<String, dynamic> json) =>
      PlayerEventStatusResponse(
        eventId: json['event_id'] as String,
        playerId: json['player_id'] as String,
        score: json['score'] as int,
        rank: json['rank'] as int?,
        matchesPlayed: json['matches_played'] as int,
        isActive: json['is_active'] as bool,
      );

  final String eventId;
  final String playerId;
  final int score;
  final int? rank;
  final int matchesPlayed;
  final bool isActive;
}

// ==========================================================================
// Ads schemas — `src/modules/api/schemas/ads.py`
// ==========================================================================

class AdFreeStatusResponse {
  const AdFreeStatusResponse({
    required this.isAdFree,
    this.reason,
    this.expiresAt,
  });

  factory AdFreeStatusResponse.fromJson(Map<String, dynamic> json) =>
      AdFreeStatusResponse(
        isAdFree: json['is_ad_free'] as bool,
        reason: json['reason'] as String?,
        expiresAt: json['expires_at'] as String?,
      );

  final bool isAdFree;
  final String? reason;
  final String? expiresAt;
}

class InterstitialRequest {
  const InterstitialRequest({required this.trigger, this.matchId});

  Map<String, dynamic> toJson() => {
    'trigger': trigger,
    if (matchId != null) 'match_id': matchId,
  };

  final String trigger;
  final String? matchId;
}

class InterstitialResponse {
  const InterstitialResponse({
    required this.adRequestId,
    required this.shouldShow,
    this.adUnitId,
  });

  factory InterstitialResponse.fromJson(Map<String, dynamic> json) =>
      InterstitialResponse(
        adRequestId: json['ad_request_id'] as String,
        shouldShow: json['should_show'] as bool,
        adUnitId: json['ad_unit_id'] as String?,
      );

  final String adRequestId;
  final bool shouldShow;
  final String? adUnitId;
}

class RewardedVideoResponse {
  const RewardedVideoResponse({
    required this.adRequestId,
    this.adUnitId,
    this.rewardPreview,
  });

  factory RewardedVideoResponse.fromJson(Map<String, dynamic> json) =>
      RewardedVideoResponse(
        adRequestId: json['ad_request_id'] as String,
        adUnitId: json['ad_unit_id'] as String?,
        rewardPreview: json['reward_preview'] as Map<String, dynamic>?,
      );

  final String adRequestId;
  final String? adUnitId;
  final Map<String, dynamic>? rewardPreview;
}

class RewardedVideoCompleteResponse {
  const RewardedVideoCompleteResponse({
    required this.rewardGranted,
    this.rewardType,
    this.rewardAmount,
  });

  factory RewardedVideoCompleteResponse.fromJson(Map<String, dynamic> json) =>
      RewardedVideoCompleteResponse(
        rewardGranted: json['reward_granted'] as bool,
        rewardType: json['reward_type'] as String?,
        rewardAmount: json['reward_amount'] as int?,
      );

  final bool rewardGranted;
  final String? rewardType;
  final int? rewardAmount;
}

// ==========================================================================
// Payments schemas — `src/modules/api/schemas/payments.py`
// ==========================================================================

class InitiatePurchaseRequest {
  const InitiatePurchaseRequest({required this.productId});

  Map<String, dynamic> toJson() => {'product_id': productId};

  final String productId;
}

class ValidatePurchaseRequest {
  const ValidatePurchaseRequest({
    required this.receiptData,
    required this.productId,
    required this.transactionId,
    required this.provider,
  });

  Map<String, dynamic> toJson() => {
    'receipt_data': receiptData,
    'product_id': productId,
    'transaction_id': transactionId,
    'provider': provider,
  };

  final String receiptData;
  final String productId;
  final String transactionId;
  final String provider;
}

class PurchaseIntentResponse {
  const PurchaseIntentResponse({
    required this.intentId,
    required this.productId,
    required this.status,
    required this.createdAt,
  });

  factory PurchaseIntentResponse.fromJson(Map<String, dynamic> json) =>
      PurchaseIntentResponse(
        intentId: json['intent_id'] as String,
        productId: json['product_id'] as String,
        status: json['status'] as String,
        createdAt: json['created_at'] as String,
      );

  final String intentId;
  final String productId;
  final String status;
  final String createdAt;
}

class PurchaseResultResponse {
  const PurchaseResultResponse({
    required this.success,
    required this.productId,
    required this.message,
    this.purchaseId,
  });

  factory PurchaseResultResponse.fromJson(Map<String, dynamic> json) =>
      PurchaseResultResponse(
        success: json['success'] as bool,
        purchaseId: json['purchase_id'] as String?,
        productId: json['product_id'] as String,
        message: json['message'] as String,
      );

  final bool success;
  final String? purchaseId;
  final String productId;
  final String message;
}

class PurchaseStatusResponse {
  const PurchaseStatusResponse({
    required this.isAdFree,
    required this.activePurchases,
    required this.purchaseHistoryCount,
  });

  factory PurchaseStatusResponse.fromJson(Map<String, dynamic> json) =>
      PurchaseStatusResponse(
        isAdFree: json['is_ad_free'] as bool,
        activePurchases: (json['active_purchases'] as List<dynamic>)
            .map((e) => e as Map<String, dynamic>)
            .toList(),
        purchaseHistoryCount: json['purchase_history_count'] as int,
      );

  final bool isAdFree;
  final List<Map<String, dynamic>> activePurchases;
  final int purchaseHistoryCount;
}

// ==========================================================================
// Health — `src/modules/api/routes/health.py`
// ==========================================================================

class HealthResponse {
  const HealthResponse({required this.status, required this.timestamp});

  factory HealthResponse.fromJson(Map<String, dynamic> json) => HealthResponse(
    status: json['status'] as String,
    timestamp: json['timestamp'] as String,
  );

  final String status;
  final String timestamp;
}

// ==========================================================================
// Card schemas — `src/modules/api/routes/cards.py`
// ==========================================================================

class CardDefinitionResponse {
  const CardDefinitionResponse({
    required this.cardId,
    required this.name,
    required this.description,
    required this.rarity,
    required this.cardSet,
    required this.setPosition,
    required this.baseValue,
    required this.tags,
    this.trigger = 'passive',
    this.effect = '',
    this.effectParams = const {},
    this.triggerCondition,
  });

  factory CardDefinitionResponse.fromJson(Map<String, dynamic> json) =>
      CardDefinitionResponse(
        cardId: json['card_id'] as int,
        name: json['name'] as String,
        description: json['description'] as String? ?? '',
        rarity: json['rarity'] as String,
        cardSet: json['card_set'] as String,
        setPosition: json['set_position'] as int,
        baseValue: json['base_value'] as int,
        tags: (json['tags'] as List<dynamic>).map((e) => e as String).toList(),
        trigger: json['trigger'] as String? ?? 'passive',
        effect: json['effect'] as String? ?? '',
        effectParams:
            (json['effect_params'] as Map<String, dynamic>?) ?? const {},
        triggerCondition:
            json['trigger_condition'] as Map<String, dynamic>?,
      );

  final int cardId;
  final String name;
  final String description;
  final String rarity;
  final String cardSet;
  final int setPosition;
  final int baseValue;
  final List<String> tags;
  final String trigger;
  final String effect;
  final Map<String, dynamic> effectParams;
  final Map<String, dynamic>? triggerCondition;
}

class PlayerCardResponse {
  const PlayerCardResponse({
    required this.id,
    required this.cardId,
    required this.definition,
    required this.position,
    required this.level,
    required this.acquiredAt,
    required this.source,
    this.sourceId,
  });

  factory PlayerCardResponse.fromJson(Map<String, dynamic> json) =>
      PlayerCardResponse(
        id: json['id'] as String,
        cardId: json['card_id'] as int,
        definition: CardDefinitionResponse.fromJson(
          json['definition'] as Map<String, dynamic>,
        ),
        position: json['position'] as int,
        level: json['level'] as int,
        acquiredAt: json['acquired_at'] as String,
        source: json['source'] as String,
        sourceId: json['source_id'] as String?,
      );

  final String id;
  final int cardId;
  final CardDefinitionResponse definition;
  final int position;
  final int level;
  final String acquiredAt;
  final String source;
  final String? sourceId;
}

class EquippedLoadoutResponse {
  const EquippedLoadoutResponse({required this.playerId, required this.cards});

  factory EquippedLoadoutResponse.fromJson(Map<String, dynamic> json) =>
      EquippedLoadoutResponse(
        playerId: json['player_id'] as String,
        cards: (json['cards'] as List<dynamic>)
            .map((e) => PlayerCardResponse.fromJson(e as Map<String, dynamic>))
            .toList(),
      );

  final String playerId;
  final List<PlayerCardResponse> cards;
}

class PlayerCardsResponse {
  const PlayerCardsResponse({
    required this.cards,
    required this.total,
    required this.limit,
    required this.offset,
    required this.hasMore,
  });

  factory PlayerCardsResponse.fromJson(Map<String, dynamic> json) =>
      PlayerCardsResponse(
        cards: (json['cards'] as List<dynamic>)
            .map((e) => PlayerCardResponse.fromJson(e as Map<String, dynamic>))
            .toList(),
        total: json['total'] as int,
        limit: json['limit'] as int,
        offset: json['offset'] as int,
        hasMore: json['has_more'] as bool,
      );

  final List<PlayerCardResponse> cards;
  final int total;
  final int limit;
  final int offset;
  final bool hasMore;
}

class MergeResultResponse {
  const MergeResultResponse({
    required this.newCard,
    required this.consumedCardIds,
    required this.sourceRarity,
    required this.targetRarity,
  });

  factory MergeResultResponse.fromJson(Map<String, dynamic> json) =>
      MergeResultResponse(
        newCard: PlayerCardResponse.fromJson(
          json['new_card'] as Map<String, dynamic>,
        ),
        consumedCardIds: (json['consumed_card_ids'] as List<dynamic>)
            .map((e) => e as String)
            .toList(),
        sourceRarity: json['source_rarity'] as String,
        targetRarity: json['target_rarity'] as String,
      );

  final PlayerCardResponse newCard;
  final List<String> consumedCardIds;
  final String sourceRarity;
  final String targetRarity;
}

// ==========================================================================
// Inventory schemas — `src/modules/api/routes/inventory.py`
// ==========================================================================

class MegaInventorySlot {
  const MegaInventorySlot({
    required this.slotIndex,
    required this.megaValue,
    required this.count,
  });

  factory MegaInventorySlot.fromJson(Map<String, dynamic> json) =>
      MegaInventorySlot(
        slotIndex: json['slot_index'] as int,
        megaValue: json['mega_value'] as int,
        count: json['count'] as int,
      );

  final int slotIndex;
  final int megaValue;
  final int count;
}

class MegaInventoryResponse {
  const MegaInventoryResponse({required this.slots});

  factory MegaInventoryResponse.fromJson(Map<String, dynamic> json) =>
      MegaInventoryResponse(
        slots: (json['slots'] as List<dynamic>)
            .map((e) => MegaInventorySlot.fromJson(e as Map<String, dynamic>))
            .toList(),
      );

  final List<MegaInventorySlot> slots;
}

class MegaActivationRequest {
  const MegaActivationRequest({
    required this.slotIndex,
    required this.timestampMs,
    this.source,
  });

  Map<String, dynamic> toJson() => {
    'slot_index': slotIndex,
    'timestamp_ms': timestampMs,
    if (source != null) 'source': source,
  };

  final int slotIndex;
  final int timestampMs;
  final String? source;
}

class CardEquipRequest {
  const CardEquipRequest({required this.cardInstanceId, required this.slot});

  Map<String, dynamic> toJson() => {
    'card_instance_id': cardInstanceId,
    'slot': slot,
  };

  final String cardInstanceId;
  final int slot;
}

class CardUnequipRequest {
  const CardUnequipRequest({required this.cardInstanceId});

  Map<String, dynamic> toJson() => {'card_instance_id': cardInstanceId};

  final String cardInstanceId;
}

class CardReorderRequest {
  const CardReorderRequest({
    required this.cardInstanceId,
    required this.newPosition,
  });

  Map<String, dynamic> toJson() => {
    'card_instance_id': cardInstanceId,
    'new_position': newPosition,
  };

  final String cardInstanceId;
  final int newPosition;
}

// ==========================================================================
// Economy — Gold currency system
// ==========================================================================

/// Backend: `src/modules/api/schemas/economy.py` GoldResponse.
class GoldResponse {
  const GoldResponse({
    required this.balance,
    required this.lifetimeEarned,
    required this.lifetimeSpent,
  });

  factory GoldResponse.fromJson(Map<String, dynamic> json) => GoldResponse(
    balance: json['balance'] as int,
    lifetimeEarned: json['lifetime_earned'] as int,
    lifetimeSpent: json['lifetime_spent'] as int,
  );

  final int balance;
  final int lifetimeEarned;
  final int lifetimeSpent;
}

/// Backend: `src/modules/api/schemas/economy.py` SellResponse.
class SellCardsResponse {
  const SellCardsResponse({
    required this.goldEarned,
    required this.cardsSold,
    required this.cardValues,
    required this.newBalance,
  });

  factory SellCardsResponse.fromJson(Map<String, dynamic> json) =>
      SellCardsResponse(
        goldEarned: json['gold_earned'] as int,
        cardsSold: json['cards_sold'] as int,
        cardValues: (json['card_values'] as List<dynamic>)
            .map((e) => e as int)
            .toList(),
        newBalance: json['new_balance'] as int,
      );

  final int goldEarned;
  final int cardsSold;
  final List<int> cardValues;
  final int newBalance;
}

/// Backend: `src/modules/api/schemas/economy.py` BuyRequest.
class BuyItemRequest {
  const BuyItemRequest({required this.itemId});

  Map<String, dynamic> toJson() => {'item_id': itemId};

  final String itemId;
}

/// Backend: `src/modules/api/schemas/economy.py` BuyResponse.
class BuyItemResponse {
  const BuyItemResponse({
    required this.itemId,
    required this.itemName,
    required this.goldSpent,
    required this.newBalance,
    required this.quantityGranted,
  });

  factory BuyItemResponse.fromJson(Map<String, dynamic> json) =>
      BuyItemResponse(
        itemId: json['item_id'] as String,
        itemName: json['item_name'] as String,
        goldSpent: json['gold_spent'] as int,
        newBalance: json['new_balance'] as int,
        quantityGranted: json['quantity_granted'] as int,
      );

  final String itemId;
  final String itemName;
  final int goldSpent;
  final int newBalance;
  final int quantityGranted;
}

/// Backend: `src/modules/api/schemas/economy.py` MarketplaceItemResponse.
class MarketplaceItemResponse {
  const MarketplaceItemResponse({
    required this.itemId,
    required this.name,
    required this.description,
    required this.category,
    required this.price,
    required this.quantity,
    required this.itemType,
    required this.itemParams,
  });

  factory MarketplaceItemResponse.fromJson(Map<String, dynamic> json) =>
      MarketplaceItemResponse(
        itemId: json['item_id'] as String,
        name: json['name'] as String,
        description: json['description'] as String,
        category: json['category'] as String,
        price: json['price'] as int,
        quantity: json['quantity'] as int,
        itemType: json['item_type'] as String,
        itemParams: json['item_params'] as Map<String, dynamic>,
      );

  final String itemId;
  final String name;
  final String description;
  final String category;
  final int price;
  final int quantity;
  final String itemType;
  final Map<String, dynamic> itemParams;
}

/// Backend: `src/modules/api/schemas/economy.py` MarketplaceResponse.
class MarketplaceListResponse {
  const MarketplaceListResponse({required this.items});

  factory MarketplaceListResponse.fromJson(Map<String, dynamic> json) =>
      MarketplaceListResponse(
        items: (json['items'] as List<dynamic>)
            .map(
              (e) =>
                  MarketplaceItemResponse.fromJson(e as Map<String, dynamic>),
            )
            .toList(),
      );

  final List<MarketplaceItemResponse> items;
}

// ==========================================================================
// Campaign schemas — `src/modules/api/routes/campaign.py`
// ==========================================================================

/// A single obstacle definition in a campaign level.
class ObstacleDefinition {
  const ObstacleDefinition({
    required this.row,
    required this.col,
    required this.func,
  });

  factory ObstacleDefinition.fromJson(Map<String, dynamic> json) =>
      ObstacleDefinition(
        row: json['row'] as int,
        col: json['col'] as int,
        func: json['func'] as int,
      );

  final int row;
  final int col;
  final int func;
}

/// Summary of a campaign level in the levels list.
class CampaignLevelSummary {
  const CampaignLevelSummary({
    required this.level,
    required this.moves,
    required this.gemColors,
    required this.objective,
    required this.isCheckpoint,
    required this.heartCost,
    required this.obstacleCount,
    required this.unlocked,
    this.reward,
  });

  factory CampaignLevelSummary.fromJson(Map<String, dynamic> json) =>
      CampaignLevelSummary(
        level: json['level'] as int,
        moves: json['moves'] as int,
        gemColors: json['gem_colors'] as int? ?? 6,
        objective: json['objective'] as String,
        isCheckpoint: json['is_checkpoint'] as bool? ?? false,
        heartCost: json['heart_cost'] as int? ?? 0,
        obstacleCount: json['obstacle_count'] as int? ?? 0,
        unlocked: json['unlocked'] as bool? ?? false,
        reward: json['reward'] as Map<String, dynamic>?,
      );

  final int level;
  final int moves;
  final int gemColors;
  final String objective;
  final bool isCheckpoint;
  final int heartCost;
  final int obstacleCount;
  final bool unlocked;
  final Map<String, dynamic>? reward;
}

/// Response from GET /campaign/levels — all levels with unlock status.
class CampaignLevelsResponse {
  const CampaignLevelsResponse({
    required this.levels,
    required this.campaignLevel,
    this.activeAttemptId,
  });

  factory CampaignLevelsResponse.fromJson(Map<String, dynamic> json) =>
      CampaignLevelsResponse(
        levels: (json['levels'] as List<dynamic>)
            .map(
              (e) =>
                  CampaignLevelSummary.fromJson(e as Map<String, dynamic>),
            )
            .toList(),
        campaignLevel: json['campaign_level'] as int,
        activeAttemptId: json['active_attempt_id'] as String?,
      );

  final List<CampaignLevelSummary> levels;
  final int campaignLevel;
  final String? activeAttemptId;
}

/// Response from GET /campaign/levels/{id} — full level definition.
class CampaignLevelResponse {
  const CampaignLevelResponse({
    required this.level,
    required this.moves,
    required this.gemColors,
    required this.objective,
    required this.isCheckpoint,
    required this.heartCost,
    required this.obstacles,
    this.reward,
  });

  factory CampaignLevelResponse.fromJson(Map<String, dynamic> json) =>
      CampaignLevelResponse(
        level: json['level'] as int,
        moves: json['moves'] as int,
        gemColors: json['gem_colors'] as int? ?? 6,
        objective: json['objective'] as String,
        isCheckpoint: json['is_checkpoint'] as bool? ?? false,
        heartCost: json['heart_cost'] as int? ?? 0,
        obstacles: (json['obstacles'] as List<dynamic>)
            .map((e) => ObstacleDefinition.fromJson(e as Map<String, dynamic>))
            .toList(),
        reward: json['reward'] as Map<String, dynamic>?,
      );

  final int level;
  final int moves;
  final int gemColors;
  final String objective;
  final bool isCheckpoint;
  final int heartCost;
  final List<ObstacleDefinition> obstacles;
  final Map<String, dynamic>? reward;
}

/// Response from GET /campaign/progress.
class CampaignProgressResponse {
  const CampaignProgressResponse({
    required this.campaignLevel,
    required this.maxLevel,
    this.activeAttemptId,
  });

  factory CampaignProgressResponse.fromJson(Map<String, dynamic> json) =>
      CampaignProgressResponse(
        campaignLevel: json['campaign_level'] as int,
        maxLevel: json['max_level'] as int,
        activeAttemptId: json['active_attempt_id'] as String?,
      );

  final int campaignLevel;
  final int maxLevel;
  final String? activeAttemptId;
}

/// Response from POST /campaign/attempts and GET /campaign/attempts/{id}.
class CampaignAttemptResponse {
  const CampaignAttemptResponse({
    required this.attemptId,
    required this.levelNumber,
    required this.movesRemaining,
    required this.obstaclesRemaining,
    required this.status,
    this.board,
  });

  factory CampaignAttemptResponse.fromJson(Map<String, dynamic> json) =>
      CampaignAttemptResponse(
        attemptId: json['attempt_id'] as String,
        levelNumber: json['level_number'] as int,
        movesRemaining: json['moves_remaining'] as int,
        obstaclesRemaining: json['obstacles_remaining'] as int,
        status: json['status'] as String,
        board: json['board'] != null
            ? BoardStateResponse.fromJson(
                json['board'] as Map<String, dynamic>,
              )
            : null,
      );

  final String attemptId;
  final int levelNumber;
  final int movesRemaining;
  final int obstaclesRemaining;
  final String status;
  final BoardStateResponse? board;
}

/// An obstacle event from a campaign move (transmute or clear).
class ObstacleEvent {
  const ObstacleEvent({
    required this.type,
    required this.row,
    required this.col,
    this.fromFunc,
    this.toFunc,
  });

  factory ObstacleEvent.fromJson(Map<String, dynamic> json) => ObstacleEvent(
    type: json['type'] as String,
    row: json['row'] as int,
    col: json['col'] as int,
    fromFunc: json['from_func'] as int?,
    toFunc: json['to_func'] as int?,
  );

  final String type;
  final int row;
  final int col;
  final int? fromFunc;
  final int? toFunc;
}

/// Response from POST /campaign/attempts/{id}/move.
class CampaignMoveResponse {
  const CampaignMoveResponse({
    required this.valid,
    required this.obstaclesRemaining,
    required this.movesRemaining,
    required this.status,
    this.newBoard,
    this.cascadeSteps = const [],
    this.appliedModifiers = const [],
    this.obstacleEvents = const [],
    this.scoreGained = 0,
    this.reshuffled = false,
  });

  factory CampaignMoveResponse.fromJson(Map<String, dynamic> json) =>
      CampaignMoveResponse(
        valid: json['valid'] as bool,
        newBoard: json['new_board'] != null
            ? BoardStateResponse.fromJson(
                json['new_board'] as Map<String, dynamic>,
              )
            : null,
        cascadeSteps: (json['cascade_steps'] as List<dynamic>?)
                ?.map(
                  (s) =>
                      CascadeStepResponse.fromJson(s as Map<String, dynamic>),
                )
                .toList() ??
            const [],
        appliedModifiers: (json['applied_modifiers'] as List<dynamic>?)
                ?.map(
                  (m) => AppliedModifierResponse.fromJson(
                      m as Map<String, dynamic>),
                )
                .toList() ??
            const [],
        obstaclesRemaining: json['obstacles_remaining'] as int,
        movesRemaining: json['moves_remaining'] as int,
        status: json['status'] as String,
        obstacleEvents: (json['obstacle_events'] as List<dynamic>?)
                ?.map(
                  (e) => ObstacleEvent.fromJson(e as Map<String, dynamic>),
                )
                .toList() ??
            const [],
        scoreGained: json['score_gained'] as int? ?? 0,
        reshuffled: json['reshuffled'] as bool? ?? false,
      );

  final bool valid;
  final BoardStateResponse? newBoard;
  final List<CascadeStepResponse> cascadeSteps;
  final List<AppliedModifierResponse> appliedModifiers;
  final int obstaclesRemaining;
  final int movesRemaining;
  final String status;
  final List<ObstacleEvent> obstacleEvents;
  final int scoreGained;
  final bool reshuffled;
}

/// Response from POST /campaign/attempts/{id}/abandon.
class CampaignAbandonResponse {
  const CampaignAbandonResponse({
    required this.attemptId,
    required this.status,
  });

  factory CampaignAbandonResponse.fromJson(Map<String, dynamic> json) =>
      CampaignAbandonResponse(
        attemptId: json['attempt_id'] as String,
        status: json['status'] as String,
      );

  final String attemptId;
  final String status;
}
