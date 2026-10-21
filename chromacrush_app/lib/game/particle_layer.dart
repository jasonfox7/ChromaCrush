/// Particle effect system — 10 effects, 500-particle budget.
///
/// Manages all game particle effects as ParticleSystemComponents.
/// Budget enforcement kills oldest non-priority effects when at capacity.
library;

import 'dart:math';
import 'dart:ui';

import 'package:flame/components.dart';
import 'package:flame/particles.dart';

import '../config/visual_config.dart';
import '../config/visual_theme_service.dart';
import '../extensions/grid_math.dart';
import '../models/gem_type.dart';

/// Manages all particle effects for the game.
///
/// Added as a child of ChromaCrushGame, layered above the board.
class ParticleLayer extends PositionComponent {
  ParticleLayer({required this.theme, required this.layout});

  final VisualThemeBase theme;
  final BoardLayout layout;
  final Random _rng = Random();

  /// Tracked active particle systems with metadata for budget enforcement.
  final List<_TrackedParticle> _active = [];

  /// Ambient particle target count (intensity-driven).
  int _ambientTarget = 0;
  double _ambientSpawnTimer = 0;

  /// Current estimated live particle count.
  int get activeParticleCount => _active.fold(0, (sum, t) => sum + t.count);

  // ---------------------------------------------------------------------------
  // Budget enforcement
  // ---------------------------------------------------------------------------

  void _enforeBudget(int incoming) {
    // Kill oldest non-priority systems until we have room.
    while (activeParticleCount + incoming > kParticleBudget) {
      final idx = _active.indexWhere((t) => !t.priority);
      if (idx == -1) break; // Only priority left — allow overshoot.
      _active[idx].component.removeFromParent();
      _active.removeAt(idx);
    }
  }

  void _addSystem(
    ParticleSystemComponent comp,
    int count, {
    bool priority = false,
  }) {
    _enforeBudget(count);
    final tracked = _TrackedParticle(
      component: comp,
      count: count,
      priority: priority,
    );
    _active.add(tracked);
    add(comp);
    // Auto-cleanup when particle completes.
    comp.removed.then((_) => _active.remove(tracked));
  }

  @override
  void update(double dt) {
    super.update(dt);
    // Prune completed systems.
    _active.removeWhere((t) => t.component.isRemoved);
    // Spawn ambient particles at intensity-driven rate.
    _updateAmbient(dt);
  }

  // ---------------------------------------------------------------------------
  // Ambient particles (intensity-driven)
  // ---------------------------------------------------------------------------

  /// Set target ambient particle density (0–50).
  void setAmbientDensity(int count) {
    _ambientTarget = count;
  }

  void _updateAmbient(double dt) {
    if (_ambientTarget <= 0) return;
    _ambientSpawnTimer -= dt;
    if (_ambientSpawnTimer > 0) return;

    // Spawn a small batch every 0.5s to approach target density.
    // Ambient particles live 2s, so steady-state ≈ target when
    // we spawn (target / 4) every 0.5s.
    final batch = (_ambientTarget / 4).ceil().clamp(1, 15);
    _ambientSpawnTimer = 0.5;

    final boardExtent = layout.boardExtent;
    final system = ParticleSystemComponent(
      particle: Particle.generate(
        count: batch,
        lifespan: 2.0,
        generator: (_) {
          final x = _rng.nextDouble() * boardExtent;
          final y = _rng.nextDouble() * boardExtent;
          final color = Color.fromRGBO(
            255,
            255,
            255,
            0.08 + _rng.nextDouble() * 0.12,
          );
          return AcceleratedParticle(
            position: Vector2(x, y),
            speed: Vector2(
              (_rng.nextDouble() - 0.5) * 8,
              -3 - _rng.nextDouble() * 5, // gentle upward drift
            ),
            acceleration: Vector2.zero(),
            child: _fadingCircle(1.0 + _rng.nextDouble(), color),
          );
        },
      ),
    );
    _addSystem(system, batch);
  }

  // ---------------------------------------------------------------------------
  // Helpers
  // ---------------------------------------------------------------------------

  /// Center position of a grid cell in board-local coordinates.
  Vector2 _cellCenter(int row, int col) {
    final pos = layout.gridToPosition(row, col);
    return Vector2(pos.x + layout.cellSize / 2, pos.y + layout.cellSize / 2);
  }

  /// Random unit vector.
  Vector2 _randomDirection() {
    final angle = _rng.nextDouble() * 2 * pi;
    return Vector2(cos(angle), sin(angle));
  }

  /// Random color between two colors (lerp with random t).
  Color _lerpColor(Color a, Color b) {
    final t = _rng.nextDouble();
    return Color.lerp(a, b, t)!;
  }

