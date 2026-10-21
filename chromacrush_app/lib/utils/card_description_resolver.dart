/// Resolves tokens in card descriptions using the visual theme.
///
/// Tokens: {gem_name}, {special_name}, {mega_name}
/// Resolved from effect_params keys + visual theme display names.
/// Unresolvable tokens are left as-is for debug visibility.
library;

import '../config/visual_theme_service.dart';

/// Resolve all tokens in [description] using [effectParams] and [theme].
String resolveCardDescription(
  String description,
  Map<String, dynamic> effectParams,
  VisualThemeBase theme,
) {
  var result = description;

  // {gem_name} -> lookup gem_color in effect_params.
  if (result.contains('{gem_name}')) {
    final gemColor = effectParams['gem_color'];
    if (gemColor is int) {
      result = result.replaceAll('{gem_name}', theme.gemName(gemColor));
    }
  }

  // {special_name} -> lookup function or target_function in effect_params.
  if (result.contains('{special_name}')) {
    final func = effectParams['function'] ?? effectParams['target_function'];
    if (func is int) {
      result = result.replaceAll('{special_name}', theme.specialName(func));
    }
  }

  // {mega_name} -> lookup mega_func or win_on_mega in effect_params.
  if (result.contains('{mega_name}')) {
    final mega = effectParams['mega_func'] ?? effectParams['win_on_mega'];
    if (mega is int) {
      result = result.replaceAll('{mega_name}', theme.megaName(mega));
    }
  }

  return result;
}
