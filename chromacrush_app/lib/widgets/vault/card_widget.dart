/// Card widget — full-art playing card with procedural shader background.
///
/// Full mode (5:7 aspect ratio):
///   Shader art fills the entire card surface. Frosted glass overlay panels
///   cover the header, type line, and text/footer areas. The center art window
///   is clear, showing raw shader art with a Cypro-Minoan glyph centered on it.
///
///   Borders by rarity: dark (common), shiny (rare), foil overlay (epic/legendary).
///
/// Compact mode shows glyph + name on a tag-tinted background.
library;

import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../config/visual_theme_service.dart';
import '../../models/backend_contract.dart';
import '../../utils/card_description_resolver.dart';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/// Rarity -> color mapping.
const _rarityColors = {
  'common': Color(0xFF8E8E93),
  'rare': Color(0xFF4FC3F7),
  'epic': Color(0xFFAB47BC),
  'legendary': Color(0xFFFFB300),
};

/// Rarity -> display label.
const _rarityLabels = {
  'common': 'COMMON',
  'rare': 'RARE',
  'epic': 'EPIC',
  'legendary': 'LEGENDARY',
};

/// Rarity -> numeric index for shader.
const _rarityIndex = {
  'common': 0.0,
  'rare': 1.0,
  'epic': 2.0,
  'legendary': 3.0,
};

/// Foil intensity per rarity (0 = no foil).
const _foilIntensity = {
  'common': 0.0,
  'rare': 0.0,
  'epic': 0.45,
  'legendary': 0.85,
};

/// Tag -> bitmask bit index.
const _tagBits = {
  'fire': 0,
  'ice': 1,
  'wind': 2,
  'earth': 3,
  'storm': 4,
  'time': 5,
  'void': 6,
  'offensive': 7,
  'defensive': 8,
  'utility': 9,
};

/// Tag -> display-friendly label.
const _tagLabels = {
  'fire': 'Fire',
  'ice': 'Ice',
  'wind': 'Wind',
  'earth': 'Earth',
  'storm': 'Storm',
  'time': 'Time',
  'void': 'Void',
  'offensive': 'Offensive',
  'defensive': 'Defensive',
  'utility': 'Utility',
};

/// Set ID -> display name.
const _setNames = {
  'prismatic': 'PRISMATIC ARTS',
  'arcane': 'ARCANE TOOLBOX',
  'forge': 'FORGE MASTERS',
  'stratagem': 'WAR DOCTRINE',
  'dominion': 'DOMINION',
  'gambit': 'GAMBIT',
  'arsenal': 'ARSENAL',
};