  // ---------------------------------------------------------------------------
  // 1. MatchBurst — 15-25 particles, 0.4s, on 3-gem match
  // ---------------------------------------------------------------------------

  void matchBurst(List<({int row, int col})> positions, GemType gemType) {
    final color = theme.gemColor(gemType.value);
    final bright = _lerpColor(color, theme.particleColor('match_burst_bright'));
    final count = 15 + _rng.nextInt(11); // 15-25

    for (final pos in positions) {
      final center = _cellCenter(pos.row, pos.col);
      final perCell = count ~/ positions.length;
      final system = ParticleSystemComponent(
        particle: Particle.generate(
          count: perCell.clamp(3, 8),
          lifespan: 0.4,
          generator: (_) => AcceleratedParticle(
            position: center.clone(),
            speed: _randomDirection() * (40 + _rng.nextDouble() * 60),
            acceleration: Vector2(0, 80), // gentle gravity
            child: _fadingCircle(2.5, bright),
          ),
        ),
      );
      _addSystem(system, perCell);
    }
  }

  // ---------------------------------------------------------------------------
  // 2. CascadeBurst — 30-50 particles, 0.5s, cascade step 2+
  // ---------------------------------------------------------------------------

  void cascadeBurst(List<({int row, int col})> positions, GemType gemType) {
    final color = theme.gemColor(gemType.value);
    final count = 30 + _rng.nextInt(21); // 30-50

    final allCenters = positions.map((p) => _cellCenter(p.row, p.col)).toList();
    final system = ParticleSystemComponent(
      particle: Particle.generate(
        count: count,
        lifespan: 0.5,
        generator: (_) {
          final origin = allCenters[_rng.nextInt(allCenters.length)];
          return AcceleratedParticle(
            position: origin.clone(),
            speed: _randomDirection() * (60 + _rng.nextDouble() * 80),
            acceleration: Vector2(0, 60),
            child: _fadingCircle(3.0, color),
          );
        },
      ),
    );
    _addSystem(system, count);
  }

  // ---------------------------------------------------------------------------
  // 3. LineSweep — 40-60 particles, 0.6s, Line Blast activation
  // ---------------------------------------------------------------------------

  void lineSweep(int row, int col, {required bool horizontal}) {
    final center = _cellCenter(row, col);
    final count = 40 + _rng.nextInt(21); // 40-60
    final color = theme.particleColor('line_sweep');

    final system = ParticleSystemComponent(
      particle: Particle.generate(
        count: count,
        lifespan: 0.6,
        generator: (i) {
          // Particles shoot along the line direction.
          final dir = horizontal
              ? Vector2(
                  (_rng.nextBool() ? 1 : -1) * (100 + _rng.nextDouble() * 150),
                  (_rng.nextDouble() - 0.5) * 30,
                )
              : Vector2(
                  (_rng.nextDouble() - 0.5) * 30,
                  (_rng.nextBool() ? 1 : -1) * (100 + _rng.nextDouble() * 150),
                );
          return AcceleratedParticle(
            position: center.clone(),
            speed: dir,
            acceleration: Vector2.zero(),
            child: _fadingCircle(2.0, color),
          );
        },
      ),
    );
    _addSystem(system, count);
  }

  // ---------------------------------------------------------------------------
  // 4. RadialWave — 60-80 particles, 0.5s, Radial Bomb activation
  // ---------------------------------------------------------------------------

  void radialWave(int row, int col) {
    final center = _cellCenter(row, col);
    final count = 60 + _rng.nextInt(21); // 60-80
    final color = theme.particleColor('radial_wave_start');

    final system = ParticleSystemComponent(
      particle: Particle.generate(
        count: count,
        lifespan: 0.5,
        generator: (_) {
          final dir = _randomDirection();
          final speed = 80 + _rng.nextDouble() * 120;
          return AcceleratedParticle(
            position: center.clone(),
            speed: dir * speed,
            acceleration: -dir * speed * 0.5, // decelerate outward
            child: _fadingCircle(
              3.5,
              _lerpColor(color, theme.particleColor('radial_wave_end')),
            ),
          );
        },
      ),
    );
    _addSystem(system, count);
  }

  // ---------------------------------------------------------------------------
  // 5. ChromaticRain — 80-120 particles, 0.8s, Chromatic Orb activation
  // ---------------------------------------------------------------------------

