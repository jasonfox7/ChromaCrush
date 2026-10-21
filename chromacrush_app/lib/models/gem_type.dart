/// Gem color enum — values 1-6 are standard gem colors, 0 is empty.
///
/// With the two-grid model, the board stores colors in one grid and
/// functions (special abilities) in another. GemType only represents colors.
enum GemType {
  empty(0),
  red(1),
  blue(2),
  green(3),
  yellow(4),
  purple(5),
  orange(6),
  obstacle(7);

  const GemType(this.value);
  final int value;

  /// Whether this gem is a standard color (1-6).
  bool get isStandard => value >= 1 && value <= 6;

  /// Whether this gem is an obstacle (campaign mode).
  bool get isObstacle => value == 7;

  /// Whether this cell is empty.
  bool get isEmpty => value == 0;

  /// Number of standard gem colors.
  static const int standardCount = 6;

  /// Look up GemType from its integer value.
  static GemType fromValue(int v) {
    return GemType.values.firstWhere(
      (g) => g.value == v,
      orElse: () => GemType.empty,
    );
  }
}

/// Gem function (special ability) — stored in the parallel func_grid.
///
/// Standard gems are [neutral]. Special gems have a non-zero function
/// and retain their base color for match participation.
enum GemFunction {
  neutral(0),
  lineBlastH(1),
  lineBlastV(2),
  radialBomb(3),
  chromaticOrb(4);

  const GemFunction(this.value);
  final int value;

  /// Whether this gem has a special ability.
  bool get isSpecial => this != neutral;

  /// Look up GemFunction from its integer value.
  ///
  /// For mega gem values (11-44) this returns the dominant component function.
  static GemFunction fromValue(int v) {
    if (isMegaGemValue(v)) return megaDominant(v);
    return GemFunction.values.firstWhere(
      (f) => f.value == v,
      orElse: () => GemFunction.neutral,
    );
  }
}

// ---------------------------------------------------------------------------
// Mega gem helpers — two specials fused into one cell.
// Encoded as funcA * 10 + funcB (canonical order, funcA <= funcB).
// ---------------------------------------------------------------------------

const _megaGemValues = {11, 12, 13, 14, 22, 23, 24, 33, 34, 44};

/// Whether [funcValue] represents a mega gem (two fused specials).
bool isMegaGemValue(int funcValue) => _megaGemValues.contains(funcValue);

/// Return the dominant (higher-priority) function of a mega gem.
GemFunction megaDominant(int v) {
  final a = v ~/ 10;
  final b = v % 10;
  return GemFunction.values.firstWhere(
    (f) => f.value == (a > b ? a : b),
    orElse: () => GemFunction.neutral,
  );
}

/// Map a raw func_grid value to the shader's u_function uniform.
///
/// Standard specials (1-4) pass through unchanged.
/// Mega gems map to dominant + 4 (values 5-8) so the shader can detect them.
/// Invincible walls (func >= 10, not in mega set) map to 0 (neutral) — walls
/// use shape/color differentiation only, no special shader effects.
int funcToShaderValue(int raw) {
  if (isMegaGemValue(raw)) return megaDominant(raw).value + 4;
  if (raw >= 10) return 0; // Invincible wall — no shader effect.
  return raw;
}
