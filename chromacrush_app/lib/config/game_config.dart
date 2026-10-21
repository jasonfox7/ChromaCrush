/// Gameplay configuration constants — centralized from 7 files.
library;

// ---------------------------------------------------------------------------
// Input (input_handler.dart)
// ---------------------------------------------------------------------------

/// Minimum drag distance to register as a swipe (logical pixels).
const double kSwipeThreshold = 22.0;

// ---------------------------------------------------------------------------
// Bot timing curves (bot_player_service.dart)
// ---------------------------------------------------------------------------

/// Bot move delay range per difficulty (min ms, range ms).
const int kBotEasyDelayMinMs = 3000;
const int kBotEasyDelayRangeMs = 2001;

const int kBotMediumDelayMinMs = 2000;
const int kBotMediumDelayRangeMs = 2001;

const int kBotHardDelayMinMs = 1500;
const int kBotHardDelayRangeMs = 1501;

// ---------------------------------------------------------------------------
// Score comparison bars (score_comparison_bars.dart)
// ---------------------------------------------------------------------------

/// Bar width in logical pixels.
const double kScoreBarWidth = 14.0;

/// Gap between bar and board.
const double kScoreBarGap = 6.0;

/// Initial dynamic max score ceiling.
const int kScoreInitialMax = 5000;

/// Score bar expansion threshold (fraction of max).
const double kScoreExpansionThreshold = 0.75;

// ---------------------------------------------------------------------------
// Intensity system (intensity_service.dart)
// ---------------------------------------------------------------------------

/// Cascade decay timer duration (seconds).
const double kCascadeDecaySeconds = 3.0;

/// Intensity change threshold for notification.
const double kIntensityNotifyThreshold = 0.02;

/// Intensity output ranges.
const double kGemPulseRateMin = 1.0;
const double kGemPulseRateRange = 1.5;

const double kGemGlowAmpMin = 0.05;
const double kGemGlowAmpRange = 0.35;

const int kAmbientParticleMax = 50;

const double kVignetteAlphaMax = 0.3;

const double kMusicSpeedRange = 0.3;

const double kMusicHighPassMax = 800.0;

/// Intensity factor weights.
const double kMovesFactorWeight = 0.4;
const double kScoreFactorWeight = 0.3;
const double kCascadeFactorWeight = 0.2;

// ---------------------------------------------------------------------------
// Bot move preview (bot_move_preview.dart)
// ---------------------------------------------------------------------------

/// Preview width (logical pixels).
const double kBotPreviewWidth = 240.0;

/// Mini grid cell size.
const double kBotPreviewCellSize = 28.0;

/// Mini grid cell spacing.
const double kBotPreviewCellSpacing = 1.5;

// ---------------------------------------------------------------------------
// Glass panel defaults (glass_panel.dart)
// ---------------------------------------------------------------------------

/// Default glass panel border radius.
const double kGlassBorderRadius = 16.0;

/// Default glass panel blur sigma.
const double kGlassBlurSigma = 20.0;

/// Default glass panel padding.
const double kGlassPadding = 12.0;
