/// Sound bank — synthesis parameters and cascade pitch ladder.
///
/// Maps SoundId to procedural synthesis recipes. All SFX are generated
/// at runtime via WAV PCM synthesis — no pre-rendered audio files.
library;

export '../config/audio_config.dart'
    show kDefaultSfxVolume, kDefaultMusicVolume;
import '../services/audio_engine.dart';

/// Cascade pitch ladder: C4 → D4 → E4 → F#4 → A4 → C5.
///
/// Each successive cascade step plays at the next pitch ratio,
/// creating an ascending musical scale that rewards chain combos.
const List<double> kCascadePitchLadder = [
  1.0, // C4
  1.122, // D4
  1.260, // E4
  1.414, // F#4
  1.682, // A4
  2.0, // C5
];

/// Synthesis recipe for a procedural sound effect.
///
/// Supports FM synthesis: a modulator oscillator modulates the carrier
/// frequency, creating rich bell/chime/metallic timbres from just two
/// oscillators. Set [fmRatio] > 0 to enable FM mode.
class SfxRecipe {
  const SfxRecipe({
    required this.frequency,
    required this.durationMs,
    this.waveform = Waveform.sine,
    this.attackMs = 5,
    this.decayMs = 50,
    this.sustainLevel = 0.7,
    this.releaseMs = 50,
    this.harmonics = 1,
    this.noiseAmount = 0.0,
    this.fmRatio = 0.0,
    this.fmIndexStart = 0.0,
    this.fmIndexEnd = 0.0,
  });

  /// Base (carrier) frequency in Hz.
  final double frequency;

  /// Total duration in milliseconds.
  final int durationMs;

  /// Waveform type (carrier waveform).
  final Waveform waveform;

  /// ADSR envelope.
  final int attackMs;
  final int decayMs;
  final double sustainLevel;
  final int releaseMs;

  /// Number of additive harmonics (1 = fundamental only).
  /// Ignored when FM mode is active (fmRatio > 0).
  final int harmonics;

  /// Noise mix (0.0 = clean, 1.0 = full noise).
  final double noiseAmount;

  /// FM modulator frequency ratio (modFreq = frequency * fmRatio).
  /// 0.0 = FM disabled (additive mode). Non-integer ratios produce
  /// metallic/bell tones; integer ratios produce harmonic tones.
  final double fmRatio;

  /// FM modulation index at note attack (brightness peak).
  /// Higher = more harmonics = brighter/glassier transient.
  final double fmIndexStart;

  /// FM modulation index at end of decay (sustain brightness).
  /// Lower = mellow ringout. Index decays exponentially from start to end.
  final double fmIndexEnd;
}

/// Waveform types for synthesis.
enum Waveform { sine, square, saw, triangle, noise }

