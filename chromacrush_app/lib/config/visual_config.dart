/// Visual effects and rendering constants — centralized from 5 files.
library;

import 'dart:ui';

// ---------------------------------------------------------------------------
// Particle system (particle_layer.dart)
// ---------------------------------------------------------------------------

/// Global particle budget.
const int kParticleBudget = 500;

// ---------------------------------------------------------------------------
// Background layer (background_layer.dart)
// ---------------------------------------------------------------------------

/// Maximum simultaneous ripple sources.
const int kMaxRipples = 8;

/// Ripple lifetime in seconds.
const double kRippleLifetime = 2.0;

/// Ripple expansion speed (pixels per second).
const double kRippleSpeed = 300.0;

/// Fallback background color (matches ChromaCrushGame.backgroundColor).
const Color kBackgroundFallbackColor = Color(0xFF0D0D14);

/// Calm tint (low intensity) — cool purple.
const Color kBackgroundCalmTint = Color(0xFFAA77DD);

/// Storm tint (high intensity) — warm amber.
const Color kBackgroundStormTint = Color(0xFFDD8844);

/// Background scroll base speed multiplier.
const double kBackgroundBaseSpeed = 0.3;

/// Background intensity speed addition.
const double kBackgroundIntensitySpeed = 0.7;

/// Background layer scroll velocities (px/sec before speed multiplier).
const double kBgLayer1SpeedX = 8.0;
const double kBgLayer1SpeedY = 4.0;
const double kBgLayer2SpeedX = -12.0;
const double kBgLayer2SpeedY = 3.0;
const double kBgLayer3SpeedX = 7.0;
const double kBgLayer3SpeedY = -10.0;

/// Ripple ring inner offset (pixels behind leading edge).
const double kRippleInnerOffset = 60.0;

// ---------------------------------------------------------------------------
// Cascade effects (cascade_animator.dart)
// ---------------------------------------------------------------------------

/// Default screen shake max displacement (pixels).
const double kDefaultShakeDisplacement = 8.0;

/// Shake frequency (Hz).
const double kShakeFrequency = 30.0;

/// Default flash peak alpha.
const double kFlashPeakAlpha = 0.4;

/// Zoom pulse peak scale.
const double kZoomPulseScale = 1.03;

/// Fusion shake displacement.
const double kFusionShakeDisplacement = 12.0;

/// Fusion flash peak alpha.
const double kFusionFlashPeakAlpha = 0.5;

/// Fusion flash color.
const Color kFusionFlashColor = Color(0xFFFFD700);

/// Normal special activation shake displacement.
const double kSpecialShakeDisplacement = 6.0;

/// Mega special activation shake displacement.
const double kMegaShakeDisplacement = 10.0;

// ---------------------------------------------------------------------------
// Gem rendering (gem_component.dart)
// ---------------------------------------------------------------------------

/// Default gem shader pulse rate (Hz).
const double kDefaultGemPulseRate = 1.5;

/// Default gem shader pulse amplitude.
const double kDefaultGemPulseAmplitude = 0.3;

/// Default gem shader brightness.
const double kDefaultGemBrightness = 1.0;

/// Default gem glow radius.
const double kDefaultGemGlowRadius = 0.3;

/// Gem pulse animation peak scale.
const double kGemPulsePeakScale = 1.2;

/// Gentle pulse scale for protected gems during removal phase.
const double kProtectedPulsePeakScale = 1.1;

/// Glow blur sigma.
const double kGemGlowBlurSigma = 4.0;

/// Extra padding around gem render rect for SDF glow falloff (pixels per side).
const double kGemGlowPadding = 10.0;

// ---------------------------------------------------------------------------
// Player status bar (player_status_bar.dart)
// ---------------------------------------------------------------------------

/// Status bar height as multiple of board cellSize.
const double kStatusBarHeightRatio = 1.8;

/// Gap between status bar and board top as fraction of cellSize.
const double kStatusBarGapRatio = 0.21;

/// Status bar gem size as fraction of board cellSize.
const double kStatusGemRatio = 1.0;

/// Status bar background color (matches bot preview style).
const Color kStatusBarBgColor = Color(0xCC14142A);

/// Count badge text color for zero-count slots.
const Color kCountZeroColor = Color(0x66FFFFFF);

/// Count badge text color for available slots.
const Color kCountAvailableColor = Color(0xFFFFD700);

// ---------------------------------------------------------------------------
// Elastic bounce (flame_effects_ext.dart)
// ---------------------------------------------------------------------------

/// Default elastic overshoot fraction.
const double kElasticOvershoot = 0.15;

/// Default elastic bounce count.
const int kElasticBounces = 2;

/// Default elastic decay rate.
const double kElasticDecay = 4.0;
