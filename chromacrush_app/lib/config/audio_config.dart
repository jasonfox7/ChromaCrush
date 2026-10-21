/// Audio configuration constants — centralized from 3 files.
library;

// ---------------------------------------------------------------------------
// SoLoud engine init (soloud_audio_engine.dart)
// ---------------------------------------------------------------------------

/// Audio sample rate for SoLoud and WAV synthesis.
const int kAudioSampleRate = 44100;

/// SoLoud audio buffer size.
const int kAudioBufferSize = 2048;

// ---------------------------------------------------------------------------
// Volume defaults (sound_bank.dart)
// ---------------------------------------------------------------------------

/// Default SFX volume (0.0-1.0).
const double kDefaultSfxVolume = 0.8;

/// Default music volume (0.0-1.0).
const double kDefaultMusicVolume = 0.4;

// ---------------------------------------------------------------------------
// Freeverb filter (soloud_audio_engine.dart)
// ---------------------------------------------------------------------------

/// Freeverb wet mix (subtle room feel).
const double kReverbWet = 0.12;

/// Freeverb room size.
const double kReverbRoomSize = 0.3;

/// Freeverb damping (high-frequency rolloff).
const double kReverbDamp = 0.7;

/// Freeverb stereo width.
const double kReverbWidth = 0.8;

// ---------------------------------------------------------------------------
// Compressor filter (soloud_audio_engine.dart)
// ---------------------------------------------------------------------------

/// Compressor wet mix.
const double kCompressorWet = 1.0;

/// Compressor threshold in dB.
const double kCompressorThreshold = -12.0;

/// Compressor ratio.
const double kCompressorRatio = 4.0;

/// Compressor attack time in ms.
const double kCompressorAttack = 5.0;

/// Compressor release time in ms.
const double kCompressorRelease = 100.0;

/// Compressor makeup gain in dB.
const double kCompressorMakeupGain = 3.0;

// ---------------------------------------------------------------------------
// Highpass filter (soloud_audio_engine.dart)
// ---------------------------------------------------------------------------

/// Biquad resonant filter type for highpass mode.
const double kHighPassType = 1.0;

/// Biquad resonant filter Q for highpass mode.
const double kHighPassResonance = 1.0;

/// Minimum highpass frequency clamp.
const double kHighPassMinFreq = 20.0;

/// Maximum highpass frequency clamp.
const double kHighPassMaxFreq = 8000.0;

/// Highpass frequency fade transition duration.
const Duration kHighPassFadeDuration = Duration(milliseconds: 200);

// ---------------------------------------------------------------------------
// Music speed clamping (soloud_audio_engine.dart)
// ---------------------------------------------------------------------------

/// Minimum music speed multiplier.
const double kMusicSpeedMin = 0.5;

/// Maximum music speed multiplier.
const double kMusicSpeedMax = 2.0;

// ---------------------------------------------------------------------------
// Menu music (main.dart, game_container.dart)
// ---------------------------------------------------------------------------

/// Asset directory for menu background music (auto-discovered, random pick).
const String kMenuMusicDir = 'assets/menu_music/';

/// Volume boost for menu music (menu track is quieter than game tracks).
const double kMenuMusicVolumeBoost = 1.8;

// ---------------------------------------------------------------------------
// Audio update throttle (chroma_crush_game.dart)
// ---------------------------------------------------------------------------

/// Frames between music filter parameter updates (~1Hz at 60fps).
const int kAudioThrottleFrames = 60;
