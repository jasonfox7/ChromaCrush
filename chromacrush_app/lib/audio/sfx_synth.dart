/// Procedural SFX synthesis — FM synthesis + WAV PCM generation.
///
/// Each SoundId has a synthesis recipe (sound_bank.dart) that describes
/// carrier frequency, FM modulation parameters, ADSR envelope, and noise.
/// This module renders those recipes into raw 16-bit PCM WAV byte arrays
/// that can be loaded directly into SoLoud via loadMem.
///
/// FM synthesis: a modulator oscillator modulates the carrier frequency,
/// creating rich bell/chime/metallic timbres from just two oscillators.
/// Non-integer mod ratios → metallic/glassy; integer → harmonic/clean.
library;

import 'dart:math';
import 'dart:typed_data';

import '../config/audio_config.dart';
import 'sound_bank.dart';

/// Synthesize a WAV byte array from an [SfxRecipe].
///
/// Returns a complete WAV file as Uint8List, ready for SoLoud.loadMem().
Uint8List synthesizeWav(SfxRecipe recipe) {
  final numSamples = (kAudioSampleRate * recipe.durationMs / 1000).round();
  final samples = Float64List(numSamples);
  final rng = Random(recipe.frequency.toInt());
  final useFm = recipe.fmRatio > 0 && recipe.fmIndexStart > 0;

  for (var i = 0; i < numSamples; i++) {
    final t = i / kAudioSampleRate;
    var sample = 0.0;

    if (useFm) {
      // FM synthesis mode.
      sample = _fmSample(recipe, t, i, numSamples);
    } else {
      // Additive harmonics mode (legacy).
      for (var h = 1; h <= recipe.harmonics; h++) {
        final freq = recipe.frequency * h;
        final harmonicAmp = 1.0 / h;
        sample += harmonicAmp * _waveform(recipe.waveform, freq, t);
      }
      if (recipe.harmonics > 1) {
        sample /= _harmonicSum(recipe.harmonics);
      }
    }

    // Mix noise.
    if (recipe.noiseAmount > 0) {
      final noise = (rng.nextDouble() * 2 - 1);
      sample = sample * (1 - recipe.noiseAmount) + noise * recipe.noiseAmount;
    }

    // Apply ADSR envelope with exponential decay.
    final envelope = _adsrExp(
      i,
      numSamples,
      kAudioSampleRate,
      recipe.attackMs,
      recipe.decayMs,
      recipe.sustainLevel,
      recipe.releaseMs,
    );
    samples[i] = sample * envelope;
  }

  return _encodeWav(samples, kAudioSampleRate);
}

/// FM synthesis: carrier modulated by a sine modulator.
///
/// output = sin(2π * carrierFreq * t + modIndex(t) * sin(2π * modFreq * t))
///
/// modIndex decays exponentially from fmIndexStart to fmIndexEnd over the
/// note duration, creating a bright transient that mellows into a ring-out.
double _fmSample(
  SfxRecipe recipe,
  double t,
  int sampleIndex,
  int totalSamples,
) {
  final carrierFreq = recipe.frequency;
  final modFreq = carrierFreq * recipe.fmRatio;

  // Exponential decay of modulation index over note duration.
  final progress = sampleIndex / totalSamples;
  final indexRange = recipe.fmIndexStart - recipe.fmIndexEnd;
  final modIndex = recipe.fmIndexEnd + indexRange * exp(-progress * 4.0);

  // FM formula: carrier phase modulated by modulator.
  final modSignal = sin(2 * pi * modFreq * t);
  return sin(2 * pi * carrierFreq * t + modIndex * modSignal);
}

/// Generate a single waveform sample.
double _waveform(Waveform type, double freq, double t) {
  final phase = (freq * t) % 1.0;
  return switch (type) {
    Waveform.sine => sin(2 * pi * freq * t),
    Waveform.square => phase < 0.5 ? 1.0 : -1.0,
    Waveform.saw => 2.0 * phase - 1.0,
    Waveform.triangle => 4.0 * (phase < 0.5 ? phase : 1.0 - phase) - 1.0,
    Waveform.noise => Random().nextDouble() * 2 - 1,
  };
}

