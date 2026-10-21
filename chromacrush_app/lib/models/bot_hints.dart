/// Typed DTOs for bot hints returned in MatchStateResponse.
///
/// Matches the JSON shape from `src/modules/api/adapters/bot_hints.py`.
/// The backend serializes `MatchBotHints` as a nested dict keyed by
/// `best_moves`, `board_analysis`, and `strategic_context`.
library;

/// A valid move with its estimated score.
class ValidMoveHint {
  const ValidMoveHint({
    required this.fromRow,
    required this.fromCol,
    required this.toRow,
    required this.toCol,
    required this.estimatedScore,
  });

  factory ValidMoveHint.fromJson(Map<String, dynamic> json) => ValidMoveHint(
    fromRow: json['from_row'] as int,
    fromCol: json['from_col'] as int,
    toRow: json['to_row'] as int,
    toCol: json['to_col'] as int,
    estimatedScore: json['estimated_score'] as int,
  );

  final int fromRow;
  final int fromCol;
  final int toRow;
  final int toCol;
  final int estimatedScore;
}

/// A move ranked by expected value with cascade and special gem info.
class RankedMove {
  const RankedMove({
    required this.move,
    required this.expectedScore,
    required this.cascadePotential,
    required this.specialGemChance,
  });

  factory RankedMove.fromJson(Map<String, dynamic> json) => RankedMove(
    move: ValidMoveHint.fromJson(json['move'] as Map<String, dynamic>),
    expectedScore: json['expected_score'] as int,
    cascadePotential: json['cascade_potential'] as String,
    specialGemChance: (json['special_gem_chance'] as num).toDouble(),
  );

  final ValidMoveHint move;
  final int expectedScore;
  final String cascadePotential; // "low", "medium", "high"
  final double specialGemChance;
}

/// Analysis of the current board state.
class BoardAnalysis {
  const BoardAnalysis({
    required this.gemDistribution,
    required this.specialGemsAvailable,
    required this.chainOpportunities,
    required this.boardVolatility,
  });

  factory BoardAnalysis.fromJson(Map<String, dynamic> json) => BoardAnalysis(
    gemDistribution: (json['gem_distribution'] as Map<String, dynamic>).map(
      (k, v) => MapEntry(k, v as int),
    ),
    specialGemsAvailable: json['special_gems_available'] as int,
    chainOpportunities: json['chain_opportunities'] as int,
    boardVolatility: json['board_volatility'] as String,
  );

  final Map<String, int> gemDistribution;
  final int specialGemsAvailable;
  final int chainOpportunities;
  final String boardVolatility; // "stable", "moderate", "volatile"
}

/// Strategic situation analysis.
class StrategicContext {
  const StrategicContext({
    required this.scoreDifferential,
    required this.recommendedStrategy,
    required this.riskTolerance,
    required this.gamePhase,
  });

  factory StrategicContext.fromJson(Map<String, dynamic> json) =>
      StrategicContext(
        scoreDifferential: json['score_differential'] as int,
        recommendedStrategy: json['recommended_strategy'] as String,
        riskTolerance: json['risk_tolerance'] as String,
        gamePhase: json['game_phase'] as String,
      );

  final int scoreDifferential;
  final String recommendedStrategy; // "aggressive", "defensive", "balanced"
  final String riskTolerance; // "low", "medium", "high"
  final String gamePhase; // "early", "mid", "late"
}

/// Complete bot hints for a match state response.
class BotHints {
  const BotHints({
    required this.bestMoves,
    required this.boardAnalysis,
    required this.strategicContext,
  });

  factory BotHints.fromJson(Map<String, dynamic> json) => BotHints(
    bestMoves: (json['best_moves'] as List<dynamic>)
        .map((e) => RankedMove.fromJson(e as Map<String, dynamic>))
        .toList(),
    boardAnalysis: BoardAnalysis.fromJson(
      json['board_analysis'] as Map<String, dynamic>,
    ),
    strategicContext: StrategicContext.fromJson(
      json['strategic_context'] as Map<String, dynamic>,
    ),
  );

  final List<RankedMove> bestMoves;
  final BoardAnalysis boardAnalysis;
  final StrategicContext strategicContext;
}