/// Maps each SoundId to its FM synthesis recipe.
///
/// FM ratios: non-integer = metallic/glassy (bell-like), integer = harmonic.
/// Index envelope: high start = bright pop, decays to mellow ring-out.
/// All game-feel pitches in C major pentatonic (C, D, E, G, A).
const Map<SoundId, SfxRecipe> sfxRecipes = {
  // Soft glassy tick — light FM sparkle.
  SoundId.gemSelect: SfxRecipe(
    frequency: 880, // A5
    durationMs: 100,
    attackMs: 1,
    decayMs: 40,
    sustainLevel: 0.0,
    releaseMs: 59,
    fmRatio: 3.01, // Slightly inharmonic → glassy
    fmIndexStart: 4.0,
    fmIndexEnd: 0.5,
  ),

  // Dual-tone sweep — two quick FM pops.
  SoundId.gemSwap: SfxRecipe(
    frequency: 660, // E5
    durationMs: 120,
    attackMs: 2,
    decayMs: 50,
    sustainLevel: 0.0,
    releaseMs: 68,
    fmRatio: 2.0, // Harmonic — clean chime
    fmIndexStart: 6.0,
    fmIndexEnd: 1.0,
  ),

  // Dissonant buzz — inharmonic FM + noise.
  SoundId.invalidSwap: SfxRecipe(
    frequency: 220, // A3
    durationMs: 200,
    attackMs: 3,
    decayMs: 80,
    sustainLevel: 0.2,
    releaseMs: 117,
    noiseAmount: 0.15,
    fmRatio: 7.1, // Highly inharmonic → clangorous
    fmIndexStart: 12.0,
    fmIndexEnd: 5.0,
  ),

  // Glassy bell ping — the core match-3 "pop!" sound.
  // Non-integer ratio gives metallic Candy Crush chime feel.
  SoundId.matchChime: SfxRecipe(
    frequency: 523, // C5
    durationMs: 300,
    attackMs: 2,
    decayMs: 80,
    sustainLevel: 0.0,
    releaseMs: 218,
    fmRatio: 1.41, // √2 — classic bell ratio
    fmIndexStart: 8.0,
    fmIndexEnd: 2.0,
  ),

  // Cascade chime — brighter than match, pitch-shifted at runtime.
  SoundId.cascadeStep: SfxRecipe(
    frequency: 523, // C5 (pitch ladder applied at play time)
    durationMs: 280,
    attackMs: 2,
    decayMs: 70,
    sustainLevel: 0.0,
    releaseMs: 208,
    fmRatio: 2.01, // Near-harmonic — bright but tonal
    fmIndexStart: 10.0,
    fmIndexEnd: 2.5,
  ),

  // Metallic burst — dramatic FM sweep for specials.
  SoundId.specialActivation: SfxRecipe(
    frequency: 784, // G5
    durationMs: 400,
    attackMs: 3,
    decayMs: 120,
    sustainLevel: 0.1,
    releaseMs: 277,
    fmRatio: 3.21, // Inharmonic — metallic shimmer
    fmIndexStart: 14.0,
    fmIndexEnd: 3.0,
  ),

  // Massive bell chord — fusion combo showstopper.
  // High mod index peak → explosive bright attack that decays to warm ring.
  SoundId.fusionFanfare: SfxRecipe(
    frequency: 440, // A4
    durationMs: 1000,
    attackMs: 5,
    decayMs: 250,
    sustainLevel: 0.15,
    releaseMs: 745,
    fmRatio: 4.51, // Very inharmonic — epic bell
    fmIndexStart: 20.0,
    fmIndexEnd: 4.0,
  ),

  // Triumphant ascending bell — victory fanfare.
  SoundId.victoryFanfare: SfxRecipe(
    frequency: 523, // C5
    durationMs: 1200,
    attackMs: 10,
    decayMs: 300,
    sustainLevel: 0.2,
    releaseMs: 890,
    fmRatio: 2.83, // Bright metallic — celebratory
    fmIndexStart: 15.0,
    fmIndexEnd: 3.0,
  ),

  // Low dissonant clang — defeat. Noise + harsh FM.
  SoundId.defeatSting: SfxRecipe(
    frequency: 165, // E3
    durationMs: 600,
    attackMs: 5,
    decayMs: 180,
    sustainLevel: 0.1,
    releaseMs: 415,
    noiseAmount: 0.08,
    fmRatio: 5.73, // Very inharmonic — unsettling
    fmIndexStart: 18.0,
    fmIndexEnd: 8.0,
  ),

  // Tiny tap — subtle FM sparkle.
  SoundId.uiTap: SfxRecipe(
    frequency: 1200, // High ping
    durationMs: 60,
    attackMs: 1,
    decayMs: 25,
    sustainLevel: 0.0,
    releaseMs: 34,
    fmRatio: 1.41,
    fmIndexStart: 3.0,
    fmIndexEnd: 0.5,
  ),

  // Soft chime back — slightly lower, mellow.
  SoundId.uiBack: SfxRecipe(
    frequency: 600,
    durationMs: 100,
    attackMs: 2,
    decayMs: 40,
    sustainLevel: 0.0,
    releaseMs: 58,
    fmRatio: 2.0,
    fmIndexStart: 4.0,
    fmIndexEnd: 1.0,
  ),

  // Alarm bell — urgent, metallic, repeating.
  SoundId.raidAlert: SfxRecipe(
    frequency: 440, // A4
    durationMs: 500,
    attackMs: 3,
    decayMs: 100,
    sustainLevel: 0.3,
    releaseMs: 397,
    noiseAmount: 0.03,
    fmRatio: 3.51, // Bell-like alarm
    fmIndexStart: 12.0,
    fmIndexEnd: 5.0,
  ),

  // Shimmering energy transfer — two specials merging into mega gem.
  // Bright metallic sweep with golden harmonic character.
  SoundId.megaMerge: SfxRecipe(
    frequency: 660, // E5
    durationMs: 500,
    attackMs: 5,
    decayMs: 150,
    sustainLevel: 0.15,
    releaseMs: 345,
    fmRatio: 2.41, // Slightly inharmonic — shimmering
    fmIndexStart: 12.0,
    fmIndexEnd: 3.0,
  ),

  // Massive golden explosion — mega gem activated.
  // Deeper than fusionFanfare, wider FM sweep.
  SoundId.megaActivation: SfxRecipe(
    frequency: 392, // G4
    durationMs: 800,
    attackMs: 3,
    decayMs: 200,
    sustainLevel: 0.1,
    releaseMs: 597,
    fmRatio: 3.71, // Inharmonic — epic golden bell
    fmIndexStart: 18.0,
    fmIndexEnd: 4.0,
  ),
};