/// Sum of 1/h for h=1..n (for normalization).
double _harmonicSum(int n) {
  var sum = 0.0;
  for (var h = 1; h <= n; h++) {
    sum += 1.0 / h;
  }
  return sum;
}

/// ADSR envelope with exponential decay and release curves.
///
/// Exponential curves create punchier transients and more natural fade-outs
/// compared to linear ramps.
double _adsrExp(
  int sampleIndex,
  int totalSamples,
  int sampleRate,
  int attackMs,
  int decayMs,
  double sustainLevel,
  int releaseMs,
) {
  final attackSamples = (sampleRate * attackMs / 1000).round();
  final decaySamples = (sampleRate * decayMs / 1000).round();
  final releaseSamples = (sampleRate * releaseMs / 1000).round();
  final releaseStart = totalSamples - releaseSamples;

  if (sampleIndex < attackSamples) {
    // Attack: 0 → 1 (linear — keeps the snap).
    return attackSamples > 0 ? sampleIndex / attackSamples : 1.0;
  } else if (sampleIndex < attackSamples + decaySamples) {
    // Decay: 1 → sustainLevel (exponential curve).
    final t = (sampleIndex - attackSamples) / decaySamples;
    return sustainLevel + (1.0 - sustainLevel) * exp(-t * 4.0);
  } else if (sampleIndex < releaseStart) {
    // Sustain.
    return sustainLevel;
  } else {
    // Release: sustainLevel → 0 (exponential curve).
    final t = releaseSamples > 0
        ? (sampleIndex - releaseStart) / releaseSamples
        : 1.0;
    return sustainLevel * exp(-t * 4.0);
  }
}

/// Encode Float64 samples as a 16-bit PCM WAV file.
Uint8List _encodeWav(Float64List samples, int sampleRate) {
  const channels = 1;
  const bitsPerSample = 16;
  const bytesPerSample = bitsPerSample ~/ 8;
  final dataSize = samples.length * channels * bytesPerSample;
  final fileSize = 44 + dataSize; // 44-byte header + data.

  final buffer = ByteData(fileSize);
  var offset = 0;

  // RIFF header.
  buffer.setUint8(offset++, 0x52); // R
  buffer.setUint8(offset++, 0x49); // I
  buffer.setUint8(offset++, 0x46); // F
  buffer.setUint8(offset++, 0x46); // F
  buffer.setUint32(offset, fileSize - 8, Endian.little);
  offset += 4;
  buffer.setUint8(offset++, 0x57); // W
  buffer.setUint8(offset++, 0x41); // A
  buffer.setUint8(offset++, 0x56); // V
  buffer.setUint8(offset++, 0x45); // E

  // fmt chunk.
  buffer.setUint8(offset++, 0x66); // f
  buffer.setUint8(offset++, 0x6D); // m
  buffer.setUint8(offset++, 0x74); // t
  buffer.setUint8(offset++, 0x20); // (space)
  buffer.setUint32(offset, 16, Endian.little); // chunk size
  offset += 4;
  buffer.setUint16(offset, 1, Endian.little); // PCM format
  offset += 2;
  buffer.setUint16(offset, channels, Endian.little);
  offset += 2;
  buffer.setUint32(offset, sampleRate, Endian.little);
  offset += 4;
  buffer.setUint32(
    offset,
    sampleRate * channels * bytesPerSample,
    Endian.little,
  ); // byte rate
  offset += 4;
  buffer.setUint16(
    offset,
    channels * bytesPerSample,
    Endian.little,
  ); // block align
  offset += 2;
  buffer.setUint16(offset, bitsPerSample, Endian.little);
  offset += 2;

  // data chunk.
  buffer.setUint8(offset++, 0x64); // d
  buffer.setUint8(offset++, 0x61); // a
  buffer.setUint8(offset++, 0x74); // t
  buffer.setUint8(offset++, 0x61); // a
  buffer.setUint32(offset, dataSize, Endian.little);
  offset += 4;

  // PCM samples.
  for (var i = 0; i < samples.length; i++) {
    final clamped = samples[i].clamp(-1.0, 1.0);
    final int16 = (clamped * 32767).round().clamp(-32768, 32767);
    buffer.setInt16(offset, int16, Endian.little);
    offset += 2;
  }

  return buffer.buffer.asUint8List();
}