  void chromaticRain(int row, int col) {
    final center = _cellCenter(row, col);
    final count = 80 + _rng.nextInt(41); // 80-120
    final colors = theme.chromaticRainColors;

    final system = ParticleSystemComponent(
      particle: Particle.generate(
        count: count,
        lifespan: 0.8,
        generator: (_) {
          final color = colors[_rng.nextInt(colors.length)];
          return AcceleratedParticle(
            position: center.clone(),
            speed: _randomDirection() * (50 + _rng.nextDouble() * 100),
            acceleration: Vector2(0, 120), // rainbow rain falls
            child: _fadingCircle(2.5, color),
          );
        },
      ),
    );
    _addSystem(system, count);
  }

  // ---------------------------------------------------------------------------
  // 6. FusionStorm — 200-300 particles, 1.5s, Fusion combo (PRIORITY)
  // ---------------------------------------------------------------------------

  void fusionStorm(int row, int col) {
    final center = _cellCenter(row, col);
    final count = 200 + _rng.nextInt(101); // 200-300

    final system = ParticleSystemComponent(
      particle: Particle.generate(
        count: count,
        lifespan: 1.5,
        generator: (_) {
          final color = _lerpColor(
            theme.particleColor('fusion_storm_start'),
            theme.particleColor('fusion_storm_end'),
          );
          final dir = _randomDirection();
          final speed = 30 + _rng.nextDouble() * 180;
          return AcceleratedParticle(
            position:
                center.clone() + _randomDirection() * _rng.nextDouble() * 20,
            speed: dir * speed,
            acceleration: Vector2(
              (_rng.nextDouble() - 0.5) * 40,
              -20 + _rng.nextDouble() * 80, // turbulent
            ),
            child: _fadingCircle(2.0 + _rng.nextDouble() * 3.0, color),
          );
        },
      ),
    );
    _addSystem(system, count, priority: true);
  }

  // ---------------------------------------------------------------------------
  // 6b. MegaMergeSparks — 40-60 golden particles from sources to center
  // ---------------------------------------------------------------------------

  void megaMergeSparks(
    int posARow,
    int posACol,
    int posBRow,
    int posBCol,
    int centerRow,
    int centerCol,
  ) {
    final centerPos = _cellCenter(centerRow, centerCol);
    final posA = _cellCenter(posARow, posACol);
    final posB = _cellCenter(posBRow, posBCol);
    final color = theme.particleColor('mega_merge_sparks');
    final count = 40 + _rng.nextInt(21); // 40-60

    final system = ParticleSystemComponent(
      particle: Particle.generate(
        count: count,
        lifespan: 0.5,
        generator: (i) {
          // Half from posA, half from posB, all converging on center.
          final origin = i.isEven ? posA : posB;
          final toCenter = (centerPos - origin);
          final speed = toCenter * (2.0 + _rng.nextDouble());
          final jitter = _randomDirection() * (_rng.nextDouble() * 20);
          return AcceleratedParticle(
            position:
                origin.clone() + _randomDirection() * (_rng.nextDouble() * 5),
            speed: speed + jitter,
            acceleration: Vector2.zero(),
            child: _fadingCircle(
              2.0 + _rng.nextDouble(),
              _lerpColor(color, theme.particleColor('mega_merge_bright')),
            ),
          );
        },
      ),
    );
    _addSystem(system, count, priority: true);
  }

  // ---------------------------------------------------------------------------
  // 6c. MegaActivationBurst — 100+ golden particles radiating outward
  // ---------------------------------------------------------------------------

  void megaActivationBurst(int row, int col) {
    final center = _cellCenter(row, col);
    final count = 100 + _rng.nextInt(51); // 100-150
    final gold = theme.particleColor('mega_activation');

    final system = ParticleSystemComponent(
      particle: Particle.generate(
        count: count,
        lifespan: 0.8,
        generator: (_) {
          final dir = _randomDirection();
          final speed = 100 + _rng.nextDouble() * 150;
          return AcceleratedParticle(
            position: center.clone(),
            speed: dir * speed,
            acceleration: -dir * speed * 0.3,
            child: _fadingCircle(
              2.5 + _rng.nextDouble() * 2,
              _lerpColor(gold, theme.particleColor('mega_activation_bright')),
            ),
          );
        },
      ),
    );
    _addSystem(system, count, priority: true);
  }

  // ---------------------------------------------------------------------------
  // 7. VictoryConfetti — 150-200 particles, 2.0s, Match won (PRIORITY)
  // ---------------------------------------------------------------------------

  void victoryConfetti(Vector2 gameSize) {
    final count = 150 + _rng.nextInt(51); // 150-200
    final colors = theme.victoryConfettiColors;

    final system = ParticleSystemComponent(
      particle: Particle.generate(
        count: count,
        lifespan: 2.0,
        generator: (_) {
          final color = colors[_rng.nextInt(colors.length)];
          final startX = _rng.nextDouble() * gameSize.x;
          return AcceleratedParticle(
            position: Vector2(startX, -10),
            speed: Vector2(
              (_rng.nextDouble() - 0.5) * 80,
              40 + _rng.nextDouble() * 60,
            ),
            acceleration: Vector2((_rng.nextDouble() - 0.5) * 20, 30),
            child: _fadingRect(4.0, 2.0, color),
          );
        },
      ),
    );
    _addSystem(system, count, priority: true);
  }

