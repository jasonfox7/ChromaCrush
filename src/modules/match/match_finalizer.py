"""Match finalization logic for match module.

Encapsulates end-of-match operations: recording match results for both
players, updating ELO ratings, processing card raids, and awarding
victory card rewards. Delegated to by ``MatchService`` and
``MoveProcessor`` when a match completes (both players finished or forfeit).
"""

from __future__ import annotations

import random
from typing import TYPE_CHECKING
from uuid import UUID

from src.core.types.game import PlayerId
from src.modules.match.types import CardRaidResult, MatchRewardResult

if TYPE_CHECKING:
    from src.core.protocols.logger import LoggerProtocol
    from src.modules.cards.service import CardService
    from src.modules.player.protocols import PlayerServiceProtocol
    from src.modules.vault.protocols import VaultServiceProtocol


class MatchFinalizer:
    """Records match results, updates ELO ratings, and processes card raids.

    Handles the post-match bookkeeping that runs when a match completes
    normally (both players exhaust moves) or via forfeit. Created by
    ``MatchService.__init__`` and called via delegation.
    """

    def __init__(
        self,
        logger: LoggerProtocol,
        player_service: PlayerServiceProtocol,
        *,
        card_service: CardService | None = None,
        vault_service: VaultServiceProtocol | None = None,
    ) -> None:
        self._logger = logger
        self._player_service = player_service
        self._card_service = card_service
        self._vault_service = vault_service

    async def finalize_match(
        self,
        player1_id: PlayerId,
        player2_id: PlayerId,
        p1_score: int,
        p2_score: int,
        winner_id: PlayerId | None,
    ) -> tuple[CardRaidResult, MatchRewardResult]:
        """Record match results for both players and update ELO ratings.

        Args:
            player1_id: First player.
            player2_id: Second player.
            p1_score: Player 1's final score.
            p2_score: Player 2's final score.
            winner_id: Winner's ID, or None for a draw.

        Returns:
            Tuple of (CardRaidResult, MatchRewardResult).
        """
        is_draw = winner_id is None

        # Record match result for player 1.
        p1_won = winner_id == player1_id if not is_draw else False
        await self._player_service.record_match_result(
            player_id=player1_id,
            won=p1_won,
            is_draw=is_draw,
            score=p1_score,
            longest_chain=0,  # Already tracked in match record.
            gems_matched=0,  # Already tracked in match record.
        )

        # Record match result for player 2.
        p2_won = winner_id == player2_id if not is_draw else False
        await self._player_service.record_match_result(
            player_id=player2_id,
            won=p2_won,
            is_draw=is_draw,
            score=p2_score,
            longest_chain=0,
            gems_matched=0,
        )

        # Calculate and apply ELO changes.
        if is_draw:
            # For draws, player order doesn't matter.
            elo_change_a, elo_change_b = (
                await self._player_service.calculate_elo_change(
                    winner_id=player1_id,
                    loser_id=player2_id,
                    is_draw=True,
                )
            )
            p1_elo = await self._player_service.get_elo(player1_id)
            p2_elo = await self._player_service.get_elo(player2_id)
            await self._player_service.update_elo(player1_id, p1_elo + elo_change_a)
            await self._player_service.update_elo(player2_id, p2_elo + elo_change_b)
        else:
            assert winner_id is not None
            loser_id = player2_id if winner_id == player1_id else player1_id
            winner_change, loser_change = (
                await self._player_service.calculate_elo_change(
                    winner_id=winner_id,
                    loser_id=loser_id,
                    is_draw=False,
                )
            )
            winner_elo = await self._player_service.get_elo(winner_id)
            loser_elo = await self._player_service.get_elo(loser_id)
            await self._player_service.update_elo(winner_id, winner_elo + winner_change)
            await self._player_service.update_elo(loser_id, loser_elo + loser_change)

        self._logger.info(
            "match.finalized",
            player1_id=str(player1_id),
            player2_id=str(player2_id),
            p1_score=p1_score,
            p2_score=p2_score,
            winner_id=str(winner_id) if winner_id else "draw",
        )

        # Process card raid if there's a winner and card_service is available.
        raid_result = CardRaidResult()
        if winner_id is not None and self._card_service is not None:
            loser_id = player2_id if winner_id == player1_id else player1_id
            raid_result = await self._process_card_raid(winner_id, loser_id)

        # Award victory card reward to the winner.
        reward_result = MatchRewardResult()
        if winner_id is not None and self._card_service is not None:
            reward_result = await self._process_match_reward(winner_id)

        return raid_result, reward_result

    async def _process_card_raid(
        self,
        winner_id: PlayerId,
        loser_id: PlayerId,
    ) -> CardRaidResult:
        """Attempt to steal a random equipped card from the loser.

        If the loser has card-based raid protection (Eternal Guardian,
        Resilient Shield), the raid is blocked entirely. If the loser has
        an active vault shield, the card is unequipped (moved to vault)
        instead of stolen.
        """
        assert self._card_service is not None

        # Check loser's equipped cards for raid protection effects.
        try:
            engine = await self._card_service.build_modifier_engine(loser_id)
            if hasattr(engine, "check_raid_protection"):
                import time

                seed = int(time.time() * 1000) & 0x7FFFFFFF
                blocked, applied = engine.check_raid_protection(seed)
                if blocked:
                    card_name = applied[0].card_name if applied else "a card"
                    self._logger.info(
                        "card_raid.blocked_by_card",
                        winner_id=str(winner_id),
                        loser_id=str(loser_id),
                        card_name=card_name,
                    )
                    return CardRaidResult(
                        occurred=True,
                        blocked_by_card=True,
                        blocked_by_card_name=card_name,
                    )
        except Exception:
            pass  # If engine fails, proceed without card protection.

        # Pick a random equipped card from the loser.
        stolen_card = await self._card_service.steal_random_equipped(loser_id)
        if stolen_card is None:
            return CardRaidResult()  # Loser has no equipped cards.

        # Check if loser is shielded.
        is_shielded = False
        if self._vault_service is not None:
            try:
                is_shielded = await self._vault_service.is_protected(loser_id)
            except Exception:
                pass

        if is_shielded:
            # Shield active: unequip the card (move to vault), don't transfer.
            try:
                await self._card_service.unequip_to_vault(stolen_card.id, loser_id)
            except Exception:
                return CardRaidResult()

            self._logger.info(
                "card_raid.shielded",
                winner_id=str(winner_id),
                loser_id=str(loser_id),
                card_id=stolen_card.card_id,
                card_name=stolen_card.definition.name,
            )
            return CardRaidResult(
                occurred=True,
                stolen_card_id=stolen_card.card_id,
                stolen_card_name=stolen_card.definition.name,
                victim_player_id=loser_id,
                thief_player_id=winner_id,
                was_shielded=True,
                card_unequipped=True,
            )

        # No shield: transfer the card to the winner.
        try:
            await self._card_service.transfer_card(
                card_instance_id=stolen_card.id,
                from_player_id=loser_id,
                to_player_id=winner_id,
            )
        except Exception:
            return CardRaidResult()

        self._logger.info(
            "card_raid.stolen",
            winner_id=str(winner_id),
            loser_id=str(loser_id),
            card_id=stolen_card.card_id,
            card_name=stolen_card.definition.name,
        )
        return CardRaidResult(
            occurred=True,
            stolen_card_id=stolen_card.card_id,
            stolen_card_name=stolen_card.definition.name,
            victim_player_id=loser_id,
            thief_player_id=winner_id,
            was_shielded=False,
            card_unequipped=False,
        )

    # -- Reward tiers (dynamic rarity pools from CardService) ------------------

    _REWARD_TIERS = [
        # (threshold, tier_name, count, rarity)
        (0.01, "1_epic", 1, "epic"),
        (0.06, "1_rare", 1, "rare"),
        (0.31, "3_common", 3, "common"),
        (0.655, "2_common", 2, "common"),
        (1.0, "1_common", 1, "common"),
    ]

    async def _process_match_reward(
        self,
        winner_id: PlayerId,
    ) -> MatchRewardResult:
        """Award random card(s) to the match winner.

        Probability tiers (mutually exclusive):
        1% → 1 epic, 5% → 1 rare, 25% → 3 commons,
        34.5% → 2 commons, 34.5% → 1 common.
        """
        assert self._card_service is not None

        roll = random.random()
        tier_name = ""
        count = 1
        rarity = "common"

        for threshold, name, cnt, rar in self._REWARD_TIERS:
            if roll < threshold:
                tier_name = name
                count = cnt
                rarity = rar
                break

        pool = self._card_service.get_card_ids_by_rarity(rarity)
        if not pool:
            return MatchRewardResult()

        cards: list[dict] = []
        for _ in range(count):
            card_id = random.choice(pool)
            try:
                granted = await self._card_service.grant_card(
                    player_id=UUID(str(winner_id)),
                    card_id=card_id,
                    source="match_reward",
                )
                cards.append(
                    {
                        "card_id": granted.card_id,
                        "name": granted.definition.name,
                        "rarity": granted.definition.rarity,
                    }
                )
            except Exception:
                self._logger.warning(
                    "match_reward.grant_failed",
                    winner_id=str(winner_id),
                    card_id=card_id,
                )

        if not cards:
            return MatchRewardResult()

        self._logger.info(
            "match_reward.awarded",
            winner_id=str(winner_id),
            tier=tier_name,
            card_count=len(cards),
        )
        return MatchRewardResult(
            awarded=True,
            cards=cards,
            tier=tier_name,
        )
