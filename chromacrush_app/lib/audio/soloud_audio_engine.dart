/// Concrete audio engine using flutter_soloud.
///
/// SFX: procedurally synthesized WAVs loaded into SoLoud at init time.
/// Music: loaded from asset files on demand.
/// Falls back silently on init failure (Windows dev, test env).
library;

import 'dart:math';

import 'package:flutter/services.dart' show AssetManifest, rootBundle;
import 'package:flutter_soloud/flutter_soloud.dart';

import '../config/audio_config.dart';
import '../services/audio_engine.dart';
import 'sfx_synth.dart';
import 'sound_bank.dart';

class SoLoudAudioEngine extends AudioEngineBase {
  /// Pre-loaded SFX audio sources, keyed by SoundId.
  final Map<SoundId, AudioSource> _sfxSources = {};

  /// Currently playing music handle + source.
  SoundHandle? _musicHandle;
  AudioSource? _musicSource;
  String? _currentMusicAsset;
  double _musicVolumeBoost = 1.0;

  /// Volume levels.
  double _sfxVolume = kDefaultSfxVolume;
  double _musicVolume = kDefaultMusicVolume;
  double _masterVolume = 1.0;

  /// Mute state.
  bool _muted = false;

  /// Whether SoLoud initialized successfully.
  bool _initialized = false;

  /// Whether the biquad highpass filter has been activated.
  bool _highPassActive = false;

  /// Menu music tracks discovered from assets/menu_music/.
  List<String> _menuTracks = [];
  final _rng = Random();

  @override
  Future<void> initialize() async {
    try {
      await SoLoud.instance.init(
        sampleRate: kAudioSampleRate,
        bufferSize: kAudioBufferSize,
        channels: Channels.stereo,
      );
      _initialized = true;
      // ignore: avoid_print
      print('[AudioEngine] SoLoud initialized successfully');

      // Synthesize and load all SFX.
      await _loadAllSfx();

      // Set initial volume.
      SoLoud.instance.setGlobalVolume(_masterVolume);

      // Enable global DSP filters for spatial depth and punch.
      _setupGlobalFilters();

      // ignore: avoid_print
      print('[AudioEngine] ${_sfxSources.length} SFX loaded');
    } catch (e) {
      // SoLoud may fail on some platforms (test, CI). Fall back silently.
      _initialized = false;
      // ignore: avoid_print
      print('[AudioEngine] SoLoud init FAILED: $e');
    }
  }

  /// Set up global SoLoud filters: light reverb for spatial depth,
  /// compressor for punch and clipping prevention.
  void _setupGlobalFilters() {
    try {
      // Light reverb — makes pops feel like they exist in a space.
      final reverb = SoLoud.instance.filters.freeverbFilter;
      reverb.activate();
      reverb.wet.value = kReverbWet;
      reverb.roomSize.value = kReverbRoomSize;
      reverb.damp.value = kReverbDamp;
      reverb.width.value = kReverbWidth;
      // ignore: avoid_print
      print('[AudioEngine] Freeverb filter active');
    } catch (e) {
      // ignore: avoid_print
      print('[AudioEngine] Freeverb setup failed: $e');
    }

    try {
      // Compressor — prevents clipping during cascades with many
      // simultaneous sounds, adds punch to transients.
      final comp = SoLoud.instance.filters.compressorFilter;
      comp.activate();
      comp.wet.value = kCompressorWet;
      comp.threshold.value = kCompressorThreshold;
      comp.ratio.value = kCompressorRatio;
      comp.attackTime.value = kCompressorAttack;
      comp.releaseTime.value = kCompressorRelease;
      comp.makeupGain.value = kCompressorMakeupGain;
      // ignore: avoid_print
      print('[AudioEngine] Compressor filter active');
    } catch (e) {
      // ignore: avoid_print
      print('[AudioEngine] Compressor setup failed: $e');
    }
  }

  Future<void> _loadAllSfx() async {
    for (final entry in sfxRecipes.entries) {
      try {
        final wav = synthesizeWav(entry.value);
        final source = await SoLoud.instance.loadMem(
          '${entry.key.name}.wav',
          wav,
        );
        _sfxSources[entry.key] = source;
      } catch (e) {
        // ignore: avoid_print
        print('[AudioEngine] Failed to load ${entry.key.name}: $e');
      }
    }
  }

  @override
  Future<void> dispose() async {
    if (!_initialized) return;
    try {
      // Dispose all loaded sources.
      for (final source in _sfxSources.values) {
        await SoLoud.instance.disposeSource(source);
      }
      _sfxSources.clear();
      if (_musicSource != null) {
        await SoLoud.instance.disposeSource(_musicSource!);
        _musicSource = null;
        _musicHandle = null;
      }
      SoLoud.instance.deinit();
      _initialized = false;
    } catch (_) {}
  }

