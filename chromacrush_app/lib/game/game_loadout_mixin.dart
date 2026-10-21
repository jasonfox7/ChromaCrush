/// Shared loadout and intensity logic for both PvP and campaign games.
///
/// Provides: equipped card loading, mega inventory loading, intensity-driven
/// visual updates, and music track discovery. Applied to both ChromaCrushGame
/// and CampaignGame via `with GameLoadoutMixin`.
library;

import 'dart:async' show Timer;
import 'dart:math' show Random;

import 'package:flame/game.dart';
import 'package:flutter/services.dart' show AssetManifest, rootBundle;

import '../extensions/grid_math.dart';
import '../models/backend_contract.dart';
import '../services/api_client.dart';
import '../services/audio_engine.dart';
import '../services/event_bus.dart';
import '../services/intensity_service.dart';
import 'background_layer.dart';
import 'board_layer.dart';
import 'particle_layer.dart';
import 'player_status_bar.dart';

/// Mixin providing shared loadout, intensity, and music logic for game classes.
///
/// Requires the mixing class to provide the named service/component accessors
/// as abstract getters (satisfied by existing `final` fields in both games).
mixin GameLoadoutMixin on FlameGame {
  // -- Required accessors (satisfied by existing fields on both games) --
  ApiClientBase get apiClient;
  EventBus get eventBus;
  PlayerStatusBar get playerStatusBar;
  BoardLayer get boardLayer;
  ParticleLayer get particleLayer;
  BackgroundLayer get backgroundLayer;
  AudioEngineBase? get audioEngine;
  IntensityService? get intensityService;

  // -- Music discovery (static, shared across all game instances) --

  static final _rng = Random();
  static List<String> _musicTracks = [];

  static Future<void> discoverMusicTracks() async {
    final manifest = await AssetManifest.loadFromAssetBundle(rootBundle);
    _musicTracks = manifest
        .listAssets()
        .where((key) => key.startsWith('assets/music/'))
        .toList();
  }

  /// Start a random music track. Called by both games on board load.
  void playRandomMusicTrack() {
    if (_musicTracks.isNotEmpty) {
      final track = _musicTracks[_rng.nextInt(_musicTracks.length)];
      audioEngine?.playMusic(track);
    }
  }

  // -- Intensity system --

  int _audioThrottleCounter = 0;

  void applyIntensity(double dt) {
    final intensity = intensityService;
    if (intensity == null) return;

    intensity.tick(dt);

    final pulseRate = intensity.gemPulseRate;
    final pulseAmp = intensity.gemGlowAmplitude;
    for (var r = 0; r < kBoardSize; r++) {
      for (var c = 0; c < kBoardSize; c++) {
        final gem = boardLayer.gemAt(r, c);
        if (gem != null) {
          gem.pulseRateOverride = pulseRate;
          gem.pulseAmpOverride = pulseAmp;
        }
      }
    }

    particleLayer.setAmbientDensity(intensity.ambientParticleCount);
    backgroundLayer.setIntensity(intensity.intensity);

    _audioThrottleCounter++;
    if (_audioThrottleCounter >= 60) {
      _audioThrottleCounter = 0;
      audioEngine?.setMusicSpeed(intensity.musicSpeedMultiplier);
      audioEngine?.setMusicHighPass(intensity.musicHighPassFreq);
    }
  }

  // -- Card loadout --

  /// Re-fetch equipped cards from the server and broadcast to HUD.
  Future<void> reloadEquippedCards() async => loadEquippedCards();

  Future<void> loadEquippedCards() async {
    try {
      final response = await apiClient.getEquippedCards();
      if (response.success && response.data != null) {
        eventBus.fire(
          EquippedCardsEvent(
            cards: response.data!.cards
                .map(
                  (c) => EquippedCardInfo(
                    cardId: c.definition.cardId,
                    rarity: c.definition.rarity,
                  ),
                )
                .toList(),
          ),
        );

        _startPeriodicShuffleTimers(response.data!.cards);
      }
    } catch (_) {
      // Non-critical — HUD just won't show runes.
    }
  }

  // -- Periodic shuffle timers (Void Instability, Tremor, Earthquake) --

  final List<Timer> _periodicShuffleTimers = [];

  void _startPeriodicShuffleTimers(List<PlayerCardResponse> cards) {
    cancelPeriodicShuffleTimers();
    for (final card in cards) {
      if (card.definition.effect != 'board_shuffle') continue;
      final interval =
          card.definition.triggerCondition?['interval_seconds'] as int?;
      if (interval == null || interval <= 0) continue;
      _periodicShuffleTimers.add(
        Timer.periodic(
          Duration(seconds: interval),
          (_) => onPeriodicShuffleTriggered(card.definition.name),
        ),
      );
    }
  }

  // -- Selection handling --

  /// Clear all gem selections, then highlight a specific gem.
  ///
  /// Shared by both PvP and campaign games. Wire to
  /// `inputHandler.onSelectionChanged` in `onLoad`.
  void handleSelectionChanged(int? row, int? col) {
    for (var r = 0; r < kBoardSize; r++) {
      for (var c = 0; c < kBoardSize; c++) {
        boardLayer.gemAt(r, c)?.setSelected(false);
      }
    }
    if (row != null && col != null) {
      boardLayer.gemAt(row, col)?.setSelected(true);
    }
  }

  void cancelPeriodicShuffleTimers() {
    for (final t in _periodicShuffleTimers) {
      t.cancel();
    }
    _periodicShuffleTimers.clear();
  }

  /// Override in each game to handle the periodic shuffle API call.
  void onPeriodicShuffleTriggered(String cardName) {}

  // -- Mega gem inventory --

  Future<void> loadMegaInventory() async {
    try {
      final response = await apiClient.getMegaInventory();
      if (response.success && response.data != null) {
        for (final slot in response.data!.slots) {
          if (slot.slotIndex >= 0 && slot.slotIndex <= 4) {
            playerStatusBar.setMegaCount(slot.slotIndex, slot.count);
          }
        }
      }
    } catch (_) {
      // Non-critical — status bar shows 0 counts.
    }
  }
}
