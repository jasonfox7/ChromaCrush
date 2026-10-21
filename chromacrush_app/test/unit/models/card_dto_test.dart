import 'package:flutter_test/flutter_test.dart';
import 'package:chromacrush_app/models/backend_contract.dart';

void main() {
  group('CardDefinitionResponse', () {
    test('fromJson parses all fields including tags list', () {
      final json = {
        'card_id': 42,
        'name': 'Flame Burst',
        'description': 'Deals fire damage to adjacent gems',
        'rarity': 'rare',
        'card_set': 'inferno',
        'set_position': 3,
        'base_value': 150,
        'tags': ['fire', 'damage', 'aoe'],
      };

      final def = CardDefinitionResponse.fromJson(json);
      expect(def.cardId, 42);
      expect(def.name, 'Flame Burst');
      expect(def.description, 'Deals fire damage to adjacent gems');
      expect(def.rarity, 'rare');
      expect(def.cardSet, 'inferno');
      expect(def.setPosition, 3);
      expect(def.baseValue, 150);
      expect(def.tags, ['fire', 'damage', 'aoe']);
    });

    test('fromJson handles empty tags list', () {
      final json = {
        'card_id': 1,
        'name': 'Basic',
        'description': 'A basic card',
        'rarity': 'common',
        'card_set': 'starter',
        'set_position': 1,
        'base_value': 10,
        'tags': <dynamic>[],
      };

      final def = CardDefinitionResponse.fromJson(json);
      expect(def.tags, isEmpty);
    });
  });

  group('PlayerCardResponse', () {
    test('fromJson parses nested definition', () {
      final json = {
        'id': 'pc-abc-123',
        'card_id': 42,
        'definition': {
          'card_id': 42,
          'name': 'Flame Burst',
          'description': 'Deals fire damage to adjacent gems',
          'rarity': 'rare',
          'card_set': 'inferno',
          'set_position': 3,
          'base_value': 150,
          'tags': ['fire', 'damage'],
        },
        'position': 2,
        'level': 5,
        'acquired_at': '2026-02-01T12:00:00Z',
        'source': 'pack_opening',
      };

      final card = PlayerCardResponse.fromJson(json);
      expect(card.id, 'pc-abc-123');
      expect(card.cardId, 42);
      expect(card.definition.name, 'Flame Burst');
      expect(card.definition.rarity, 'rare');
      expect(card.definition.tags, ['fire', 'damage']);
      expect(card.position, 2);
      expect(card.level, 5);
      expect(card.acquiredAt, '2026-02-01T12:00:00Z');
      expect(card.source, 'pack_opening');
    });
  });

  group('EquippedLoadoutResponse', () {
    test('fromJson parses player_id and card list', () {
      final json = {
        'player_id': 'p-xyz-789',
        'cards': [
          {
            'id': 'pc-1',
            'card_id': 10,
            'definition': {
              'card_id': 10,
              'name': 'Ice Shard',
              'description': 'Freezes a column',
              'rarity': 'common',
              'card_set': 'frost',
              'set_position': 1,
              'base_value': 50,
              'tags': ['ice'],
            },
            'position': 0,
            'level': 1,
            'acquired_at': '2026-01-15T00:00:00Z',
            'source': 'starter',
          },
          {
            'id': 'pc-2',
            'card_id': 20,
            'definition': {
              'card_id': 20,
              'name': 'Thunder Strike',
              'description': 'Clears a row',
              'rarity': 'epic',
              'card_set': 'storm',
              'set_position': 5,
              'base_value': 300,
              'tags': ['lightning', 'row_clear'],
            },
            'position': 1,
            'level': 3,
            'acquired_at': '2026-01-20T00:00:00Z',
            'source': 'reward',
          },
        ],
      };

      final loadout = EquippedLoadoutResponse.fromJson(json);
      expect(loadout.playerId, 'p-xyz-789');
      expect(loadout.cards.length, 2);
      expect(loadout.cards[0].definition.name, 'Ice Shard');
      expect(loadout.cards[1].definition.name, 'Thunder Strike');
      expect(loadout.cards[1].level, 3);
    });

    test('fromJson handles empty card list', () {
      final json = {'player_id': 'p-empty', 'cards': <dynamic>[]};

      final loadout = EquippedLoadoutResponse.fromJson(json);
      expect(loadout.playerId, 'p-empty');
      expect(loadout.cards, isEmpty);
    });
  });

  group('PlayerCardsResponse', () {
    test('fromJson parses cards list and total count', () {
      final json = {
        'cards': [
          {
            'id': 'pc-1',
            'card_id': 10,
            'definition': {
              'card_id': 10,
              'name': 'Ice Shard',
              'description': 'Freezes a column',
              'rarity': 'common',
              'card_set': 'frost',
              'set_position': 1,
              'base_value': 50,
              'tags': ['ice'],
            },
            'position': 0,
            'level': 1,
            'acquired_at': '2026-01-15T00:00:00Z',
            'source': 'starter',
          },
        ],
        'total': 25,
        'limit': 50,
        'offset': 0,
        'has_more': false,
      };

      final response = PlayerCardsResponse.fromJson(json);
      expect(response.cards.length, 1);
      expect(response.cards[0].definition.name, 'Ice Shard');
      expect(response.total, 25);
      expect(response.limit, 50);
      expect(response.offset, 0);
      expect(response.hasMore, isFalse);
    });

    test('fromJson handles empty cards with zero total', () {
      final json = {
        'cards': <dynamic>[],
        'total': 0,
        'limit': 50,
        'offset': 0,
        'has_more': false,
      };

      final response = PlayerCardsResponse.fromJson(json);
      expect(response.cards, isEmpty);
      expect(response.total, 0);
    });
  });

  group('MergeResultResponse', () {
    test('fromJson parses new card and consumed IDs', () {
      final json = {
        'new_card': {
          'id': 'pc-merged',
          'card_id': 99,
          'definition': {
            'card_id': 99,
            'name': 'Phoenix Rising',
            'description': 'Reborn from merged flames',
            'rarity': 'legendary',
            'card_set': 'inferno',
            'set_position': 10,
            'base_value': 500,
            'tags': ['fire', 'rebirth'],
          },
          'position': 0,
          'level': 1,
          'acquired_at': '2026-02-10T08:00:00Z',
          'source': 'merge',
        },
        'consumed_card_ids': ['pc-1', 'pc-2', 'pc-3'],
        'source_rarity': 'rare',
        'target_rarity': 'legendary',
      };

      final result = MergeResultResponse.fromJson(json);
      expect(result.newCard.id, 'pc-merged');
      expect(result.newCard.definition.name, 'Phoenix Rising');
      expect(result.newCard.definition.rarity, 'legendary');
      expect(result.consumedCardIds, ['pc-1', 'pc-2', 'pc-3']);
      expect(result.sourceRarity, 'rare');
      expect(result.targetRarity, 'legendary');
    });
  });

  group('CardEquipRequest', () {
    test('toJson produces correct snake_case keys', () {
      const req = CardEquipRequest(cardInstanceId: 'pc-abc-123', slot: 2);

      final json = req.toJson();
      expect(json['card_instance_id'], 'pc-abc-123');
      expect(json['slot'], 2);
      expect(json.length, 2);
    });
  });

  group('CardUnequipRequest', () {
    test('toJson produces correct snake_case keys', () {
      const req = CardUnequipRequest(cardInstanceId: 'pc-def-456');

      final json = req.toJson();
      expect(json['card_instance_id'], 'pc-def-456');
      expect(json.length, 1);
    });
  });

  group('CardReorderRequest', () {
    test('toJson produces correct snake_case keys', () {
      const req = CardReorderRequest(
        cardInstanceId: 'pc-ghi-789',
        newPosition: 4,
      );

      final json = req.toJson();
      expect(json['card_instance_id'], 'pc-ghi-789');
      expect(json['new_position'], 4);
      expect(json.length, 2);
    });
  });
}