  // ---------------------------------------------------------------------------
  // 8. NearMissSparkle — 5-8/spot, 0.3s, Board settle near-match
  // ---------------------------------------------------------------------------

  void nearMissSparkle(int row, int col) {
    final center = _cellCenter(row, col);
    final count = 5 + _rng.nextInt(4); // 5-8
    final color = theme.particleColor('near_miss_sparkle');

    final system = ParticleSystemComponent(
      particle: Particle.generate(
        count: count,
        lifespan: 0.3,
        generator: (_) => AcceleratedParticle(
          position:
              center.clone() +
              _randomDirection() * (_rng.nextDouble() * layout.cellSize / 2),
          speed: _randomDirection() * (10 + _rng.nextDouble() * 20),
          acceleration: Vector2(0, -30), // sparkles float up
          child: _fadingCircle(1.5, color),
        ),
      ),
    );
    _addSystem(system, count);
  }

  // ---------------------------------------------------------------------------
  // 9. GemTrail — 3-5/gem, 0.2s, Gem falling
  // ---------------------------------------------------------------------------

  void gemTrail(int row, int col, GemType gemType) {
    final center = _cellCenter(row, col);
    final count = 3 + _rng.nextInt(3); // 3-5
    final color = theme.gemColor(gemType.value).withValues(alpha: 0.6);

    final system = ParticleSystemComponent(
      particle: Particle.generate(
        count: count,
        lifespan: 0.2,
        generator: (_) => AcceleratedParticle(
          position: center.clone(),
          speed: Vector2((_rng.nextDouble() - 0.5) * 10, -5),
          acceleration: Vector2.zero(),
          child: _fadingCircle(1.5, color),
        ),
      ),
    );
    _addSystem(system, count);
  }

  // ---------------------------------------------------------------------------
  // 10. DefeatDust — 30-40 particles, 1.0s, Match lost
  // ---------------------------------------------------------------------------

  void defeatDust(Vector2 gameSize) {
    final count = 30 + _rng.nextInt(11); // 30-40
    final color = theme.particleColor('defeat_dust_dark');

    final system = ParticleSystemComponent(
      particle: Particle.generate(
        count: count,
        lifespan: 1.0,
        generator: (_) {
          final startX = _rng.nextDouble() * gameSize.x;
          final startY =
              _rng.nextDouble() * gameSize.y * 0.5 + gameSize.y * 0.3;
          return AcceleratedParticle(
            position: Vector2(startX, startY),
            speed: Vector2(
              (_rng.nextDouble() - 0.5) * 30,
              -10 - _rng.nextDouble() * 20,
            ),
            acceleration: Vector2(0, 15),
            child: _fadingCircle(
              2.5,
              _lerpColor(color, theme.particleColor('defeat_dust_light')),
            ),
          );
        },
      ),
    );
    _addSystem(system, count);
  }

  // ---------------------------------------------------------------------------
  // Particle primitives
  // ---------------------------------------------------------------------------

  /// Fading circle particle — scales down and fades over lifetime.
  Particle _fadingCircle(double radius, Color color) {
    return ComputedParticle(
      renderer: (canvas, particle) {
        final alpha = (1.0 - particle.progress).clamp(0.0, 1.0);
        final r = radius * (0.5 + 0.5 * (1.0 - particle.progress));
        final paint = Paint()..color = color.withValues(alpha: alpha);
        canvas.drawCircle(Offset.zero, r, paint);
      },
    );
  }

  /// Fading rectangle particle — for confetti.
  Particle _fadingRect(double width, double height, Color color) {
    return ComputedParticle(
      renderer: (canvas, particle) {
        final alpha = (1.0 - particle.progress).clamp(0.0, 1.0);
        final rotation = particle.progress * pi * 4; // tumble
        final paint = Paint()..color = color.withValues(alpha: alpha);
        canvas.save();
        canvas.rotate(rotation);
        canvas.drawRect(
          Rect.fromCenter(center: Offset.zero, width: width, height: height),
          paint,
        );
        canvas.restore();
      },
    );
  }
}

/// Internal tracking for budget enforcement.
class _TrackedParticle {
  _TrackedParticle({
    required this.component,
    required this.count,
    this.priority = false,
  });

  final ParticleSystemComponent component;
  final int count;
  final bool priority;
}