/// Set ID -> total card count.
const _setSizes = {
  'prismatic': 19,
  'arcane': 16,
  'forge': 18,
  'stratagem': 22,
  'dominion': 12,
  'gambit': 7,
  'arsenal': 10,
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/// Encodes a list of tag strings into a float bitmask for the shader.
double _tagBitmask(List<String> tags) {
  int mask = 0;
  for (final tag in tags) {
    final bit = _tagBits[tag];
    if (bit != null) mask |= (1 << bit);
  }
  return mask.toDouble();
}

/// Maps card_id to a Cypro-Minoan Unicode character (U+12F90 block).
String _cardGlyph(int cardId) => String.fromCharCode(0x12F90 + cardId);

/// Converts a Color to RGB floats (0-1) for shader uniforms.
(double r, double g, double b) _colorToRgb(Color c) => (c.r, c.g, c.b);

/// Primary element tag color (for fallbacks and compact tinting).
Color _tagColor(List<String> tags) {
  if (tags.contains('fire')) return const Color(0xFFCC4400);
  if (tags.contains('ice')) return const Color(0xFF2288BB);
  if (tags.contains('wind')) return const Color(0xFF66AA77);
  if (tags.contains('earth')) return const Color(0xFF886633);
  if (tags.contains('storm')) return const Color(0xFF7744AA);
  if (tags.contains('time')) return const Color(0xFF448877);
  if (tags.contains('void')) return const Color(0xFF552266);
  return const Color(0xFF444444);
}

/// Returns the border color for a given rarity.
Color _borderColor(String rarity, Color rarityColor) {
  switch (rarity) {
    case 'common':
      return const Color(0xFF2A2A2E);
    case 'rare':
      return rarityColor;
    case 'epic':
      return rarityColor.withValues(alpha: 0.6);
    case 'legendary':
      return rarityColor.withValues(alpha: 0.8);
    default:
      return const Color(0xFF2A2A2E);
  }
}

// ---------------------------------------------------------------------------
// CardWidget
// ---------------------------------------------------------------------------

class CardWidget extends StatelessWidget {
  const CardWidget({super.key, required this.card, this.compact = false});
  final PlayerCardResponse card;
  final bool compact;

  Color get _rarityColor =>
      _rarityColors[card.definition.rarity] ?? _rarityColors['common']!;

  bool get _hasFoil =>
      card.definition.rarity == 'epic' || card.definition.rarity == 'legendary';

  @override
  Widget build(BuildContext context) {
    if (compact) return _buildCompact();
    return _buildFull(context);
  }

  // -------------------------------------------------------------------------
  // Compact mode (equip slots)
  // -------------------------------------------------------------------------

  Widget _buildCompact() {
    final def = card.definition;
    final borderCol = _borderColor(def.rarity, _rarityColor);

    return Container(
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: borderCol, width: 1.5),
        boxShadow: def.rarity == 'rare'
            ? [
                BoxShadow(
                  color: _rarityColor.withValues(alpha: 0.3),
                  blurRadius: 8,
                  spreadRadius: 1,
                ),
              ]
            : null,
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(9),
        child: Stack(
          children: [
            // Tag-tinted dark background.
            Positioned.fill(
              child: Container(
                color: Color.lerp(
                  _tagColor(def.tags),
                  const Color(0xFF0A0A14),
                  0.75,
                ),
              ),
            ),
            // Content.
            Center(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    _cardGlyph(def.cardId),
                    style: TextStyle(
                      fontFamily: 'CyproMinoan',
                      fontSize: 24,
                      color: _rarityColor,
                      shadows: [
                        Shadow(
                          color: _rarityColor.withValues(alpha: 0.6),
                          blurRadius: 8,
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 4),
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 4),
                    child: Text(
                      def.name,
                      textAlign: TextAlign.center,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 9,
                        fontWeight: FontWeight.w600,
                        height: 1.2,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  // -------------------------------------------------------------------------
  // Full mode — full-art with glass overlay panels
  // -------------------------------------------------------------------------

  Widget _buildFull(BuildContext context) {
    final def = card.definition;
    final theme = context.read<VisualThemeBase>();
    final resolvedDescription = resolveCardDescription(
      def.description,
      def.effectParams,
      theme,
    );
    final borderCol = _borderColor(def.rarity, _rarityColor);
    Widget content = AspectRatio(
      aspectRatio: 5 / 7,
      child: LayoutBuilder(
        builder: (context, constraints) {
          // Scale factor: 1.0 at ~250px card width (expanded preview),
          // shrinks proportionally in carousel.
          final s = (constraints.maxWidth / 250).clamp(0.55, 1.0);

          return Container(
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: borderCol, width: 2),
              boxShadow: def.rarity == 'rare'
                  ? [
                      BoxShadow(
                        color: _rarityColor.withValues(alpha: 0.25),
                        blurRadius: 12,
                        spreadRadius: 2,
                      ),
                    ]
                  : null,
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(14),
              child: Stack(
                children: [
                  // Layer 1: Full-bleed shader art.
                  Positioned.fill(
                    child: _ShaderBackground(
                      card: card,
                      rarityColor: _rarityColor,
                    ),
                  ),

                  // Layer 2: Content with glass overlay panels.
                  Padding(
                    padding: EdgeInsets.all(6 * s),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                        // --- Header glass panel ---
                        _GlassOverlay(
                          padding: EdgeInsets.symmetric(
                            horizontal: 10 * s,
                            vertical: 6 * s,
                          ),
                          child: Row(
                            children: [
                              Expanded(
                                child: Text(
                                  def.name,
                                  maxLines: 1,
                                  overflow: TextOverflow.ellipsis,
                                  style: TextStyle(
                                    color: Colors.white,
                                    fontSize: 14 * s,
                                    fontWeight: FontWeight.w700,
                                    letterSpacing: 0.3,
                                  ),
                                ),
                              ),
                              SizedBox(width: 8 * s),
                              Text(
                                '${def.baseValue}',
                                style: TextStyle(
                                  color: _rarityColor.withValues(alpha: 0.9),
                                  fontSize: 12 * s,
                                  fontWeight: FontWeight.w700,
                                ),
                              ),
                            ],
                          ),
                        ),

                        SizedBox(height: 4 * s),

                        // --- Clear art window: raw shader + glyph ---
                        Expanded(
                          flex: 5,
                          child: Center(
                            child: Text(
                              _cardGlyph(def.cardId),
                              style: TextStyle(
                                fontFamily: 'CyproMinoan',
                                fontSize: 48 * s,
                                color: Colors.white.withValues(alpha: 0.85),
                                shadows: [
                                  Shadow(
                                    color: _rarityColor.withValues(alpha: 0.7),
                                    blurRadius: 16,
                                  ),
                                  Shadow(
                                    color: Colors.black.withValues(alpha: 0.5),
                                    blurRadius: 4,
                                  ),
                                ],
                              ),
                            ),
                          ),
                        ),

                        SizedBox(height: 4 * s),

                        // --- Type line glass panel ---
                        _GlassOverlay(
                          padding: EdgeInsets.symmetric(
                            horizontal: 10 * s,
                            vertical: 6 * s,
                          ),
                          child: _TypeLine(
                            tags: def.tags,
                            rarityColor: _rarityColor,
                            scale: s,
                          ),
                        ),

                        SizedBox(height: 4 * s),

                        // --- Text box + footer glass panel ---
                        Flexible(
                          flex: 3,
                          child: _GlassOverlay(
                            padding: EdgeInsets.symmetric(
                              horizontal: 10 * s,
                              vertical: 8 * s,
                            ),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                // Flavor text.
                                Flexible(
                                  child: Text(
                                    resolvedDescription,
                                    maxLines: s < 0.75 ? 2 : 3,
                                    overflow: TextOverflow.ellipsis,
                                    style: TextStyle(
                                      color: Colors.white.withValues(
                                        alpha: 0.6,
                                      ),
                                      fontSize: 11 * s,
                                      fontStyle: FontStyle.italic,
                                      height: 1.4,
                                    ),
                                  ),
                                ),
                                SizedBox(height: 6 * s),
                                // Thin separator.
                                Container(
                                  height: 0.5,
                                  color: Colors.white.withValues(alpha: 0.08),
                                ),
                                SizedBox(height: 6 * s),
                                // Footer row.
                                Row(
                                  children: [
                                    Text(
                                      'Lv ${card.level}',
                                      style: TextStyle(
                                        color: Colors.white.withValues(
                                          alpha: 0.45,
                                        ),
                                        fontSize: 10 * s,
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                    const Spacer(),
                                    Flexible(
                                      child: Text(
                                        _setNames[def.cardSet] ??
                                            def.cardSet.toUpperCase(),
                                        maxLines: 1,
                                        overflow: TextOverflow.ellipsis,
                                        style: TextStyle(
                                          color: Colors.white.withValues(
                                            alpha: 0.3,
                                          ),
                                          fontSize: 8 * s,
                                          fontWeight: FontWeight.w700,
                                          letterSpacing: 1.5,
                                        ),
                                      ),
                                    ),
                                    SizedBox(width: 6 * s),
                                    Text(
                                      '${def.setPosition}/${_setSizes[def.cardSet] ?? '?'}',
                                      style: TextStyle(
                                        color: Colors.white.withValues(
                                          alpha: 0.3,
                                        ),
                                        fontSize: 8 * s,
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                  ],
                                ),
                                SizedBox(height: 4 * s),
                                Align(
                                  alignment: Alignment.centerRight,
                                  child: _RarityBadge(
                                    rarity: def.rarity,
                                    color: _rarityColor,
                                    scale: s,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),

                  // Layer 3: Foil overlay (epic/legendary).
                  if (_hasFoil)
                    Positioned.fill(
                      child: _FoilOverlay(
                        intensity: _foilIntensity[def.rarity] ?? 0.0,
                      ),
                    ),
                ],
              ),
            ),
          );
        },
      ),
    );

    // Legendary gets extra outer glow.
    if (def.rarity == 'legendary') {
      content = Container(
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: _rarityColor.withValues(alpha: 0.3),
              blurRadius: 24,
              spreadRadius: 4,
            ),
          ],
        ),
        child: content,
      );
    }

    return content;
  }
}

// ---------------------------------------------------------------------------
// Glass overlay panel — frosted dark panel over the shader art
// ---------------------------------------------------------------------------

class _GlassOverlay extends StatelessWidget {
  const _GlassOverlay({required this.child, this.padding});
  final Widget child;
  final EdgeInsetsGeometry? padding;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(8),
      child: BackdropFilter(
        filter: ui.ImageFilter.blur(sigmaX: 10, sigmaY: 10),
        child: Container(
          padding:
              padding ??
              const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(
            color: const Color(0xFF0A0A14).withValues(alpha: 0.65),
            borderRadius: BorderRadius.circular(8),
            border: Border.all(color: Colors.white.withValues(alpha: 0.06)),
          ),
          child: child,
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Shader background — procedural art filling the entire card
// ---------------------------------------------------------------------------

class _ShaderBackground extends StatefulWidget {
  const _ShaderBackground({required this.card, required this.rarityColor});
  final PlayerCardResponse card;
  final Color rarityColor;

  @override
  State<_ShaderBackground> createState() => _ShaderBackgroundState();
}

class _ShaderBackgroundState extends State<_ShaderBackground>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  ui.FragmentProgram? _program;
  bool _shaderFailed = false;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController.unbounded(vsync: this)
      ..repeat(min: 0, max: 1, period: const Duration(seconds: 4));
    _loadShader();
  }

  Future<void> _loadShader() async {
    try {
      final program = await ui.FragmentProgram.fromAsset(
        'shaders/card_art.frag',
      );
      if (!mounted) return;
      setState(() => _program = program);
    } catch (_) {
      if (!mounted) return;
      setState(() => _shaderFailed = true);
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final def = widget.card.definition;

    if (_shaderFailed || _program == null) {
      return _ArtFallback(
        tags: def.tags,
        rarityColor: widget.rarityColor,
        showLoading: !_shaderFailed,
      );
    }

    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) {
        return CustomPaint(
          painter: _CardArtPainter(
            program: _program!,
            time: _controller.value * 4.0,
            seed: def.cardId.toDouble(),
            rarity: _rarityIndex[def.rarity] ?? 0.0,
            tags: _tagBitmask(def.tags),
            color: widget.rarityColor,
          ),
        );
      },
    );
  }
}

// ---------------------------------------------------------------------------
// Card art painter — sets shader uniforms
// ---------------------------------------------------------------------------

class _CardArtPainter extends CustomPainter {
  _CardArtPainter({
    required this.program,
    required this.time,
    required this.seed,
    required this.rarity,
    required this.tags,
    required this.color,
  });

  final ui.FragmentProgram program;
  final double time;
  final double seed;
  final double rarity;
  final double tags;
  final Color color;

  @override
  void paint(Canvas canvas, Size size) {
    final shader = program.fragmentShader();
    final (r, g, b) = _colorToRgb(color);

    // u_size (vec2)
    shader.setFloat(0, size.width);
    shader.setFloat(1, size.height);
    // u_time (float)
    shader.setFloat(2, time);
    // u_seed (float)
    shader.setFloat(3, seed);
    // u_rarity (float)
    shader.setFloat(4, rarity);
    // u_tags (float)
    shader.setFloat(5, tags);
    // u_color (vec3)
    shader.setFloat(6, r);
    shader.setFloat(7, g);
    shader.setFloat(8, b);

    canvas.drawRect(Offset.zero & size, Paint()..shader = shader);

    shader.dispose();
  }

  @override
  bool shouldRepaint(_CardArtPainter oldDelegate) => true;
}

// ---------------------------------------------------------------------------
// Art fallback (no shader support)
// ---------------------------------------------------------------------------

class _ArtFallback extends StatelessWidget {
  const _ArtFallback({
    required this.tags,
    required this.rarityColor,
    this.showLoading = false,
  });
  final List<String> tags;
  final Color rarityColor;
  final bool showLoading;

  @override
  Widget build(BuildContext context) {
    if (showLoading) return const SizedBox.shrink();
    final tc = _tagColor(tags);
    return Container(
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            tc.withValues(alpha: 0.6),
            rarityColor.withValues(alpha: 0.3),
            tc.withValues(alpha: 0.4),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Type line — tags displayed as subtypes + rarity dot
// ---------------------------------------------------------------------------

class _TypeLine extends StatelessWidget {
  const _TypeLine({
    required this.tags,
    required this.rarityColor,
    this.scale = 1.0,
  });
  final List<String> tags;
  final Color rarityColor;
  final double scale;

  @override
  Widget build(BuildContext context) {
    final labels = tags
        .map((t) => _tagLabels[t] ?? t[0].toUpperCase() + t.substring(1))
        .join(' \u00B7 '); // middle dot separator

    return Row(
      children: [
        Expanded(
          child: Text(
            labels,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.6),
              fontSize: 10 * scale,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        SizedBox(width: 6 * scale),
        // Rarity dot.
        Container(
          width: 8 * scale,
          height: 8 * scale,
          decoration: BoxDecoration(
            color: rarityColor,
            shape: BoxShape.circle,
            boxShadow: [
              BoxShadow(
                color: rarityColor.withValues(alpha: 0.5),
                blurRadius: 4,
              ),
            ],
          ),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Foil overlay — animated holographic shader
// ---------------------------------------------------------------------------

class _FoilOverlay extends StatefulWidget {
  const _FoilOverlay({required this.intensity});
  final double intensity;

  @override
  State<_FoilOverlay> createState() => _FoilOverlayState();
}

class _FoilOverlayState extends State<_FoilOverlay>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  ui.FragmentProgram? _program;
  bool _shaderFailed = false;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController.unbounded(vsync: this)
      ..repeat(
        min: 0,
        max: 1,
        reverse: true,
        period: const Duration(seconds: 3),
      );
    _loadShader();
  }

  Future<void> _loadShader() async {
    try {
      final program = await ui.FragmentProgram.fromAsset('shaders/foil.frag');
      if (!mounted) return;
      setState(() => _program = program);
    } catch (_) {
      if (!mounted) return;
      setState(() => _shaderFailed = true);
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_shaderFailed || _program == null) {
      if (_shaderFailed) return _FoilFallback(intensity: widget.intensity);
      return const SizedBox.shrink();
    }

    return AnimatedBuilder(
      animation: _controller,
      builder: (context, _) {
        return CustomPaint(
          painter: _FoilPainter(
            program: _program!,
            time: _controller.value,
            intensity: widget.intensity,
          ),
        );
      },
    );
  }
}

class _FoilPainter extends CustomPainter {
  _FoilPainter({
    required this.program,
    required this.time,
    required this.intensity,
  });

  final ui.FragmentProgram program;
  final double time;
  final double intensity;

  @override
  void paint(Canvas canvas, Size size) {
    final shader = program.fragmentShader();
    shader.setFloat(0, size.width);
    shader.setFloat(1, size.height);
    shader.setFloat(2, time);
    shader.setFloat(3, intensity);

    canvas.drawRect(Offset.zero & size, Paint()..shader = shader);

    shader.dispose();
  }

  @override
  bool shouldRepaint(_FoilPainter oldDelegate) => true;
}

// ---------------------------------------------------------------------------
// Foil fallback shimmer (no shader support)
// ---------------------------------------------------------------------------

class _FoilFallback extends StatelessWidget {
  const _FoilFallback({required this.intensity});
  final double intensity;

  @override
  Widget build(BuildContext context) {
    return IgnorePointer(
      child: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Colors.white.withValues(alpha: 0.05 * intensity),
              Colors.purple.withValues(alpha: 0.08 * intensity),
              Colors.cyan.withValues(alpha: 0.06 * intensity),
              Colors.amber.withValues(alpha: 0.05 * intensity),
            ],
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Rarity badge
// ---------------------------------------------------------------------------

class _RarityBadge extends StatelessWidget {
  const _RarityBadge({
    required this.rarity,
    required this.color,
    this.scale = 1.0,
  });
  final String rarity;
  final Color color;
  final double scale;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: EdgeInsets.symmetric(horizontal: 8 * scale, vertical: 3 * scale),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.2),
        borderRadius: BorderRadius.circular(6),
        border: Border.all(color: color.withValues(alpha: 0.4)),
      ),
      child: Text(
        _rarityLabels[rarity] ?? rarity.toUpperCase(),
        style: TextStyle(
          color: color,
          fontSize: 9 * scale,
          fontWeight: FontWeight.w800,
          letterSpacing: 1.5,
        ),
      ),
    );
  }
}
