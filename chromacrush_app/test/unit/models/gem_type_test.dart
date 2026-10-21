import 'package:flutter_test/flutter_test.dart';
import 'package:chromacrush_app/models/gem_type.dart';

void main() {
  group('GemType', () {
    test('standard gem values match backend int8 encoding', () {
      expect(GemType.empty.value, 0);
      expect(GemType.red.value, 1);
      expect(GemType.blue.value, 2);
      expect(GemType.green.value, 3);
      expect(GemType.yellow.value, 4);
      expect(GemType.purple.value, 5);
      expect(GemType.orange.value, 6);
    });

    test('isStandard returns true only for values 1-6', () {
      expect(GemType.empty.isStandard, isFalse);
      expect(GemType.red.isStandard, isTrue);
      expect(GemType.blue.isStandard, isTrue);
      expect(GemType.green.isStandard, isTrue);
      expect(GemType.yellow.isStandard, isTrue);
      expect(GemType.purple.isStandard, isTrue);
      expect(GemType.orange.isStandard, isTrue);
    });

    test('isEmpty returns true only for value 0', () {
      expect(GemType.empty.isEmpty, isTrue);
      expect(GemType.red.isEmpty, isFalse);
    });

    test('standardCount is 6', () {
      expect(GemType.standardCount, 6);
    });

    test('fromValue maps all known values', () {
      for (final gem in GemType.values) {
        expect(GemType.fromValue(gem.value), gem);
      }
    });

    test('fromValue returns empty for unknown value', () {
      expect(GemType.fromValue(99), GemType.empty);
      expect(GemType.fromValue(-99), GemType.empty);
    });

    test('enum has exactly 8 values (empty + 6 colors + obstacle)', () {
      expect(GemType.values.length, 8);
    });
  });

  group('GemFunction', () {
    test('function values match backend encoding', () {
      expect(GemFunction.neutral.value, 0);
      expect(GemFunction.lineBlastH.value, 1);
      expect(GemFunction.lineBlastV.value, 2);
      expect(GemFunction.radialBomb.value, 3);
      expect(GemFunction.chromaticOrb.value, 4);
    });

    test('isSpecial returns true only for non-neutral', () {
      expect(GemFunction.neutral.isSpecial, isFalse);
      expect(GemFunction.lineBlastH.isSpecial, isTrue);
      expect(GemFunction.lineBlastV.isSpecial, isTrue);
      expect(GemFunction.radialBomb.isSpecial, isTrue);
      expect(GemFunction.chromaticOrb.isSpecial, isTrue);
    });

    test('fromValue maps all known values', () {
      for (final f in GemFunction.values) {
        expect(GemFunction.fromValue(f.value), f);
      }
    });

    test('fromValue returns neutral for unknown value', () {
      expect(GemFunction.fromValue(99), GemFunction.neutral);
      expect(GemFunction.fromValue(-1), GemFunction.neutral);
    });

    test('enum has exactly 5 values', () {
      expect(GemFunction.values.length, 5);
    });
  });
}
