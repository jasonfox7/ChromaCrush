import 'package:chromacrush_app/config/visual_theme_service.dart';
import 'package:chromacrush_app/game/background_layer.dart';
import 'package:flame/components.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  late BackgroundLayer layer;

  setUp(() {
    final theme = VisualThemeService.fromMap({});
    layer = BackgroundLayer(screenSize: Vector2(400, 800), theme: theme);
  });

  group('BackgroundLayer', () {
    test('starts and updates without error', () {
      layer.update(0.016);
    });

    test('addRipple does not throw', () {
      layer.addRipple(100.0, 200.0);
      layer.update(0.016);
    });

    test('multiple addRipple calls do not throw', () {
      for (var i = 0; i < 10; i++) {
        layer.addRipple(i * 10.0, i * 20.0);
      }
      layer.update(0.016);
    });

    test('setIntensity clamps to 0-1', () {
      layer.setIntensity(0.5);
      layer.update(0.016);

      layer.setIntensity(-1.0);
      layer.update(0.016);

      layer.setIntensity(2.0);
      layer.update(0.016);
    });

    test('has correct size and priority', () {
      expect(layer.size.x, 400.0);
      expect(layer.size.y, 800.0);
      expect(layer.priority, -10);
    });

    test('position is at origin', () {
      expect(layer.position.x, 0.0);
      expect(layer.position.y, 0.0);
    });
  });
}