  @override
  void playSfx(SoundId sound, {double pitch = 1.0, double volume = 1.0}) {
    if (!_initialized || _muted) return;
    final source = _sfxSources[sound];
    if (source == null) return;

    try {
      final effectiveVolume = volume * _sfxVolume * _masterVolume;
      SoLoud.instance
          .play(source, volume: effectiveVolume)
          .then((handle) {
            if (pitch != 1.0) {
              SoLoud.instance.setRelativePlaySpeed(handle, pitch);
            }
          })
          .catchError((e) {
            // ignore: avoid_print
            print('[AudioEngine] play error for ${sound.name}: $e');
          });
    } catch (e) {
      // ignore: avoid_print
      print('[AudioEngine] playSfx sync error: $e');
    }
  }

  @override
  String? get currentMusicAsset => _currentMusicAsset;

  @override
  Future<void> discoverMenuTracks() async {
    final manifest = await AssetManifest.loadFromAssetBundle(rootBundle);
    _menuTracks = manifest
        .listAssets()
        .where((key) => key.startsWith(kMenuMusicDir))
        .toList();
    // ignore: avoid_print
    print('[AudioEngine] ${_menuTracks.length} menu music tracks discovered');
  }

  @override
  void playMenuMusic() {
    if (_menuTracks.isEmpty) return;
    // Already playing a menu track — don't restart.
    if (_currentMusicAsset != null &&
        _currentMusicAsset!.startsWith(kMenuMusicDir)) {
      return;
    }
    final track = _menuTracks[_rng.nextInt(_menuTracks.length)];
    playMusic(track);
    _musicVolumeBoost = kMenuMusicVolumeBoost;
    _updateMusicVolume();
  }

  @override
  void playMusic(String assetPath, {bool loop = true}) {
    if (!_initialized || _muted) return;

    // Stop current music (resets boost to 1.0).
    stopMusic();

    _currentMusicAsset = assetPath;
    try {
      SoLoud.instance.loadAsset(assetPath).then((source) {
        _musicSource = source;
        // Activate pitch-shift filter for tempo-without-pitch-change support.
        source.filters.pitchShiftFilter.activate();
        final effectiveVolume = _musicVolume * _masterVolume * _musicVolumeBoost;
        SoLoud.instance
            .play(source, volume: effectiveVolume, looping: loop)
            .then((handle) {
              _musicHandle = handle;
              SoLoud.instance.setProtectVoice(handle, true);
            });
      });
    } catch (_) {}
  }

  @override
  void stopMusic() {
    if (!_initialized) return;
    try {
      if (_musicHandle != null) {
        SoLoud.instance.stop(_musicHandle!);
      }
      if (_musicSource != null) {
        SoLoud.instance.disposeSource(_musicSource!);
      }
    } catch (_) {}
    _musicHandle = null;
    _musicSource = null;
    _currentMusicAsset = null;
    _musicVolumeBoost = 1.0;
  }

  @override
  void setMusicVolume(double volume) {
    _musicVolume = volume.clamp(0.0, 1.0);
    _updateMusicVolume();
  }

  @override
  void setSfxVolume(double volume) {
    _sfxVolume = volume.clamp(0.0, 1.0);
  }

  @override
  void setMasterVolume(double volume) {
    _masterVolume = volume.clamp(0.0, 1.0);
    if (_initialized) {
      try {
        SoLoud.instance.setGlobalVolume(_masterVolume);
      } catch (_) {}
    }
  }

  @override
  bool get isMuted => _muted;

  @override
  set isMuted(bool value) {
    _muted = value;
    if (_muted) {
      stopMusic();
    }
  }

  @override
  void setMusicSpeed(double speed) {
    if (!_initialized || _musicSource == null || _musicHandle == null) return;
    try {
      // timeStretch changes tempo without affecting pitch.
      _musicSource!.filters.pitchShiftFilter.timeStretch(
        _musicHandle!,
        speed.clamp(kMusicSpeedMin, kMusicSpeedMax),
      );
    } catch (_) {}
  }

  @override
  void setMusicHighPass(double frequency) {
    if (!_initialized) return;
    try {
      final biquad = SoLoud.instance.filters.biquadResonantFilter;
      if (frequency <= 0) {
        // Deactivate highpass when frequency is zero.
        if (_highPassActive) {
          biquad.deactivate();
          _highPassActive = false;
        }
        return;
      }
      // Activate on first use.
      if (!_highPassActive) {
        biquad.activate();
        biquad.type.value = kHighPassType;
        biquad.resonance.value = kHighPassResonance;
        _highPassActive = true;
      }
      biquad.frequency.fadeFilterParameter(
        to: frequency.clamp(kHighPassMinFreq, kHighPassMaxFreq),
        time: kHighPassFadeDuration,
      );
    } catch (_) {}
  }

  void _updateMusicVolume() {
    if (!_initialized || _musicHandle == null) return;
    try {
      final effectiveVolume = _musicVolume * _masterVolume * _musicVolumeBoost;
      SoLoud.instance.setVolume(_musicHandle!, effectiveVolume);
    } catch (_) {}
  }
}
