/// Animation timing constants — centralized from 10+ files.
library;

// ---------------------------------------------------------------------------
// Board swap & removal (animation_sequencer.dart, board_layer.dart)
// ---------------------------------------------------------------------------

/// Optimistic swap animation.
const Duration kSwapDuration = Duration(milliseconds: 150);

/// Rubber-band (invalid swap reversal).
const Duration kInvalidSwapDuration = Duration(milliseconds: 250);

/// Gem removal scale-to-zero.
const Duration kRemovalDuration = Duration(milliseconds: 350);

/// Pause after removal so the player sees the gap.
const Duration kRemovalPauseDuration = Duration(milliseconds: 150);

/// Gravity drop per row.
const Duration kDropPerRowDuration = Duration(milliseconds: 120);

/// Board-layer default drop per row (used by animateDrops).
const Duration kBoardDropPerRowDuration = Duration(milliseconds: 80);

/// Pause after drops land.
const Duration kDropPauseDuration = Duration(milliseconds: 100);

/// New gems appearing.
const Duration kFillDuration = Duration(milliseconds: 300);

/// Board-layer default fill duration.
const Duration kBoardFillDuration = Duration(milliseconds: 150);

/// Pause after fill before next cascade check.
const Duration kFillPauseDuration = Duration(milliseconds: 150);

/// Board-layer default removal animation.
const Duration kBoardRemovalDuration = Duration(milliseconds: 200);

/// Settle between cascade steps.
const Duration kCascadeSettleDuration = Duration(milliseconds: 200);

/// Special gem appear animation.
const Duration kSpecialAppearDuration = Duration(milliseconds: 250);

/// Pause after special gem activation.
const Duration kSpecialActivationPause = Duration(milliseconds: 200);

/// Pause after special attraction merge.
const Duration kAttractionSettleDuration = Duration(milliseconds: 200);

/// Board sync settle.
const Duration kBoardSyncSettleDuration = Duration(milliseconds: 250);

// ---------------------------------------------------------------------------
// Cascade animator (cascade_animator.dart)
// ---------------------------------------------------------------------------

/// Default screen shake duration.
const Duration kShakeDuration = Duration(milliseconds: 400);

/// Screen flash duration.
const Duration kFlashDuration = Duration(milliseconds: 150);

/// Zoom pulse duration.
const Duration kZoomPulseDuration = Duration(milliseconds: 300);

/// Fusion shake duration (longer than normal shake).
const Duration kFusionShakeDuration = Duration(milliseconds: 600);

/// Fusion flash delay before flash fires.
const Duration kFusionFlashDelay = Duration(milliseconds: 100);

/// Fusion flash duration.
const Duration kFusionFlashDuration = Duration(milliseconds: 200);

/// Fusion settle pause.
const Duration kFusionSettleDuration = Duration(milliseconds: 200);

/// Fusion zoom pulse duration.
const Duration kFusionZoomDuration = Duration(milliseconds: 300);

// ---------------------------------------------------------------------------
// Special activation shake durations (animation_sequencer.dart)
// ---------------------------------------------------------------------------

/// Normal special activation shake duration.
const Duration kSpecialShakeDuration = Duration(milliseconds: 400);

/// Mega special activation shake duration.
const Duration kMegaShakeDuration = Duration(milliseconds: 500);

/// Chromatic conversion flash-in duration (O combo: gems flash white).
const Duration kChromaFlashDuration = Duration(milliseconds: 200);

/// Chromatic conversion hold duration (bright hold before explosions).
const Duration kChromaFlashHoldDuration = Duration(milliseconds: 150);

/// Cascade step screen shake duration.
const Duration kCascadeShakeDuration = Duration(milliseconds: 300);

// ---------------------------------------------------------------------------
// Gem component (gem_component.dart)
// ---------------------------------------------------------------------------

/// Default gem appear duration.
const Duration kGemAppearDuration = Duration(milliseconds: 150);

/// Default gem removal duration.
const Duration kGemRemovalDuration = Duration(milliseconds: 200);

/// Gem pulse (highlight) duration.
const Duration kGemPulseDuration = Duration(milliseconds: 300);

/// Attraction source pulse.
const Duration kAttractionPulseDuration = Duration(milliseconds: 300);

/// Attraction result pulse.
const Duration kAttractionResultPulseDuration = Duration(milliseconds: 250);

// ---------------------------------------------------------------------------
// Score comparison bars (score_comparison_bars.dart)
// ---------------------------------------------------------------------------

/// Bot score reveal interval minimum (ms).
const int kBotRevealDelayMinMs = 3000;

/// Bot score reveal interval random range (ms).
const int kBotRevealDelayRangeMs = 2001;

/// Score bar fill animation (normal).
const Duration kScoreBarNormalFillDuration = Duration(milliseconds: 300);

/// Score bar fill animation (bot flash bounce).
const Duration kScoreBarFlashFillDuration = Duration(milliseconds: 800);

// ---------------------------------------------------------------------------
// Post-match screens
// ---------------------------------------------------------------------------

/// Title animation duration.
const Duration kTitleAnimDuration = Duration(milliseconds: 500);

/// Buttons fade-in duration.
const Duration kButtonsFadeDuration = Duration(milliseconds: 400);

/// Score count-up duration.
const Duration kScoreCountUpDuration = Duration(milliseconds: 800);

/// Near-miss animation duration.
const Duration kNearMissAnimDuration = Duration(milliseconds: 600);

/// Delay before score panel appears.
const Duration kScorePhaseDelay = Duration(milliseconds: 500);

/// Delay before near-miss text appears (after scores).
const Duration kNearMissPhaseDelay = Duration(milliseconds: 300);

/// Delay before buttons appear (win).
const Duration kButtonsDelayWin = Duration(milliseconds: 2500);

/// Delay before buttons appear (loss/draw).
const Duration kButtonsDelayLoss = Duration(milliseconds: 1500);

/// Opponent score reveal delay.
const Duration kOpponentScoreDelay = Duration(milliseconds: 200);

/// Delay before card reward appears (after scores).
const Duration kRewardPhaseDelay = Duration(milliseconds: 500);

/// Delay before raid result appears (after reward).
const Duration kRaidPhaseDelay = Duration(milliseconds: 500);

// ---------------------------------------------------------------------------
// Bot move preview (bot_move_preview.dart)
// ---------------------------------------------------------------------------

/// Total bot preview animation duration.
const Duration kBotPreviewDuration = Duration(milliseconds: 1500);

/// Gap between consecutive bot previews.
const Duration kBotPreviewGapDuration = Duration(milliseconds: 300);

// ---------------------------------------------------------------------------
// Matchmaking screen
// ---------------------------------------------------------------------------

/// Opponent card slide animation.
const Duration kMatchmakingSlideInDuration = Duration(milliseconds: 400);

/// Hold time before navigation to game.
const Duration kMatchmakingHoldDuration = Duration(seconds: 1);
