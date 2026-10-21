/// Data models for the offline tutorial script.
///
/// Parses the enriched JSON produced by `board enrich-tutorial`.
/// Reuses [BoardStateResponse] and [MoveResultResponse] from
/// [backend_contract.dart] — no modifications to those classes.
library;

import 'backend_contract.dart';

class TutorialScript {
  const TutorialScript({
    required this.seed,
    required this.initialBoard,
    required this.steps,
  });

  factory TutorialScript.fromJson(Map<String, dynamic> json) {
    return TutorialScript(
      seed: json['seed'] as int,
      initialBoard: BoardStateResponse.fromJson(
        json['initial_board'] as Map<String, dynamic>,
      ),
      steps: (json['steps'] as List<dynamic>)
          .map((s) => TutorialStep.fromJson(s as Map<String, dynamic>))
          .toList(),
    );
  }

  final int seed;
  final BoardStateResponse initialBoard;
  final List<TutorialStep> steps;
}

class TutorialStep {
  const TutorialStep({
    required this.step,
    required this.fromRow,
    required this.fromCol,
    required this.toRow,
    required this.toCol,
    required this.coachText,
    required this.boardBefore,
    required this.boardAfter,
    required this.moveResult,
  });

  factory TutorialStep.fromJson(Map<String, dynamic> json) {
    final move = json['move'] as Map<String, dynamic>;
    return TutorialStep(
      step: json['step'] as int,
      fromRow: move['from_row'] as int,
      fromCol: move['from_col'] as int,
      toRow: move['to_row'] as int,
      toCol: move['to_col'] as int,
      coachText: json['coach_text'] as String? ?? '',
      boardBefore: BoardStateResponse.fromJson(
        json['board_before'] as Map<String, dynamic>,
      ),
      boardAfter: BoardStateResponse.fromJson(
        json['board_after'] as Map<String, dynamic>,
      ),
      moveResult: MoveResultResponse.fromJson(
        json['move_result'] as Map<String, dynamic>,
      ),
    );
  }

  final int step;
  final int fromRow;
  final int fromCol;
  final int toRow;
  final int toCol;
  final String coachText;
  final BoardStateResponse boardBefore;
  final BoardStateResponse boardAfter;
  final MoveResultResponse moveResult;
}
