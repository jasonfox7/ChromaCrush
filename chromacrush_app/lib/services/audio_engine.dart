/// Audio engine interface — flutter_soloud wrapper.
///
/// Three logical buses: SFX, Music, Ambient.
/// Concrete implementation using flutter_soloud in Phase 2.
library;

/// Sound identifier for the sound bank.
enum SoundId {
  gemSelect,
  gemSwap,
  invalidSwap,
  matchChime,
  cascadeStep,
  specialActivation,
  fusionFanfare,
  victoryFanfare,
  defeatSting,
  uiTap,
  uiBack,
  raidAlert,
  megaMerge,
  megaActivation,
}

/// Abstract audio engine interface.
abstract class AudioEngineBase {
  Future<void> initialize();
  Future<void> dispose();

  void playSfx(SoundId sound, {double pitch = 1.0, double volume = 1.0});
  void playMusic(String assetPath, {bool loop = true});
  void stopMusic();
  String? get currentMusicAsset;
  Future<void> discoverMenuTracks();
  void playMenuMusic();
  void setMusicVolume(double volume);
  void setSfxVolume(double volume);
  void setMasterVolume(double volume);
  void setMusicSpeed(double speed);
  void setMusicHighPass(double frequency);
  bool get isMuted;
  set isMuted(bool value);
}

/// Stub audio engine — silent. Used during Phase 0-1 and testing.
class StubAudioEngine extends AudioEngineBase {
  bool _muted = false;

  @override
  Future<void> initialize() async {}
  @override
  Future<void> dispose() async {}
  @override
  void playSfx(SoundId sound, {double pitch = 1.0, double volume = 1.0}) {}
  @override
  void playMusic(String assetPath, {bool loop = true}) {}
  @override
  void stopMusic() {}
  @override
  String? get currentMusicAsset => null;
  @override
  Future<void> discoverMenuTracks() async {}
  @override
  void playMenuMusic() {}
  @override
  void setMusicVolume(double volume) {}
  @override
  void setSfxVolume(double volume) {}
  @override
  void setMasterVolume(double volume) {}
  @override
  void setMusicSpeed(double speed) {}
  @override
  void setMusicHighPass(double frequency) {}
  @override
  bool get isMuted => _muted;
  @override
  set isMuted(bool value) => _muted = value;
}
