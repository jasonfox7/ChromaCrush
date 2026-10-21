# Project Skeleton — 523 files

## Import Legend
| Token | Import |
|---|---|
| I1 | `from __future__ import annotations` |
| I2 | `from datetime import datetime` |
| I3 | `from uuid import UUID` |
| I4 | `from typing import TYPE_CHECKING` |
| I5 | `from datetime import timezone` |
| I6 | `from src.core.types.game import PlayerId` |
| I7 | `from typing import Any` |
| I8 | `from src.core.protocols.logger import LoggerProtocol` |
| I9 | `from src.core.protocols.error_service import ErrorServiceProtocol` |
| I10 | `from dataclasses import dataclass` |
| I11 | `from src.core.errors import AppError` |
| I12 | `import pytest` |
| I13 | `from typing import Protocol` |
| I14 | `from sqlalchemy.dialects.postgresql import UUID` |
| I15 | `from src.core.protocols.data_context import DataContextProtocol` |
| I16 | `from src.core.types.board import BoardState` |
| I17 | `from src.data.models.base import Base` |
| I18 | `from src.core.protocols.config import ConfigProtocol` |
| I19 | `from sqlalchemy import select` |
| I20 | `from sqlalchemy.orm import Mapped` |
| I21 | `from sqlalchemy.orm import mapped_column` |
| I22 | `from datetime import date` |
| I23 | `from src.core.types.game import Position` |
| I24 | `from dataclasses import field` |
| I25 | `from src.core.types.game import MatchId` |
| I26 | `from sqlalchemy import DateTime` |
| I27 | `from uuid import uuid4` |
| I28 | `from sqlalchemy import ForeignKey` |
| I29 | `from datetime import timedelta` |
| I30 | `from src.core.types.game import GemType` |
| I31 | `package:flutter/material.dart` |
| I32 | `from src.core.types.player import PlayerType` |
| I33 | `import uuid` |
| I34 | `from sqlalchemy import Integer` |
| I35 | `from src.modules.api.adapters.response import ResponseAdapter` |
| I36 | `from src.data.models.base import UUIDMixin` |
| I37 | `from sqlalchemy import String` |
| I38 | `from src.core.types.game import EventId` |
| I39 | `from src.core.types.game import Move` |
| I40 | `from tests.mocks.services import MockLogService` |
| I41 | `from unittest.mock import AsyncMock` |
| I42 | `../../theme/chroma_theme.dart` |
| I43 | `from enum import Enum` |
| I44 | `from typing import Sequence` |
| I45 | `from typing import Union` |
| I46 | `from tests.mocks.services import MockConfigService` |
| I47 | `from tests.mocks.services import MockErrorService` |
| I48 | `import click` |
| I49 | `from alembic import op` |
| I50 | `import sqlalchemy as sa` |
| I51 | `from fastapi import Request` |
| I52 | `package:provider/provider.dart` |
| I53 | `dart:async` |
| I54 | `import numpy as np` |
| I55 | `from sqlalchemy import func` |
| I56 | `from unittest.mock import MagicMock` |
| I57 | `import json` |
| I58 | `from rich.table import Table` |
| I59 | `from fastapi import APIRouter` |
| I60 | `../../theme/glass_panel.dart` |
| I61 | `package:go_router/go_router.dart` |
| I62 | `from rich.console import Console` |
| I63 | `from src.core.types.board import MatchResult` |
| I64 | `from fastapi import Depends` |
| I65 | `from src.modules.api.dependencies import get_correlation_id` |
| I66 | `from src.modules.api.dependencies import get_current_player_id` |
| I67 | `from src.modules.api.dependencies import get_response_adapter` |
| I68 | `from pydantic import BaseModel` |
| I69 | `from pydantic import ConfigDict` |
| I70 | `from rich.panel import Panel` |
| I71 | `from src.core.composition_root import ApplicationContext` |
| I72 | `from fastapi import FastAPI` |
| I73 | `from src.modules.api.adapters.bot_hints import BotHintGenerator` |
| I74 | `from src.modules.events.types import EventStatus` |
| I75 | `from src.data.models.base import TimestampMixin` |
| I76 | `from src.modules.player.protocols import PlayerServiceProtocol` |
| I77 | `dart:math` |
| I78 | `dart:ui` |
| I79 | `../models/backend_contract.dart` |
| I80 | `package:flutter/cupertino.dart` |
| I81 | `package:flutter_test/flutter_test.dart` |
| I82 | `import asyncio` |
| I83 | `from src.cli.helpers.async_bridge import run_cli_async` |
| I84 | `from src.modules.ads.types import AdFreeReason` |
| I85 | `import time` |
| I86 | `from src.core.types.player import Player` |
| I87 | `from sqlalchemy.dialects.postgresql import JSONB` |
| I88 | `from starlette.middleware.base import BaseHTTPMiddleware` |
| I89 | `from src.cli.helpers.async_bridge import resolve_player` |
| I90 | `from src.modules.ads.types import AdType` |
| I91 | `from src.modules.payments.types import PaymentProvider` |
| I92 | `from src.modules.board.types import MoveProcessingResult` |
| I93 | `from starlette.middleware.base import RequestResponseEndpoint` |
| I94 | `from starlette.requests import Request` |
| I95 | `from starlette.responses import Response` |
| I96 | `package:flame/components.dart` |
| I97 | `from src.modules.matchmaking.types import PoolType` |
| I98 | `from src.modules.api.middleware.error_handler import register_error_handlers` |
| I99 | `from pydantic import Field` |
| I100 | `../config/visual_config.dart` |
| I101 | `../config/visual_theme_service.dart` |
| I102 | `../../services/api_client.dart` |
| I103 | `import random` |
| I104 | `from src.modules.events.dto import EventCreate` |
| I105 | `from src.modules.events.types import EventType` |
| I106 | `from src.core.types.game import ArtifactId` |
| I107 | `from sqlalchemy import Text` |
| I108 | `from src.modules.events.dto import EventDbUpdate` |
| I109 | `from src.modules.auth.protocols import AuthServiceProtocol` |
| I110 | `../extensions/grid_math.dart` |
| I111 | `package:flame/game.dart` |
| I112 | `../../models/backend_contract.dart` |
| I113 | `../../services/session_manager.dart` |
| I114 | `from pathlib import Path` |
| I115 | `from src.modules.ads.types import AdRequestId` |
| I116 | `from src.modules.player.service import PlayerService` |
| I117 | `from src.modules.match.types import MatchType` |
| I118 | `from src.modules.payments.types import PurchaseReceipt` |
| I119 | `from src.modules.vault.dto import ArtifactRarity` |
| I120 | `from src.data.models.player import PlayerModel` |
| I121 | `from src.modules.board.service import BoardService` |
| I122 | `from src.core.types.player import PlayerStats` |
| I123 | `from sqlalchemy import Boolean` |
| I124 | `from src.modules.events.dto import ParticipantUpdate` |
| I125 | `from src.modules.ads.types import AdImpression` |
| I126 | `from src.modules.match.types import MatchState` |
| I127 | `from src.modules.events.types import EventParticipant` |
| I128 | `../services/audio_engine.dart` |
| I129 | `dart:convert` |
| I130 | `../services/event_bus.dart` |
| I131 | `../../services/event_bus.dart` |
| I132 | `../../config/animation_timings.dart` |
| I133 | `from src.modules.ads.types import StatsPeriod` |
| I134 | `from src.modules.ads.types import AdProviderResponse` |
| I135 | `from src.modules.ads.types import BotAdAttributionReport` |
| I136 | `from src.modules.energy.dto import BonusSource` |
| I137 | `from src.modules.payments.types import ProductId` |
| I138 | `from src.modules.ads.types import AdFreeStatus` |
| I139 | `from src.modules.payments.types import ReceiptValidationResult` |
| I140 | `from src.core.types.board import MatchGroup` |
| I141 | `from src.modules.cards.service import CardService` |
| I142 | `from src.core.types.player import EnergyState` |
| I143 | `from sqlalchemy import UniqueConstraint` |
| I144 | `from src.modules.match.dto import MatchUpdate` |
| I145 | `from src.modules.matchmaking.types import QueueEntryData` |
| I146 | `from src.modules.ads.dto import AdImpressionCreate` |
| I147 | `from src.modules.ads.protocols import PlayerServiceProtocol` |
| I148 | `from fastapi import Query` |
| I149 | `from src.modules.events.types import Event` |
| I150 | `from src.modules.board._constants import OBSTACLE_COLOR` |
| I151 | `from src.modules.match.types import MatchStatus` |
| I152 | `from src.modules.special_gems.types import SpecialGemEffect` |
| I153 | `from src.modules.scoring.types import SpecialGemBonus` |
| I154 | `from starlette.testclient import TestClient` |
| I155 | `package:flutter/services.dart` |
| I156 | `../services/haptics_engine.dart` |
| I157 | `../../config/visual_theme_service.dart` |
| I158 | `../../services/audio_engine.dart` |
| I159 | `../../view_models/match_view_model.dart` |
| I160 | `from src.modules.ads.service import AdRepositoryBundle` |
| I161 | `from src.modules.ads.service import AdService` |
| I162 | `from src.modules.ads.types import BannerPlacement` |
| I163 | `from src.modules.ads.types import InterstitialTrigger` |
| I164 | `from src.modules.ads.types import RewardedAdType` |
| I165 | `from src.data.repositories.energy_state_repository import SQLAlchemyEnergyStateRepository` |
| I166 | `from src.data.repositories.player_stats_repository import SQLAlchemyPlayerStatsRepository` |
| I167 | `from src.modules.bot_earnings.types import PayoutStatus` |
| I168 | `from src.modules.events.dto import EventUpdate` |
| I169 | `from src.modules.events.types import MatchEventStats` |
| I170 | `from src.core.types.game import GemFunction` |
| I171 | `from src.modules.board.types import CascadeStep` |
| I172 | `from sqlalchemy import update` |
| I173 | `from src.modules.scoring.service import ScoringService` |
| I174 | `from src.data.models.match import MatchModel` |
| I175 | `from src.modules.events.dto import EventMatchCreate` |
| I176 | `from src.modules.events.dto import ParticipantCreate` |
| I177 | `from src.modules.ads.dto import AdRequestUpdate` |
| I178 | `from src.modules.ads.types import EventAdOpportunity` |
| I179 | `from src.modules.ads.types import MatchAdAttribution` |
| I180 | `from src.modules.ads.types import PlayerAdStats` |
| I181 | `from src.modules.ads.protocols import AdFreeStatusRepositoryProtocol` |
| I182 | `from src.modules.ads.protocols import AdImpressionRepositoryProtocol` |
| I183 | `from src.core.types.pagination import PaginatedResult as PaginatedResult` |
| I184 | `from src.modules.energy.protocols import EnergyServiceProtocol` |
| I185 | `from src.modules.api.dependencies import get_auth_type` |
| I186 | `from src.modules.events.types import EventLeaderboard` |
| I187 | `from src.modules.match.types import MoveSubmissionResult` |
| I188 | `from src.modules.vault.dto import CollectionProgress` |
| I189 | `from src.modules.vault.dto import VaultArtifact` |
| I190 | `from src.modules.vault.dto import PaginatedResult` |
| I191 | `from src.modules.events.dto import PaginatedResult` |
| I192 | `from src.modules.events.types import EventSummary` |
| I193 | `from src.modules.events.protocols import EventRepositoryProtocol` |
| I194 | `from src.modules.scoring.types import MoveScore` |
| I195 | `from fastapi.testclient import TestClient` |
| I196 | `package:flutter/painting.dart` |
| I197 | `../models/gem_type.dart` |
| I198 | `background_layer.dart` |
| I199 | `board_layer.dart` |
| I200 | `particle_layer.dart` |
| I201 | `../services/api_client.dart` |
| I202 | `../../services/haptics_engine.dart` |
| I203 | `../../extensions/grid_math.dart` |
| I204 | `package:chromacrush_app/models/backend_contract.dart` |
| I205 | `from src.core.composition_root import load_config` |
| I206 | `from src.cli.helpers.display import console` |
| I207 | `from src.modules.board_gen.types import BoardGenOptions` |
| I208 | `from src.modules.board_gen.types import MatchType` |
| I209 | `from src.modules.bot_earnings.service import BotEarningsService` |
| I210 | `from src.modules.bot_earnings.types import EarningsPeriod` |
| I211 | `from src.modules.bot_earnings.types import PayoutRequestId` |
| I212 | `from src.modules.matchmaking.types import MatchmakingStatus` |
| I213 | `from src.modules.payments.service import PaymentService` |
| I214 | `from src.modules.payments.types import RefundNotification` |
| I215 | `from src.modules.special_gems.service import SpecialGemsService` |
| I216 | `from src.modules.board_gen.service import BoardGenService` |
| I217 | `from src.modules.match.service import MatchRepositoryBundle` |
| I218 | `from src.core.protocols.correlation import correlation_id_var` |
| I219 | `from src.core.types.auth import ApiKeyInfo` |
| I220 | `from src.data.models.artifact_definition import ArtifactDefinitionModel` |
| I221 | `from src.data.models.match_move import MatchMoveModel` |
| I222 | `from src.data.models.event import EventModel` |
| I223 | `from sqlalchemy import update as sa_update` |
| I224 | `from src.modules.ads.dto import AdRequestCreate` |
| I225 | `from src.modules.ads.dto import PaginatedResult` |
| I226 | `from src.modules.ads.types import AdRequestStatus` |
| I227 | `from src.modules.ads.types import EventAdRewardResult` |
| I228 | `from src.modules.ads.types import InterstitialAdResult` |
| I229 | `from src.modules.ads.types import RewardedVideoRequest` |
| I230 | `from src.modules.ads.types import RewardedVideoResult` |
| I231 | `from src.modules.ads._helpers import build_impression` |
| I232 | `from src.modules.vault.protocols import VaultServiceProtocol` |
| I233 | `from src.modules.events.types import LeaderboardEntry` |
| I234 | `from src.modules.match.types import MatchSummary` |
| I235 | `from src.modules.match.types import MoveRecord` |
| I236 | `from src.modules.match.types import PlayerBoardState` |
| I237 | `from src.modules.vault.dto import RaidResult` |
| I238 | `from src.modules.vault.dto import Shield` |
| I239 | `from src.modules.vault.dto import VaultSummary` |
| I240 | `from src.modules.auth.dto import RateLimitStatus` |
| I241 | `from src.modules.board_gen.types import GeneratedBoard` |
| I242 | `from src.modules.events.types import PlayerEventRank` |
| I243 | `from src.modules.events.types import PlayerEventSummary` |
| I244 | `from src.modules.events.types import ScheduledEventResult` |
| I245 | `from src.modules.events.protocols import EventLeaderboardRepositoryProtocol` |
| I246 | `from src.modules.events.protocols import EventParticipantRepositoryProtocol` |
| I247 | `from src.modules.events.protocols import PlayerServiceProtocol` |
| I248 | `from src.modules.matchmaking.types import MatchmakingResult` |
| I249 | `from src.modules.payments.types import PurchaseRecord` |
| I250 | `from src.modules.special_gems.types import FusionEffect` |
| I251 | `from src.modules.vault.dto import ArtifactDefinition` |
| I252 | `package:flutter/foundation.dart` |
| I253 | `package:flame/effects.dart` |
| I254 | `../config/animation_timings.dart` |
| I255 | `cascade_animator.dart` |
| I256 | `../services/session_manager.dart` |
| I257 | `gem_shader_library.dart` |
| I258 | `../config/game_config.dart` |
| I259 | `dart:io` |
| I260 | `package:http/http.dart` |
| I261 | `package:chromacrush_app/services/event_bus.dart` |
| I262 | `package:chromacrush_app/services/session_manager.dart` |
| I263 | `from src.cli.helpers.display import render_board` |
| I264 | `from src.cli.helpers.service_factory import build_sync_services` |
| I265 | `from src.data.repositories.player_repository import SQLAlchemyPlayerRepository` |
| I266 | `from src.modules.auth.service import AuthService` |
| I267 | `from src.modules.energy.service import EnergyService` |
| I268 | `from src.modules.match.service import MatchService` |
| I269 | `from src.modules.matchmaking.service import MatchmakingService` |
| I270 | `from src.modules.vault.service import VaultService` |
| I271 | `from src.modules.events.service import EventService` |
| I272 | `import os` |
| I273 | `from src.core.types.auth import AuthToken` |
| I274 | `from typing import NewType` |
| I275 | `from typing import Generic` |
| I276 | `from typing import TypeVar` |
| I277 | `from src.data.models.player_stats import PlayerStatsModel` |
| I278 | `from src.data.models.energy_state import EnergyStateModel` |
| I279 | `from src.data.models.session import SessionModel` |
| I280 | `from src.data.models.api_key import ApiKeyModel` |
| I281 | `from src.data.models.vault_artifact import VaultArtifactModel` |
| I282 | `from src.data.models.vault_shield import VaultShieldModel` |
| I283 | `from src.data.models.raid_log import RaidLogModel` |
| I284 | `from src.data.models.event_participant import EventParticipantModel` |
| I285 | `from src.data.models.event_match import EventMatchRecordModel` |
| I286 | `from src.data.models.ad_request import AdRequestModel` |
| I287 | `from src.data.models.ad_impression import AdImpressionModel` |
| I288 | `from src.data.models.ad_free_status import AdFreeStatusModel` |
| I289 | `from src.data.models.ad_reward import AdRewardModel` |
| I290 | `from src.data.models.event_ad_opportunity import EventAdOpportunityModel` |
| I291 | `from src.data.models.event_ad_claim import EventAdClaimModel` |
| I292 | `from src.data.models.product import ProductModel` |
| I293 | `from src.data.models.purchase_intent import PurchaseIntentModel` |
| I294 | `from src.data.models.purchase import PurchaseModel` |
| I295 | `from src.data.models.receipt_validation import ReceiptValidationModel` |
| I296 | `from src.data.models.refund_notification import RefundNotificationModel` |
| I297 | `from src.data.models.bot_earnings_ledger import BotEarningsLedgerModel` |
| I298 | `from src.data.models.bot_attribution_entry import BotAttributionEntryModel` |
| I299 | `from src.data.models.bot_payout_request import BotPayoutRequestModel` |
| I300 | `from src.data.models.bot_earnings_daily import BotEarningsDailyModel` |
| I301 | `from sqlalchemy import Date` |
| I302 | `from sqlalchemy import BigInteger` |
| I303 | `from src.modules.match.dto import MatchCreate` |
| I304 | `from src.modules.match.dto import MoveCreate` |
| I305 | `from src.modules.ads.dto import AdFreeStatusUpsert` |
| I306 | `from src.modules.ads.dto import AdRewardCreate` |
| I307 | `from src.modules.bot_earnings.dto import AttributionEntryCreate` |
| I308 | `from src.modules.bot_earnings.dto import DailyEarningsUpsert` |
| I309 | `from src.modules.bot_earnings.dto import EarningsLedgerCreate` |
| I310 | `from src.modules.bot_earnings.dto import EarningsLedgerUpdate` |
| I311 | `from src.modules.bot_earnings.dto import PayoutRequestCreate` |
| I312 | `from src.modules.bot_earnings.dto import PayoutRequestUpdate` |
| I313 | `from src.data.protocols.campaign_attempt_repository import CampaignAttemptRecord` |
| I314 | `from src.modules.ads.dto import EventAdClaimCreate` |
| I315 | `from src.modules.payments.dto import PurchaseIntentCreate` |
| I316 | `from src.modules.payments.dto import PurchaseIntentUpdate` |
| I317 | `from src.modules.payments.dto import PurchaseCreate` |
| I318 | `from src.modules.payments.dto import PurchaseUpdate` |
| I319 | `from src.modules.payments.dto import ReceiptValidationCreate` |
| I320 | `from src.modules.payments.dto import ReceiptValidationUpdate` |
| I321 | `from src.modules.payments.dto import RefundNotificationCreate` |
| I322 | `from src.modules.ads.types import AdEligibility` |
| I323 | `from typing import Callable` |
| I324 | `from src.modules.ads.protocols import AdRequestRepositoryProtocol` |
| I325 | `from src.modules.ads._helpers import calc_revenue` |
| I326 | `from src.modules.events.protocols import EventServiceProtocol` |
| I327 | `from src.modules.match.protocols import MatchServiceProtocol` |
| I328 | `from src.modules.api.middleware.auth import AuthMiddleware` |
| I329 | `from src.modules.api.middleware.correlation import CorrelationMiddleware` |
| I330 | `from src.modules.api.middleware.rate_limit import RateLimitMiddleware` |
| I331 | `from starlette.responses import JSONResponse` |
| I332 | `from src.modules.player.dto import PlayerUpdate` |
| I333 | `from src.modules.auth.dto import AuthResult` |
| I334 | `import re` |
| I335 | `import hashlib` |
| I336 | `from src.modules.board_gen.protocols import BoardGenServiceProtocol` |
| I337 | `from src.modules.bot_earnings.dto import PaginatedResult` |
| I338 | `from src.modules.bot_earnings.types import AttributionEntry` |
| I339 | `from src.modules.bot_earnings.types import AttributionSyncResult` |
| I340 | `from src.modules.bot_earnings.types import BulkSyncResult` |
| I341 | `from src.modules.bot_earnings.types import DailyEarnings` |
| I342 | `from src.modules.bot_earnings.types import EarningsBalance` |
| I343 | `from src.modules.bot_earnings.types import EarningsSummary` |
| I344 | `from src.modules.bot_earnings.types import PayoutRequest` |
| I345 | `from src.modules.events.types import EventFinalizationResult` |
| I346 | `from src.modules.events.types import RewardTier` |
| I347 | `from src.modules.events.types import ScoringType` |
| I348 | `from src.modules.events.protocols import EnergyServiceProtocol` |
| I349 | `from src.modules.matchmaking.types import QueueEntry` |
| I350 | `from src.modules.matchmaking.types import QueueStats` |
| I351 | `from src.modules.matchmaking.types import QueueStatus` |
| I352 | `from src.modules.payments.dto import PaginatedResult` |
| I353 | `from src.modules.payments.types import PlayerPurchaseStatus` |
| I354 | `from src.modules.payments.types import Product` |
| I355 | `from src.modules.payments.types import PurchaseId` |
| I356 | `from src.modules.payments.types import PurchaseIntent` |
| I357 | `from src.modules.payments.types import PurchaseResult` |
| I358 | `from src.modules.payments.types import PurchaseStatus` |
| I359 | `from src.modules.payments.types import RefundResult` |
| I360 | `from src.modules.payments.types import RestoreResult` |
| I361 | `from uuid import UUID as _UUID` |
| I362 | `from src.modules.player.dto import PaginatedResult` |
| I363 | `from src.modules.special_gems.types import SPECIAL_GEM_TYPES` |
| I364 | `from src.modules.vault.dto import RaidEligibility` |
| I365 | `from src.modules.vault.dto import RaidLog` |
| I366 | `from unittest.mock import patch` |
| I367 | `from tests.unit.modules.api.conftest import TEST_PLAYER_ID` |
| I368 | `../services/intensity_service.dart` |
| I369 | `animation_sequencer.dart` |
| I370 | `input_handler.dart` |
| I371 | `player_status_bar.dart` |
| I372 | `../../config/game_config.dart` |
| I373 | `../../view_models/campaign_view_model.dart` |
| I374 | `import sys` |
| I375 | `from src.core.composition_root import create_application_context` |
| I376 | `from src.core.composition_root import shutdown_application_context` |
| I377 | `from src.data.repositories.ad_free_status_repository import SQLAlchemyAdFreeStatusRepository` |
| I378 | `from src.data.repositories.ad_impression_repository import SQLAlchemyAdImpressionRepository` |
| I379 | `from src.data.repositories.ad_request_repository import SQLAlchemyAdRequestRepository` |
| I380 | `from src.data.repositories.ad_reward_repository import SQLAlchemyAdRewardRepository` |
| I381 | `from src.data.repositories.event_ad_claim_repository import SQLAlchemyEventAdClaimRepository` |
| I382 | `from src.data.repositories.event_ad_opportunity_repository import SQLAlchemyEventAdOpportunityRepository` |
| I383 | `from src.data.repositories.event_repository import SQLAlchemyEventRepository` |
| I384 | `from src.data.repositories.bot_attribution_entry_repository import SQLAlchemyAttributionEntryRepository` |
| I385 | `from src.data.repositories.bot_daily_earnings_repository import SQLAlchemyDailyEarningsRepository` |
| I386 | `from src.data.repositories.bot_earnings_ledger_repository import SQLAlchemyEarningsLedgerRepository` |
| I387 | `from src.data.repositories.bot_payout_request_repository import SQLAlchemyPayoutRequestRepository` |
| I388 | `from src.modules.payments.service import PaymentRepositoryBundle` |
| I389 | `from src.data.repositories.product_repository import SQLAlchemyProductRepository` |
| I390 | `from src.data.repositories.purchase_intent_repository import SQLAlchemyPurchaseIntentRepository` |
| I391 | `from src.data.repositories.purchase_repository import SQLAlchemyPurchaseRepository` |
| I392 | `from src.data.repositories.receipt_validation_repository import SQLAlchemyReceiptValidationRepository` |
| I393 | `from src.data.repositories.refund_notification_repository import SQLAlchemyRefundNotificationRepository` |
| I394 | `from src.core.types.game import is_mega_gem` |
| I395 | `from src.core.types.game import decode_mega_gem` |
| I396 | `from src.core.error_service import ErrorService` |
| I397 | `from src.core.logger import LogService` |
| I398 | `from src.core.config import ConfigService` |
| I399 | `from src.core.data_context import DataContext` |
| I400 | `from src.data.repositories.session_repository import SQLAlchemySessionRepository` |
| I401 | `from src.data.repositories.api_key_repository import SQLAlchemyApiKeyRepository` |
| I402 | `from src.modules.economy.service import EconomyService` |
| I403 | `from src.modules.campaign.service import CampaignService` |
| I404 | `from src.core.types.auth import TokenType` |
| I405 | `from src.core.types.websocket import WSChannel` |
| I406 | `from src.core.types.websocket import WSMessage` |
| I407 | `from src.core.types.websocket import WSMessageType` |
| I408 | `from src.data.protocols.energy_state_repository import EnergyStateRepositoryProtocol` |
| I409 | `from src.data.protocols.gold_balance_repository import GoldBalanceRepositoryProtocol` |
| I410 | `from src.modules.ads.dto import EventAdOpportunityCreate` |
| I411 | `import dataclasses` |
| I412 | `from src.modules.ads.protocols import AdServiceProtocol` |
| I413 | `from src.modules.ads.types import AdContext` |
| I414 | `from src.modules.ads._helpers import build_ad_free_status` |
| I415 | `from src.modules.ads._helpers import guard_ad_free` |
| I416 | `from src.modules.ads.protocols import AdProviderProtocol` |
| I417 | `from src.modules.bot_earnings.protocols import BotEarningsServiceProtocol` |
| I418 | `from src.modules.matchmaking.protocols import MatchmakingServiceProtocol` |
| I419 | `from src.modules.payments.protocols import PaymentServiceProtocol` |
| I420 | `from src.modules.api.websocket.channels import ChannelManager` |
| I421 | `from src.modules.api.websocket.manager import ConnectionManager` |
| I422 | `import secrets` |
| I423 | `from src.modules.player.validation import validate_username` |
| I424 | `from starlette.websockets import WebSocket` |
| I425 | `from src.modules.auth.dto import ApiKeyCreationResult` |
| I426 | `from src.modules.auth.dto import SessionInfo` |
| I427 | `import jwt` |
| I428 | `from src.core.types.game import FUNCTION_TO_SPECIAL` |
| I429 | `from src.core.types.game import SPECIAL_TO_FUNCTION` |
| I430 | `from src.core.types.game import encode_mega_gem` |
| I431 | `from src.modules.board_gen.types import GenerationMetadata` |
| I432 | `from src.modules.board_gen.types import StartingSpecial` |
| I433 | `from src.modules.special_gems.protocols import SpecialGemsServiceProtocol` |
| I434 | `from src.modules.cards.modifier_types import CardModifierDef` |
| I435 | `from src.modules.economy.dto import BuyResult` |
| I436 | `from src.modules.economy.dto import GoldInfo` |
| I437 | `from src.modules.economy.dto import MarketplaceItem` |
| I438 | `from src.modules.economy.dto import SellResult` |
| I439 | `from src.modules.energy.dto import BonusGrantResult` |
| I440 | `from src.modules.energy.dto import EnergyConsumeResult` |
| I441 | `from src.modules.energy.dto import EnergyInfo` |
| I442 | `from src.modules.energy.dto import LoginResult` |
| I443 | `from src.modules.energy.dto import RegenResult` |
| I444 | `from src.modules.energy.dto import StreakInfo` |
| I445 | `from src.modules.energy.dto import TimeToHeartResult` |
| I446 | `from src.modules.events.types import BonusCondition` |
| I447 | `from src.modules.events.types import EntryRequirements` |
| I448 | `from src.modules.events.types import RewardItem` |
| I449 | `from src.modules.events._data_mapper import parse_reward_tiers` |
| I450 | `from src.modules.match.types import PlayerMatchState` |
| I451 | `from src.modules.match.dto import PaginatedResult` |
| I452 | `from src.modules.payments.types import ProductType` |
| I453 | `from src.modules.payments.types import PurchaseIntentStatus` |
| I454 | `from src.modules.player.dto import EnergyStateUpdate` |
| I455 | `from src.modules.scoring.types import CascadeStepScore` |
| I456 | `from src.modules.scoring.types import MatchGroupScore` |
| I457 | `from src.modules.scoring.types import MatchScore` |
| I458 | `from src.modules.special_gems.types import FusionType` |
| I459 | `from src.data.protocols.artifact_definition_repository import ArtifactDefinitionRepositoryProtocol` |
| I460 | `from src.data.protocols.vault_artifact_repository import VaultArtifactRepositoryProtocol` |

### `tutorial_script.json` (json)
  keys: seed, initial_board, steps

### `chromacrush_app/assets/config/campaign_levels.json` (json)
  keys: (array of 100)

### `chromacrush_app/assets/config/tutorial_script.json` (json)
  keys: seed, initial_board, steps

### `chromacrush_app/assets/config/visual_theme.json` (json)
  keys: version, gem_colors, gem_shapes, gem_shader, special_symbols, gem_names, special_names, mega_names, particle_colors, chromatic_rain_colors, victory_confetti_colors, background

### `chromacrush_app/lib/config.dart` (dart)
  classes: AppConfig

### `chromacrush_app/lib/main.dart` (dart)
  imports: I252, I31, I52, audio/soloud_audio_engine.dart, config.dart, config/visual_theme_service.dart, services/audio_engine.dart, services/bot_player_service.dart, services/debug_logger.dart, services/event_bus.dart, services/haptics_engine.dart, services/http_api_client.dart, services/api_client.dart, services/intensity_service.dart, services/session_manager.dart, services/iap_service.dart, services/token_storage.dart, navigation/app_router.dart, theme/chroma_theme.dart, view_models/campaign_view_model.dart, view_models/match_view_model.dart
  classes: ChromaCrushApp
  functions: build, main

### `chromacrush_app/lib/audio/sfx_synth.dart` (dart)
  imports: I77, dart:typed_data, ../config/audio_config.dart, sound_bank.dart
  functions: _adsrExp, _encodeWav, _fmSample, _harmonicSum, _waveform, synthesizeWav

### `chromacrush_app/lib/audio/soloud_audio_engine.dart` (dart)
  imports: I77, I155, package:flutter_soloud/flutter_soloud.dart, ../config/audio_config.dart, I128, sfx_synth.dart, sound_bank.dart
  classes: SoLoudAudioEngine
  functions: _loadAllSfx, _setupGlobalFilters, _updateMusicVolume, discoverMenuTracks, dispose, initialize, playMenuMusic, playMusic, playSfx, setMasterVolume, setMusicHighPass, setMusicSpeed, setMusicVolume, setSfxVolume, stopMusic

### `chromacrush_app/lib/audio/sound_bank.dart` (dart)
  imports: I128
  classes: SfxRecipe

### `chromacrush_app/lib/config/visual_config.dart` (dart)
  imports: I78

### `chromacrush_app/lib/config/visual_theme_service.dart` (dart)
  imports: I129, I78, I155
  classes: VisualThemeBase, VisualThemeService
  functions: _parse, _parseColorList, _useDefaults, gemName, gemShape, load, megaName, specialName, specialSymbol

### `chromacrush_app/lib/extensions/flame_effects_ext.dart` (dart)
  imports: I77, I96, I253, I196, I100
  classes: ElasticBounceController, ShakeController, FlashOverlay
  functions: advance, recede, setToEnd, setToStart, update

### `chromacrush_app/lib/extensions/grid_math.dart` (dart)
  imports: I96
  classes: BoardLayout
  functions: isAdjacent

### `chromacrush_app/lib/game/animation_sequencer.dart` (dart)
  imports: ../audio/sound_bank.dart, I254, I100, I110, I79, I197, ../models/match_event.dart, I128, I130, I156, I198, I199, I255, I200
  classes: AnimationSequencer
  functions: _addRippleAtCentroid, _playEvent, playCascadeSteps, playMoveResult, playSequence

### `chromacrush_app/lib/game/background_layer.dart` (dart)
  imports: I77, dart:typed_data, I78, I96, I155, I100, I101
  classes: BackgroundLayer
  functions: _drawLayer, _drawRipples, addRipple, onLoad, render, setIntensity, update

### `chromacrush_app/lib/game/board_differ.dart` (dart)
  imports: ../models/match_event.dart
  classes: BoardDiffer
  functions: derive

### `chromacrush_app/lib/game/board_layer.dart` (dart)
  imports: I53, I96, I253, package:flame/events.dart, I254, I101, I110, I79, I197, gem_component.dart
  classes: BoardLayer
  functions: Function, _animateObstacleShatter, animateAttraction, animateDrops, animateFill, animateRemoval, animateSwap, flashPositions, loadBoard, onDragCancel, onDragEnd, onDragStart, onDragUpdate, onLoad, syncToBoard

### `chromacrush_app/lib/game/campaign_game.dart` (dart)
  imports: I111, I196, I100, I101, I110, I79, I201, I128, ../services/debug_logger.dart, I130, I156, I368, I256, I369, I198, I199, I255, game_loadout_mixin.dart, I257, I370, I200, I371
  classes: CampaignGame
  functions: Function, _onGemTapped, _onMegaActivated, _onSwapCommitted, loadBoard, onLoad, onPeriodicShuffleTriggered, update

### `chromacrush_app/lib/game/cascade_animator.dart` (dart)
  imports: I53, I96, I253, I111, package:flutter/animation.dart, I254, I100, ../extensions/flame_effects_ext.dart
  classes: CascadeAnimator, _ShakeEffect
  functions: apply, onFinish, playFusionSequence, screenFlash, screenShake, zoomPulse

### `chromacrush_app/lib/game/chroma_crush_game.dart` (dart)
  imports: I111, I196, I100, I101, I110, I79, I201, I128, ../services/debug_logger.dart, I130, I156, I368, I256, I369, I198, I199, I255, game_loadout_mixin.dart, I257, I370, I200, I371
  classes: ChromaCrushGame
  functions: Function, _onGemTapped, _onMegaActivated, _onSwapCommitted, loadBoard, onLoad, onPeriodicShuffleTriggered, update

### `chromacrush_app/lib/game/game_loadout_mixin.dart` (dart)
  imports: I53, I77, I111, I155, I110, I79, I201, I128, I130, I368, I198, I199, I200, I371
  classes: GameLoadoutMixin
  functions: _startPeriodicShuffleTimers, applyIntensity, cancelPeriodicShuffleTimers, discoverMusicTracks, handleSelectionChanged, loadEquippedCards, loadMegaInventory, onPeriodicShuffleTriggered, playRandomMusicTrack, reloadEquippedCards

### `chromacrush_app/lib/game/gem_component.dart` (dart)
  imports: I53, I78, I196, I96, I253, package:flame/events.dart, I254, I100, I101, ../extensions/flame_effects_ext.dart, I197, I257
  classes: GemComponent
  functions: Function, _drawFallbackShape, _labelText, _renderFallback, _renderShader, _updatePaints, animateAppear, animateMoveTo, animateMoveToElastic, animatePulse, animateRemoval, onLoad, onTapUp, render, setFlashOverlay, setSelected, update, updateGemFunction, updateGemType, updateGridPosition

### `chromacrush_app/lib/game/gem_shader_library.dart` (dart)
  imports: I78
  classes: GemShaderLibrary, GemUniforms, RippleUniforms
  functions: load, rippleOriginX, rippleOriginY, rippleStartTime

### `chromacrush_app/lib/game/input_handler.dart` (dart)
  imports: I258, I110
  classes: InputHandler
  functions: Function, _commitSwap, _deselect, _select, onAnimationComplete, onDragComplete, onGemTapped

### `chromacrush_app/lib/game/particle_layer.dart` (dart)
  imports: I77, I78, I96, package:flame/particles.dart, I100, I101, I110, I197
  classes: ParticleLayer, _TrackedParticle
  functions: _addSystem, _enforeBudget, _updateAmbient, cascadeBurst, chromaticRain, defeatDust, fusionStorm, gemTrail, lineSweep, matchBurst, megaActivationBurst, megaMergeSparks, nearMissSparkle, radialWave, setAmbientDensity, update, victoryConfetti

### `chromacrush_app/lib/game/player_status_bar.dart` (dart)
  imports: I78, I96, I100, I101, I197, gem_component.dart
  classes: _MegaSlot, PlayerStatusBar
  functions: Function, _drawBackground, _drawCountBadges, _drawHearts, _gemX, onLoad, render, setHearts, setMegaCount

### `chromacrush_app/lib/game/tutorial_game.dart` (dart)
  imports: I111, I196, I101, I110, ../models/tutorial_script.dart, I128, I130, I156, I369, I198, I199, I255, I257, I370, I200
  classes: TutorialGame
  functions: Function, _matchesScriptedMove, _onGemTapped, _onSelectionChanged, _onSwapCommitted, loadCurrentStepBoard, loadScript, onLoad, setInputEnabled

### `chromacrush_app/lib/haptics/haptic_patterns.dart` (dart)
  imports: I156
  classes: HapticEvent, HapticPatternDef
  functions: toJson

### `chromacrush_app/lib/haptics/ios_haptics_engine.dart` (dart)
  imports: I155, I156, haptic_patterns.dart
  classes: IOSHapticsEngine
  functions: dispose, initialize, playPattern

### `chromacrush_app/lib/models/app_error.dart` (dart)
  classes: AppError, NetworkError, TimeoutError, ValidationError, NotFoundError, AuthError, ForbiddenError, ConflictError, RateLimitError, ServerError
  functions: toString

### `chromacrush_app/lib/models/backend_contract.dart` (dart)
  classes: ResponseMeta, ErrorDetail, ApiResponse, RegisterRequest, LoginRequest, AppleLoginRequest, RefreshRequest, LoginResponse, PlayerResponse, RegisterResponse, ApiKeyResponse, ApiKeyListItem, PlayerUpdateRequest, PlayerProfileResponse, UsernameCheckResponse, PlayerStatsResponse, LeaderboardEntry, LeaderboardResponse, EnergyResponse, StreakResponse, LoginStreakResponse, JoinQueueRequest, QueueEntryResponse, QueueStatusResponse, QuickMatchRequest, PoolStatsResponse, MoveRequest, PlayerMatchStateResponse, MatchStateResponse, MatchSummaryResponse, BoardStateResponse, SpecialActivationResponse, SpecialAttractionResponse, CascadeStepResponse, AppliedModifierResponse, CardRaidResultResponse, RewardCardEntry, MatchRewardResponse, MoveResultResponse, MoveHistoryEntry, ShieldRequest, RaidRequest, ArtifactResponse, ShieldResponse, RaidResponse, CollectionProgressResponse, RaidTargetResponse, EventResponse, EventParticipantResponse, EventLeaderboardEntryResponse, EventLeaderboardResponse, PlayerEventStatusResponse, AdFreeStatusResponse, InterstitialRequest, InterstitialResponse, RewardedVideoResponse, RewardedVideoCompleteResponse, InitiatePurchaseRequest, ValidatePurchaseRequest, PurchaseIntentResponse, PurchaseResultResponse, PurchaseStatusResponse, HealthResponse, CardDefinitionResponse, PlayerCardResponse, EquippedLoadoutResponse, PlayerCardsResponse, MergeResultResponse, MegaInventorySlot, MegaInventoryResponse, MegaActivationRequest, CardEquipRequest, CardUnequipRequest, CardReorderRequest, GoldResponse, SellCardsResponse, BuyItemRequest, BuyItemResponse, MarketplaceItemResponse, MarketplaceListResponse, ObstacleDefinition, CampaignLevelSummary, CampaignLevelsResponse, CampaignLevelResponse, CampaignProgressResponse, CampaignAttemptResponse, ObstacleEvent, CampaignMoveResponse, CampaignAbandonResponse
  functions: toJson

### `chromacrush_app/lib/models/bot_hints.dart` (dart)
  classes: ValidMoveHint, RankedMove, BoardAnalysis, StrategicContext, BotHints

### `chromacrush_app/lib/models/gem_type.dart` (dart)
  functions: funcToShaderValue, isMegaGemValue

### `chromacrush_app/lib/models/match_event.dart` (dart)
  classes: MatchEvent, SwapEvent, InvalidSwapEvent, MatchRemovalEvent, GravityEvent, FillEvent, SpecialGemCreatedEvent, SpecialGemActivatedEvent, SpecialAttractionEvent, BoardSyncEvent

### `chromacrush_app/lib/models/tutorial_script.dart` (dart)
  imports: backend_contract.dart
  classes: TutorialScript, TutorialStep

### `chromacrush_app/lib/navigation/app_router.dart` (dart)
  imports: I80, I31, I61, ../theme/chroma_theme.dart, ../widgets/game/game_container.dart, ../widgets/post_match/post_match_screen.dart, ../widgets/shell/choose_username_screen.dart, ../widgets/shell/login_screen.dart, ../widgets/shell/main_menu_screen.dart, ../widgets/shell/matchmaking_screen.dart, ../widgets/shell/settings_screen.dart, ../widgets/barter/barter_screen.dart, ../widgets/campaign/campaign_game_container.dart, ../widgets/campaign/campaign_level_screen.dart, ../widgets/campaign/campaign_screen.dart, ../widgets/tutorial/tutorial_screen.dart, ../widgets/vault/vault_screen.dart

### `chromacrush_app/lib/services/api_client.dart` (dart)
  imports: I79
  classes: ApiClientBase, StubApiClient

### `chromacrush_app/lib/services/audio_engine.dart` (dart)
  classes: AudioEngineBase, StubAudioEngine
  functions: discoverMenuTracks, dispose, initialize, playMenuMusic, playMusic, playSfx, setMasterVolume, setMusicHighPass, setMusicSpeed, setMusicVolume, setSfxVolume, stopMusic

### `chromacrush_app/lib/services/bot_api_client.dart` (dart)
  imports: I129, I259, I260, ../models/app_error.dart, I79
  classes: BotApiClientBase, BotApiClient
  functions: _get, _headers, _post, getMatchState, submitMove

### `chromacrush_app/lib/services/bot_player_service.dart` (dart)
  imports: I53, I129, dart:isolate, I77, I260, I258, debug_logger.dart, event_bus.dart
  classes: BotPlayerServiceBase, _BotMoveParams, _BotMoveResult, BotPlayerService
  functions: _executeBotMoveInIsolate, _pickMoveIndex, _playMove, _scheduleNext, dispose, startPlaying, stop

### `chromacrush_app/lib/services/debug_logger.dart` (dart)
  imports: I129, I259
  classes: DebugLogger
  functions: _boardToAscii, _initLogFile, _log, clear, dispose, logApiRequest, logApiResponse, logBoardState, logBoardSync, logError, logMoveAttempt, logMoveResponse

### `chromacrush_app/lib/services/event_bus.dart` (dart)
  imports: I53
  classes: GameEvent, ScoreUpdatedEvent, MovesUpdatedEvent, ChainCompletedEvent, MatchEndedEvent, EnergyChangedEvent, BotScoreUpdatedEvent, IntensityChangedEvent, ObstaclesUpdatedEvent, MegaActivatedEvent, CardProcEvent, EquippedCardsEvent, EquippedCardInfo, EventBus
  functions: dispose, fire

### `chromacrush_app/lib/services/haptics_engine.dart` (dart)
  classes: HapticsEngineBase, StubHapticsEngine
  functions: dispose, initialize, playPattern

### `chromacrush_app/lib/services/http_api_client.dart` (dart)
  imports: I129, I259, dart:isolate, I260, ../config.dart, ../models/app_error.dart, I79, api_client.dart, session_manager.dart, token_storage.dart
  classes: HttpApiClient
  functions: _attemptTokenRefresh, _delete, _get, _patch, _post, _saveTokens, setAccessToken

### `chromacrush_app/lib/services/iap_service.dart` (dart)
  imports: I53, I259, I252, package:in_app_purchase/in_app_purchase.dart, I79, api_client.dart, debug_logger.dart, session_manager.dart
  classes: IapServiceBase, StoreKitIapService, StubIapService
  functions: _handlePurchaseUpdate, _verifyAndDeliver, buyGoldPack, dispose, init

### `chromacrush_app/lib/services/intensity_service.dart` (dart)
  imports: I53, I77, I252, I258, event_bus.dart
  classes: IntensityService
  functions: _recompute, _subscribe, dispose, reset, setMaxMoves, tick, updateOpponentScore

### `chromacrush_app/lib/services/session_manager.dart` (dart)
  imports: I252, I79
  classes: SessionManager
  functions: clearActiveMatch, clearAuth, clearCards, setActiveMatch, setAdFree, setAuth, tickRegenTimer, updateEnergy, updateEquippedLoadout, updateGold, updateGoldBalance, updateOwnedCards, updateTokens, updateUsername

### `chromacrush_app/lib/services/token_storage.dart` (dart)
  imports: package:shared_preferences/shared_preferences.dart
  classes: TokenStorage
  functions: clearTokens, saveTokens

### `chromacrush_app/lib/theme/chroma_theme.dart` (dart)
  imports: I31
  classes: ChromaColors, ChromaText, ChromaGradients

### `chromacrush_app/lib/theme/glass_panel.dart` (dart)
  imports: I78, I31, I258, chroma_theme.dart
  classes: GlassPanel
  functions: build

### `chromacrush_app/lib/utils/card_description_resolver.dart` (dart)
  imports: I101
  functions: resolveCardDescription

### `chromacrush_app/lib/view_models/campaign_view_model.dart` (dart)
  imports: I53, package:flutter/widgets.dart, I79, I201, I130, I256
  classes: CampaignViewModel
  functions: _subscribeToEvents, abandon, dispose, markFailed, reset, startLevel

### `chromacrush_app/lib/view_models/match_view_model.dart` (dart)
  imports: I53, package:flutter/widgets.dart, I79, ../models/view_state.dart, I201, ../services/bot_player_service.dart, I130, I256
  classes: MatchViewModel
  functions: _onMatchEnded, _startMatchFlow, _subscribeToEvents, dispose, forfeit, playAgain, rejoinMatch, startMatch, startSinglePlayer

### `chromacrush_app/lib/widgets/barter/barter_screen.dart` (dart)
  imports: I78, I80, I31, I61, I52, I112, I102, ../../services/iap_service.dart, I113, I42, I60, ../shell/starfield_background.dart
  classes: BarterScreen, _BarterScreenState, _GoldBalanceHeader, _GlassPillTabBar, _HeartsStatusRow, _ProductCard
  functions: _buildContent, _buildDollarPrice, _buildGoldPrice, _buyItem, _fetchMarketplace, _formatGold, _formatNumber, _formatTimer, _itemsForTab, build, createState, initState

### `chromacrush_app/lib/widgets/campaign/campaign_game_container.dart` (dart)
  imports: I53, I111, I80, I31, I61, I52, I157, ../../game/campaign_game.dart, I102, I158, ../../services/debug_logger.dart, I131, I202, ../../services/intensity_service.dart, I113, I132, I372, I203, I42, I60, I373, ../game/campaign_hud.dart
  classes: CampaignGameContainer, _CampaignGameContainerState, _CompletionOverlay, _FailedOverlay, _ObjectiveTooltip, _ObjectiveTooltipState, _LoadingOverlay, _CampaignScoreBar, _CampaignScoreBarState
  functions: _formatValue, _loadBoardIfReady, _maybeExpandMax, _onViewModelChanged, _scaleTicks, _showAbandonDialog, build, createState, dispose, initState

### `chromacrush_app/lib/widgets/campaign/campaign_level_screen.dart` (dart)
  imports: I80, I31, I61, I52, I112, I102, I158, I42, I60, I373
  classes: CampaignLevelScreen, _CampaignLevelScreenState, _ObstaclePreviewGrid
  functions: _buildContent, _fetchLevel, _funcSymbol, build, createState, initState

### `chromacrush_app/lib/widgets/campaign/campaign_screen.dart` (dart)
  imports: I80, I31, I61, I52, I157, I112, I102, I42, I60
  classes: CampaignScreen, _CampaignScreenState, _LevelSection, _CheckpointBar, _LevelTile
  functions: _buildReward, _buildSections, _capitalize, _fetchLevels, _formatNumber, _tileSize, build, createState, initState

### `chromacrush_app/lib/widgets/game/bot_move_preview.dart` (dart)
  imports: I53, I77, I78, I31, I52, I132, I372, I157, ../../models/gem_type.dart, I131, I42
  classes: BotMovePreview, _BotMovePreviewState, _BotPreviewPainter
  functions: _drawGem, _drawSparkles, _generateGrid, _onAnimStatus, _startPreview, build, createState, dispose, initState, paint, shouldRepaint

### `chromacrush_app/lib/widgets/game/campaign_hud.dart` (dart)
  imports: I53, I31, I131, I42, I60, I373, card_rune_panel.dart
  classes: CampaignHUD, _CampaignHUDState
  functions: _buildScoreBar, build, createState, dispose, initState

### `chromacrush_app/lib/widgets/game/card_rune_panel.dart` (dart)
  imports: I53, I31, I131, I60
  classes: CardRunePanel, _CardRunePanelState
  functions: _buildRuneGlyph, build, createState, dispose, initState

### `chromacrush_app/lib/widgets/game/game_container.dart` (dart)
  imports: I111, I80, I31, I61, I52, I203, ../../game/chroma_crush_game.dart, I102, I157, I158, ../../services/debug_logger.dart, I131, I202, ../../services/intensity_service.dart, I113, I42, I159, bot_move_preview.dart, game_hud.dart, score_comparison_bars.dart
  classes: GameContainerWidget, _GameContainerWidgetState, _LoadingOverlay
  functions: _loadBoardIfReady, _onViewModelChanged, _showForfeitDialog, build, createState, dispose, initState

### `chromacrush_app/lib/widgets/game/game_hud.dart` (dart)
  imports: I80, I31, I131, I42, I60, I159, card_rune_panel.dart
  classes: GameHUD, _ChainCounter
  functions: _buildOpponentBar, _buildScoreBar, build

### `chromacrush_app/lib/widgets/game/score_comparison_bars.dart` (dart)
  imports: I53, I77, I31, I132, I372, I203, ../../services/bot_player_service.dart, I131, I159
  classes: ScoreComparisonBars, _ScoreComparisonBarsState, _ScaleTick, _ScoreBar
  functions: _formatValue, _maybeExpandMax, _revealBotScore, _scaleTicks, _scheduleBotReveal, build, createState, dispose, initState

### `chromacrush_app/lib/widgets/post_match/near_miss_widget.dart` (dart)
  imports: I31, I132, I42
  classes: NearMissWidget, _NearMissWidgetState
  functions: build, createState, dispose, initState

### `chromacrush_app/lib/widgets/post_match/post_match_screen.dart` (dart)
  imports: I31, I61, I52, I132, ../../models/view_state.dart, I158, I202, I42, I60, I159, near_miss_widget.dart, score_reveal_widget.dart
  classes: PostMatchScreen, _PostMatchScreenState
  functions: _buildRaidPanel, _buildRewardPanel, _runSequence, build, createState, dispose, initState

### `chromacrush_app/lib/widgets/post_match/score_reveal_widget.dart` (dart)
  imports: I31, I132, ../../models/view_state.dart, I42
  classes: ScoreRevealWidget, _ScoreRevealWidgetState
  functions: build, createState, dispose, initState

### `chromacrush_app/lib/widgets/shell/choose_username_screen.dart` (dart)
  imports: I53, I31, I61, I52, I112, I102, I113, I42, I60
  classes: ChooseUsernameScreen, _ChooseUsernameScreenState
  functions: _buildStatusMessage, _buildSuffixIcon, _checkAvailability, _confirm, _onChanged, _skip, _validateLocally, build, createState, dispose, initState

### `chromacrush_app/lib/widgets/shell/login_screen.dart` (dart)
  imports: I31, I61, I52, package:sign_in_with_apple/sign_in_with_apple.dart, I112, I102, I113, I42, starfield_background.dart
  classes: LoginScreen, _LoginScreenState
  functions: _authenticate, _completeAppleLogin, _signInWithApple, _tryRestore, build, createState, dispose, initState

### `chromacrush_app/lib/widgets/shell/main_menu_screen.dart` (dart)
  imports: I53, I80, I31, I61, I52, I112, I102, I113, I42, I60, I159, starfield_background.dart
  classes: MainMenuScreen, _MainMenuScreenState, _PlayButton, _PlayButtonState, _EnergyDisplay, _GoldDisplay, _LeaderboardPanel, _ModeToggle, _LeaderboardRow
  functions: _buildPrimary, _buildSecondary, _buyHeartAndPlay, _checkActiveMatch, _formatTimer, _primaryContainer, _resumeMatch, _showHeartPurchaseDialog, _startSinglePlayer, _syncEnergy, _syncGold, _syncLeaderboard, _toggleSegment, build, createState, dispose, initState

### `chromacrush_app/lib/widgets/shell/matchmaking_screen.dart` (dart)
  imports: I80, I31, I61, I52, I132, I42, I60, I159
  classes: MatchmakingScreen, _MatchmakingScreenState, _OpponentCard
  functions: _navigateToGame, _onViewModelChanged, build, createState, dispose, initState

### `chromacrush_app/lib/widgets/shell/settings_screen.dart` (dart)
  imports: I80, I31, I61, I52, I158, I202, I113, I42, I60
  classes: SettingsScreen, _SettingsScreenState
  functions: build, createState

### `chromacrush_app/lib/widgets/shell/starfield_background.dart` (dart)
  imports: I77, I31
  classes: StarfieldBackground, _StarfieldBackgroundState, _Star, _StarfieldPainter
  functions: _tick, build, createState, dispose, initState, paint, shouldRepaint, update

### `chromacrush_app/lib/widgets/tutorial/coach_overlay.dart` (dart)
  imports: I77, I31, I203, I42, I60
  classes: CoachOverlay, _CoachOverlayState, _SpotlightPainter
  functions: build, createState, dispose, initState, paint, shouldRepaint

### `chromacrush_app/lib/widgets/tutorial/tutorial_screen.dart` (dart)
  imports: I129, I111, I80, I31, I155, I61, I52, I157, I203, ../../game/tutorial_game.dart, ../../models/tutorial_script.dart, I158, I202, I42, I60, coach_overlay.dart
  classes: TutorialScreen, _TutorialScreenState, _LoadingOverlay, _ErrorOverlay, _WellDoneFlash, _WellDoneFlashState, _CompletionOverlay
  functions: _loadScript, _onCoachDismissed, _onFinalCascadeStarted, _onStepAdvanced, _onTutorialComplete, _startTutorial, build, createState, dispose, initState

### `chromacrush_app/lib/widgets/vault/card_widget.dart` (dart)
  imports: I78, I31, I52, I157, I112, ../../utils/card_description_resolver.dart
  classes: CardWidget, _GlassOverlay, _ShaderBackground, _ShaderBackgroundState, _CardArtPainter, _ArtFallback, _TypeLine, _FoilOverlay, _FoilOverlayState, _FoilPainter, _FoilFallback, _RarityBadge
  functions: _buildCompact, _buildFull, _cardGlyph, _loadShader, _tagBitmask, build, createState, dispose, initState, paint, shouldRepaint

### `chromacrush_app/lib/widgets/vault/vault_help_overlay.dart` (dart)
  imports: I31, I42, I60
  classes: VaultHelpOverlay, _HintRow
  functions: build

### `chromacrush_app/lib/widgets/vault/vault_screen.dart` (dart)
  imports: I78, I80, I31, I61, I52, I112, I102, I113, I42, ../shell/starfield_background.dart, card_widget.dart, vault_help_overlay.dart
  classes: VaultScreen, _VaultScreenState, _EquipSlot, _EquipSlotState, _ActionButton, _CardCarousel, _CardCarouselState, _DraggableCard, _DraggableCardState, _GlowingHelpButton, _GlowingHelpButtonState
  functions: _buildActiveCardPreview, _buildBody, _buildCompactCarousel, _buildEquipRow, _buildFilterRow, _confirmExchange, _confirmMerge, _cycleSortMode, _equipCard, _fetchCards, _toggleRarityFilter, _unequipCard, build, createState, didUpdateWidget, dispose, initState

### `config/board_rules.json` (json)
  keys: version, board, match_detection, special_gems, mega_gems, obstacles

### `config/campaign_levels.json` (json)
  keys: (array of 100)

### `config/card_definitions.json` (json)
  keys: version, equip_slots, max_equip_slots, rarity_weights, rarity_order, sets, cards

### `scripts/gen_campaign_levels.py` (py)
  imports: I57, import math
  functions: _obstacle_count(level, is_checkpoint), _lerp(lo, hi, level, range_lo, range_hi), _moves(level, is_checkpoint), _gem_colors(level), _func_pool(level), _place_obstacles(level, count, func_pool), _next_rng(), _checkpoint_reward(level), generate_levels()

### `scripts/seed_bots.py` (py)
  imports: I1, I82, I374, I114, I375, I376, I32, from src.modules.player.bot_names import generate_unique_bot_name
  functions: main()

### `src/main.py` (py)
  imports: from src.modules.api.factory import create_app

### `src/cli/cli_entry.py` (py)
  imports: I1, I48, I62, I58, I205, from src.cli.commands.player_commands import player, from src.cli.commands.auth_commands import auth, from src.cli.commands.scoring_commands import scoring, from src.cli.commands.energy_commands import energy, from src.cli.commands.special_gems_commands import special_gems, from src.cli.commands.vault_commands import vault, from src.cli.commands.board_commands import board, from src.cli.commands.board_gen_commands import board_gen, from src.cli.commands.match_commands import match, from src.cli.commands.matchmaking_commands import matchmaking, from src.cli.commands.events_commands import events, from src.cli.commands.ads_commands import ads, from src.cli.commands.payments_commands import payments, from src.cli.commands.bot_earnings_commands import bot_earnings, from src.cli.commands.api_commands import api, from src.cli.commands.cards_commands import cards as cards_group, from src.cli.commands.economy_commands import economy as economy_group
  functions: cli(), version(config_path), show_config(config_path)

### `src/cli/commands/ads_commands.py` (py)
  imports: I1, I22, I7, I3, I48, I62, I70, I58, I89, I83, I71, I11, I38, I25, I6, I160, I161, I84, I115, I90, I162, I163, I164, I133, I377, I378, I379, I380, I165, I381, I382, I166, I160, I161, I134, I116, I383
  classes: _EventServiceStub, _MockAdProvider
  functions: _ads_unavailable(), _run_async(coro_factory, config_path), _bridge(ctx), _build_ad_service(ctx), __init__(self, data_ctx), get_event(self, event_id), get_event_participant(self, event_id, player_id), request_interstitial(self, ad_unit_id, user_id), request_rewarded_video(self, ad_unit_id, user_id), verify_impression(self, ad_request_id, impression_data), get_estimated_cpm(self, ad_type), ads(), check_status(player_username, config_path), _do(svc, ctx), grant_ad_free(player_username, reason, days, config_path), _do(svc, ctx), revoke_ad_free(player_username, reason, config_path), _do(svc, ctx), request_interstitial(player_username, trigger, match_id, config_path), _do(svc, ctx), record_interstitial(ad_request_id, viewed, duration, config_path), _do(svc, ctx), request_rewarded(player_username, reward_type, config_path), _do(svc, ctx), complete_rewarded(ad_request_id, completed, duration, config_path), _do(svc, ctx), record_banner(player_username, placement, duration, config_path), _do(svc, ctx), player_stats(player_username, period, config_path), _do(svc, ctx), impressions(player_username, ad_type, limit, offset, config_path), _do(svc, ctx), match_attribution(match_id, config_path), _do(svc, ctx), bot_report(bot_player_username, start, end, config_path), _do(svc, ctx), event_opportunities(event_id, player, config_path), _do(svc, ctx), claim_opportunity(event_id, opportunity_id, player, config_path), _do(svc, ctx)

### `src/cli/commands/api_commands.py` (py)
  imports: I1, I48, I62, I70, I58, I205, import uvicorn, I72, from src.modules.api.routes import ads_router, from src.modules.api.routes import auth_router, from src.modules.api.routes import bot_earnings_router, from src.modules.api.routes import cards_router, from src.modules.api.routes import economy_router, from src.modules.api.routes import energy_router, from src.modules.api.routes import events_router, from src.modules.api.routes import health_router, from src.modules.api.routes import inventory_router, from src.modules.api.routes import matchmaking_router, from src.modules.api.routes import matches_router, from src.modules.api.routes import payments_router, from src.modules.api.routes import players_router, from src.modules.api.routes import vault_router, from src.modules.api.routes import ws_router, I57, from urllib.request import urlopen, from urllib.error import URLError
  functions: api(), start(host, port, auto_reload, config_path), routes(), health(url), show_config(config_path)

### `src/cli/commands/auth_commands.py` (py)
  imports: I1, I3, I48, I62, I70, I58, I89, I83, I71, I205, I11, I6
  functions: auth(), hash_password(password, config_path), _do(ctx), verify_password(password, hash_value, config_path), _do(ctx), show_config(config_path), login(username, password, config_path), _do(ctx), validate_token(token, config_path), _do(ctx), refresh(refresh_token, config_path), _do(ctx), logout(player_username, session_id, revoke_all, config_path), _do(ctx), sessions(player_username, config_path), _do(ctx), create_key(player_username, description, config_path), _do(ctx), list_keys(player_username, include_revoked, config_path), _do(ctx), revoke_key(key_id, player_username, config_path), _do(ctx), rate_limit(key_id, config_path), _do(ctx), cleanup_sessions(config_path), _do(ctx)

### `src/cli/commands/board_commands.py` (py)
  imports: I1, I57, I85, I48, I206, I263, from src.cli.helpers.display import render_move_result, I264, I11, I16, I39, I23, import random as _random, import random as _random, I73, from src.cli.helpers.display import _COLORS, from src.cli.helpers.display import _COLOR_LABELS
  functions: board(), generate(seed, width, height, no_functions, config_path), detect_matches(board_json, no_functions, config_path), process_move(board_json, from_pos, to_pos, seed, verbose, no_functions, config_path), has_moves(board_json, config_path), _serialize_cascade_steps(cascades), enrich_tutorial(input_path, output_path, config_path), interactive(seed, verbose, output_path, config_path)

### `src/cli/commands/board_gen_commands.py` (py)
  imports: I1, I57, I103, I48, I206, I263, I264, I16, I207, I208
  functions: board_gen(), generate(seed, cascade_potential, near_miss_factor, no_functions, config_path), for_match(seed, match_type, no_functions, config_path), analyze(board_json, no_functions, config_path), validate_seed(seed, config_path), reshuffle(board_json, seed, no_functions, config_path)

### `src/cli/commands/bot_earnings_commands.py` (py)
  imports: I1, I22, I7, I3, I48, I62, I70, I58, I83, I71, I11, I6, I209, I210, I211, I167, I135, I10, I24, I384, I385, I386, I387, I165, I166, I116
  classes: _AdsServiceStub, _Stub
  functions: _run_async(coro_factory, config_path), _bridge(ctx), _build_ads_service_stub(), get_bot_ad_attributions(self, bot_player_id, start_date, end_date), _build_bot_earnings_service(ctx), bot_earnings(), balance(bot_player_id, config_path), _do(svc, ctx), summary(bot_player_id, period, config_path), _do(svc, ctx), daily(bot_player_id, start, end, config_path), _do(svc, ctx), attributions(bot_player_id, start, end, limit, config_path), _do(svc, ctx), sync(bot_player_id, config_path), _do(svc, ctx), sync_all(config_path), _do(svc, ctx), request_payout(bot_player_id, owner, config_path), _do(svc, ctx), payout_requests(bot_player_id, status, config_path), _do(svc, ctx), cancel_payout(payout_request_id, owner, config_path), _do(svc, ctx), process_payout(payout_request_id, processor, reference, config_path), _do(svc, ctx), reject_payout(payout_request_id, processor, reason, config_path), _do(svc, ctx), pending_payouts(past_hold_only, config_path), _do(svc, ctx)

### `src/cli/commands/cards_commands.py` (py)
  imports: I1, I3, I48, I62, I70, I58, I89, I83, I71, I11
  functions: cards(), list_definitions(rarity, limit, config_path), _do(ctx), get_definition(card_id, config_path), _do(ctx), player_cards(player_username, equipped_only, rarity, config_path), _do(ctx), equipped(player_username, config_path), _do(ctx), grant(player_username, card_id, config_path), _do(ctx), equip(player_username, card_instance_id, position, config_path), _do(ctx), unequip(player_username, card_instance_id, config_path), _do(ctx), reorder(player_username, card_instance_id, new_position, config_path), _do(ctx), merge(player_username, config_path), _do(ctx), grant_starter(player_username, config_path), _do(ctx), show_modifiers(player_username, config_path), _do(ctx)

### `src/cli/commands/economy_commands.py` (py)
  imports: I1, I48, I62, I70, I58, I89, I83, I71, I11
  functions: economy(), gold(player_username, config_path), _do(ctx), sell(player_username, config_path), _do(ctx), buy(player_username, item_id, config_path), _do(ctx), marketplace(config_path), _do(ctx)

### `src/cli/commands/energy_commands.py` (py)
  imports: I1, I48, I62, I70, I58, I89, I83, I71, I11, I6, I136
  functions: energy(), get_energy(player_username, config_path), _do(ctx), consume_heart(player_username, amount, config_path), _do(ctx), can_play(player_username, config_path), _do(ctx), apply_regen(player_username, config_path), _do(ctx), time_to_heart(player_username, config_path), _do(ctx), record_login(player_username, config_path), _do(ctx), get_streak(player_username, config_path), _do(ctx), grant_bonus(player_username, amount, source, config_path), _do(ctx), refund_heart(player_username, amount, reason, config_path), _do(ctx)

### `src/cli/commands/events_commands.py` (py)
  imports: I1, I2, I3, I48, I62, I70, I58, I89, I83, I71, I11, I38, I25, I6, I104, I168, I74, I105, I169
  functions: events(), create(name, event_type, start_at, end_at, scoring, description, config_path), _do(ctx), get(event_id, config_path), _do(ctx), list_cmd(status, event_type, limit, offset, config_path), _do(ctx), active(config_path), _do(ctx), join(event_id, player, config_path), _do(ctx), leave(event_id, player, config_path), _do(ctx), record_match(event_id, player, match_id, score, chains, gems, specials, duration, config_path), _do(ctx), leaderboard(event_id, limit, config_path), _do(ctx), rank(event_id, player, config_path), _do(ctx), player_events(player_username, include_past, limit, config_path), _do(ctx), finalize(event_id, config_path), _do(ctx), cancel(event_id, reason, config_path), _do(ctx), update(event_id, name, description, config_path), _do(ctx), process_scheduled(config_path), _do(ctx)

### `src/cli/commands/match_commands.py` (py)
  imports: I1, I85, I3, I48, I70, I58, I89, I83, I206, I263, from src.cli.helpers.display import render_move_result, I71, I11, I25, I39, I6, I23, I117
  functions: match(), create(player1_username, player2_username, seed, match_type, config_path), _do(ctx), submit_move(match_id, player_username, from_row, from_col, to_row, to_col, timestamp, verbose, config_path), _do(ctx), show(match_id, config_path), _do(ctx), board(match_id, player_username, no_functions, config_path), _do(ctx), active(player_username, config_path), _do(ctx), history(player_username, limit, offset, config_path), _do(ctx), moves(match_id, player_username, config_path), _do(ctx), forfeit(match_id, player_username, config_path), _do(ctx), abandon_stale(config_path), _do(ctx), cleanup(older_than, config_path), _do(ctx)

### `src/cli/commands/matchmaking_commands.py` (py)
  imports: I1, I48, I62, I70, I58, I89, I83, I71, I11, I6, I212, I97
  functions: matchmaking(), join(player_username, pool, config_path), _do(ctx), leave(player_username, config_path), _do(ctx), status(player_username, config_path), _do(ctx), find(player_username, config_path), _do(ctx), process(pool, config_path), _do(ctx), cleanup(config_path), _do(ctx), stats(pool, config_path), _do(ctx)

### `src/cli/commands/payments_commands.py` (py)
  imports: I1, I7, I48, I62, I70, I58, I89, I83, I71, I11, I6, I388, I213, I91, I137, I118, I214, I84, I138, I10, I10, I165, I166, I389, I390, I391, I392, I393, I116, I139
  classes: _AdsServiceStub, _Stub, _Stub, _MockPaymentProvider
  functions: _run_async(coro_factory, config_path), _bridge(ctx), _build_ads_service_stub(), check_ad_free_status(self, player_id), grant_ad_free_status(self, player_id, reason, duration_days, granted_by), revoke_ad_free_status(self, player_id, reason), _build_payment_service(ctx), validate_receipt(self, receipt_data, product_id, is_sandbox), verify_webhook_signature(self, payload, signature), _get_ad_free_product_id(config), payments(), products(config_path), _do(svc, ctx), initiate(player_username, product_id, config_path), _do(svc, ctx), validate(player_username, provider, receipt_data, config_path), _do(svc, ctx), status(player_username, config_path), _do(svc, ctx), history(player_username, limit, offset, config_path), _do(svc, ctx), restore(player_username, provider, receipt_data, config_path), _do(svc, ctx), simulate_refund(provider, transaction_id, config_path), _do(svc, ctx), list_refunds(unprocessed, config_path), _do(svc, ctx), get_purchase(purchase_id, config_path), _do(svc, ctx), get_validation(player_username, transaction_id, config_path), _do(svc, ctx)

### `src/cli/commands/player_commands.py` (py)
  imports: I1, I48, I62, I70, I58, I89, I83, I71, I11, I6, I32
  functions: player(), create(username, is_bot, email, config_path), _do(ctx), get_player(player_username, config_path), _do(ctx), list_players(player_type_filter, limit, offset, config_path), _do(ctx), show_stats(player_username, config_path), _do(ctx), show_elo(player_username, config_path), _do(ctx), calc_elo(winner_username, loser_username, draw, config_path), _do(ctx), show_energy(player_username, config_path), _do(ctx)

### `src/cli/commands/scoring_commands.py` (py)
  imports: I1, I57, I48, I58, I206, I264, I11, I16, I30
  functions: scoring(), calculate_match(board_json, chain_step, config_path), show_multipliers(config_path), special_gem_bonus(gem_type, gems_affected, config_path)

### `src/cli/commands/special_gems_commands.py` (py)
  imports: I1, I57, I48, I206, I263, I264, I11, I16, I140, I63, I30, I23
  functions: _parse_position(value), _parse_gem_type(value), special_gems(), check_special_gem(board_json, position, config_path), activate_special_gem(board_json, position, target_color, no_functions, config_path), fuse_special_gems(board_json, pos_a, pos_b, target_color, no_functions, config_path), from_match(match_result_json, config_path), simulate(board_json, position, target_color, apply_effect, no_functions, config_path)

### `src/cli/commands/vault_commands.py` (py)
  imports: I1, I3, I48, I62, I70, I58, I89, I83, I71, I11, I106, I6, I119
  functions: vault(), list_artifacts(player_username, rarity, artifact_set, config_path), _do(ctx), summary(player_username, config_path), _do(ctx), add_artifact(player_username, artifact_type_id, source, config_path), _do(ctx), get_artifact(artifact_id, config_path), _do(ctx), catalog(rarity, artifact_set, config_path), _do(ctx), shield_status(player_username, config_path), _do(ctx), shield_activate(player_username, hours, config_path), _do(ctx), raid(attacker_username, defender_username, config_path), _do(ctx), can_raid(attacker_username, defender_username, config_path), _do(ctx), raid_history(player_username, config_path), _do(ctx)

### `src/cli/helpers/async_bridge.py` (py)
  imports: I1, I82, I7, I3, I48, I71, I375, I376
  functions: run_cli_async(coro_factory, config_path), _inner(), resolve_player(ctx, username)

### `src/cli/helpers/display.py` (py)
  imports: I1, I62, I58, from rich.text import Text, I16, I170, I394, I395, I171, I92
  functions: render_board(board, show_functions), render_cascade_step(step, step_number, verbose), render_move_result(result, verbose)

### `src/cli/helpers/password_store.py` (py)
  imports: I1, I3, I19, I120, I172, I120
  classes: CLIPasswordStore, StubPasswordStore
  functions: __init__(self, data_ctx), get_password_hash(self, player_id), set_password_hash(self, player_id, password_hash), __init__(self, data_ctx), get_password_hash(self, player_id), set_password_hash(self, player_id, password_hash)

### `src/cli/helpers/service_factory.py` (py)
  imports: I1, I205, I396, I397, I121, I173, I215, I216
  functions: build_sync_services(config_path)

### `src/core/composition_root.py` (py)
  imports: I1, I7, I10, I398, I399, from src.core.debug_logger import DebugLogger, I396, I397, I18, I15, I9, I8, I265, I166, I165, I400, I401, from src.data.repositories.password_store_repository import SQLAlchemyPasswordStoreRepository, from src.data.repositories.match_repository import SQLAlchemyMatchRepository, from src.data.repositories.match_repository import SQLAlchemyMatchMoveRepository, from src.data.repositories.vault_artifact_repository import SQLAlchemyVaultArtifactRepository, from src.data.repositories.vault_shield_repository import SQLAlchemyVaultShieldRepository, from src.data.repositories.artifact_definition_repository import SQLAlchemyArtifactDefinitionRepository, from src.data.repositories.raid_log_repository import SQLAlchemyRaidLogRepository, from src.data.repositories.player_card_repository import SQLAlchemyPlayerCardRepository, I383, from src.data.repositories.event_participant_repository import SQLAlchemyEventParticipantRepository, from src.data.repositories.event_leaderboard_repository import RedisEventLeaderboardRepository, from src.data.repositories.matchmaking_queue_repository import RedisMatchmakingQueueRepository, I379, I378, I377, I380, I382, I381, I389, I390, I391, I392, I393, I386, I384, I387, I385, I121, I173, I215, I216, I116, I266, I267, I217, I268, I269, I270, I271, I160, I161, I388, I213, I209, I141, from src.modules.inventory.service import InventoryService, from src.data.repositories.mega_gem_inventory_repository import SQLAlchemyMegaGemInventoryRepository, from src.data.repositories.gold_balance_repository import SQLAlchemyGoldBalanceRepository, from src.data.repositories.gold_transaction_repository import SQLAlchemyGoldTransactionRepository, from src.data.repositories.campaign_attempt_repository import SQLAlchemyCampaignAttemptRepository, I402, I403, I134, I134, I91, I139, from src.modules.payments.apple_provider import AppleAppStoreProvider
  classes: _MockAdProvider, _MockPaymentProvider, ApplicationContext
  functions: request_interstitial(self, ad_unit_id, user_id), request_rewarded_video(self, ad_unit_id, user_id), verify_impression(self, ad_request_id, impression_data), get_estimated_cpm(self, ad_type), validate_receipt(self, receipt_data, product_id, is_sandbox), verify_webhook_signature(self, payload, signature), create_application_context(config_path), load_config(config_path), shutdown_application_context(ctx)

### `src/core/config.py` (py)
  imports: I1, I272, import tomllib, from copy import deepcopy, I114, I7, from dotenv import load_dotenv
  classes: ConfigService
  functions: __init__(self, data), load(cls, config_path), get(self, key, default), require(self, key), _traverse(self, key), _deep_merge(base, override), _apply_env_overrides(cls, data), _apply_env_recursive(cls, node, prefix_parts), _coerce_type(env_value, original)

### `src/core/data_context.py` (py)
  imports: I1, from contextlib import asynccontextmanager, I4, from typing import AsyncIterator, from sqlalchemy.ext.asyncio import AsyncEngine, from sqlalchemy.ext.asyncio import AsyncSession, from sqlalchemy.ext.asyncio import async_sessionmaker, from sqlalchemy.ext.asyncio import create_async_engine, from redis.asyncio import Redis, I18, I9, I8, import redis.asyncio as aioredis
  classes: DataContext
  functions: __init__(self, engine, session_factory, redis_client, logger), create(cls, config, logger, errors), session(self), redis(self), close(self)

### `src/core/debug_logger.py` (py)
  imports: I1, I57, I272, I85, I2, I5, I43, I7, I18
  classes: DebugCategory(str, Enum), DebugLogger
  functions: _board_to_ascii(cells), __init__(self, config), enabled(self), _log(self, category, action, data), log_board_state(self, label, board_cells), log_board_loaded_from_db(self, board_cells), log_move_attempt(self, match_id, player_id, from_row, from_col, to_row, to_col, board_before), log_post_swap_board(self, board_after_swap), log_match_detection(self, matches_found, total_gems, match_details, board), log_cascade_step(self, step, matches_found, gems_cleared, board_after), log_move_result(self, valid, chain_count, total_cleared, board_after), log_api_request(self, endpoint, method), log_api_response(self, endpoint, status), log_error(self, message), get_events(self, category, match_id), get_log_file_path(self), clear(self)

### `src/core/error_service.py` (py)
  imports: I1, I2, I5, I7, I27, I11, I218, I8
  classes: ErrorService
  functions: __init__(self, logger), validation(self, message, code), not_found(self, message, code), unauthorized(self, message, code), forbidden(self, message, code), conflict(self, message, code), rate_limited(self, message, retry_after, code), internal(self, message, code), _create_error(self, code, message)

### `src/core/errors.py` (py)
  imports: I1, I10, I24, I2, I5, I7, I27
  classes: AppError(Exception)
  functions: __str__(self), __repr__(self), to_dict(self)

### `src/core/logger.py` (py)
  imports: I1, I57, I374, I2, I5, I7, from typing import TextIO, I18, I218
  classes: LogService
  functions: __init__(self, config), trace(self, message), debug(self, message), info(self, message), warn(self, message), error(self, message), fatal(self, message), _log(self, level, level_name, message), _safe_str(value)

### `src/core/move_pipeline.py` (py)
  imports: I1, I10, I4
  classes: BoardProcessingResult
  functions: derive_move_seed(board_seed, player_id, moves_remaining), derive_reshuffle_seed(board_seed, player_id, move_number), process_move_pipeline(board, move, seed), process_mega_pipeline(board, mega_value, seed), _score_and_finalize(move_result, result_board), _handle_deadlock(result_board, board_seed, player_id, moves_made, moves_remaining, board_service, board_gen_service, deadlock_reshuffle)

### `src/core/protocols/__init__.py` (py)
  imports: I18, from src.core.protocols.correlation import CorrelationContextProtocol, I218, I15, I9, I8

### `src/core/protocols/config.py` (py)
  imports: I1, I7, I13
  classes: ConfigProtocol(Protocol)
  functions: get(self, key, default), require(self, key)

### `src/core/protocols/correlation.py` (py)
  imports: I1, from contextvars import ContextVar, I13
  classes: CorrelationContextProtocol(Protocol)
  functions: get_id(self), set_id(self, correlation_id), clear(self)

### `src/core/protocols/data_context.py` (py)
  imports: I1, from typing import AsyncContextManager, I13, from sqlalchemy.ext.asyncio import AsyncSession
  classes: DataContextProtocol(Protocol)
  functions: session(self), close(self)

### `src/core/protocols/error_service.py` (py)
  imports: I1, I7, I13, I11
  classes: ErrorServiceProtocol(Protocol)
  functions: validation(self, message, code), not_found(self, message, code), unauthorized(self, message, code), forbidden(self, message, code), conflict(self, message, code), rate_limited(self, message, retry_after, code), internal(self, message, code)

### `src/core/protocols/logger.py` (py)
  imports: I1, I13
  classes: LoggerProtocol(Protocol)
  functions: trace(self, message), debug(self, message), info(self, message), warn(self, message), error(self, message), fatal(self, message)

### `src/core/types/__init__.py` (py)
  imports: I219, I273, I404, from src.core.types.board import BoardGrid, I16, I140, I63, I106, I38, I30, I25, I39, I6, I23, from src.core.types.match import MatchState, from src.core.types.match import MatchStatus, from src.core.types.match import MatchType, from src.core.types.match import PlayerMatchState, I142, I86, I122, I32, from src.core.types.websocket import WSAuthMessage, I405, from src.core.types.websocket import WSMatchUpdate, I406, I407, from src.core.types.websocket import WSSubscribeMessage

### `src/core/types/auth.py` (py)
  imports: I10, I2, I5, I43, I3, I6
  classes: TokenType(Enum), AuthToken, ApiKeyInfo
  functions: is_expired(self)

### `src/core/types/board.py` (py)
  imports: I10, I24, I54, from numpy.typing import NDArray, I30, I23
  classes: BoardState, MatchGroup, MatchResult
  functions: __post_init__(self), get(self, pos), copy(self), to_list(self), to_dict(self), from_list(cls, data), from_dict(cls, data), __post_init__(self)

### `src/core/types/game.py` (py)
  imports: I10, from enum import IntEnum, I274, I3
  classes: GemType(IntEnum), GemFunction(IntEnum), Position, Move
  functions: is_mega_gem(func_value), encode_mega_gem(func_a, func_b), decode_mega_gem(mega_value), mega_gem_dominant(mega_value), __post_init__(self), is_adjacent_to(self, other), __post_init__(self)

### `src/core/types/match.py` (py)
  imports: I10, I24, I2, I5, I43, I16, I25, I39, I6
  classes: MatchType(Enum), MatchStatus(Enum), PlayerMatchState, MatchState

### `src/core/types/pagination.py` (py)
  imports: I1, I10, I275, I276
  classes: PaginatedResult
  functions: has_more(self)

### `src/core/types/player.py` (py)
  imports: I10, I24, I22, I2, I5, I43, I6
  classes: PlayerType(Enum), Player, PlayerStats, EnergyState
  functions: is_bot(self), win_rate(self)

### `src/core/types/websocket.py` (py)
  imports: I10, I24, I2, I5, I43, I7
  classes: WSMessageType(Enum), WSChannel(Enum), WSMessage, WSAuthMessage, WSSubscribeMessage, WSMatchUpdate
  functions: to_dict(self)

### `src/data/migrations/env.py` (py)
  imports: I1, I82, from alembic import context, from sqlalchemy import pool, from sqlalchemy.engine import Connection, from sqlalchemy.ext.asyncio import async_engine_from_config, I398, I17, I120, I277, I278, I279, I280, I281, I282, I220, I283, I174, I221, I222, I284, I285, I286, I287, I288, I289, I290, I291, I292, I293, I294, I295, I296, I297, I298, I299, I300
  functions: _build_database_url(), run_migrations_offline(), _do_run_migrations(connection), _run_migrations_online_async(), run_migrations_online()

### `src/data/migrations/versions/001_initial_schema.py` (py)
  imports: I44, I45, I49, I50, I14
  functions: upgrade(), downgrade()

### `src/data/migrations/versions/002_player_stats_and_energy.py` (py)
  imports: I44, I45, I49, I50, I14
  functions: upgrade(), downgrade()

### `src/data/migrations/versions/003_auth_sessions_and_api_keys.py` (py)
  imports: I44, I45, I49, I50, I14
  functions: upgrade(), downgrade()

### `src/data/migrations/versions/004_vault_tables.py` (py)
  imports: I44, I45, I50, I49, I14
  functions: upgrade(), downgrade()

### `src/data/migrations/versions/005_match_tables.py` (py)
  imports: I44, I45, I50, I49, I14
  functions: upgrade(), downgrade()

### `src/data/migrations/versions/006_event_tables.py` (py)
  imports: I44, I45, I50, I49, I14
  functions: upgrade(), downgrade()

### `src/data/migrations/versions/007_ad_tables.py` (py)
  imports: I44, I45, I50, I49, I87, I14
  functions: upgrade(), downgrade()

### `src/data/migrations/versions/008_payment_tables.py` (py)
  imports: I44, I45, I50, I49, I87, I14
  functions: upgrade(), downgrade()

### `src/data/migrations/versions/009_bot_earnings_tables.py` (py)
  imports: I44, I45, I50, I49, I14
  functions: upgrade(), downgrade()

### `src/data/migrations/versions/010_card_tables.py` (py)
  imports: I44, I45, I50, I49, I14
  functions: upgrade(), downgrade()

### `src/data/migrations/versions/011_mega_inventory.py` (py)
  imports: I44, I45, I50, I49, I14
  functions: upgrade(), downgrade()

### `src/data/migrations/versions/012_match_raid_data.py` (py)
  imports: I44, I45, I50, I49, I87
  functions: upgrade(), downgrade()

### `src/data/migrations/versions/013_merge_heads.py` (py)
  imports: I44, I45
  functions: upgrade(), downgrade()

### `src/data/migrations/versions/014_nullable_board_states.py` (py)
  imports: I44, I45, I49
  functions: upgrade(), downgrade()

### `src/data/migrations/versions/015_gold_balances.py` (py)
  imports: I44, I45, I50, I49, I14
  functions: upgrade(), downgrade()

### `src/data/migrations/versions/016_match_reward_data.py` (py)
  imports: I44, I45, I50, I49, I87
  functions: upgrade(), downgrade()

### `src/data/migrations/versions/017_apple_auth.py` (py)
  imports: I44, I45, I50, I49
  functions: upgrade(), downgrade()

### `src/data/migrations/versions/018_gold_transactions.py` (py)
  imports: I44, I45, I50, I49, I14
  functions: upgrade(), downgrade()

### `src/data/migrations/versions/019_campaign.py` (py)
  imports: I44, I45, I50, I49, I87, I14
  functions: upgrade(), downgrade()

### `src/data/migrations/versions/020_campaign_score.py` (py)
  imports: I44, I45, I50, I49
  functions: upgrade(), downgrade()

### `src/data/models/__init__.py` (py)
  imports: I17, I75, I36, I280, I278, I120, I277, I279, I281, I282, I220, I283, I174, I221, I222, I284, I285, I286, I287, I288, I289, I290, I291, I292, I293, I294, I295, I296, I297, I298, I299, I300, from src.data.models.player_card import PlayerCardModel, from src.data.models.gold_balance import GoldBalanceModel, from src.data.models.campaign_attempt import CampaignAttemptModel

### `src/data/models/ad_free_status.py` (py)
  imports: I1, I33, I2, I5, I123, I26, I28, I37, I107, I14, I20, I21, I17
  classes: AdFreeStatusModel(Base)

### `src/data/models/ad_impression.py` (py)
  imports: I1, I33, I22, I2, I5, I123, I301, I26, I28, I34, from sqlalchemy import Numeric, I37, I14, I20, I21, I17, I36
  classes: AdImpressionModel(Base, UUIDMixin)

### `src/data/models/ad_request.py` (py)
  imports: I1, I33, I2, I5, I26, I28, I34, I37, I107, I87, I14, I20, I21, I17, I75, I36
  classes: AdRequestModel(Base, UUIDMixin, TimestampMixin)

### `src/data/models/ad_reward.py` (py)
  imports: I1, I33, I2, I5, I26, I28, I34, I37, I143, I14, I20, I21, I17, I36
  classes: AdRewardModel(Base, UUIDMixin)

### `src/data/models/api_key.py` (py)
  imports: I1, I2, I26, I28, from sqlalchemy import Index, I37, from sqlalchemy.dialects.postgresql import UUID as PG_UUID, I20, I21, I17, I75, I36
  classes: ApiKeyModel(Base, UUIDMixin, TimestampMixin)

### `src/data/models/artifact_definition.py` (py)
  imports: I1, I2, I5, I26, I34, I37, I107, I20, I21, I17
  classes: ArtifactDefinitionModel(Base)

### `src/data/models/base.py` (py)
  imports: I1, I33, I2, I5, I26, I14, from sqlalchemy.orm import DeclarativeBase, I20, I21
  classes: Base(DeclarativeBase), UUIDMixin, TimestampMixin

### `src/data/models/bot_attribution_entry.py` (py)
  imports: I1, I33, I22, I2, I5, I301, I26, I28, I34, from sqlalchemy import Numeric, I14, I20, I21, I17, I36
  classes: BotAttributionEntryModel(Base, UUIDMixin)

### `src/data/models/bot_earnings_daily.py` (py)
  imports: I1, I33, I22, I2, I5, I301, I26, I28, I34, I14, I20, I21, I17
  classes: BotEarningsDailyModel(Base)

### `src/data/models/bot_earnings_ledger.py` (py)
  imports: I1, I33, I2, I5, I26, I28, I34, I14, I20, I21, I17, I75
  classes: BotEarningsLedgerModel(Base, TimestampMixin)

### `src/data/models/bot_payout_request.py` (py)
  imports: I1, I33, I2, I5, I26, I28, I34, I37, I107, I14, I20, I21, I17, I36
  classes: BotPayoutRequestModel(Base, UUIDMixin)

### `src/data/models/campaign_attempt.py` (py)
  imports: I1, I33, I2, I302, I26, I28, I34, I37, I87, I14, I20, I21, I17, I75, I36
  classes: CampaignAttemptModel(Base, UUIDMixin, TimestampMixin)

### `src/data/models/energy_state.py` (py)
  imports: I1, I33, I22, I2, I5, I301, I26, I28, I34, I14, I20, I21, I17, I75
  classes: EnergyStateModel(Base, TimestampMixin)

### `src/data/models/event.py` (py)
  imports: I1, I33, I2, I5, from sqlalchemy import CheckConstraint, I26, I28, I34, I37, I107, I87, I14, I20, I21, I17, I75, I36
  classes: EventModel(Base, UUIDMixin, TimestampMixin)

### `src/data/models/event_ad_claim.py` (py)
  imports: I1, I33, I2, I5, I26, I28, I37, I143, I14, I20, I21, I17, I36
  classes: EventAdClaimModel(Base, UUIDMixin)

### `src/data/models/event_ad_opportunity.py` (py)
  imports: I1, I33, I2, I5, I26, I28, I34, I37, I107, I14, I20, I21, I17
  classes: EventAdOpportunityModel(Base)

### `src/data/models/event_match.py` (py)
  imports: I1, I33, I2, I5, I26, I28, I34, I143, I14, I20, I21, I17, I36
  classes: EventMatchRecordModel(Base, UUIDMixin)

### `src/data/models/event_participant.py` (py)
  imports: I1, I33, I2, I5, I123, I26, I28, I34, I37, I14, I20, I21, I17
  classes: EventParticipantModel(Base)

### `src/data/models/gold_balance.py` (py)
  imports: I1, I33, I28, I34, I14, I20, I21, I17, I75
  classes: GoldBalanceModel(Base, TimestampMixin)

### `src/data/models/gold_transaction.py` (py)
  imports: I1, I33, I2, I5, I26, I28, I34, I37, I14, I20, I21, I17, I36
  classes: GoldTransactionModel(Base, UUIDMixin)

### `src/data/models/match.py` (py)
  imports: I1, I33, I2, I5, I302, from sqlalchemy import CheckConstraint, I26, I28, I34, I37, I87, I14, I20, I21, I17, I36
  classes: MatchModel(Base, UUIDMixin)

### `src/data/models/match_move.py` (py)
  imports: I1, I33, I2, I5, I302, I26, I28, I34, I143, I87, I14, I20, I21, I17, I36
  classes: MatchMoveModel(Base, UUIDMixin)

### `src/data/models/mega_gem_inventory.py` (py)
  imports: I1, I28, I34, I143, I14, I20, I21, I17, I36
  classes: MegaGemInventoryModel(Base, UUIDMixin)

### `src/data/models/player.py` (py)
  imports: I1, I2, I26, I34, I37, I20, I21, I17, I75, I36
  classes: PlayerModel(Base, UUIDMixin, TimestampMixin)

### `src/data/models/player_card.py` (py)
  imports: I1, I2, I5, I26, I28, I34, I37, I143, I14, I20, I21, I17, I36
  classes: PlayerCardModel(Base, UUIDMixin)

### `src/data/models/player_stats.py` (py)
  imports: I1, I33, I302, I28, I34, I14, I20, I21, I17, I75
  classes: PlayerStatsModel(Base, TimestampMixin)

### `src/data/models/product.py` (py)
  imports: I1, I2, I5, I123, I26, I34, I37, I107, I20, I21, I17
  classes: ProductModel(Base)

### `src/data/models/purchase.py` (py)
  imports: I1, I33, I2, I5, I123, I26, I28, I34, I37, I143, I14, I20, I21, I17, I75, I36
  classes: PurchaseModel(Base, UUIDMixin, TimestampMixin)

### `src/data/models/purchase_intent.py` (py)
  imports: I1, I33, I2, I5, I26, I28, I37, I14, I20, I21, I17, I75, I36
  classes: PurchaseIntentModel(Base, UUIDMixin, TimestampMixin)

### `src/data/models/raid_log.py` (py)
  imports: I1, I2, I5, I123, I26, I28, I37, I14, I20, I21, I17, I36
  classes: RaidLogModel(Base, UUIDMixin)

### `src/data/models/receipt_validation.py` (py)
  imports: I1, I33, I2, I5, I123, I26, I28, I37, I107, I87, I14, I20, I21, I17, I36
  classes: ReceiptValidationModel(Base, UUIDMixin)

### `src/data/models/refund_notification.py` (py)
  imports: I1, I33, I2, I5, I123, I26, I28, I37, I107, I87, I14, I20, I21, I17, I36
  classes: RefundNotificationModel(Base, UUIDMixin)

### `src/data/models/session.py` (py)
  imports: I1, I2, I26, I28, from sqlalchemy import Index, I37, from sqlalchemy.dialects.postgresql import UUID as PG_UUID, I20, I21, I17, I75, I36
  classes: SessionModel(Base, UUIDMixin, TimestampMixin)

### `src/data/models/vault_artifact.py` (py)
  imports: I1, I2, I5, I26, I28, I37, I14, I20, I21, I17, I36
  classes: VaultArtifactModel(Base, UUIDMixin)

### `src/data/models/vault_shield.py` (py)
  imports: I1, I2, I5, I26, I28, I34, I14, I20, I21, I17
  classes: VaultShieldModel(Base)

### `src/data/protocols/__init__.py` (py)
  imports: from src.data.protocols.api_key_repository import ApiKeyRepositoryProtocol, I408, from src.data.protocols.player_repository import PlayerRepositoryProtocol, from src.data.protocols.player_stats_repository import PlayerStatsRepositoryProtocol, from src.data.protocols.session_repository import SessionRepositoryProtocol, I409

### `src/data/protocols/ad_free_status_repository.py` (py)
  imports: I1, I2, I7, I13, I3
  classes: AdFreeStatusRepositoryProtocol(Protocol)
  functions: find_by_player(self, player_id), upsert(self, data), revoke(self, player_id, reason), find_expiring(self, before)

### `src/data/protocols/ad_impression_repository.py` (py)
  imports: I1, I22, I7, I13, I3
  classes: AdImpressionRepositoryProtocol(Protocol)
  functions: create(self, data), find_by_id(self, impression_id), find_by_request_id(self, ad_request_id), find_by_player(self, player_id, ad_type, limit, offset), find_by_match(self, match_id), get_player_stats(self, player_id, start_date, end_date), get_bot_attributions(self, bot_player_id, start_date, end_date), get_daily_attributions(self, bot_player_id, start_date, end_date)

### `src/data/protocols/ad_request_repository.py` (py)
  imports: I1, I2, I7, I13, I3
  classes: AdRequestRepositoryProtocol(Protocol)
  functions: create(self, data), find_by_id(self, request_id), update(self, request_id, changes), find_pending_by_player(self, player_id), find_last_by_type(self, player_id, ad_type), expire_old_requests(self, before)

### `src/data/protocols/ad_reward_repository.py` (py)
  imports: I1, I7, I13, I3
  classes: AdRewardRepositoryProtocol(Protocol)
  functions: create(self, data), find_by_request_id(self, ad_request_id)

### `src/data/protocols/api_key_repository.py` (py)
  imports: I1, I10, I2, I13, I3
  classes: ApiKeyRecord, ApiKeyRepositoryProtocol(Protocol)
  functions: create(self, player_id, key_hash, key_prefix, description), find_by_id(self, key_id), find_by_prefix(self, prefix), find_by_player_id(self, player_id, include_revoked), update_last_used(self, key_id), revoke(self, key_id), count_active_for_player(self, player_id)

### `src/data/protocols/artifact_definition_repository.py` (py)
  imports: I1, I7, I13
  classes: ArtifactDefinitionRepositoryProtocol(Protocol)
  functions: find_by_type_id(self, type_id), list_all(self, rarity, artifact_set), list_by_set(self, artifact_set), get_set_type_ids(self, artifact_set), list_all_sets(self)

### `src/data/protocols/campaign_attempt_repository.py` (py)
  imports: I1, I10, I24, I13, I3
  classes: CampaignAttemptRecord, CampaignAttemptRepositoryProtocol(Protocol)
  functions: create(self, player_id, level_number, board_seed, board_state, moves_remaining, obstacles_remaining), find_by_id(self, attempt_id), find_active_by_player(self, player_id), update(self, attempt_id)

### `src/data/protocols/energy_state_repository.py` (py)
  imports: I1, I22, I2, I13, I3, I142
  classes: EnergyStateRepositoryProtocol(Protocol)
  functions: find_by_player_id(self, player_id), create(self, player_id, hearts, max_hearts), update(self, player_id)

### `src/data/protocols/event_ad_claim_repository.py` (py)
  imports: I1, I7, I13, I3
  classes: EventAdClaimRepositoryProtocol(Protocol)
  functions: create(self, data), count_claims(self, event_id, opportunity_id, player_id), find_last_claim(self, event_id, opportunity_id, player_id)

### `src/data/protocols/event_ad_opportunity_repository.py` (py)
  imports: I1, I7, I13, I3
  classes: EventAdOpportunityRepositoryProtocol(Protocol)
  functions: find_by_event(self, event_id), find_by_id(self, event_id, opportunity_id), create(self, data)

### `src/data/protocols/event_leaderboard_repository.py` (py)
  imports: I1, I7, I13, I3
  classes: EventLeaderboardRepositoryProtocol(Protocol)
  functions: update_score(self, event_id, player_id, score), get_rank(self, event_id, player_id), get_score(self, event_id, player_id), get_top(self, event_id, limit, offset), get_total_count(self, event_id), get_percentile(self, event_id, player_id), remove_player(self, event_id, player_id), clear_leaderboard(self, event_id), sync_to_database(self, event_id, participant_repo)

### `src/data/protocols/event_participant_repository.py` (py)
  imports: I1, I7, I13, I3, I175, I176, I124
  classes: EventParticipantRepositoryProtocol(Protocol)
  functions: create(self, data), find_by_event_and_player(self, event_id, player_id), update(self, event_id, player_id, changes), find_by_event(self, event_id, active_only, limit, offset), find_by_player(self, player_id, include_past, limit, offset), find_ranked_by_event(self, event_id, limit, offset), count_by_event(self, event_id, active_only), bulk_update_ranks(self, event_id, ranks), find_eligible_for_rewards(self, event_id, min_matches), create_event_match(self, data)

### `src/data/protocols/event_repository.py` (py)
  imports: I1, I2, I7, I13, I3, I104, I108
  classes: EventRepositoryProtocol(Protocol)
  functions: create(self, data), find_by_id(self, event_id), update(self, event_id, changes), find_by_status(self, status, event_type, limit, offset), find_active(self), find_scheduled_to_start(self, before), find_active_to_end(self, before), find_ended_to_finalize(self, before), increment_participant_count(self, event_id), decrement_participant_count(self, event_id)

### `src/data/protocols/gold_balance_repository.py` (py)
  imports: I1, I10, I13, I3
  classes: GoldBalanceRecord, GoldBalanceRepositoryProtocol(Protocol)
  functions: find_by_player_id(self, player_id), create(self, player_id), credit(self, player_id, amount), debit(self, player_id, amount)

### `src/data/protocols/gold_transaction_repository.py` (py)
  imports: I1, I10, I2, I13, I3
  classes: GoldTransactionRecord, GoldTransactionRepositoryProtocol(Protocol)
  functions: create(self, player_id, tx_type, amount, balance_after, source, reference_id), find_by_player(self, player_id, limit, offset), find_by_reference(self, reference_id)

### `src/data/protocols/match_repository.py` (py)
  imports: I1, I2, I4, I13, I3, I174, I221, I303, I144, I304
  classes: MatchRepositoryProtocol(Protocol), MatchMoveRepositoryProtocol(Protocol)
  functions: create(self, data), find_by_id(self, match_id), update(self, match_id, changes), find_active_by_player(self, player_id), find_by_player(self, player_id, status, limit, offset), find_stale_matches(self, cutoff), bulk_abandon(self, match_ids), create(self, data), find_by_match(self, match_id, player_id), count_by_player(self, match_id, player_id)

### `src/data/protocols/matchmaking_queue_repository.py` (py)
  imports: I1, I2, I13, I3, I97, I145
  classes: MatchmakingQueueRepositoryProtocol(Protocol)
  functions: add_to_queue(self, player_id, elo_rating, pool_type, initial_elo_range), remove_from_queue(self, player_id), get_player_queue_state(self, player_id), is_in_queue(self, player_id), find_opponents_in_range(self, pool_type, min_elo, max_elo, exclude_player_id, limit), get_queue_count(self, pool_type), get_all_queued_players(self, pool_type), update_elo_range(self, player_id, new_min_elo, new_max_elo), remove_stale_entries(self, cutoff_time), get_players_by_elo_bucket(self, pool_type, bucket_size), atomic_remove_pair(self, player1_id, player2_id)

### `src/data/protocols/player_card_repository.py` (py)
  imports: I1, I7, I13, I3
  classes: PlayerCardRepositoryProtocol(Protocol)
  functions: find_by_id(self, card_instance_id), find_by_player(self, player_id, limit, offset), find_equipped(self, player_id), count_by_player(self, player_id), find_max_position(self, player_id), create(self, player_id, card_id, position, source, source_id), update_position(self, card_instance_id, new_position), delete(self, card_instance_id), delete_multiple(self, card_instance_ids)

### `src/data/protocols/player_repository.py` (py)
  imports: I1, I7, I13, I3, I86, I32
  classes: PlayerRepositoryProtocol(Protocol)
  functions: find_by_id(self, player_id), find_by_username(self, username), create(self, username, player_type, password_hash), update(self, player_id), delete(self, player_id), list_players(self, player_type, limit, offset)

### `src/data/protocols/player_stats_repository.py` (py)
  imports: I1, I13, I3, I122
  classes: PlayerStatsRepositoryProtocol(Protocol)
  functions: find_by_player_id(self, player_id), create(self, player_id), update(self, player_id)

### `src/data/protocols/raid_log_repository.py` (py)
  imports: I1, I7, I13, I3
  classes: RaidLogRepositoryProtocol(Protocol)
  functions: create(self, attacker_id, defender_id, success, artifact_id, artifact_type_id), find_by_player(self, player_id, as_attacker, as_defender, limit, offset), find_last_raid_between(self, attacker_id, defender_id)

### `src/data/protocols/session_repository.py` (py)
  imports: I1, I10, I2, I13, I3
  classes: SessionRecord, SessionRepositoryProtocol(Protocol)
  functions: create(self, player_id, refresh_token_hash, expires_at, device_info, session_id), find_by_id(self, session_id), find_by_player_id(self, player_id, include_revoked), update_last_used(self, session_id), revoke(self, session_id), revoke_all_for_player(self, player_id), count_active_for_player(self, player_id), cleanup_expired(self)

### `src/data/protocols/vault_artifact_repository.py` (py)
  imports: I1, I7, I13, I3
  classes: VaultArtifactRepositoryProtocol(Protocol)
  functions: find_by_id(self, artifact_id), find_by_owner(self, owner_id, rarity, artifact_set, limit, offset), count_by_owner(self, owner_id), count_by_owner_and_rarity(self, owner_id), find_by_owner_and_type(self, owner_id, artifact_type_id), list_owned_type_ids(self, owner_id, artifact_set), create(self, owner_id, artifact_type_id, source, source_id), update_owner(self, artifact_id, new_owner_id), delete(self, artifact_id), get_random_artifact(self, owner_id, exclude_legendary)

### `src/data/protocols/vault_shield_repository.py` (py)
  imports: I1, I2, I7, I13, I3
  classes: VaultShieldRepositoryProtocol(Protocol)
  functions: find_by_player(self, player_id), create(self, player_id, activated_at, expires_at, duration_hours), delete(self, player_id), delete_expired(self)

### `src/data/repositories/__init__.py` (py)
  imports: I401, I165, I265, I166, I400

### `src/data/repositories/ad_free_status_repository.py` (py)
  imports: I1, I2, I5, I4, I3, I19, I288, I15, I9, I8, I305
  classes: SQLAlchemyAdFreeStatusRepository
  functions: __init__(self, data_ctx, logger, errors), find_by_player(self, player_id), upsert(self, data), revoke(self, player_id, reason), find_expiring(self, before)

### `src/data/repositories/ad_impression_repository.py` (py)
  imports: I1, I22, I4, I7, I3, I55, I19, I287, I15, I9, I8, I146
  classes: SQLAlchemyAdImpressionRepository
  functions: __init__(self, data_ctx, logger, errors), create(self, data), find_by_id(self, impression_id), find_by_request_id(self, ad_request_id), find_by_player(self, player_id, ad_type, limit, offset), find_by_match(self, match_id), get_player_stats(self, player_id, start_date, end_date), get_bot_attributions(self, bot_player_id, start_date, end_date), get_daily_attributions(self, bot_player_id, start_date, end_date)

### `src/data/repositories/ad_request_repository.py` (py)
  imports: I1, I2, I4, I3, I19, I223, I286, I15, I9, I8, I224, I177
  classes: SQLAlchemyAdRequestRepository
  functions: __init__(self, data_ctx, logger, errors), create(self, data), find_by_id(self, request_id), update(self, request_id, changes), find_pending_by_player(self, player_id), find_last_by_type(self, player_id, ad_type), expire_old_requests(self, before)

### `src/data/repositories/ad_reward_repository.py` (py)
  imports: I1, I4, I3, I19, I289, I15, I9, I8, I306
  classes: SQLAlchemyAdRewardRepository
  functions: __init__(self, data_ctx, logger, errors), create(self, data), find_by_request_id(self, ad_request_id)

### `src/data/repositories/api_key_repository.py` (py)
  imports: I1, I2, I5, I4, I3, I55, I19, I172, I280, from src.data.protocols.api_key_repository import ApiKeyRecord, I15, I9, I8
  classes: SQLAlchemyApiKeyRepository
  functions: __init__(self, data_ctx, logger, errors), create(self, player_id, key_hash, key_prefix, description), find_by_id(self, key_id), find_by_prefix(self, prefix), find_by_player_id(self, player_id, include_revoked), update_last_used(self, key_id), revoke(self, key_id), count_active_for_player(self, player_id), _to_record(model)

### `src/data/repositories/artifact_definition_repository.py` (py)
  imports: I1, I10, I2, I4, I3, I55, I19, I220, I15, I9, I8
  classes: ArtifactDefinitionRecord, SQLAlchemyArtifactDefinitionRepository
  functions: __init__(self, data_ctx, logger, errors), find_by_type_id(self, type_id), list_all(self, rarity, artifact_set), list_by_set(self, artifact_set), get_set_type_ids(self, artifact_set), list_all_sets(self), _to_record(model)

### `src/data/repositories/bot_attribution_entry_repository.py` (py)
  imports: I1, I22, I4, I7, I3, I55, I19, I298, I15, I9, I8, I307
  classes: SQLAlchemyAttributionEntryRepository
  functions: __init__(self, data_ctx, logger, errors), create(self, data), create_batch(self, entries), find_by_impression_id(self, ad_impression_id), find_by_bot(self, bot_player_id, start_date, end_date, limit, offset), get_daily_summary(self, bot_player_id, start_date, end_date), get_period_summary(self, bot_player_id, start_date, end_date), get_last_recorded_for_bot(self, bot_player_id)

### `src/data/repositories/bot_daily_earnings_repository.py` (py)
  imports: I1, I22, I4, I3, I19, I300, I15, I9, I8, I308
  classes: SQLAlchemyDailyEarningsRepository
  functions: __init__(self, data_ctx, logger, errors), upsert(self, data), find_range(self, bot_player_id, start_date, end_date)

### `src/data/repositories/bot_earnings_ledger_repository.py` (py)
  imports: I1, I2, I4, I3, I19, I297, I15, I9, I8, I309, I310
  classes: SQLAlchemyEarningsLedgerRepository
  functions: __init__(self, data_ctx, logger, errors), find_by_bot_id(self, bot_player_id), create(self, data), update(self, bot_player_id, changes), increment_earned(self, bot_player_id, cents), increment_pending(self, bot_player_id, cents), complete_payout(self, bot_player_id, cents), cancel_pending(self, bot_player_id, cents), find_bots_needing_sync(self, since, limit)

### `src/data/repositories/bot_payout_request_repository.py` (py)
  imports: I1, I2, I4, I3, I55, I19, I299, I15, I9, I8, I311, I312
  classes: SQLAlchemyPayoutRequestRepository
  functions: __init__(self, data_ctx, logger, errors), create(self, data), find_by_id(self, payout_request_id), update(self, payout_request_id, changes), find_by_bot(self, bot_player_id, status, limit, offset), find_pending_by_bot(self, bot_player_id), find_pending_past_hold(self, as_of)

### `src/data/repositories/campaign_attempt_repository.py` (py)
  imports: I1, I2, I5, I4, I3, I19, from src.data.models.campaign_attempt import CampaignAttemptModel, I313, I15, I9, I8
  classes: SQLAlchemyCampaignAttemptRepository
  functions: __init__(self, data_ctx, logger, errors), create(self, player_id, level_number, board_seed, board_state, moves_remaining, obstacles_remaining), find_by_id(self, attempt_id), find_active_by_player(self, player_id), update(self, attempt_id), _to_record(model)

### `src/data/repositories/energy_state_repository.py` (py)
  imports: I1, I4, I3, I19, I6, I142, I278, I15, I9, I8
  classes: SQLAlchemyEnergyStateRepository
  functions: __init__(self, data_ctx, logger, errors), find_by_player_id(self, player_id), create(self, player_id, hearts, max_hearts), update(self, player_id), _to_domain(model)

### `src/data/repositories/event_ad_claim_repository.py` (py)
  imports: I1, I4, I3, I55, I19, I291, I15, I9, I8, I314
  classes: SQLAlchemyEventAdClaimRepository
  functions: __init__(self, data_ctx, logger, errors), create(self, data), count_claims(self, event_id, opportunity_id, player_id), find_last_claim(self, event_id, opportunity_id, player_id)

### `src/data/repositories/event_ad_opportunity_repository.py` (py)
  imports: I1, I4, I3, I19, I290, I15, I9, I8, I410
  classes: SQLAlchemyEventAdOpportunityRepository
  functions: __init__(self, data_ctx, logger, errors), find_by_event(self, event_id), find_by_id(self, event_id, opportunity_id), create(self, data)

### `src/data/repositories/event_leaderboard_repository.py` (py)
  imports: I1, I4, I7, I3, from redis.asyncio import Redis, I8
  classes: RedisEventLeaderboardRepository
  functions: __init__(self, redis, logger), _key(self, event_id), update_score(self, event_id, player_id, score), get_rank(self, event_id, player_id), get_score(self, event_id, player_id), get_top(self, event_id, limit, offset), get_total_count(self, event_id), get_percentile(self, event_id, player_id), remove_player(self, event_id, player_id), clear_leaderboard(self, event_id), sync_to_database(self, event_id, participant_repo)

### `src/data/repositories/event_participant_repository.py` (py)
  imports: I1, I411, I4, I3, from sqlalchemy import and_, I55, I19, I223, I222, I285, I284, I15, I9, I8, I175, I176, I124
  classes: SQLAlchemyEventParticipantRepository
  functions: __init__(self, data_ctx, logger, errors), create(self, data), find_by_event_and_player(self, event_id, player_id), update(self, event_id, player_id, changes), find_by_event(self, event_id, active_only, limit, offset), find_by_player(self, player_id, include_past, limit, offset), find_ranked_by_event(self, event_id, limit, offset), count_by_event(self, event_id, active_only), bulk_update_ranks(self, event_id, ranks), find_eligible_for_rewards(self, event_id, min_matches), create_event_match(self, data)

### `src/data/repositories/event_repository.py` (py)
  imports: I1, I411, I2, I4, I3, I55, I19, I223, I222, I15, I9, I8, I104, I108
  classes: SQLAlchemyEventRepository
  functions: __init__(self, data_ctx, logger, errors), create(self, data), find_by_id(self, event_id), update(self, event_id, changes), find_by_status(self, status, event_type, limit, offset), find_active(self), find_scheduled_to_start(self, before), find_active_to_end(self, before), find_ended_to_finalize(self, before), increment_participant_count(self, event_id), decrement_participant_count(self, event_id)

### `src/data/repositories/gold_balance_repository.py` (py)
  imports: I1, I4, I3, I19, from src.data.models.gold_balance import GoldBalanceModel, from src.data.protocols.gold_balance_repository import GoldBalanceRecord, I15, I9, I8
  classes: SQLAlchemyGoldBalanceRepository
  functions: __init__(self, data_ctx, logger, errors), find_by_player_id(self, player_id), create(self, player_id), credit(self, player_id, amount), debit(self, player_id, amount), _to_record(model)

### `src/data/repositories/gold_transaction_repository.py` (py)
  imports: I1, I4, I3, I19, from src.data.models.gold_transaction import GoldTransactionModel, from src.data.protocols.gold_transaction_repository import GoldTransactionRecord, I15, I9, I8
  classes: SQLAlchemyGoldTransactionRepository
  functions: __init__(self, data_ctx, logger, errors), create(self, player_id, tx_type, amount, balance_after, source, reference_id), find_by_player(self, player_id, limit, offset), find_by_reference(self, reference_id), _to_record(model)

### `src/data/repositories/match_repository.py` (py)
  imports: I1, I411, I2, I4, I3, from sqlalchemy import delete as sa_delete, I55, from sqlalchemy import or_, I19, from sqlalchemy import text, I223, I174, I221, I15, I9, I8, I303, I144, I304
  classes: SQLAlchemyMatchRepository, SQLAlchemyMatchMoveRepository
  functions: __init__(self, data_ctx, logger, errors), create(self, data), find_by_id(self, match_id), update(self, match_id, changes), find_active_by_player(self, player_id), find_by_player(self, player_id, status, limit, offset), find_stale_matches(self, cutoff), bulk_abandon(self, match_ids), cleanup_match_data(self, match_id), __init__(self, data_ctx, logger, errors), create(self, data), find_by_match(self, match_id, player_id), count_by_player(self, match_id, player_id), delete_by_match_id(self, match_id)

### `src/data/repositories/matchmaking_queue_repository.py` (py)
  imports: I1, I2, I5, I4, I3, I97, I145, I399
  classes: RedisMatchmakingQueueRepository
  functions: _queue_key(pool_type), _player_key(player_id), _parse_queue_entry_data(player_id, data), __init__(self, data_ctx), add_to_queue(self, player_id, elo_rating, pool_type, initial_elo_range), remove_from_queue(self, player_id), get_player_queue_state(self, player_id), is_in_queue(self, player_id), find_opponents_in_range(self, pool_type, min_elo, max_elo, exclude_player_id, limit), get_queue_count(self, pool_type), get_all_queued_players(self, pool_type), update_elo_range(self, player_id, new_min_elo, new_max_elo), remove_stale_entries(self, cutoff_time), get_players_by_elo_bucket(self, pool_type, bucket_size), atomic_remove_pair(self, player1_id, player2_id)

### `src/data/repositories/mega_gem_inventory_repository.py` (py)
  imports: I1, I10, I4, I3, I19, I172, from sqlalchemy.dialects.postgresql import insert as pg_insert, from src.data.models.mega_gem_inventory import MegaGemInventoryModel, I15, I9, I8
  classes: MegaGemInventoryRecord, SQLAlchemyMegaGemInventoryRepository
  functions: __init__(self, data_ctx, logger, errors), get_inventory(self, player_id), get_slot(self, player_id, slot_index), consume_one(self, player_id, slot_index), add_count(self, player_id, slot_index, amount), ensure_slots(self, player_id), _to_record(model)

### `src/data/repositories/password_store_repository.py` (py)
  imports: I1, I4, I3, I19, I172, I120, I15
  classes: SQLAlchemyPasswordStoreRepository
  functions: __init__(self, data_ctx), get_password_hash(self, player_id), set_password_hash(self, player_id, password_hash)

### `src/data/repositories/player_card_repository.py` (py)
  imports: I1, I10, I2, I4, I3, from sqlalchemy import delete as sa_delete, I55, I19, I172, from src.data.models.player_card import PlayerCardModel, I15, I9, I8
  classes: PlayerCardRecord, SQLAlchemyPlayerCardRepository
  functions: __init__(self, data_ctx, logger, errors), find_by_id(self, card_instance_id), find_by_player(self, player_id, limit, offset), find_equipped(self, player_id), count_by_player(self, player_id), find_max_position(self, player_id), create(self, player_id, card_id, position, source, source_id), update_position(self, card_instance_id, new_position), delete(self, card_instance_id), delete_multiple(self, card_instance_ids), _to_record(model)

### `src/data/repositories/player_repository.py` (py)
  imports: I1, I4, I7, I3, I55, I19, I6, I86, I32, I120, I15, I9, I8
  classes: SQLAlchemyPlayerRepository
  functions: __init__(self, data_ctx, logger, errors), find_by_id(self, player_id), find_by_username(self, username), find_by_apple_user_id(self, apple_user_id), create(self, username, player_type, password_hash, apple_user_id, auth_provider), update(self, player_id), delete(self, player_id), list_players(self, player_type, limit, offset), _to_domain(model)

### `src/data/repositories/player_stats_repository.py` (py)
  imports: I1, I4, I3, I55, I19, I6, I122, I120, I277, I15, I9, I8
  classes: SQLAlchemyPlayerStatsRepository
  functions: __init__(self, data_ctx, logger, errors), find_by_player_id(self, player_id), create(self, player_id), update(self, player_id), list_by_highest_score(self, limit, offset), _to_domain(model)

### `src/data/repositories/product_repository.py` (py)
  imports: I1, I4, I19, I292, I15, I9, I8
  classes: SQLAlchemyProductRepository
  functions: __init__(self, data_ctx, logger, errors), find_by_id(self, product_id), find_all_active(self)

### `src/data/repositories/purchase_intent_repository.py` (py)
  imports: I1, I2, I4, I3, I19, I223, I293, I15, I9, I8, I315, I316
  classes: SQLAlchemyPurchaseIntentRepository
  functions: __init__(self, data_ctx, logger, errors), create(self, data), find_by_id(self, intent_id), update(self, intent_id, changes), find_pending_by_player(self, player_id), expire_old_intents(self, before)

### `src/data/repositories/purchase_repository.py` (py)
  imports: I1, I4, I3, I55, I19, I294, I15, I9, I8, I317, I318
  classes: SQLAlchemyPurchaseRepository
  functions: __init__(self, data_ctx, logger, errors), create(self, data), find_by_id(self, purchase_id), find_by_transaction(self, provider, transaction_id), find_by_player(self, player_id, limit, offset), find_completed_by_player(self, player_id, product_id), update(self, purchase_id, changes)

### `src/data/repositories/raid_log_repository.py` (py)
  imports: I1, I10, I2, I4, I3, I55, from sqlalchemy import or_, I19, I283, I15, I9, I8
  classes: RaidLogRecord, SQLAlchemyRaidLogRepository
  functions: __init__(self, data_ctx, logger, errors), create(self, attacker_id, defender_id, success, artifact_id, artifact_type_id), find_by_player(self, player_id, as_attacker, as_defender, limit, offset), find_last_raid_between(self, attacker_id, defender_id), _to_record(model)

### `src/data/repositories/receipt_validation_repository.py` (py)
  imports: I1, I4, I3, I19, I295, I15, I9, I8, I319, I320
  classes: SQLAlchemyReceiptValidationRepository
  functions: __init__(self, data_ctx, logger, errors), create(self, data), find_by_hash(self, receipt_hash), find_by_transaction(self, provider, transaction_id), update(self, validation_id, changes)

### `src/data/repositories/refund_notification_repository.py` (py)
  imports: I1, I2, I5, I4, I3, I19, I296, I15, I9, I8, I321
  classes: SQLAlchemyRefundNotificationRepository
  functions: __init__(self, data_ctx, logger, errors), create(self, data), find_unprocessed(self), mark_processed(self, notification_id, result, error)

### `src/data/repositories/session_repository.py` (py)
  imports: I1, I2, I29, I5, I4, I7, I3, from sqlalchemy import delete, I55, I19, I172, I279, from src.data.protocols.session_repository import SessionRecord, I15, I9, I8
  classes: SQLAlchemySessionRepository
  functions: __init__(self, data_ctx, logger, errors), create(self, player_id, refresh_token_hash, expires_at, device_info, session_id), find_by_id(self, session_id), find_by_player_id(self, player_id, include_revoked), update_last_used(self, session_id), revoke(self, session_id), revoke_all_for_player(self, player_id), count_active_for_player(self, player_id), cleanup_expired(self), _to_record(model)

### `src/data/repositories/vault_artifact_repository.py` (py)
  imports: I1, I10, I2, I4, I7, I3, I55, I19, from sqlalchemy.sql.expression import literal_column, I220, I281, I15, I9, I8
  classes: VaultArtifactRecord, SQLAlchemyVaultArtifactRepository
  functions: __init__(self, data_ctx, logger, errors), find_by_id(self, artifact_id), find_by_owner(self, owner_id, rarity, artifact_set, limit, offset), count_by_owner(self, owner_id), count_by_owner_and_rarity(self, owner_id), find_by_owner_and_type(self, owner_id, artifact_type_id), list_owned_type_ids(self, owner_id, artifact_set), create(self, owner_id, artifact_type_id, source, source_id), update_owner(self, artifact_id, new_owner_id), delete(self, artifact_id), get_random_artifact(self, owner_id, exclude_legendary), _to_record(model)

### `src/data/repositories/vault_shield_repository.py` (py)
  imports: I1, I10, I2, I5, I4, I3, from sqlalchemy import delete, I55, I19, I282, I15, I9, I8
  classes: VaultShieldRecord, SQLAlchemyVaultShieldRepository
  functions: __init__(self, data_ctx, logger, errors), find_by_player(self, player_id), create(self, player_id, activated_at, expires_at, duration_hours), delete(self, player_id), delete_expired(self), _to_record(model)

### `src/modules/ads/__init__.py` (py)
  imports: I305, I146, I224, I177, I306, I314, I410, I225, I412, I160, I161, I413, I322, I84, I138, I125, from src.modules.ads.types import AdImpressionId, I134, I115, I226, I90, I162, I135, from src.modules.ads.types import DailyAttribution, I178, I227, I228, I163, I179, I180, I164, I229, I230, I133

### `src/modules/ads/_helpers.py` (py)
  imports: I1, I22, I2, I29, I5, I4, I7, from typing import Awaitable, I323, I13, from typing import runtime_checkable, I38, I25, I6, I177, I84, I138, I125, from src.modules.ads.types import AdImpressionId, I134, I115, I226, I90, I135, from src.modules.ads.types import DailyAttribution, I178, I179, I180, I133, I18, I9, I8, I181, I324, I3
  classes: AdFreeStatusRecord(Protocol), ImpressionRecord(Protocol), PlayerStatsRecord(Protocol), DailyAttributionRecord(Protocol), EventOpportunityRecord(Protocol), AdRequestRecord(Protocol), BotAggregateRecord(Protocol)
  functions: build_ad_free_status(record, player_id), build_impression(record), calc_revenue(ad_type, viewed, cpm_cents), stats_date_range(period), build_player_stats(record, pid, period), build_daily_attr(record), build_event_opp(record, event_id, claimed, avail, next_at), build_match_attribution(match_id, impressions, share), build_bot_report(pid, start, end, agg, daily_recs, share), cooldown_seconds(ad_type, cd_inter, cd_reward), guard_ad_free(player_id, free_repo, errors), guard_cooldown(player_id, ad_type, cd_inter, cd_reward, req_repo, errors), valid_request(rid, req_repo, errors), provider_call(fn, unit, player_id, config, logger, errors)

### `src/modules/ads/ad_free_manager.py` (py)
  imports: I1, I2, I29, I5, I4, I6, I414, I305, I84, I138, I18, I9, I8, I181, I147
  classes: AdFreeManager
  functions: __init__(self, config, logger, errors, player_service, free_repo), check_ad_free_status(self, player_id), grant_ad_free_status(self, player_id, reason, duration_days, granted_by), revoke_ad_free_status(self, player_id, reason)

### `src/modules/ads/analytics_service.py` (py)
  imports: I1, I22, I4, I25, I6, from src.modules.ads._helpers import build_bot_report, I231, from src.modules.ads._helpers import build_match_attribution, from src.modules.ads._helpers import build_player_stats, from src.modules.ads._helpers import stats_date_range, I225, I125, I90, I135, I179, I180, I133, I18, I9, I8, I182, I147
  classes: AdAnalyticsService
  functions: __init__(self, config, logger, errors, player_service, imp_repo), get_player_ad_stats(self, player_id, period), get_ad_impressions(self, player_id, ad_type, limit, offset), get_match_ad_attribution(self, match_id), get_bot_ad_attributions(self, bot_player_id, start_date, end_date)

### `src/modules/ads/banner_manager.py` (py)
  imports: I1, I4, I6, I231, I325, I415, I146, I125, I90, I162, I18, I9, I8, I181, I182, I147
  classes: BannerManager
  functions: __init__(self, config, logger, errors, player_service, imp_repo, free_repo), record_banner_impression(self, player_id, banner_placement, view_duration_ms)

### `src/modules/ads/dto.py` (py)
  imports: I1, I10, I2, I7, I3, I183
  classes: AdRequestCreate, AdRequestUpdate, AdImpressionCreate, AdFreeStatusUpsert, AdRewardCreate, EventAdOpportunityCreate, EventAdClaimCreate

### `src/modules/ads/event_ad_service.py` (py)
  imports: I1, I2, I5, I4, I38, I6, from src.modules.ads._helpers import build_event_opp, I231, I325, I146, I314, I90, I178, I227, I18, I9, I8, I182, from src.modules.ads.protocols import EventAdClaimRepositoryProtocol, from src.modules.ads.protocols import EventAdOpportunityRepositoryProtocol, from src.modules.ads.protocols import EventServiceProtocol, I147
  classes: EventAdService
  functions: __init__(self, config, logger, errors, player_service, events_service, opp_repo, claim_repo, imp_repo), get_event_ad_opportunities(self, player_id, event_id), claim_event_ad_reward(self, player_id, event_id, opportunity_id)

### `src/modules/ads/interstitial_manager.py` (py)
  imports: I1, I2, I29, I5, I4, I25, I6, I414, I231, I325, I415, from src.modules.ads._helpers import guard_cooldown, from src.modules.ads._helpers import provider_call, from src.modules.ads._helpers import valid_request, I146, I224, I177, I125, I115, I226, I90, I228, I163, I18, I9, I8, I181, I182, I416, I324, I147
  classes: InterstitialManager
  functions: __init__(self, config, logger, errors, player_service, req_repo, imp_repo, free_repo, provider), request_interstitial(self, player_id, trigger, match_id), record_interstitial_impression(self, ad_request_id, viewed, duration_ms), _mid_request_check(self, ar)

### `src/modules/ads/protocols.py` (py)
  imports: I1, I22, I2, I7, I13, I3, I38, I25, I6, I305, I146, I224, I177, I306, I314, I410, I225, I413, I322, I84, I138, I125, I134, I115, I90, I162, I135, I178, I227, I228, I163, I179, I180, I164, I229, I230, I133
  classes: AdServiceProtocol(Protocol), AdImpressionRepositoryProtocol(Protocol), AdRequestRepositoryProtocol(Protocol), AdFreeStatusRepositoryProtocol(Protocol), AdRewardRepositoryProtocol(Protocol), EventAdOpportunityRepositoryProtocol(Protocol), EventAdClaimRepositoryProtocol(Protocol), AdProviderProtocol(Protocol), PlayerServiceProtocol(Protocol), EventServiceProtocol(Protocol)
  functions: check_ad_free_status(self, player_id), can_show_ad(self, player_id, ad_type, context), request_interstitial(self, player_id, trigger, match_id), record_interstitial_impression(self, ad_request_id, viewed, duration_ms), request_rewarded_video(self, player_id, reward_type), complete_rewarded_video(self, ad_request_id, completed, watched_duration_ms), record_banner_impression(self, player_id, banner_placement, view_duration_ms), get_player_ad_stats(self, player_id, period), get_ad_impressions(self, player_id, ad_type, limit, offset), get_match_ad_attribution(self, match_id), get_bot_ad_attributions(self, bot_player_id, start_date, end_date), grant_ad_free_status(self, player_id, reason, duration_days, granted_by), revoke_ad_free_status(self, player_id, reason), get_event_ad_opportunities(self, player_id, event_id), claim_event_ad_reward(self, player_id, event_id, opportunity_id), create(self, data), find_by_id(self, impression_id), find_by_request_id(self, ad_request_id), find_by_player(self, player_id, ad_type, limit, offset), find_by_match(self, match_id), get_player_stats(self, player_id, start_date, end_date), get_bot_attributions(self, bot_player_id, start_date, end_date), get_daily_attributions(self, bot_player_id, start_date, end_date), create(self, data), find_by_id(self, request_id), update(self, request_id, changes), find_pending_by_player(self, player_id), find_last_by_type(self, player_id, ad_type), expire_old_requests(self, before), find_by_player(self, player_id), upsert(self, data), revoke(self, player_id, reason), find_expiring(self, before), create(self, data), find_by_request_id(self, ad_request_id), find_by_event(self, event_id), find_by_id(self, event_id, opportunity_id), create(self, data), create(self, data), count_claims(self, event_id, opportunity_id, player_id), find_last_claim(self, event_id, opportunity_id, player_id), request_interstitial(self, ad_unit_id, user_id), request_rewarded_video(self, ad_unit_id, user_id), verify_impression(self, ad_request_id, impression_data), get_estimated_cpm(self, ad_type), get_player(self, player_id), get_event(self, event_id), get_event_participant(self, event_id, player_id)

### `src/modules/ads/rewarded_video_manager.py` (py)
  imports: I1, I2, I29, I5, I4, I6, I231, I325, I415, from src.modules.ads._helpers import guard_cooldown, from src.modules.ads._helpers import provider_call, from src.modules.ads._helpers import valid_request, I146, I224, I177, I306, I115, I226, I90, I164, I229, I230, I18, I9, I8, I181, I182, I416, I324, from src.modules.ads.protocols import AdRewardRepositoryProtocol, I147
  classes: RewardedVideoManager
  functions: __init__(self, config, logger, errors, player_service, req_repo, imp_repo, free_repo, rew_repo, provider), request_rewarded_video(self, player_id, reward_type), complete_rewarded_video(self, ad_request_id, completed, watched_duration_ms)

### `src/modules/ads/service.py` (py)
  imports: I1, I22, I2, I5, I4, I38, I25, I6, I414, from src.modules.ads._helpers import cooldown_seconds, from src.modules.ads.ad_free_manager import AdFreeManager, from src.modules.ads.analytics_service import AdAnalyticsService, from src.modules.ads.banner_manager import BannerManager, I225, from src.modules.ads.event_ad_service import EventAdService, from src.modules.ads.interstitial_manager import InterstitialManager, from src.modules.ads.rewarded_video_manager import RewardedVideoManager, I413, I322, I84, I138, I125, I115, I90, I162, I135, I178, I227, I228, I163, I179, I180, I164, I229, I230, I133, I18, I9, I8, I181, I182, I416, I324, from src.modules.ads.protocols import AdRewardRepositoryProtocol, from src.modules.ads.protocols import EventAdClaimRepositoryProtocol, from src.modules.ads.protocols import EventAdOpportunityRepositoryProtocol, from src.modules.ads.protocols import EventServiceProtocol, I147
  classes: AdRepositoryBundle, AdService
  functions: __init__(self, ad_request, ad_impression, ad_free_status, ad_reward, event_opportunity, event_claim), __init__(self, config, logger, errors, player_service, events_service, repos, ad_provider), check_ad_free_status(self, player_id), grant_ad_free_status(self, player_id, reason, duration_days, granted_by), revoke_ad_free_status(self, player_id, reason), can_show_ad(self, player_id, ad_type, context), request_interstitial(self, player_id, trigger, match_id), record_interstitial_impression(self, ad_request_id, viewed, duration_ms), request_rewarded_video(self, player_id, reward_type), complete_rewarded_video(self, ad_request_id, completed, watched_duration_ms), record_banner_impression(self, player_id, banner_placement, view_duration_ms), get_player_ad_stats(self, player_id, period), get_ad_impressions(self, player_id, ad_type, limit, offset), get_match_ad_attribution(self, match_id), get_bot_ad_attributions(self, bot_player_id, start_date, end_date), get_event_ad_opportunities(self, player_id, event_id), claim_event_ad_reward(self, player_id, event_id, opportunity_id)

### `src/modules/ads/types.py` (py)
  imports: I1, I10, I24, I22, I2, I43, I7, I274, I3, I38, I25, I6
  classes: AdType(Enum), InterstitialTrigger(Enum), RewardedAdType(Enum), BannerPlacement(Enum), AdFreeReason(Enum), AdRequestStatus(Enum), StatsPeriod(Enum), AdContext, DailyAttribution, AdFreeStatus, AdEligibility, InterstitialAdResult, AdImpression, RewardedVideoRequest, RewardedVideoResult, PlayerAdStats, MatchAdAttribution, BotAdAttributionReport, EventAdOpportunity, EventAdRewardResult, AdProviderResponse

### `src/modules/api/__init__.py` (py)
  imports: from src.modules.api.factory import ApiFactory, from src.modules.api.protocols import ApiFactoryProtocol

### `src/modules/api/dependencies.py` (py)
  imports: I1, I4, I51, I73, I35, I18, I9, I8, I412, I109, I417, I184, I326, I327, I418, I419, I76, I232
  functions: get_config(request), get_logger(request), get_errors(request), get_auth_service(request), get_player_service(request), get_energy_service(request), get_matchmaking_service(request), get_match_service(request), get_vault_service(request), get_event_service(request), get_ad_service(request), get_payment_service(request), get_card_service(request), get_bot_earnings_service(request), get_response_adapter(request), get_bot_hint_generator(request), get_correlation_id(request), get_current_player_id(request), get_auth_type(request)

### `src/modules/api/factory.py` (py)
  imports: I1, I4, I72, from starlette.middleware.cors import CORSMiddleware, I73, I35, I328, I329, I98, I330, from src.modules.api.routes import ads_router, from src.modules.api.routes import auth_router, from src.modules.api.routes import bot_earnings_router, from src.modules.api.routes import campaign_router, from src.modules.api.routes import cards_router, from src.modules.api.routes import economy_router, from src.modules.api.routes import energy_router, from src.modules.api.routes import events_router, from src.modules.api.routes import health_router, from src.modules.api.routes import inventory_router, from src.modules.api.routes import matchmaking_router, from src.modules.api.routes import matches_router, from src.modules.api.routes import payments_router, from src.modules.api.routes import players_router, from src.modules.api.routes import vault_router, from src.modules.api.routes import ws_router, I420, from src.modules.api.websocket.handler import WebSocketHandler, I421, I18, I9, I8, I412, I109, I417, I184, I326, I327, I418, I419, I76, I141, from src.modules.economy.protocols import EconomyServiceProtocol, I232, from collections.abc import AsyncIterator, from contextlib import asynccontextmanager, I375, I205, I376, I82, I82, I329, I328, I330
  classes: ApiFactory
  functions: __init__(self, config, logger, errors, auth_service, player_service, energy_service, matchmaking_service, match_service, vault_service, event_service, ad_service, payment_service, bot_earnings_service, card_service, economy_service), create_app(self), _configure_state(self, app), _register_middleware(self, app), _register_routers(self, app), create_app(), _periodic_cleanup(ctx), lifespan(app)

### `src/modules/api/protocols.py` (py)
  imports: I1, I4, I13, I72
  classes: ApiFactoryProtocol(Protocol)
  functions: create_app(self)

### `src/modules/api/adapters/__init__.py` (py)
  imports: I73, I35

### `src/modules/api/adapters/bot_hints.py` (py)
  imports: I1, I10, from typing import Literal
  classes: ValidMoveHint, RankedMove, BoardAnalysis, StrategicContext, MatchBotHints, BotHintGenerator
  functions: generate_match_hints(self, board, valid_moves, my_score, opponent_score, turns_remaining), _analyze_board(self, board), _count_chain_opportunities(self, board), _rank_moves(self, board, valid_moves), _estimate_cascade(self, board, move), _count_aligned(board, row, col, gem, rows, cols, exclude_row, exclude_col), find_valid_moves(board), _has_match(b, r, c), _determine_strategy(self, my_score, opponent_score, turns_remaining, analysis)

### `src/modules/api/adapters/cascade_serializer.py` (py)
  imports: I1, I7
  functions: serialize_cascade_steps(cascades), serialize_applied_modifiers(move_result)

### `src/modules/api/adapters/response.py` (py)
  imports: I1, I2, I5, I7, from src.modules.api.schemas.common import ApiResponse, from src.modules.api.schemas.common import ErrorDetail, from src.modules.api.schemas.common import ResponseMeta
  classes: ResponseAdapter
  functions: success(self, data, correlation_id), error(self, code, message, correlation_id, details)

### `src/modules/api/middleware/__init__.py` (py)
  imports: I328, I329, I330

### `src/modules/api/middleware/auth.py` (py)
  imports: I1, I2, I5, I4, I88, I93, I94, I331, I95, I11, I109
  classes: AuthMiddleware(BaseHTTPMiddleware)
  functions: __init__(self, app, auth_service), dispatch(self, request, call_next), _authenticate_api_key(self, api_key, request, call_next), _authenticate_jwt(self, token, request, call_next), _auth_error(code, message, request)

### `src/modules/api/middleware/correlation.py` (py)
  imports: I1, I422, I85, I88, I93, I94, I95, I218
  classes: CorrelationMiddleware(BaseHTTPMiddleware)
  functions: dispatch(self, request, call_next), _generate_correlation_id()

### `src/modules/api/middleware/error_handler.py` (py)
  imports: I1, I2, I5, I72, I51, I331, I11
  functions: register_error_handlers(app), handle_app_error(request, exc), handle_unexpected_error(request, exc), _resolve_status_code(error_code)

### `src/modules/api/middleware/rate_limit.py` (py)
  imports: I1, I2, I5, I4, I88, I93, I94, I331, I95, I11, I18, I109
  classes: RateLimitMiddleware(BaseHTTPMiddleware)
  functions: __init__(self, app, auth_service, config), dispatch(self, request, call_next), _get_identifier(request), _rate_limit_response(identifier, retry_after, request)

### `src/modules/api/routes/__init__.py` (py)
  imports: from src.modules.api.routes.ads import router as ads_router, from src.modules.api.routes.auth import router as auth_router, from src.modules.api.routes.bot_earnings import router as bot_earnings_router, from src.modules.api.routes.energy import router as energy_router, from src.modules.api.routes.events import router as events_router, from src.modules.api.routes.health import router as health_router, from src.modules.api.routes.inventory import router as inventory_router, from src.modules.api.routes.matchmaking import router as matchmaking_router, from src.modules.api.routes.matches import router as matches_router, from src.modules.api.routes.payments import router as payments_router, from src.modules.api.routes.players import router as players_router, from src.modules.api.routes.vault import router as vault_router, from src.modules.api.routes.cards import router as cards_router, from src.modules.api.routes.ws import router as ws_router, from src.modules.api.routes.economy import router as economy_router, from src.modules.api.routes.campaign import router as campaign_router

### `src/modules/api/routes/ads.py` (py)
  imports: I1, I22, I4, I7, I59, I64, I148, I51, I185, I65, I66, I67, from src.modules.api.schemas.ads import AdFreeStatusResponse, from src.modules.api.schemas.ads import BotAttributionResponse, from src.modules.api.schemas.ads import DailyBreakdownItem, from src.modules.api.schemas.ads import InterstitialCompleteRequest, from src.modules.api.schemas.ads import InterstitialCompleteResponse, from src.modules.api.schemas.ads import InterstitialRequest, from src.modules.api.schemas.ads import InterstitialResponse, from src.modules.api.schemas.ads import RewardedVideoCompleteRequest, from src.modules.api.schemas.ads import RewardedVideoCompleteResponse, from src.modules.api.schemas.ads import RewardedVideoRequestSchema, from src.modules.api.schemas.ads import RewardedVideoResponse, I35
  functions: _require_jwt(request), _require_api_key(request), get_ad_free_status(request, correlation_id, response), request_interstitial(request, body, correlation_id, response), complete_interstitial(request, body, correlation_id, response), request_rewarded_video(request, body, correlation_id, response), complete_rewarded_video(request, body, correlation_id, response), get_bot_attributions(request, start_date, end_date, correlation_id, response)

### `src/modules/api/routes/auth.py` (py)
  imports: I1, I4, I7, I3, I59, I64, I51, I6, I32, from src.modules.api.dependencies import get_auth_service, I65, I66, I67, from src.modules.api.schemas.auth import ApiKeyCreateRequest, from src.modules.api.schemas.auth import ApiKeyListItem, from src.modules.api.schemas.auth import ApiKeyResponse, from src.modules.api.schemas.auth import AppleLoginRequest, from src.modules.api.schemas.auth import BotRegisterRequest, from src.modules.api.schemas.auth import BotRegisterResponse, from src.modules.api.schemas.auth import LoginRequest, from src.modules.api.schemas.auth import LoginResponse, from src.modules.api.schemas.auth import PlayerResponse, from src.modules.api.schemas.auth import RefreshRequest, from src.modules.api.schemas.auth import RegisterRequest, from src.modules.api.schemas.auth import RegisterResponse, I35, I109, from src.modules.player.bot_names import generate_unique_bot_name
  functions: _player_to_response(player), _auth_result_to_response(auth_result), _onboard_new_player(request, player), register(body, request, correlation_id, response, auth_service), login(body, correlation_id, response, auth_service), apple_login(body, request, correlation_id, response, auth_service), register_bot(body, request, correlation_id, response), refresh_token(body, correlation_id, response, auth_service), logout(request, correlation_id, response, auth_service, player_id), create_api_key(body, correlation_id, response, auth_service, player_id), revoke_api_key(key_id, correlation_id, response, auth_service, player_id), list_api_keys(correlation_id, response, auth_service, player_id)

### `src/modules/api/routes/bot_earnings.py` (py)
  imports: I1, I22, I4, I7, I59, I64, I148, I51, I185, I65, I66, I67, from src.modules.api.schemas.bot_earnings import AttributionEntryResponse, from src.modules.api.schemas.bot_earnings import AttributionListResponse, from src.modules.api.schemas.bot_earnings import EarningsBalanceResponse, from src.modules.api.schemas.bot_earnings import PayoutHistoryResponse, from src.modules.api.schemas.bot_earnings import PayoutRequestResponse, from src.modules.api.schemas.bot_earnings import SyncResultResponse, I35, I167
  functions: _require_api_key(request), get_earnings_balance(request, correlation_id, response), sync_attributions(request, correlation_id, response), request_payout(request, correlation_id, response), get_payout_history(request, status, limit, offset, correlation_id, response), get_attribution_entries(request, start_date, end_date, limit, offset, correlation_id, response)

### `src/modules/api/routes/campaign.py` (py)
  imports: I1, I7, I3, I59, I64, I51, I39, I6, I23, from src.modules.api.adapters.cascade_serializer import serialize_applied_modifiers, from src.modules.api.adapters.cascade_serializer import serialize_cascade_steps, I65, I66, I67, from src.modules.api.schemas.campaign import CampaignMegaRequest, from src.modules.api.schemas.campaign import CampaignMoveRequest, from src.modules.api.schemas.campaign import StartAttemptRequest
  functions: list_levels(request, correlation_id, response, player_id), get_level(level_number, request, correlation_id, response, player_id), get_progress(request, correlation_id, response, player_id), start_attempt(body, request, correlation_id, response, player_id), get_attempt(attempt_id, request, correlation_id, response, player_id), submit_move(attempt_id, body, request, correlation_id, response, player_id), activate_mega(attempt_id, body, request, correlation_id, response, player_id), abandon_attempt(attempt_id, request, correlation_id, response, player_id)

### `src/modules/api/routes/cards.py` (py)
  imports: I1, I4, I7, I3, I59, I64, I148, I51, I6, I65, I66, I67, from src.modules.api.schemas.cards import CardEquipRequest, from src.modules.api.schemas.cards import CardReorderRequest, from src.modules.api.schemas.cards import CardUnequipRequest, I35, from src.modules.cards.dto import CardDefinition, from src.modules.cards.dto import EquippedLoadout, from src.modules.cards.dto import PlayerCard, I141, I126
  functions: _reject_if_active_match(request, player_id), _definition_to_dict(defn), _player_card_to_dict(card), _loadout_to_dict(loadout), list_definitions(request, rarity, card_set, correlation_id, response), get_definition(card_id, request, correlation_id, response), get_my_cards(request, limit, offset, correlation_id, response), get_equipped(request, correlation_id, response), equip_card(body, request, correlation_id, response), unequip_card(body, request, correlation_id, response), reorder_card(body, request, correlation_id, response), merge_cards(request, correlation_id, response), get_player_equipped(player_id, request, correlation_id, response)

### `src/modules/api/routes/economy.py` (py)
  imports: I1, I4, I7, I3, I59, I64, I51, I6, I65, I66, I67, from src.modules.api.schemas.economy import BuyRequest, from src.modules.api.schemas.economy import BuyResponse, from src.modules.api.schemas.economy import GoldResponse, from src.modules.api.schemas.economy import MarketplaceItemResponse, from src.modules.api.schemas.economy import MarketplaceResponse, from src.modules.api.schemas.economy import SellResponse, I35, I126
  functions: get_gold(request, correlation_id, response, player_id), sell_cards(request, correlation_id, response, player_id), get_marketplace(request, correlation_id, response, player_id), buy_item(body, request, correlation_id, response, player_id)

### `src/modules/api/routes/energy.py` (py)
  imports: I1, I4, I7, I3, I59, I64, I51, I6, I65, I66, I67, from src.modules.api.schemas.energy import EnergyResponse, from src.modules.api.schemas.energy import LoginStreakResponse, from src.modules.api.schemas.energy import StreakResponse, I35
  functions: _energy_info_to_response(energy_info), get_energy(request, correlation_id, response, player_id), record_login(request, correlation_id, response, player_id), get_streak(request, correlation_id, response, player_id)

### `src/modules/api/routes/events.py` (py)
  imports: I1, I4, I7, I3, I59, I64, I148, I51, I38, I6, I65, I66, I67, I35, I326, I149, I186, I127, I233, I74
  functions: _event_to_dict(event), _participant_to_dict(participant), _leaderboard_entry_to_dict(entry), list_events(request, correlation_id, response), get_event(event_id, request, correlation_id, response), join_event(event_id, request, correlation_id, response), get_leaderboard(event_id, request, limit, offset, correlation_id, response), get_player_event_status(event_id, request, correlation_id, response)

### `src/modules/api/routes/health.py` (py)
  imports: I1, I2, I5, I7, I59, I51, I331
  functions: health_check(request), readiness_check(request), liveness_check()

### `src/modules/api/routes/inventory.py` (py)
  imports: I1, I4, I7, I3, I59, I64, I51, I6, I65, I66, I67, I35
  functions: get_mega_inventory(request, correlation_id, response)

### `src/modules/api/routes/matches.py` (py)
  imports: I1, I4, I7, I3, I59, I64, I148, I51, I25, I39, I6, I23, I185, I65, I66, I67, from src.modules.api.adapters.cascade_serializer import serialize_applied_modifiers, from src.modules.api.adapters.cascade_serializer import serialize_cascade_steps, from src.modules.api.schemas.match import MatchHistoryQuery, from src.modules.api.schemas.match import MegaActivationRequest, from src.modules.api.schemas.match import MoveRequest, I73, from src.modules.api.adapters.bot_hints import ValidMoveHint, I35, I327, I126, I234, I235, I187, I236
  functions: _match_state_to_dict(state, player_id), _match_summary_to_dict(summary), _move_record_to_dict(record), get_active_matches(request, correlation_id, response), get_match_history(request, limit, offset, correlation_id, response), get_match(match_id, request, correlation_id, response), get_match_state(match_id, request, correlation_id, response), get_board(match_id, request, correlation_id, response), submit_move(match_id, body, request, correlation_id, response), activate_mega_gem(match_id, body, request, correlation_id, response), forfeit_match(match_id, request, correlation_id, response), debug_board(match_id, request, correlation_id, response), get_move_history(match_id, request, correlation_id, response)

### `src/modules/api/routes/matchmaking.py` (py)
  imports: I1, I4, I7, I3, I59, I64, I51, I6, I185, I65, I66, I67, from src.modules.api.schemas.matchmaking import JoinQueueRequest, from src.modules.api.schemas.matchmaking import PoolStatsResponse, from src.modules.api.schemas.matchmaking import QueueEntryResponse, from src.modules.api.schemas.matchmaking import QueueStatusResponse, from src.modules.api.schemas.matchmaking import QuickMatchRequest, I32, I97, I35, I109, I85, I103
  functions: join_queue(body, request, correlation_id, response, player_id), leave_queue(request, correlation_id, response, player_id), get_queue_status(request, correlation_id, response, player_id), get_pool_stats(request, correlation_id, response, auth_type), quick_match(request, body, correlation_id, response, player_id), _pick_random_bot(player_service)

### `src/modules/api/routes/payments.py` (py)
  imports: I1, I4, I7, I59, I64, I51, I185, I65, I66, I67, from src.modules.api.schemas.payments import InitiatePurchaseRequest, from src.modules.api.schemas.payments import PurchaseIntentResponse, from src.modules.api.schemas.payments import PurchaseResultResponse, from src.modules.api.schemas.payments import PurchaseStatusResponse, from src.modules.api.schemas.payments import RestorePurchasesRequest, from src.modules.api.schemas.payments import RestoreResultResponse, from src.modules.api.schemas.payments import ValidatePurchaseRequest, I35, I91, I118, I91, I118
  functions: _require_jwt(request), initiate_purchase(request, body, correlation_id, response), validate_purchase(request, body, correlation_id, response), restore_purchases(request, body, correlation_id, response), get_purchase_status(request, correlation_id, response)

### `src/modules/api/routes/players.py` (py)
  imports: I1, I4, I7, I3, I59, I64, I148, I51, I6, I65, I66, I67, from src.modules.api.schemas.player import LeaderboardEntry, from src.modules.api.schemas.player import LeaderboardResponse, from src.modules.api.schemas.player import PlayerProfileResponse, from src.modules.api.schemas.player import PlayerStatsResponse, from src.modules.api.schemas.player import PlayerUpdateRequest, from src.modules.api.schemas.player import UsernameCheckResponse, I332, I423, I35
  functions: _player_to_profile(player, include_email), get_leaderboard(request, correlation_id, response, limit, offset, sort_by), get_current_player(request, correlation_id, response, player_id), check_username(request, correlation_id, response, player_id, username), get_player_by_id(target_player_id, request, correlation_id, response), update_current_player(body, request, correlation_id, response, player_id), delete_current_player(request, correlation_id, response, player_id), get_player_stats(target_player_id, request, correlation_id, response)

### `src/modules/api/routes/vault.py` (py)
  imports: I1, I4, I7, I3, I59, I64, I148, I51, I106, I6, I185, I65, I66, I67, from src.modules.api.schemas.vault import RaidRequest, from src.modules.api.schemas.vault import ShieldRequest, I35, I188, I237, I238, I189, I239, I232, I119, I32
  functions: _artifact_to_dict(artifact), _shield_to_dict(shield), _collection_to_dict(progress), get_artifacts(request, rarity, artifact_set, limit, offset, correlation_id, response), get_artifact(artifact_id, request, correlation_id, response), activate_shield(request, body, correlation_id, response), get_shield_status(request, correlation_id, response), attempt_raid(body, request, correlation_id, response), get_collection_progress(request, artifact_set, correlation_id, response), get_raid_targets(request, correlation_id, response)

### `src/modules/api/routes/ws.py` (py)
  imports: I1, I59, I424
  functions: websocket_endpoint(websocket)

### `src/modules/api/schemas/__init__.py` (py)
  imports: from src.modules.api.schemas.common import ApiResponse, from src.modules.api.schemas.common import BotHint, from src.modules.api.schemas.common import ErrorDetail, from src.modules.api.schemas.common import ResponseMeta

### `src/modules/api/schemas/ads.py` (py)
  imports: I1, I68, I69, I99
  classes: InterstitialRequest(BaseModel), InterstitialCompleteRequest(BaseModel), RewardedVideoRequestSchema(BaseModel), RewardedVideoCompleteRequest(BaseModel), BotAttributionQueryParams(BaseModel), AdFreeStatusResponse(BaseModel), InterstitialResponse(BaseModel), InterstitialCompleteResponse(BaseModel), RewardedVideoResponse(BaseModel), RewardedVideoCompleteResponse(BaseModel), DailyBreakdownItem(BaseModel), BotAttributionResponse(BaseModel)

### `src/modules/api/schemas/auth.py` (py)
  imports: I1, I68, I69, I99
  classes: RegisterRequest(BaseModel), LoginRequest(BaseModel), RefreshRequest(BaseModel), BotRegisterRequest(BaseModel), AppleLoginRequest(BaseModel), ApiKeyCreateRequest(BaseModel), LoginResponse(BaseModel), PlayerResponse(BaseModel), RegisterResponse(BaseModel), BotRegisterResponse(BaseModel), ApiKeyResponse(BaseModel), ApiKeyListItem(BaseModel)

### `src/modules/api/schemas/bot_earnings.py` (py)
  imports: I1, I68, I69, I99
  classes: PayoutRequestSchema(BaseModel), AttributionQueryParams(BaseModel), PayoutHistoryQueryParams(BaseModel), EarningsBalanceResponse(BaseModel), SyncResultResponse(BaseModel), PayoutRequestResponse(BaseModel), PayoutHistoryResponse(BaseModel), AttributionEntryResponse(BaseModel), AttributionListResponse(BaseModel)

### `src/modules/api/schemas/campaign.py` (py)
  imports: I1, I68, I69
  classes: StartAttemptRequest(BaseModel), CampaignMoveRequest(BaseModel), CampaignMegaRequest(BaseModel)

### `src/modules/api/schemas/cards.py` (py)
  imports: I1, I68, I69, I99
  classes: CardEquipRequest(BaseModel), CardUnequipRequest(BaseModel), CardReorderRequest(BaseModel)

### `src/modules/api/schemas/common.py` (py)
  imports: I1, I2, I7, I275, I276, I68, I69
  classes: ResponseMeta(BaseModel), ErrorDetail(BaseModel), BotHint(BaseModel), ApiResponse(BaseModel)

### `src/modules/api/schemas/economy.py` (py)
  imports: I1, I68, I69
  classes: GoldResponse(BaseModel), SellResponse(BaseModel), BuyRequest(BaseModel), BuyResponse(BaseModel), MarketplaceItemResponse(BaseModel), MarketplaceResponse(BaseModel)

### `src/modules/api/schemas/energy.py` (py)
  imports: I1, I68, I69
  classes: EnergyResponse(BaseModel), StreakResponse(BaseModel), LoginStreakResponse(BaseModel)

### `src/modules/api/schemas/events.py` (py)
  imports: I1, I68, I69, I99
  classes: EventListQuery(BaseModel), LeaderboardQuery(BaseModel), EventResponse(BaseModel), EventParticipantResponse(BaseModel), LeaderboardEntryResponse(BaseModel), EventLeaderboardResponse(BaseModel), PlayerEventStatusResponse(BaseModel)

### `src/modules/api/schemas/match.py` (py)
  imports: I1, I7, I68, I69, I99, from pydantic import model_validator
  classes: MoveRequest(BaseModel), MegaActivationRequest(BaseModel), MatchHistoryQuery(BaseModel), PlayerMatchStateResponse(BaseModel), MatchSummaryResponse(BaseModel), MatchStateResponse(BaseModel), BoardStateResponse(BaseModel), CascadeRemovalResponse(BaseModel), CascadeDropResponse(BaseModel), CascadeSpawnResponse(BaseModel), SpecialActivationResponse(BaseModel), SpecialAttractionResponse(BaseModel), CascadeStepResponse(BaseModel), MoveResultResponse(BaseModel), MoveHistoryEntry(BaseModel)
  functions: positions_must_be_adjacent(self)

### `src/modules/api/schemas/matchmaking.py` (py)
  imports: I1, I68, I69, I99
  classes: JoinQueueRequest(BaseModel), QuickMatchRequest(BaseModel), QueueEntryResponse(BaseModel), QueueStatusResponse(BaseModel), PoolStatsResponse(BaseModel)

### `src/modules/api/schemas/payments.py` (py)
  imports: I1, I68, I69, I99
  classes: InitiatePurchaseRequest(BaseModel), ValidatePurchaseRequest(BaseModel), RestorePurchasesRequest(BaseModel), PurchaseIntentResponse(BaseModel), PurchaseResultResponse(BaseModel), RestoreResultResponse(BaseModel), PurchaseStatusResponse(BaseModel)

### `src/modules/api/schemas/player.py` (py)
  imports: I1, I68, I69, I99
  classes: PlayerUpdateRequest(BaseModel), PlayerProfileResponse(BaseModel), PlayerStatsResponse(BaseModel), UsernameCheckResponse(BaseModel), LeaderboardEntry(BaseModel), LeaderboardResponse(BaseModel)

### `src/modules/api/schemas/vault.py` (py)
  imports: I1, I68, I69, I99
  classes: ShieldRequest(BaseModel), RaidRequest(BaseModel), ArtifactListQuery(BaseModel), ArtifactResponse(BaseModel), ShieldResponse(BaseModel), RaidResponse(BaseModel), CollectionProgressResponse(BaseModel), RaidTargetResponse(BaseModel)

### `src/modules/api/websocket/__init__.py` (py)
  imports: I420, from src.modules.api.websocket.handler import WebSocketHandler, I421

### `src/modules/api/websocket/channels.py` (py)
  imports: I1, I82, I7, I3, I405, I407
  classes: _Subscription, ChannelManager
  functions: __init__(self, channel, params), __init__(self), subscribe(self, player_id, channel, params), unsubscribe(self, player_id, channel, params), unsubscribe_all(self, player_id), is_subscribed(self, player_id, channel, params), get_subscribed_players(self, channel, params), get_channel_events(channel)

### `src/modules/api/websocket/handler.py` (py)
  imports: I1, I82, I57, I4, I7, I3, I424, from starlette.websockets import WebSocketDisconnect, from starlette.websockets import WebSocketState, I11, I405, I406, I407, I420, I421, I18, I8, I109
  classes: WebSocketHandler
  functions: __init__(self, connection_manager, channel_manager, auth_service, config, logger), handle(self, websocket), _authenticate(self, websocket), _message_loop(self, websocket, player_id), _handle_message(self, websocket, player_id, msg_type, payload), _handle_subscribe(self, websocket, player_id, payload), _handle_unsubscribe(self, websocket, player_id, payload), _cleanup(self, websocket, player_id), _send_message(websocket, message), _send_error(websocket, code, message), _send_auth_failed(websocket, code, message)

### `src/modules/api/websocket/manager.py` (py)
  imports: I1, I82, I4, I7, I3, I424, I406
  classes: ConnectionManager
  functions: __init__(self), connect(self, websocket, player_id), disconnect(self, websocket), subscribe_to_match(self, player_id, match_id), unsubscribe_from_match(self, player_id, match_id), broadcast_to_player(self, player_id, message), broadcast_to_match(self, match_id, message), get_player_connection_count(self, player_id), _find_player_for_connection(self, websocket), _safe_send(websocket, payload)

### `src/modules/auth/__init__.py` (py)
  imports: I425, I333, I240, I426, from src.modules.auth.dto import TokenPayload, I109, from src.modules.auth.protocols import PasswordStoreProtocol, I266

### `src/modules/auth/api_key_generator.py` (py)
  imports: I1, import base64, I422, import bcrypt
  functions: generate_api_key(prefix, key_length), hash_api_key(key), verify_api_key(key, key_hash)

### `src/modules/auth/dto.py` (py)
  imports: I1, I10, I24, I2, I3, I219
  classes: AuthResult, ApiKeyCreationResult, SessionInfo, RateLimitStatus, TokenPayload
  functions: authorization_header(self), __post_init__(self)

### `src/modules/auth/jwt_handler.py` (py)
  imports: I1, I2, I29, I5, I3, I27, I427, I11, from src.modules.auth.dto import TokenPayload
  classes: JwtHandler
  functions: __init__(self, secret, algorithm), create_access_token(self, player_id, session_id, expiry_minutes), create_refresh_token(self, player_id, session_id, expiry_days), decode_token(self, token)

### `src/modules/auth/password_handler.py` (py)
  imports: I1, import bcrypt
  functions: hash_password(password, rounds), verify_password(password, password_hash), validate_password_strength(password, min_length)

### `src/modules/auth/protocols.py` (py)
  imports: I1, I4, I13, I3, I219, I273, I6, I425, I333, I240, I426
  classes: AuthServiceProtocol(Protocol), PasswordStoreProtocol(Protocol)
  functions: authenticate(self, username, password), authenticate_apple(self, identity_token, authorization_code, display_name), validate_token(self, token), refresh_token(self, refresh_token), logout(self, player_id, session_id), get_active_sessions(self, player_id), create_api_key(self, player_id, description), revoke_api_key(self, key_id, player_id), list_api_keys(self, player_id, include_revoked), check_rate_limit(self, key_id), record_api_request(self, key_id), create_bot_match_token(self, bot_player_id, match_id), cleanup_expired_sessions(self), hash_password(self, password), verify_password(self, password, password_hash), get_password_hash(self, player_id), set_password_hash(self, player_id, password_hash)

### `src/modules/auth/rate_limiter.py` (py)
  imports: I1, I2, I29, I5, I7, I3, I240
  classes: RateLimiter
  functions: __init__(self, redis, max_requests, window_seconds), get_status(self, key_id), record_request(self, key_id)

### `src/modules/auth/service.py` (py)
  imports: I1, I2, I29, I5, I4, I7, I3, I219, I273, I404, I6, from src.modules.auth.api_key_generator import generate_api_key, from src.modules.auth.api_key_generator import verify_api_key, I425, I333, I240, I426, from src.modules.auth.jwt_handler import JwtHandler, from src.modules.auth.password_handler import hash_password as _hash_password, from src.modules.auth.password_handler import validate_password_strength, from src.modules.auth.password_handler import verify_password as _verify_password, from src.modules.auth.rate_limiter import RateLimiter, I18, I9, I8, from src.data.protocols.api_key_repository import ApiKeyRepositoryProtocol, from src.data.protocols.session_repository import SessionRepositoryProtocol, from src.modules.auth.protocols import PasswordStoreProtocol, I76, import jwt as pyjwt, I32, I334, I335, I27, I27, I335
  classes: AuthService
  functions: __init__(self, config, logger, errors, player_service, session_repo, api_key_repo, password_store, redis), authenticate(self, username, password), authenticate_apple(self, identity_token, authorization_code, display_name), _generate_apple_username(display_name, apple_user_id), validate_token(self, token), refresh_token(self, refresh_token), logout(self, player_id, session_id), get_active_sessions(self, player_id), create_api_key(self, player_id, description), revoke_api_key(self, key_id, player_id), list_api_keys(self, player_id, include_revoked), check_rate_limit(self, key_id), record_api_request(self, key_id), create_bot_match_token(self, bot_player_id, match_id), hash_password(self, password), verify_password(self, password, password_hash), _create_session(self, player_id, device_info), _validate_jwt(self, token), _validate_api_key(self, key), cleanup_expired_sessions(self)

### `src/modules/board/__init__.py` (py)
  imports: I121, I171, from src.modules.board.types import GemDrop, from src.modules.board.types import GemSpawn, I92

### `src/modules/board/cascade.py` (py)
  imports: I1, from collections import deque, I16, I63, I428, I429, I170, I30, I39, I23, I395, I430, I394, from src.modules.board._constants import MAX_CASCADE_STEPS, I150, from src.modules.board.types import CascadeContext, I171, from src.modules.board.types import SpecialActivation, from src.modules.board.types import SpecialAttraction, I54
  classes: _CascadeMixin
  functions: _obstacle_satisfied(obstacle_func, blast_func), _create_activation(self, board, position, raw_func, trigger_color, overrides), _drain_clear_queue(self, board, initial_positions, inert_megas, trigger_color, modifiers, initial_blast_func), _execute_swap_activation(self, board, move, from_func, to_func, seed, inert_megas, modifiers), _execute_fusion_activation(self, board, move, from_func, to_func, seed, inert_megas, modifiers), _try_attraction_only_step_inplace(self, board, chain, inert_megas), _run_cascade_step_inplace(self, board, matches, chain, cascade_seed, modifiers, inert_megas), _phase_record_special(ctx), _phase_place_new_special(self, ctx), _phase_fill(self, ctx), _phase_post_fill_injection(self, ctx), _rebuild_inert_megas(board, inert_megas)

### `src/modules/board/detection.py` (py)
  imports: I1, I54, I16, I140, I63, I428, I429, I170, I30, I23, from src.modules.board._constants import SENTINEL
  classes: _DetectionMixin
  functions: detect_matches(self, board, min_length), _determine_special_gem(self, matches), _expand_contiguous(board, matches)

### `src/modules/board/effect_interpreter.py` (py)
  imports: I1, from collections import Counter, I16, I140, I30, I23
  classes: EffectInterpreter
  functions: __init__(self, schema), _validate_spawn_refs(self), determine_special_gem(self, matches), _try_creation_rule(self, rule, all_matches, h_matches, v_matches), _try_tl_shape(h_matches, v_matches, func_id), _try_straight_match(rule, all_matches, func_id, placement), calculate_effect_positions(self, board, position, func_value, trigger_color, overrides), calculate_mega_effect_positions(self, board, position, mega_value, trigger_color), _execute_select(self, board, effect, position, trigger_color), _select_rows(affected, position, h, w, effect), _select_columns(affected, position, h, w, effect), _select_radius(affected, position, h, w, effect), _select_color_match(self, affected, board, trigger_color, effect), _select_cross(affected, position, h, w), _select_entire_board(affected, board), _resolve_color_target(board, trigger_color, fallback), get_attraction_config(self), get_chain_config(self), get_board_config(self), get_obstacle_config(self)

### `src/modules/board/mega_gems.py` (py)
  imports: I1, I54, I16, I170, I30, I23, I430, I394, from src.modules.board.types import SpecialAttraction
  classes: _MegaGemsMixin
  functions: _check_special_attractions(board), _process_attractions(board, triples), _process_attractions_inplace(board, triples), _calculate_mega_gem_effect_positions(self, board, position, mega_value, trigger_color)

### `src/modules/board/schema_loader.py` (py)
  imports: I1, I57, I114
  functions: load_board_rules(path), validate_board_rules(schema), _validate_board(board, errors), _validate_match_detection(detection, errors), _validate_special_gems(special_gems, errors), _validate_mega_gems(mega_gems, valid_function_ids, errors), _validate_effect(effect, prefix, errors, valid_function_ids)

### `src/modules/board/service.py` (py)
  imports: I1, I7, I54, I18, I9, I8, I16, I63, I429, I30, I39, I23, from src.modules.board._constants import LCG_INCREMENT, from src.modules.board._constants import LCG_MASK, from src.modules.board._constants import LCG_MULTIPLIER, from src.modules.board._constants import MAX_CASCADE_STEPS, I150, from src.modules.board.cascade import _CascadeMixin, from src.modules.board.detection import _DetectionMixin, from src.modules.board.effect_interpreter import EffectInterpreter, from src.modules.board.mega_gems import _MegaGemsMixin, from src.modules.board.schema_loader import load_board_rules, from src.modules.board.special_gems import _SpecialGemsMixin, I171, from src.modules.board.types import GemDrop, from src.modules.board.types import GemSpawn, I92, from src.modules.board.types import SpecialActivation, I428, I395, import copy
  classes: BoardService(_CascadeMixin, _DetectionMixin, _SpecialGemsMixin, _MegaGemsMixin)
  functions: __init__(self, config, logger, errors), create_board(self, width, height, seed), create_board_with_obstacles(self, width, height, seed, obstacles, gem_colors), swap_gems(self, board, move), clear_matches(self, board, matches), apply_gravity(self, board), fill_empty(self, board, seed), apply_gravity_inplace(self, board), fill_empty_inplace(self, board, seed, spawn_weights), _place_special_gem_inplace(board, matches), _advance_seed(seed), _place_special_gem(board, matches), process_move(self, board, move, seed, modifiers), process_mega_activation(self, board, mega_value, seed, modifiers), shuffle_board(self, board, seed), validate_board(self, board), has_valid_moves(self, board), _validate_position(self, pos, board), _swap_positions(self, board, a, b)

### `src/modules/board/special_gems.py` (py)
  imports: I1, I54, I16, I30, I23
  classes: _SpecialGemsMixin
  functions: _calculate_special_effect_positions(self, board, position, gem_type, trigger_color, overrides), _clear_positions_inplace(board, positions), _clear_matches_inplace(board, matches)

### `src/modules/board/types.py` (py)
  imports: I1, I10, I24, I16, I63, I170, I30, I39, I23
  classes: GemDrop, GemSpawn, SpecialActivation, SpecialAttraction, CascadeContext, CascadeStep, MoveProcessingResult
  functions: total_cleared(self), build_step(self)

### `src/modules/board_gen/__init__.py` (py)
  imports: I336, I216, I207, I241, I431, I208, I432

### `src/modules/board_gen/cascade_analyzer.py` (py)
  imports: I1, I4, I323, I16
  functions: calculate_cascade_potential(board, count_valid_moves), count_favorable_patterns(board), calculate_vertical_alignment(board), calculate_color_clustering(board)

### `src/modules/board_gen/protocols.py` (py)
  imports: I1, I13, I16, I63, I207, I241, I208
  classes: BoardServiceProtocol(Protocol), BoardGenServiceProtocol(Protocol)
  functions: create_board(self, width, height, seed), detect_matches(self, board), validate_board(self, board), has_valid_moves(self, board), generate_board(self, seed, options), generate_board_for_match(self, seed, match_type), validate_seed(self, seed), regenerate_from_deadlock(self, board, seed), calculate_cascade_potential(self, board)

### `src/modules/board_gen/service.py` (py)
  imports: I1, I85, I4, I54, I16, I30, I23, from src.modules.board_gen.cascade_analyzer import calculate_cascade_potential as _analyze_cascade_potential, from src.modules.board_gen.tuning_engine import apply_cascade_tuning, from src.modules.board_gen.tuning_engine import apply_near_miss_tuning, I150, I207, I241, I431, I208, I432, from numpy.random import Generator, I18, I9, I8, from src.modules.board_gen.protocols import BoardServiceProtocol, I433
  classes: BoardGenService
  functions: __init__(self, config, logger, errors, board_service, special_gems_service), generate_board(self, seed, options), generate_board_for_match(self, seed, match_type), validate_seed(self, seed), regenerate_from_deadlock(self, board, seed), calculate_cascade_potential(self, board), _resolve_options(self, options), _validate_options(self, width, height, cascade_potential, near_miss_factor, specials, gem_weights), _generate_base_board(self, width, height, rng, gem_weights), _apply_cascade_tuning(self, board, target, rng), _apply_near_miss_tuning(self, board, factor, rng), _place_starting_specials(self, board, specials, rng), _find_random_special_position(self, height, width, gem_type, occupied, rng), _get_match_type_preset(self, match_type), _count_valid_moves(self, board), _evolve_seed(seed)

### `src/modules/board_gen/tuning_engine.py` (py)
  imports: I1, I4, I323, I54, I16, from numpy.random import Generator
  functions: apply_cascade_tuning(board, target, rng, gem_types, special_gem_values, calculate_cascade_potential), apply_near_miss_tuning(board, factor, rng, special_gem_values), _would_create_match(grid, row, col, height, width)

### `src/modules/board_gen/types.py` (py)
  imports: I1, I10, I24, I16, I30, I23, from src.core.types.match import MatchType as MatchType
  classes: StartingSpecial, BoardGenOptions, GenerationMetadata, GeneratedBoard

### `src/modules/bot_earnings/__init__.py` (py)
  imports: I307, I308, I309, I310, I337, I311, I312, I417, I209, from src.modules.bot_earnings.types import AdImpressionId, I338, from src.modules.bot_earnings.types import AttributionEntryId, I339, I340, I341, I342, I210, I343, I344, I211, I167

### `src/modules/bot_earnings/dto.py` (py)
  imports: I1, I10, I22, I2, I3, I183
  classes: EarningsLedgerCreate, EarningsLedgerUpdate, AttributionEntryCreate, PayoutRequestCreate, PayoutRequestUpdate, DailyEarningsUpsert

### `src/modules/bot_earnings/protocols.py` (py)
  imports: I1, I22, I2, I7, I13, I3, I6, I307, I308, I309, I310, I337, I311, I312, I338, I339, I340, I341, I342, I210, I343, I344, I211, I167
  classes: BotEarningsServiceProtocol(Protocol), EarningsLedgerRepositoryProtocol(Protocol), AttributionEntryRepositoryProtocol(Protocol), PayoutRequestRepositoryProtocol(Protocol), DailyEarningsRepositoryProtocol(Protocol), PlayerServiceProtocol(Protocol), AdServiceProtocol(Protocol)
  functions: get_earnings_balance(self, bot_player_id), get_earnings_summary(self, bot_player_id, period), get_attribution_entries(self, bot_player_id, start_date, end_date, limit, offset), get_daily_earnings(self, bot_player_id, start_date, end_date), sync_attributions(self, bot_player_id), sync_all_attributions(self), request_payout(self, bot_player_id, requesting_owner_id), get_payout_requests(self, bot_player_id, status, limit, offset), get_payout_request(self, payout_request_id), cancel_payout_request(self, payout_request_id, requesting_owner_id), process_payout(self, payout_request_id, processor_id, external_reference), reject_payout(self, payout_request_id, processor_id, reason), get_pending_payouts(self, past_hold_only), get_bot_owner(self, bot_player_id), find_by_bot_id(self, bot_player_id), create(self, data), update(self, bot_player_id, changes), increment_earned(self, bot_player_id, cents), increment_pending(self, bot_player_id, cents), complete_payout(self, bot_player_id, cents), cancel_pending(self, bot_player_id, cents), find_bots_needing_sync(self, since, limit), create(self, data), create_batch(self, entries), find_by_impression_id(self, ad_impression_id), find_by_bot(self, bot_player_id, start_date, end_date, limit, offset), get_daily_summary(self, bot_player_id, start_date, end_date), get_period_summary(self, bot_player_id, start_date, end_date), get_last_recorded_for_bot(self, bot_player_id), create(self, data), find_by_id(self, payout_request_id), update(self, payout_request_id, changes), find_by_bot(self, bot_player_id, status, limit, offset), find_pending_by_bot(self, bot_player_id), find_pending_past_hold(self, as_of), upsert(self, data), find_range(self, bot_player_id, start_date, end_date), get_player(self, player_id), get_bot_ad_attributions(self, bot_player_id, start_date, end_date)

### `src/modules/bot_earnings/service.py` (py)
  imports: I1, I22, I2, I29, I5, I4, I7, I25, I6, I307, I308, I309, I310, I337, I311, I312, from src.modules.bot_earnings.types import AdImpressionId, I338, from src.modules.bot_earnings.types import AttributionEntryId, I339, I340, I341, I342, I210, I343, I344, I211, I167, I18, I15, I9, I8, from src.modules.bot_earnings.protocols import AdServiceProtocol, from src.modules.bot_earnings.protocols import AttributionEntryRepositoryProtocol, from src.modules.bot_earnings.protocols import DailyEarningsRepositoryProtocol, from src.modules.bot_earnings.protocols import EarningsLedgerRepositoryProtocol, from src.modules.bot_earnings.protocols import PayoutRequestRepositoryProtocol, from src.modules.bot_earnings.protocols import PlayerServiceProtocol, import uuid as _uuid
  classes: BotEarningsService
  functions: __init__(self, config, logger, errors, player_service, ads_service, earnings_ledger_repository, attribution_entry_repository, payout_request_repository, daily_earnings_repository, data_ctx), get_earnings_balance(self, bot_player_id), get_earnings_summary(self, bot_player_id, period), get_attribution_entries(self, bot_player_id, start_date, end_date, limit, offset), get_daily_earnings(self, bot_player_id, start_date, end_date), sync_attributions(self, bot_player_id), sync_all_attributions(self), request_payout(self, bot_player_id, requesting_owner_id), get_payout_requests(self, bot_player_id, status, limit, offset), get_payout_request(self, payout_request_id), cancel_payout_request(self, payout_request_id, requesting_owner_id), process_payout(self, payout_request_id, processor_id, external_reference), reject_payout(self, payout_request_id, processor_id, reason), get_pending_payouts(self, past_hold_only), get_bot_owner(self, bot_player_id), _validate_admin(self, processor_id, operation), _validate_bot(self, bot_player_id), _validate_pagination(self, limit, offset), _validate_date_range(self, start_date, end_date), _compute_period_range(self, period, reference), _extract_owner_id(player), _generate_impression_id(bot_player_id, daily_date), _build_payout_request(record), _build_attribution_entry(record)

### `src/modules/bot_earnings/types.py` (py)
  imports: I1, I10, I24, I22, I2, I43, I274, I3, I25, I6
  classes: EarningsPeriod(Enum), PayoutStatus(Enum), EarningsBalance, EarningsSummary, AttributionEntry, DailyEarnings, AttributionSyncResult, BulkSyncResult, PayoutRequest

### `src/modules/campaign/__init__.py` (py)
  imports: from src.modules.campaign.level_loader import LevelLoader, I403

### `src/modules/campaign/level_loader.py` (py)
  imports: I1, I57, I114
  classes: LevelLoader
  functions: __init__(self, path), get(self, level_number), max_level(self), count(self)

### `src/modules/campaign/service.py` (py)
  imports: I1, I82, I4, I3, I54, from src.core.move_pipeline import derive_move_seed, from src.core.move_pipeline import process_mega_pipeline, from src.core.move_pipeline import process_move_pipeline, I150, from src.modules.board.types import BoardState, from src.modules.board.types import Move, from src.modules.board.types import Position, from src.modules.campaign.level_loader import LevelLoader, I18, I9, I8, I313, from src.data.protocols.campaign_attempt_repository import CampaignAttemptRepositoryProtocol, I265, I121, I336, I141, I402, I184, I173, I92, from src.modules.economy.service import _MARKETPLACE_BY_ID
  classes: CampaignService
  functions: __init__(self, config, logger, errors, board_service, energy_service, player_repo, campaign_repo), get_level_definition(self, level_number), max_level(self), start_attempt(self, player_id, level_number), submit_move(self, attempt_id, player_id, move), activate_mega(self, attempt_id, player_id, slot_index, source), abandon_attempt(self, attempt_id, player_id), get_player_progress(self, player_id), _on_level_won(self, player_id, level_number), _on_level_lost(self, player_id, level_number), _grant_level_reward(self, player_id, level_number), _derive_board_seed(player_id, level_number)

### `src/modules/cards/dto.py` (py)
  imports: I1, I10, I24, I2, I275, I276, I3
  classes: CardDefinition, PlayerCard, EquippedLoadout, MergeResult

### `src/modules/cards/modifier_engine.py` (py)
  imports: I1, from dataclasses import replace, from src.modules.cards.modifier_types import AppliedModifier, I434, from src.modules.cards.modifier_types import InjectionAction, from src.modules.cards.modifier_types import ScoreModifiers
  classes: CardModifierEngine
  functions: __init__(self, card_defs), is_empty(self), apply_special_override(self, original_func), get_effect_param_overrides(self, func_value), get_cascade_injection(self, step_number, seed), get_spawn_weights(self, gem_types), get_special_type_bias(self), get_three_match_special_chance(self, seed), get_score_modifiers(self), check_win_condition(self, cascades), check_energy_grant(self, chain_count), check_raid_protection(self, seed)

### `src/modules/cards/modifier_types.py` (py)
  imports: I1, I10, I24
  classes: CardModifierDef, AppliedModifier, InjectionAction, ScoreModifiers

### `src/modules/cards/service.py` (py)
  imports: I1, I57, I103, I10, I24, I114, I4, from src.modules.cards.dto import CardDefinition, from src.modules.cards.dto import EquippedLoadout, from src.modules.cards.dto import MergeResult, from src.modules.cards.dto import PlayerCard, I190, I3, I18, I9, I8, from src.data.protocols.player_card_repository import PlayerCardRepositoryProtocol, I76, from src.modules.cards.modifier_engine import CardModifierEngine, I434
  classes: _DefinitionRecord, CardService
  functions: __init__(self, config, logger, errors, player_service, player_card_repo, definitions_path), _load_definitions(self, path), get_card_definition(self, card_id), get_card_ids_by_rarity(self, rarity), list_card_definitions(self, rarity, card_set), get_player_cards(self, player_id, limit, offset), get_equipped_cards(self, player_id), build_modifier_engine(self, player_id), grant_card(self, player_id, card_id, source, source_id), equip_card(self, player_id, card_instance_id, slot), unequip_card(self, player_id, card_instance_id), reorder_card(self, player_id, card_instance_id, new_position), remove_card(self, player_id, card_instance_id, reason), merge_equipped(self, player_id), steal_random_equipped(self, from_player_id), transfer_card(self, card_instance_id, from_player_id, to_player_id), unequip_to_vault(self, card_instance_id, player_id), ensure_bot_loadout(self, player_id), grant_starter_pack(self, player_id), grant_bot_full_loadout(self, player_id), _get_definition(self, card_id), _definition_from_record(record), _player_card_from_record(record, definition)

### `src/modules/economy/__init__.py` (py)
  imports: I435, I436, I437, I438, from src.modules.economy.protocols import EconomyServiceProtocol, I402

### `src/modules/economy/dto.py` (py)
  imports: I1, I10, I24
  classes: GoldInfo, SellResult, MarketplaceItem, BuyResult

### `src/modules/economy/protocols.py` (py)
  imports: I1, I4, I13, I6, I435, I436, I437, I438
  classes: EconomyServiceProtocol(Protocol)
  functions: get_gold(self, player_id), sell_equipped_cards(self, player_id), buy_item(self, player_id, item_id), get_marketplace(self)

### `src/modules/economy/service.py` (py)
  imports: I1, I103, I4, I3, I6, I435, I436, I437, I438, I18, I9, I8, I409, from src.data.protocols.gold_transaction_repository import GoldTransactionRepositoryProtocol, I141, I184, from src.modules.inventory.service import InventoryService, I136
  classes: EconomyService
  functions: __init__(self, config, logger, errors, gold_repo, card_service, inventory_service, energy_service, gold_tx_repo), get_gold(self, player_id), sell_equipped_cards(self, player_id), buy_item(self, player_id, item_id), get_marketplace(self), credit_gold(self, player_id, amount, source), grant_card_pack(self, player_id, rarity, count, source), grant_mega_reward(self, player_id, slot_index, count), _ensure_balance(self, player_id)

### `src/modules/energy/__init__.py` (py)
  imports: I439, I136, I440, I441, I442, I443, I444, I445, I184, I267

### `src/modules/energy/bonuses.py` (py)
  imports: I1, I4, I3
  functions: validate_bonus_amount(amount), build_idempotency_redis_key(player_id, idempotency_key), calculate_bonus_hearts(current_hearts, amount, max_hearts, overflow_limit), calculate_refund_hearts(current_hearts, amount, max_hearts)

### `src/modules/energy/consumption.py` (py)
  imports: I1
  functions: validate_consume_amount(amount), check_can_play(effective_hearts, hearts_required), calculate_hearts_after_consume(effective_hearts, amount)

### `src/modules/energy/dto.py` (py)
  imports: I1, I10, I22, I2, I43
  classes: BonusSource(Enum), EnergyInfo, EnergyConsumeResult, RegenResult, TimeToHeartResult, LoginResult, StreakInfo, BonusGrantResult

### `src/modules/energy/protocols.py` (py)
  imports: I1, I4, I13, I6, I439, I136, I440, I441, I442, I443, I444, I445
  classes: EnergyServiceProtocol(Protocol)
  functions: get_energy(self, player_id), consume_heart(self, player_id, amount), can_play(self, player_id, hearts_required), apply_pending_regeneration(self, player_id), get_time_to_next_heart(self, player_id), record_login(self, player_id), get_streak(self, player_id), grant_bonus_hearts(self, player_id, amount, source, idempotency_key), refund_heart(self, player_id, amount, reason)

### `src/modules/energy/regen.py` (py)
  imports: I1, I2, I29
  functions: calculate_regenerated_hearts(current_hearts, max_hearts, last_regen_at, now, regen_interval_seconds), calculate_time_to_next_heart(current_hearts, max_hearts, last_regen_at, now, regen_interval_seconds)

### `src/modules/energy/service.py` (py)
  imports: I1, I22, I2, I29, I5, I4, I7, I3, I11, I6, I439, I136, I440, I441, I442, I443, I444, I445, from src.modules.energy.bonuses import IDEMPOTENCY_TTL_SECONDS, from src.modules.energy.bonuses import build_idempotency_redis_key, from src.modules.energy.bonuses import calculate_bonus_hearts, from src.modules.energy.bonuses import calculate_refund_hearts, from src.modules.energy.bonuses import validate_bonus_amount, from src.modules.energy.consumption import calculate_hearts_after_consume, from src.modules.energy.consumption import check_can_play, from src.modules.energy.consumption import validate_consume_amount, from src.modules.energy.regen import calculate_regenerated_hearts, from src.modules.energy.regen import calculate_time_to_next_heart, from src.modules.energy.streak import calculate_next_reward_threshold, from src.modules.energy.streak import calculate_streak_reward, from src.modules.energy.streak import calculate_streak_update, I18, I15, I9, I8, I408, I76
  classes: EnergyService
  functions: __init__(self, config, logger, errors, player_service, energy_repo, redis, data_ctx), get_energy(self, player_id), consume_heart(self, player_id, amount), can_play(self, player_id, hearts_required), apply_pending_regeneration(self, player_id), get_time_to_next_heart(self, player_id), record_login(self, player_id), get_streak(self, player_id), grant_bonus_hearts(self, player_id, amount, source, idempotency_key), refund_heart(self, player_id, amount, reason)

### `src/modules/energy/streak.py` (py)
  imports: I1, I22
  functions: calculate_streak_update(last_login_date, current_streak, today), calculate_streak_reward(streak_day, threshold_7, threshold_14, threshold_30, repeat_interval), calculate_next_reward_threshold(current_streak)

### `src/modules/events/__init__.py` (py)
  imports: I104, I108, I175, I168, I191, I176, I124, I326, I271, I446, I447, I149, I345, I186, I127, from src.modules.events.types import EventRules, I74, I192, I105, I233, I169, I242, I243, I448, I346, I244, I347

### `src/modules/events/_data_mapper.py` (py)
  imports: I1, I2, I7, I38, I6, I446, I447, I149, I127, from src.modules.events.types import EventRules, I74, I192, I105, I448, I346, I347
  functions: record_to_event(record), record_to_summary(record, now), build_participant(record, player_username, event_record, rank), parse_requirements(data), parse_reward_tiers(data), parse_rules(data)

### `src/modules/events/dto.py` (py)
  imports: I1, I10, I24, I2, I3, I38, I25, I6, I183
  classes: EventCreate, EventUpdate, EventDbUpdate, ParticipantCreate, ParticipantUpdate, EventMatchCreate

### `src/modules/events/leaderboard_service.py` (py)
  imports: I1, I2, I5, I4, I7, I3, I38, I6, I449, I186, I74, I233, I242, I346, I9, I8, I245, I246, I193, I247
  classes: LeaderboardService
  functions: __init__(self, logger, errors, player_service, event_repo, participant_repo, leaderboard_repo), get_leaderboard(self, event_id, limit, offset), get_player_rank(self, event_id, player_id), _determine_reward_tier(rank, total_participants, tiers), _calculate_points_to_next_tier(rank, total, tiers, current_score)

### `src/modules/events/lifecycle_service.py` (py)
  imports: I1, I2, I5, I4, I7, I38, I6, from src.modules.events._data_mapper import parse_requirements, from src.modules.events._data_mapper import record_to_event, from src.modules.events._data_mapper import record_to_summary, I104, I108, I168, I191, I149, I74, I192, I105, I9, I8, I348, I245, I246, I193
  classes: EventLifecycleService
  functions: __init__(self, logger, errors, energy_service, event_repo, participant_repo, leaderboard_repo), create_event(self, event_data), get_event(self, event_id), list_events(self, status, event_type, limit, offset), get_active_events(self), update_event(self, event_id, updates), cancel_event(self, event_id, reason)

### `src/modules/events/participation_service.py` (py)
  imports: I1, I2, I5, I4, I7, I38, I6, from src.modules.events._data_mapper import build_participant, from src.modules.events._data_mapper import parse_requirements, I191, I176, I124, I447, I127, I74, I105, I243, I18, I9, I8, I348, I245, I246, I193, I247
  classes: ParticipationService
  functions: __init__(self, logger, errors, player_service, energy_service, event_repo, participant_repo, leaderboard_repo, allow_leave_after_match), join_event(self, event_id, player_id), leave_event(self, event_id, player_id), get_event_participant(self, event_id, player_id), get_player_events(self, player_id, include_past, limit, offset), _check_entry_requirements(self, player, requirements, event_id), _calculate_level(stats)

### `src/modules/events/protocols.py` (py)
  imports: I1, I2, I7, I13, I3, I38, I25, I6, I104, I108, I175, I168, I191, I176, I124, I149, I345, I186, I127, I74, I192, I105, I169, I242, I243, I244
  classes: EventServiceProtocol(Protocol), EventRepositoryProtocol(Protocol), EventParticipantRepositoryProtocol(Protocol), EventLeaderboardRepositoryProtocol(Protocol), MatchServiceProtocol(Protocol), PlayerServiceProtocol(Protocol), EnergyServiceProtocol(Protocol), VaultServiceProtocol(Protocol)
  functions: create_event(self, event_data), get_event(self, event_id), list_events(self, status, event_type, limit, offset), get_active_events(self), join_event(self, event_id, player_id), leave_event(self, event_id, player_id), record_event_match(self, event_id, player_id, match_id, score, match_stats), get_leaderboard(self, event_id, limit, offset), get_player_rank(self, event_id, player_id), get_player_events(self, player_id, include_past, limit, offset), get_event_participant(self, event_id, player_id), finalize_event(self, event_id), cancel_event(self, event_id, reason), update_event(self, event_id, updates), process_scheduled_events(self), create(self, data), find_by_id(self, event_id), update(self, event_id, changes), find_by_status(self, status, event_type, limit, offset), find_active(self), find_scheduled_to_start(self, before), find_active_to_end(self, before), find_ended_to_finalize(self, before), increment_participant_count(self, event_id), decrement_participant_count(self, event_id), create(self, data), find_by_event_and_player(self, event_id, player_id), update(self, event_id, player_id, changes), find_by_event(self, event_id, active_only, limit, offset), find_by_player(self, player_id, include_past, limit, offset), find_ranked_by_event(self, event_id, limit, offset), count_by_event(self, event_id, active_only), bulk_update_ranks(self, event_id, ranks), find_eligible_for_rewards(self, event_id, min_matches), create_event_match(self, data), update_score(self, event_id, player_id, score), get_rank(self, event_id, player_id), get_score(self, event_id, player_id), get_top(self, event_id, limit, offset), get_total_count(self, event_id), get_percentile(self, event_id, player_id), remove_player(self, event_id, player_id), clear_leaderboard(self, event_id), sync_to_database(self, event_id, participant_repo), get_match(self, match_id), get_player(self, player_id), get_stats(self, player_id), get_elo(self, player_id), update_elo(self, player_id, new_rating), get_energy(self, player_id), consume_heart(self, player_id, amount), grant_bonus_hearts(self, player_id, amount, source, idempotency_key), refund_heart(self, player_id, amount, reason), add_artifact(self, player_id, artifact_type_id, source, source_id)

### `src/modules/events/reward_service.py` (py)
  imports: I1, I4, I38, I6, I136, I449, from src.modules.events.leaderboard_service import LeaderboardService, I448, I346, I9, I8, I348, I247, from src.modules.events.protocols import VaultServiceProtocol
  classes: RewardService
  functions: __init__(self, logger, errors, vault_service, energy_service, player_service), determine_reward_tier(self, rank, total_participants, tiers), grant_reward(self, player_id, reward, event_id)

### `src/modules/events/scheduling_service.py` (py)
  imports: I1, I2, I29, I5, I4, I7, I38, I108, I74, I244, I8, I193
  classes: EventSchedulingService
  functions: __init__(self, logger, data_ctx, event_repo, auto_finalize_delay, facade), process_scheduled_events(self)

### `src/modules/events/scoring_service.py` (py)
  imports: I1, I2, I5, I4, I7, I38, I25, I6, from src.modules.events._data_mapper import build_participant, from src.modules.events._data_mapper import parse_rules, I175, I124, I446, I127, I74, I169, I347, I9, I8, I245, I246, I193, I247
  classes: EventScoringService
  functions: __init__(self, logger, errors, event_repo, participant_repo, leaderboard_repo, player_service), record_event_match(self, event_id, player_id, match_id, score, match_stats), _check_bonus_condition(bonus, stats), _calculate_new_score(scoring_type, current_total, matches_played, new_score)

### `src/modules/events/service.py` (py)
  imports: I1, I2, I5, I4, I7, I3, I38, I25, I6, I449, I104, I108, I168, I191, I124, from src.modules.events.leaderboard_service import LeaderboardService, from src.modules.events.lifecycle_service import EventLifecycleService, from src.modules.events.participation_service import ParticipationService, from src.modules.events.reward_service import RewardService, from src.modules.events.scheduling_service import EventSchedulingService, from src.modules.events.scoring_service import EventScoringService, I149, I345, I186, I127, I74, I192, I105, I233, I169, I242, I243, I244, I18, I9, I8, I348, I245, I246, I193, from src.modules.events.protocols import MatchServiceProtocol, I247, from src.modules.events.protocols import VaultServiceProtocol
  classes: EventService
  functions: __init__(self, config, logger, errors, data_ctx, vault_service, energy_service, match_service, player_service, event_repository, event_participant_repository, event_leaderboard_repository), create_event(self, event_data), get_event(self, event_id), list_events(self, status, event_type, limit, offset), get_active_events(self), update_event(self, event_id, updates), cancel_event(self, event_id, reason), join_event(self, event_id, player_id), leave_event(self, event_id, player_id), get_event_participant(self, event_id, player_id), get_player_events(self, player_id, include_past, limit, offset), record_event_match(self, event_id, player_id, match_id, score, match_stats), get_leaderboard(self, event_id, limit, offset), get_player_rank(self, event_id, player_id), finalize_event(self, event_id), process_scheduled_events(self)

### `src/modules/events/types.py` (py)
  imports: I1, I10, I24, I2, I43, I4, I38, I25, I6
  classes: EventType(Enum), EventStatus(Enum), ScoringType(Enum), EntryRequirements, RewardItem, RewardTier, BonusCondition, EventRules, MatchEventStats, Event, EventSummary, EventParticipant, LeaderboardEntry, EventLeaderboard, PlayerEventRank, PlayerEventSummary, EventFinalizationResult, ScheduledEventResult

### `src/modules/inventory/protocols.py` (py)
  imports: I1, I13, I6
  classes: InventoryServiceProtocol(Protocol)
  functions: get_mega_counts(self, player_id), consume_mega(self, player_id, slot_index), grant_mega(self, player_id, slot_index, amount)

### `src/modules/inventory/service.py` (py)
  imports: I1, I4, I6, I18, I9, I8, from src.data.repositories.mega_gem_inventory_repository import SQLAlchemyMegaGemInventoryRepository
  classes: InventoryService
  functions: __init__(self, config, logger, errors, inventory_repo), get_mega_counts(self, player_id), consume_mega(self, player_id, slot_index), grant_mega(self, player_id, slot_index, amount)

### `src/modules/match/__init__.py` (py)
  imports: I327, I126, I151, I234, I117, I235, I187, I236, I450, I217, I268

### `src/modules/match/dto.py` (py)
  imports: I1, I10, I24, I2, I7, I3, I183
  classes: MatchCreate, MatchUpdate, MoveCreate

### `src/modules/match/match_finalizer.py` (py)
  imports: I1, I103, I4, I3, I6, from src.modules.match.types import CardRaidResult, from src.modules.match.types import MatchRewardResult, I8, I141, I76, I232, I85
  classes: MatchFinalizer
  functions: __init__(self, logger, player_service), finalize_match(self, player1_id, player2_id, p1_score, p2_score, winner_id), _process_card_raid(self, winner_id, loser_id), _process_match_reward(self, winner_id)

### `src/modules/match/move_processor.py` (py)
  imports: I1, I82, I2, I5, I4, I3, from src.core.move_pipeline import BoardProcessingResult, from src.core.move_pipeline import derive_move_seed, from src.core.move_pipeline import process_mega_pipeline, from src.core.move_pipeline import process_move_pipeline, I16, I25, I39, I6, I144, I304, I151, I187, I18, I9, I8, I336, from src.modules.match.match_finalizer import MatchFinalizer, from src.modules.match.protocols import BoardServiceProtocol, from src.modules.match.protocols import ScoringServiceProtocol, I217, I76, from src.modules.match.types import CardRaidResult, from src.modules.match.types import MatchRewardResult
  classes: MoveProcessor
  functions: __init__(self, config, logger, errors, board_service, scoring_service, board_gen_service, repos, finalizer), submit_move(self, match_id, player_id, move), process_mega_activation(self, match_id, player_id, slot_index, mega_value), _validate_move_preconditions(self, match_id, player_id), _check_and_finalize(self, match_record, update, is_player1, new_moves_remaining, new_score, new_chain, move_result, now)

### `src/modules/match/protocols.py` (py)
  imports: I1, I2, I7, I13, I3, I16, I25, I39, I6, I303, I144, I304, I451, I126, I234, I117, I235, I187, I236
  classes: MatchServiceProtocol(Protocol), MatchRepositoryProtocol(Protocol), MatchMoveRepositoryProtocol(Protocol), BoardServiceProtocol(Protocol), ScoringServiceProtocol(Protocol)
  functions: create_match(self, player1_id, player2_id, board_seed, match_type), submit_move(self, match_id, player_id, move), get_match(self, match_id), get_player_board(self, match_id, player_id), get_active_matches(self, player_id), get_match_history(self, player_id, limit, offset), get_move_history(self, match_id, player_id), activate_mega(self, match_id, player_id, slot_index, source), forfeit_match(self, match_id, player_id), abandon_stale_matches(self), create(self, data), find_by_id(self, match_id), update(self, match_id, changes), find_active_by_player(self, player_id), find_by_player(self, player_id, status, limit, offset), find_stale_matches(self, cutoff), bulk_abandon(self, match_ids), cleanup_match_data(self, match_id), create(self, data), find_by_match(self, match_id, player_id), count_by_player(self, match_id, player_id), delete_by_match_id(self, match_id), process_move(self, board, move, seed, modifiers), process_mega_activation(self, board, mega_value, seed, modifiers), shuffle_board(self, board, seed), has_valid_moves(self, board), calculate_move_score(self, move_result)

### `src/modules/match/queries.py` (py)
  imports: I1, I4, I3, I16, I30, I25, I39, I6, I23, I451, I126, I151, I234, I117, I235, I236, I450
  classes: _MatchQueriesMixin
  functions: get_match(self, match_id), get_match_state(self, match_id, for_player_id), get_player_board(self, match_id, player_id), get_active_matches(self, player_id), get_match_history(self, player_id, limit, offset, status), get_move_history(self, match_id, player_id), _build_match_state(self, match_record, player1, player2)

### `src/modules/match/service.py` (py)
  imports: I1, I422, I2, I29, I5, I4, I3, I25, I39, I6, I303, I144, from src.modules.match.match_finalizer import MatchFinalizer, from src.modules.match.move_processor import MoveProcessor, from src.modules.match.queries import _MatchQueriesMixin, I126, I151, I117, I187, I18, I15, I9, I8, I109, I336, I184, from src.modules.match.protocols import BoardServiceProtocol, from src.modules.match.protocols import MatchMoveRepositoryProtocol, from src.modules.match.protocols import MatchRepositoryProtocol, from src.modules.match.protocols import ScoringServiceProtocol, I76, I433, I16, I39, I23, I92, I194, I82, I82, I19, I174
  classes: MatchRepositoryBundle, MatchService(_MatchQueriesMixin)
  functions: __init__(self, match_repository, match_move_repository), __init__(self, config, logger, errors, data_ctx, board_gen_service, board_service, scoring_service, special_gems_service, player_service, auth_service, energy_service, repos), create_match(self, player1_id, player2_id, board_seed, match_type), submit_move(self, match_id, player_id, move), activate_mega(self, match_id, player_id, slot_index, source), forfeit_match(self, match_id, player_id), abandon_stale_matches(self), _schedule_cleanup(self, match_id), _delayed_cleanup(self, match_id), cleanup_completed_matches(self, older_than_hours), _generate_seed()

### `src/modules/match/types.py` (py)
  imports: I1, I10, I24, I2, I5, I43, I16, I30, I25, I39, I6, I23, from src.core.types.match import MatchType as MatchType, I92, I194, I152
  classes: MatchStatus(Enum), PlayerMatchState, MatchState, CardRaidResult, MatchRewardResult, MoveSubmissionResult, MatchSummary, MoveRecord, PlayerBoardState
  functions: get_player_state(self, player_id), get_opponent_state(self, player_id), both_finished(self), is_participant(self, player_id)

### `src/modules/matchmaking/__init__.py` (py)
  imports: I418, I269, I248, I212, I97, I349, I145, I350, I351

### `src/modules/matchmaking/_helpers.py` (py)
  imports: I1, import math, I2, I5, I4, I11, I6, I248, I212, I97, I145, I9, I8, from src.modules.matchmaking.protocols import MatchServiceProtocol, from src.modules.matchmaking.protocols import MatchmakingQueueRepositoryProtocol
  functions: maybe_expand_elo_range(player_id, queue_state), try_create_match(player_id, player_elo, opponent_id, opponent_elo, pool_type, wait_seconds), re_add_to_queue(player_id, elo_rating, pool_type), calculate_queue_position(player_id, pool_type), estimate_wait_time(elo_rating, pool_type)

### `src/modules/matchmaking/protocols.py` (py)
  imports: I1, I2, I7, I13, I3, I25, I6, I248, I97, I349, I145, I350, I351
  classes: MatchmakingServiceProtocol(Protocol), MatchmakingQueueRepositoryProtocol(Protocol), MatchServiceProtocol(Protocol), PlayerServiceProtocol(Protocol)
  functions: join_queue(self, player_id, pool_type), leave_queue(self, player_id), get_queue_status(self, player_id), find_match(self, player_id), process_queue(self, pool_type), cleanup_stale_entries(self), get_queue_stats(self, pool_type), add_to_queue(self, player_id, elo_rating, pool_type, initial_elo_range), remove_from_queue(self, player_id), get_player_queue_state(self, player_id), is_in_queue(self, player_id), find_opponents_in_range(self, pool_type, min_elo, max_elo, exclude_player_id, limit), get_queue_count(self, pool_type), get_all_queued_players(self, pool_type), update_elo_range(self, player_id, new_min_elo, new_max_elo), remove_stale_entries(self, cutoff_time), get_players_by_elo_bucket(self, pool_type, bucket_size), atomic_remove_pair(self, player1_id, player2_id), create_match(self, player1_id, player2_id, board_seed, match_type), get_active_matches(self, player_id), get_player(self, player_id), get_elo(self, player_id), list_players(self, player_type, limit, offset)

### `src/modules/matchmaking/service.py` (py)
  imports: I1, I2, I29, I5, I4, I11, I25, I6, I32, from src.modules.matchmaking._helpers import calculate_queue_position, from src.modules.matchmaking._helpers import estimate_wait_time, from src.modules.matchmaking._helpers import maybe_expand_elo_range, from src.modules.matchmaking._helpers import try_create_match, I248, I212, I97, I349, I145, I350, I351, I18, I9, I8, from src.modules.matchmaking.protocols import MatchmakingQueueRepositoryProtocol, from src.modules.matchmaking.protocols import MatchServiceProtocol, from src.modules.matchmaking.protocols import PlayerServiceProtocol, I103
  classes: MatchmakingService
  functions: __init__(self, config, logger, errors, match_service, player_service, matchmaking_queue_repository), join_queue(self, player_id, pool_type), leave_queue(self, player_id), get_queue_status(self, player_id), find_match(self, player_id), process_queue(self, pool_type), cleanup_stale_entries(self), get_queue_stats(self, pool_type), _maybe_expand_elo_range(self, player_id, queue_state), _try_create_match(self, player_id, player_elo, opponent_id, opponent_elo, pool_type, wait_seconds), _calculate_queue_position(self, player_id, pool_type), _estimate_wait_time(self, elo_rating, pool_type), _try_bot_fallback(self, player_id, queue_state, wait_seconds)

### `src/modules/matchmaking/types.py` (py)
  imports: I1, I10, I24, I2, I43, I25, I6
  classes: PoolType(Enum), MatchmakingStatus(Enum), QueueEntryData, QueueEntry, QueueStatus, MatchmakingResult, QueueStats

### `src/modules/payments/__init__.py` (py)
  imports: I352, I317, I315, I316, I318, I319, I320, I321, I419, I213, I91, I353, I354, I137, I452, I355, I356, from src.modules.payments.types import PurchaseIntentId, I453, I249, I118, I357, I358, I139, I214, I359, I360

### `src/modules/payments/_helpers.py` (py)
  imports: I1, I335, I7, I6, I91, I137, I355, I249, I358
  functions: hash_receipt(receipt_data), to_purchase_record(rec)

### `src/modules/payments/apple_provider.py` (py)
  imports: I1, import base64, I57, I85, I2, I5, I114, I7, import httpx, I427, I91, I139
  classes: AppleAppStoreProvider
  functions: __init__(self), validate_receipt(self, receipt_data, product_id, is_sandbox), verify_webhook_signature(self, payload, signature), _create_server_jwt(self), _decode_jws_payload(jws_string)

### `src/modules/payments/dto.py` (py)
  imports: I1, I10, I2, I7, I3, I183
  classes: PurchaseIntentCreate, PurchaseIntentUpdate, PurchaseCreate, PurchaseUpdate, ReceiptValidationCreate, ReceiptValidationUpdate, RefundNotificationCreate

### `src/modules/payments/protocols.py` (py)
  imports: I1, I2, I7, I13, I3, I6, I352, I317, I315, I316, I318, I319, I320, I321, I91, I353, I354, I137, I356, I249, I118, I357, I139, I214, I359, I360
  classes: PaymentServiceProtocol(Protocol), PaymentProviderProtocol(Protocol), ProductRepositoryProtocol(Protocol), PurchaseIntentRepositoryProtocol(Protocol), PurchaseRepositoryProtocol(Protocol), ReceiptValidationRepositoryProtocol(Protocol), RefundNotificationRepositoryProtocol(Protocol), PlayerServiceProtocol(Protocol), AdServiceProtocol(Protocol)
  functions: initiate_purchase(self, player_id, product_id), validate_purchase(self, player_id, receipt), get_purchase_status(self, player_id), get_purchase_history(self, player_id, limit, offset), process_refund(self, refund_notification), restore_purchases(self, player_id, receipts), get_products(self), verify_webhook_signature(self, payload, signature, provider), list_refund_notifications(self, unprocessed_only), get_purchase(self, purchase_id), get_validation_by_transaction(self, transaction_id), validate_receipt(self, receipt_data, product_id, is_sandbox), verify_webhook_signature(self, payload, signature), find_by_id(self, product_id), find_all_active(self), create(self, data), find_by_id(self, intent_id), update(self, intent_id, changes), find_pending_by_player(self, player_id), expire_old_intents(self, before), create(self, data), find_by_id(self, purchase_id), find_by_transaction(self, provider, transaction_id), find_by_player(self, player_id, limit, offset), find_completed_by_player(self, player_id, product_id), update(self, purchase_id, changes), create(self, data), find_by_hash(self, receipt_hash), find_by_transaction(self, provider, transaction_id), update(self, validation_id, changes), create(self, data), find_unprocessed(self), mark_processed(self, notification_id, result, error), get_player(self, player_id), check_ad_free_status(self, player_id), grant_ad_free_status(self, player_id, reason, duration_days, granted_by), revoke_ad_free_status(self, player_id, reason)

### `src/modules/payments/service.py` (py)
  imports: I1, I2, I29, I5, I4, I7, I6, from src.modules.payments._helpers import hash_receipt, from src.modules.payments._helpers import to_purchase_record, I352, I317, I315, I316, I318, I319, I320, I321, I91, I353, I354, I137, I452, I355, I356, from src.modules.payments.types import PurchaseIntentId, I453, I249, I118, I357, I358, I139, I214, I359, I360, I18, I9, I8, I409, from src.data.protocols.gold_transaction_repository import GoldTransactionRepositoryProtocol, from src.modules.payments.protocols import AdServiceProtocol, from src.modules.payments.protocols import PaymentProviderProtocol, from src.modules.payments.protocols import PlayerServiceProtocol, from src.modules.payments.protocols import ProductRepositoryProtocol, from src.modules.payments.protocols import PurchaseIntentRepositoryProtocol, from src.modules.payments.protocols import PurchaseRepositoryProtocol, from src.modules.payments.protocols import ReceiptValidationRepositoryProtocol, from src.modules.payments.protocols import RefundNotificationRepositoryProtocol, I361, I361, I84, I361, I84, I361
  classes: PaymentRepositoryBundle, PaymentService
  functions: __init__(self, product_repo, intent_repo, purchase_repo, receipt_repo, refund_repo), __init__(self, config, logger, errors, player_service, ads_service, repos, payment_provider, gold_repo, gold_tx_repo, product_repo, intent_repo, purchase_repo, receipt_repo, refund_repo), initiate_purchase(self, player_id, product_id), validate_purchase(self, player_id, receipt), get_purchase_status(self, player_id), get_purchase_history(self, player_id, limit, offset), process_refund(self, refund_notification), restore_purchases(self, player_id, receipts), get_products(self), verify_webhook_signature(self, payload, signature, provider), list_refund_notifications(self, unprocessed_only), get_purchase(self, purchase_id), get_validation_by_transaction(self, transaction_id), _hash_receipt(receipt_data), _to_purchase_record(rec)

### `src/modules/payments/types.py` (py)
  imports: I1, I10, I2, I43, I7, I274, I3, I6
  classes: PaymentProvider(Enum), ProductType(Enum), PurchaseIntentStatus(Enum), PurchaseStatus(Enum), PurchaseReceipt, RefundNotification, PurchaseIntent, ReceiptValidationResult, PurchaseResult, PlayerPurchaseStatus, PurchaseRecord, RefundResult, RestoreResult, Product

### `src/modules/player/__init__.py` (py)
  imports: I76, I116

### `src/modules/player/bot_names.py` (py)
  imports: I1, I103, I85, I4, I116
  functions: generate_bot_name(), generate_unique_bot_name(player_service)

### `src/modules/player/dto.py` (py)
  imports: I1, I10, I22, I2, I183
  classes: PlayerUpdate, EnergyStateUpdate

### `src/modules/player/elo.py` (py)
  imports: I1
  functions: calculate_expected_score(rating_a, rating_b), calculate_elo_change(winner_rating, loser_rating, k_factor, is_draw)

### `src/modules/player/protocols.py` (py)
  imports: I1, I4, I13, I6, I142, I86, I122, I32, I454, I362, I332
  classes: PlayerServiceProtocol(Protocol)
  functions: create_player(self, username, player_type, password_hash, email, apple_user_id, auth_provider), get_player(self, player_id), get_player_by_username(self, username), get_player_by_apple_id(self, apple_user_id), update_player(self, player_id, updates), soft_delete_player(self, player_id), list_players(self, player_type, limit, offset), get_elo(self, player_id), update_elo(self, player_id, new_rating), calculate_elo_change(self, winner_id, loser_id, is_draw), get_stats(self, player_id), record_match_result(self, player_id, won, is_draw, score, longest_chain, gems_matched), get_energy_state(self, player_id), update_energy_state(self, player_id, energy_update), initialize_energy_state(self, player_id)

### `src/modules/player/service.py` (py)
  imports: I1, I2, I5, I4, I6, I142, I86, I122, I32, I454, I362, I332, from src.modules.player.elo import calculate_elo_change as _calc_elo, from src.modules.player.elo import calculate_expected_score as _calc_expected, I423, I18, I9, I8, I408, from src.data.protocols.player_repository import PlayerRepositoryProtocol, from src.data.protocols.player_stats_repository import PlayerStatsRepositoryProtocol
  classes: PlayerService
  functions: __init__(self, config, logger, errors, player_repo, stats_repo, energy_repo), create_player(self, username, player_type, password_hash, email, apple_user_id, auth_provider), get_player(self, player_id), get_player_by_username(self, username), get_player_by_apple_id(self, apple_user_id), update_player(self, player_id, updates), soft_delete_player(self, player_id), list_players(self, player_type, limit, offset), get_high_score_leaderboard(self, limit, offset), get_elo(self, player_id), update_elo(self, player_id, new_rating), calculate_elo_change(self, winner_id, loser_id, is_draw), get_stats(self, player_id), record_match_result(self, player_id, won, is_draw, score, longest_chain, gems_matched), get_energy_state(self, player_id), update_energy_state(self, player_id, energy_update), initialize_energy_state(self, player_id)

### `src/modules/player/validation.py` (py)
  imports: I1, I334
  functions: validate_username(username, min_length, max_length, pattern)

### `src/modules/scoring/__init__.py` (py)
  imports: I173, I455, I456, I457, I194, I153

### `src/modules/scoring/service.py` (py)
  imports: I1, I4, I63, I30, I92, I455, I456, I457, I194, I153, I18, I9, I8
  classes: ScoringService
  functions: __init__(self, config, logger, errors), calculate_match_score(self, match_result, chain_step), calculate_move_score(self, move_result, score_modifiers), calculate_special_gem_bonus(self, gem_type, gems_affected), get_chain_multiplier(self, chain_step), get_match_length_multiplier(self, match_length), get_base_points(self, gem_type), get_scoring_config(self), _validate_positive_int(self, value, key, default), _validate_multiplier_list(self, value, key, default)

### `src/modules/scoring/types.py` (py)
  imports: I1, I10, I140, I30
  classes: MatchGroupScore, MatchScore, SpecialGemBonus, CascadeStepScore, MoveScore
  functions: summary(self)

### `src/modules/special_gems/__init__.py` (py)
  imports: I433, I215, I363, I250, I458, I152

### `src/modules/special_gems/fusion_service.py` (py)
  imports: I1, I4, I16, I30, I23, I363, from src.modules.special_gems.types import STANDARD_GEM_TYPES, I250, I458, I152, I9, I8, from src.modules.special_gems.protocols import ScoringServiceProtocol
  classes: FusionService
  functions: __init__(self, logger, errors, scoring_service), calculate_fusion_effect(self, board, pos_a, pos_b, target_color), _is_special_gem(gem_type), _validate_position(self, board, position), _validate_target_color(self, target_color), _find_triggered_specials(self, board, affected, exclude), _calculate_fusion(self, board, gem_a, gem_b, pos_a, pos_b, target_color), _fusion_cross_blast(self, board, pos_a, pos_b), _fusion_mega_bomb(self, board, pos_a, pos_b), _fusion_triple_line(self, board, pos_a, pos_b, line_type), _fusion_color_line_blast(self, board, pos_a, pos_b, target_color, line_type), _fusion_color_bomb(self, board, pos_a, pos_b, target_color), _fusion_board_clear(self, board, pos_a, pos_b)

### `src/modules/special_gems/protocols.py` (py)
  imports: I1, I4, I13, I16, I63, I30, I23, I153, I250, I152
  classes: ScoringServiceProtocol(Protocol), SpecialGemsServiceProtocol(Protocol)
  functions: calculate_special_gem_bonus(self, gem_type, gems_affected), calculate_effect(self, board, position, target_color), calculate_fusion_effect(self, board, pos_a, pos_b, target_color), apply_effect(self, board, effect), is_special_gem(self, gem_type), get_special_gem_for_match(self, match_result), find_triggered_special_gems(self, board, cleared_positions)

### `src/modules/special_gems/service.py` (py)
  imports: I1, I4, I16, I63, I30, I23, from src.modules.special_gems.fusion_service import FusionService, I363, from src.modules.special_gems.types import STANDARD_GEM_TYPES, I250, I152, I18, I9, I8, from src.modules.special_gems.protocols import ScoringServiceProtocol
  classes: SpecialGemsService
  functions: __init__(self, config, logger, errors, scoring_service), is_special_gem(self, gem_type), calculate_effect(self, board, position, target_color), calculate_fusion_effect(self, board, pos_a, pos_b, target_color), apply_effect(self, board, effect), get_special_gem_for_match(self, match_result), find_triggered_special_gems(self, board, cleared_positions), _validate_position(self, board, position), _validate_target_color(self, target_color), _calculate_line_blast(self, board, position, is_horizontal), _calculate_radial_bomb(self, board, position, radius), _calculate_chromatic_orb(self, board, position, target_color), _find_triggered_specials(self, board, affected, exclude), _find_center(positions)

### `src/modules/special_gems/types.py` (py)
  imports: I1, I10, I43, I30, I23, I153
  classes: FusionType(Enum), SpecialGemEffect, FusionEffect

### `src/modules/vault/__init__.py` (py)
  imports: I251, I119, I188, I190, I364, I365, I237, I238, I189, I239, I232, I270

### `src/modules/vault/artifact_service.py` (py)
  imports: I1, I4, I106, I6, from src.modules.vault.collection import calculate_collection_progress, I251, I119, I188, I190, I189, I239, I9, I8, I459, I460, I76
  classes: ArtifactService
  functions: __init__(self, logger, errors, player_service, vault_artifact_repo, artifact_definition_repo, max_artifacts_per_player), add_artifact(self, player_id, artifact_type_id, source, source_id), get_artifact(self, artifact_id), get_player_artifacts(self, player_id, rarity, artifact_set, limit, offset), get_vault_summary(self, player_id), remove_artifact(self, artifact_id, reason), transfer_artifact(self, artifact_id, from_player_id, to_player_id, reason), get_artifact_definition(self, artifact_type_id), list_artifact_definitions(self, rarity, artifact_set), get_collection_progress(self, player_id, artifact_set), _record_to_definition(record), _record_to_vault_artifact(record, definition)

### `src/modules/vault/collection.py` (py)
  imports: I1, I188
  functions: calculate_collection_progress(owned_type_ids, set_type_ids, set_name, artifact_set)

### `src/modules/vault/dto.py` (py)
  imports: I1, I10, I2, I5, I43, I275, I276, I3, I106, I6
  classes: ArtifactRarity(Enum), ArtifactDefinition, VaultArtifact, VaultSummary, Shield, RaidResult, RaidEligibility, RaidLog, CollectionProgress, PaginatedResult
  functions: is_active(self), remaining_seconds(self), is_complete(self), completion_percent(self), has_more(self)

### `src/modules/vault/protocols.py` (py)
  imports: I1, I2, I4, I13, I106, I6, I251, I119, I188, I190, I364, I365, I237, I238, I189, I239
  classes: VaultServiceProtocol(Protocol)
  functions: add_artifact(self, player_id, artifact_type_id, source, source_id), get_artifact(self, artifact_id), get_player_artifacts(self, player_id, rarity, artifact_set, limit, offset), get_vault_summary(self, player_id), remove_artifact(self, artifact_id, reason), transfer_artifact(self, artifact_id, from_player_id, to_player_id, reason), get_artifact_definition(self, artifact_type_id), list_artifact_definitions(self, rarity, artifact_set), get_collection_progress(self, player_id, artifact_set), activate_shield(self, player_id, duration_hours), get_shield_status(self, player_id), deactivate_shield(self, player_id), is_protected(self, player_id), attempt_raid(self, attacker_id, defender_id), can_raid(self, attacker_id, defender_id), get_raid_history(self, player_id, as_attacker, as_defender, limit, offset), get_raid_cooldown(self, attacker_id, defender_id)

### `src/modules/vault/raid_engine.py` (py)
  imports: I1, I103, I2, I29, I5
  functions: calculate_raid_success(base_chance, target_artifact_rarity, legendary_modifier), select_raid_target_artifact(artifacts, rng), is_raid_on_cooldown(last_raid_timestamp, cooldown_hours)

### `src/modules/vault/raid_service.py` (py)
  imports: I1, I85, I2, I5, I4, I323, from typing import Awaitable, I106, I6, I251, I119, I190, I364, I365, I237, I189, from src.modules.vault.raid_engine import calculate_raid_success, from src.modules.vault.raid_engine import is_raid_on_cooldown, from src.modules.vault.raid_engine import select_raid_target_artifact, I3, I9, I8, I459, from src.data.protocols.raid_log_repository import RaidLogRepositoryProtocol, I460, I76, from src.modules.vault.shield_service import ShieldService
  classes: RaidService
  functions: __init__(self, logger, errors, player_service, vault_artifact_repo, artifact_definition_repo, raid_log_repo, shield_service, raid_cooldown_hours, raid_energy_cost, raid_success_base_chance, empty_vault_protection, legendary_steal_chance_modifier, max_artifacts_per_player, build_modifier_engine), attempt_raid(self, attacker_id, defender_id), can_raid(self, attacker_id, defender_id), get_raid_history(self, player_id, as_attacker, as_defender, limit, offset), get_raid_cooldown(self, attacker_id, defender_id), _record_to_definition(record), _record_to_vault_artifact(record, definition)

### `src/modules/vault/service.py` (py)
  imports: I1, I2, I4, I106, I6, from src.modules.vault.artifact_service import ArtifactService, I251, I119, I188, I190, I364, I365, I237, I238, I189, I239, from src.modules.vault.raid_service import RaidService, from src.modules.vault.shield_service import ShieldService, I18, I15, I9, I8, I459, from src.data.protocols.raid_log_repository import RaidLogRepositoryProtocol, I460, from src.data.protocols.vault_shield_repository import VaultShieldRepositoryProtocol, I76
  classes: VaultService
  functions: __init__(self, config, logger, errors, player_service, vault_artifact_repo, vault_shield_repo, artifact_definition_repo, raid_log_repo, data_ctx, card_service), add_artifact(self, player_id, artifact_type_id, source, source_id), get_artifact(self, artifact_id), get_player_artifacts(self, player_id, rarity, artifact_set, limit, offset), get_vault_summary(self, player_id), remove_artifact(self, artifact_id, reason), transfer_artifact(self, artifact_id, from_player_id, to_player_id, reason), get_artifact_definition(self, artifact_type_id), list_artifact_definitions(self, rarity, artifact_set), get_collection_progress(self, player_id, artifact_set), activate_shield(self, player_id, duration_hours), get_shield_status(self, player_id), deactivate_shield(self, player_id), is_protected(self, player_id), attempt_raid(self, attacker_id, defender_id), can_raid(self, attacker_id, defender_id), get_raid_history(self, player_id, as_attacker, as_defender, limit, offset), get_raid_cooldown(self, attacker_id, defender_id)

### `src/modules/vault/shield_service.py` (py)
  imports: I1, I2, I29, I5, I4, I6, I238, I9, I8, from src.data.protocols.vault_shield_repository import VaultShieldRepositoryProtocol, I76
  classes: ShieldService
  functions: __init__(self, logger, errors, player_service, vault_shield_repo, shield_duration_hours), activate_shield(self, player_id, duration_hours), get_shield_status(self, player_id), deactivate_shield(self, player_id), is_protected(self, player_id), _record_to_shield(record)

## Test Files

**chromacrush_app/test/**
  widget_test.dart

**chromacrush_app/test/game/**
  input_handler_test.dart

**chromacrush_app/test/unit/extensions/**
  grid_math_test.dart

**chromacrush_app/test/unit/game/**
  background_layer_test.dart

**chromacrush_app/test/unit/models/**
  backend_contract_test.dart
  card_dto_test.dart
  gem_type_test.dart

**chromacrush_app/test/unit/services/**
  event_bus_test.dart
  http_api_client_test.dart — _FakeTokenStorage
  intensity_service_test.dart
  session_manager_test.dart

**chromacrush_app/test/unit/view_models/**
  match_view_model_test.dart — _MockApiClient

**tests/**
  __init__.py
  code_explorer.py — Visitor(ast.NodeVisitor)
  conftest.py
  find_hardcoded.py

**tests/integration/**
  __init__.py
  conftest.py
  test_ad_bot_earnings_flow.py — TestAdFreeStatus, TestBotEarnings, test_check_ad_free_status_default_false(self, factory), test_grant_ad_free_status_happy_path(self, factory), test_grant_ad_free_with_duration(self, factory), test_check_ad_free_player_not_found(self, factory), test_bot_earnings_balance_zero_initially(self, factory), test_sync_attributions_for_bot(self, factory), test_sync_attributions_human_raises(self, factory)
  test_api_integration.py — TestHealthAndInfrastructure, TestAuthFlow, TestErrorFormat, test_health_endpoint_returns_200(self, client), test_liveness_endpoint(self, client), test_not_found_route_returns_401_or_404(self, client), test_correlation_id_in_response_headers(self, client), test_register_and_login(self, client), test_protected_route_requires_auth(self, client), test_protected_route_with_valid_token(self, client), test_app_error_returns_structured_json(self, client)
  test_cli_smoke.py — TestCliRoot, TestSubcommandHelp, test_help_displays_commands(self), test_version_command(self), test_show_config_command(self), test_player_help(self), test_auth_help(self), test_scoring_help(self), test_energy_help(self), test_vault_help(self), test_match_help(self), test_matchmaking_help(self), test_events_help(self), test_ads_help(self), test_payments_help(self), test_bot_earnings_help(self), test_board_gen_help(self), test_special_gems_help(self), test_board_help(self)
  test_event_reward_flow.py — TestEventWorkflow, test_create_event_happy_path(self, factory), test_join_event_happy_path(self, factory), test_join_event_not_found_raises(self, factory), test_leave_event_happy_path(self, factory), test_get_leaderboard_empty(self, factory), test_finalize_event_already_finalized_raises(self, factory), test_finalize_event_not_ended_raises(self, factory), test_list_events_returns_created(self, factory)
  test_match_creation_flow.py — TestMatchCreationHappyPath, TestMatchCreationErrors, test_create_match_returns_pending_state(self, factory), test_create_match_generates_valid_board(self, factory), test_create_match_consumes_energy(self, factory), test_create_match_with_deterministic_seed(self, factory), test_create_match_player_not_found(self, factory), test_create_match_same_player(self, factory), test_create_match_insufficient_energy(self, factory), test_create_match_concurrent_limit(self, factory)
  test_move_submission_flow.py — TestMoveSubmissionHappyPath, TestMoveSubmissionErrors, TestMatchCompletionAndForfeit, test_submit_valid_move_returns_result(self, factory), test_submit_move_cascades_earn_points(self, factory), test_first_move_transitions_to_in_progress(self, factory), test_submit_move_decrements_moves_remaining(self, factory), test_submit_invalid_swap_no_matches(self, factory), test_submit_move_wrong_player(self, factory), test_submit_move_no_moves_remaining(self, factory), test_match_completion_when_both_finish(self, factory), test_forfeit_match(self, factory), test_get_match_state_returns_current_state(self, factory)
  test_purchase_flow.py — TestPurchaseFlow, test_get_products_empty(self, factory), test_purchase_status_no_purchases(self, factory), test_purchase_status_player_not_found(self, factory), test_validate_purchase_already_ad_free(self, factory), test_initiate_purchase_product_not_found(self, factory)

**tests/integration/helpers/**
  __init__.py
  service_factory.py — IntegrationServiceFactory

**tests/mocks/**
  __init__.py
  redis.py — RedisOperation, MockRedis
  services.py — MockConfigService, MockLogService, MockErrorService

**tests/unit/**
  __init__.py

**tests/unit/core/**
  __init__.py
  test_config.py — TestConfigLoad, TestGetWithDefault, TestRequire, TestDotNotation, test_load_from_toml(self), test_load_nonexistent_file_raises(self), test_get_with_default_returns_fallback(self), test_get_with_default_none(self), test_require_missing_key_raises(self), test_require_existing_key(self), test_dot_notation_access(self), test_nested_access(self), test_section_returns_dict(self)
  test_errors.py — TestAppError, TestErrorService, test_app_error_to_dict(self), test_app_error_str(self), test_app_error_repr(self), test_app_error_is_exception(self), test_error_service_validation(self), test_error_service_not_found(self), test_error_service_unauthorized(self), test_error_service_forbidden(self), test_error_service_conflict(self), test_error_service_rate_limited(self), test_error_service_internal(self), test_error_service_logs_error(self), test_error_service_custom_code(self), test_error_service_context_passed_through(self), test_error_service_correlation_id_set(self)
  test_logger.py — TestJsonFormat, TestLevelFiltering, TestTextFormat, test_log_at_info_level(self, capsys), test_context_included(self, capsys), test_correlation_id_included(self, capsys), test_correlation_id_none_when_unset(self, capsys), test_log_below_threshold_suppressed(self, capsys), test_log_at_threshold_emitted(self, capsys), test_error_goes_to_stderr(self, capsys), test_text_format(self, capsys), test_text_format_with_context(self, capsys)
  test_types.py — TestGemType, TestPosition, TestMove, TestBoardState, TestPlayerType, TestMatchStatus, test_gem_type_values(self), test_special_gem_negative_values(self), test_gem_type_int_conversion(self), test_position_creation(self), test_position_non_negative(self), test_position_adjacency(self), test_position_not_adjacent_diagonal(self), test_position_not_adjacent_distance(self), test_position_not_adjacent_same(self), test_position_frozen(self), test_move_requires_adjacent(self), test_valid_move(self), test_move_frozen(self), test_board_state_from_list(self), test_board_state_to_list(self), test_board_state_copy(self), test_board_state_dimensions(self), test_player_type_enum(self), test_player_type_members(self), test_match_status_enum(self), test_match_status_members(self)

**tests/unit/modules/**
  __init__.py
  test_campaign_service.py — TestStartAttempt, TestSubmitMove, TestWinLoseConditions, TestLevelProgression, TestAbandonAttempt, TestGetPlayerProgress, test_start_attempt_success(self, campaign_service, mock_campaign_repo), test_start_attempt_level_locked(self, campaign_service, mock_player_repo), test_start_attempt_player_not_found(self, campaign_service, mock_player_repo), test_start_attempt_abandons_active(self, campaign_service, mock_campaign_repo), test_start_attempt_checkpoint_deducts_heart(self, campaign_service, mock_energy_service, mock_player_repo), test_start_attempt_insufficient_hearts(self, campaign_service, mock_energy_service, mock_player_repo), test_start_attempt_nonexistent_level(self, campaign_service), test_submit_move_success(self, campaign_service, mock_campaign_repo, mock_board_service), test_submit_move_invalid_swap_raises(self, campaign_service, mock_campaign_repo, mock_board_service), test_submit_move_attempt_not_found(self, campaign_service, mock_campaign_repo), test_submit_move_wrong_player(self, campaign_service, mock_campaign_repo), test_submit_move_attempt_already_finished(self, campaign_service, mock_campaign_repo), test_all_obstacles_cleared_is_win(self, campaign_service, mock_campaign_repo, mock_board_service, mock_player_repo), test_no_moves_left_with_obstacles_is_lose(self, campaign_service, mock_campaign_repo, mock_board_service), test_moves_and_obstacles_remaining_is_in_progress(self, campaign_service, mock_campaign_repo, mock_board_service), test_win_advances_campaign_level(self, campaign_service, mock_campaign_repo, mock_board_service, mock_player_repo), test_win_replay_does_not_advance(self, campaign_service, mock_campaign_repo, mock_board_service, mock_player_repo), test_checkpoint_loss_regresses_by_5(self, campaign_service, mock_campaign_repo, mock_board_service, mock_player_repo), test_non_checkpoint_loss_no_regression(self, campaign_service, mock_campaign_repo, mock_board_service, mock_player_repo), test_checkpoint_regression_floor_is_1(self, campaign_service, mock_campaign_repo, mock_board_service, mock_player_repo), test_abandon_success(self, campaign_service, mock_campaign_repo), test_abandon_not_found(self, campaign_service, mock_campaign_repo), test_abandon_wrong_player(self, campaign_service, mock_campaign_repo), test_abandon_already_finished(self, campaign_service, mock_campaign_repo), test_progress_with_no_active_attempt(self, campaign_service, mock_player_repo, mock_campaign_repo), test_progress_with_active_attempt(self, campaign_service, mock_player_repo, mock_campaign_repo), test_progress_player_not_found(self, campaign_service, mock_player_repo)
  test_obstacles.py — TestObstacleSatisfied, TestObstacleClearing, TestObstacleTransmutation, TestAnchoredGravity, TestBoardGenerationWithObstacles, TestObstacleEventTracking, test_regular_match_cannot_damage_any_obstacle(self), test_basic_glass_cleared_by_any_special(self), test_keyed_obstacle_cleared_by_matching_special(self), test_keyed_obstacle_not_cleared_by_wrong_special(self), test_mega_gem_clears_if_component_matches(self), test_special_blast_clears_glass_obstacle(self, service), test_glass_obstacle_removed_from_grid(self, service), test_keyed_obstacle_not_cleared_by_wrong_special(self, service), test_cannot_swap_obstacle_cell(self, service), test_func2_transmutes_to_func1(self, service), test_func1_transmutes_to_func0(self, service), test_grid_stays_7_during_transmutation(self), test_obstacle_stays_in_place(self, service), test_gems_above_obstacle_compact_independently(self, service), test_gems_below_obstacle_compact_independently(self, service), test_multiple_obstacles_in_column(self, service), test_no_obstacles_uses_standard_gravity(self, service), test_obstacles_placed_correctly(self, service), test_non_obstacle_cells_filled_with_gems(self, service), test_no_initial_three_in_a_row(self, service), test_deterministic_with_same_seed(self, service), test_different_seed_produces_different_board(self, service), test_reduced_gem_colors(self, service), test_obstacle_func_grid_untouched_by_fill(self, service), test_normal_move_has_empty_obstacle_events(self, service), test_cascade_step_obstacle_fields_default_empty(self)

**tests/unit/modules/ads/**
  __init__.py
  test_ad_service.py — test_check_ad_free_status_not_ad_free(), test_check_ad_free_status_active(), test_check_ad_free_status_expired(), test_can_show_ad_eligible(), test_can_show_ad_ad_free_player(), test_can_show_ad_cooldown_active(), test_grant_ad_free_status_success(), test_grant_ad_free_status_with_duration(), test_grant_ad_free_invalid_duration(), test_revoke_ad_free_status_success(), test_revoke_ad_free_status_not_active(), test_revoke_ad_free_reason_too_long(), test_request_interstitial_success(), test_request_interstitial_ad_free_blocked(), test_request_interstitial_cooldown(), test_record_interstitial_impression_success(), test_record_interstitial_not_found(), test_record_interstitial_already_recorded(), test_record_interstitial_expired(), test_request_rewarded_video_success(), test_complete_rewarded_video_granted(), test_complete_rewarded_video_not_granted(), test_record_banner_impression_success(), test_record_banner_too_short(), test_record_banner_ad_free_blocked(), test_get_player_ad_stats_success(), test_get_ad_impressions_success(), test_get_ad_impressions_invalid_limit(), test_get_match_ad_attribution_with_impressions(), test_get_match_ad_attribution_no_impressions(), test_get_bot_ad_attributions_success(), test_get_bot_ad_attributions_not_bot(), test_get_bot_ad_attributions_invalid_dates(), test_get_event_ad_opportunities_success(), test_get_event_ad_opportunities_fully_claimed(), test_claim_event_ad_reward_success(), test_claim_event_ad_reward_not_found(), test_claim_event_ad_reward_fully_claimed(), test_claim_event_ad_reward_cooldown(), test_interstitial_provider_error(), test_mid_request_ad_free_blocks_impression()

**tests/unit/modules/api/**
  __init__.py
  conftest.py — TestAuthMiddleware(BaseHTTPMiddleware), test_app(mock_config, mock_logger, mock_errors, mock_auth_service, mock_player_service, mock_energy_service, mock_matchmaking_service)
  test_adapters.py — TestResponseAdapter, TestBotHintGenerator, test_success_returns_correct_envelope_structure(self, adapter), test_success_meta_includes_timestamp(self, adapter), test_success_meta_includes_version(self, adapter), test_success_with_none_data(self, adapter), test_success_with_complex_data(self, adapter), test_error_returns_correct_envelope_structure(self, adapter), test_error_with_details(self, adapter), test_error_without_details(self, adapter), test_correlation_id_is_included_in_meta(self, adapter), test_generate_match_hints_returns_correct_structure(self, generator, simple_board, sample_moves), test_board_analysis_counts_gem_distribution(self, generator), test_board_analysis_counts_special_gems(self, generator), test_board_analysis_volatility_stable(self, generator), test_board_analysis_volatility_volatile(self, generator), test_move_ranking_sorts_by_expected_score(self, generator, simple_board, sample_moves), test_move_ranking_returns_ranked_move_instances(self, generator, simple_board, sample_moves), test_best_moves_limited_to_top_five(self, generator), test_strategic_context_large_deficit_late_game_aggressive(self, generator, simple_board), test_strategic_context_large_lead_defensive(self, generator, simple_board), test_strategic_context_even_score_balanced(self, generator, simple_board), test_strategic_context_early_game_phase(self, generator, simple_board), test_strategic_context_none_turns_remaining_mid_phase(self, generator, simple_board), test_score_differential_calculated_correctly(self, generator, simple_board), test_empty_valid_moves_returns_empty_best_moves(self, generator, simple_board)
  test_ads_routes.py — _AdFreeReason(Enum), _AdFreeStatus, _InterstitialResult, _ImpressionRecord, _RewardType(Enum), _RewardedVideoResult, _RewardedCompleteResult, _DailyBreakdown, _BotAttributionResult, _TestAuthMiddleware(BaseHTTPMiddleware), TestGetAdFreeStatus, TestRequestInterstitial, TestCompleteInterstitial, TestRequestRewardedVideo, TestCompleteRewardedVideo, TestGetBotAttributions, test_ad_free(self), test_not_ad_free(self), test_success_jwt(self), test_forbidden_api_key(self), test_success(self), test_success_jwt(self), test_forbidden_api_key(self), test_success(self), test_not_completed(self), test_success_api_key(self), test_forbidden_jwt(self)
  test_auth_routes.py — FakeAuthResult, FakeApiKeyResult, FakeKeyInfo, TestRegisterRoute, TestLoginRoute, TestRefreshTokenRoute, TestLogoutRoute, TestBotRegisterRoute, TestCreateApiKeyRoute, TestRevokeApiKeyRoute, TestListApiKeysRoute, test_register_success(self, client, mock_auth_service, mock_player_service), test_register_short_username_returns_422(self, client), test_register_short_password_returns_422(self, client), test_register_invalid_username_chars_returns_422(self, client), test_register_conflict_returns_error(self, client, mock_player_service), test_login_success(self, client, mock_auth_service), test_login_invalid_credentials(self, client, mock_auth_service), test_login_missing_fields_returns_422(self, client), test_refresh_success(self, client, mock_auth_service), test_refresh_invalid_token(self, client, mock_auth_service), test_refresh_missing_token_returns_422(self, client), test_logout_success(self, client, mock_auth_service), test_logout_player_not_found(self, client, mock_auth_service), test_bot_register_success(self, client, mock_player_service), test_bot_register_short_name_returns_422(self, client), test_create_api_key_success(self, client, mock_auth_service), test_create_api_key_no_description(self, client, mock_auth_service), test_create_api_key_forbidden_for_human(self, client, mock_auth_service), test_revoke_api_key_success(self, client, mock_auth_service), test_revoke_api_key_not_found(self, client, mock_auth_service), test_revoke_api_key_not_owner(self, client, mock_auth_service), test_list_api_keys_success(self, client, mock_auth_service), test_list_api_keys_empty(self, client, mock_auth_service)
  test_bot_earnings_routes.py — _PayoutStatus(Enum), _EarningsBalance, _SyncResult, _PayoutRequest, _PaginatedResult, _AttributionEntry, _TestAuthMiddleware(BaseHTTPMiddleware), TestGetEarningsBalance, TestSyncAttributions, TestRequestPayout, TestGetPayoutHistory, TestGetAttributionEntries, test_success_api_key(self), test_forbidden_jwt(self), test_success(self), test_success(self), test_success_with_pagination(self), test_success_with_pagination(self)
  test_campaign_endpoints.py — _TestAuthMiddleware(BaseHTTPMiddleware), TestListLevels, TestGetLevel, TestGetProgress, TestStartAttempt, TestGetAttempt, TestSubmitMove, TestAbandonAttempt, test_list_levels_success(self, client, mock_campaign_service), test_list_levels_includes_level_metadata(self, client, mock_campaign_service), test_get_level_success(self, client), test_progress_success(self, client), test_start_attempt_success(self, client), test_get_attempt_success(self, client, mock_campaign_service), test_get_attempt_not_found(self, client, mock_campaign_service), test_get_attempt_wrong_player(self, client, mock_campaign_service), test_submit_move_success(self, client), test_submit_move_response_structure(self, client), test_abandon_success(self, client)
  test_energy_routes.py — FakeEnergyInfo, FakeLoginResult, FakeStreakInfo, TestGetEnergy, TestRecordLogin, TestGetStreak, test_get_energy_success(self, client, mock_energy_service), test_get_energy_full_hearts(self, client, mock_energy_service), test_get_energy_player_not_found(self, client, mock_energy_service), test_record_login_success(self, client, mock_energy_service), test_record_login_streak_broken(self, client, mock_energy_service), test_record_login_bonus_hearts(self, client, mock_energy_service), test_record_login_service_error(self, client, mock_energy_service), test_get_streak_success(self, client, mock_energy_service), test_get_streak_no_login_history(self, client, mock_energy_service), test_get_streak_player_not_found(self, client, mock_energy_service)
  test_events_routes.py — _EventType(Enum), _EventStatus(Enum), _Event, _EventParticipant, _LeaderboardEntry, _EventLeaderboard, _TestAuthMiddleware(BaseHTTPMiddleware), TestListEvents, TestGetEvent, TestJoinEvent, TestGetLeaderboard, TestGetPlayerEventStatus, test_success_with_list(self), test_success(self), test_not_found(self), test_success(self), test_already_joined(self), test_at_capacity(self), test_success(self), test_success(self), test_not_participant(self)
  test_match_routes.py — _MatchStatus(Enum), _MatchType(Enum), _PlayerMatchState, _MatchState, _MatchSummary, _PaginatedResult, _Position, _Move, _MoveRecord, _FakeBoard, _FakeGrid, _PlayerBoardState, _MoveResult, _RewardResult, _MoveSubmissionResult, _TestAuthMiddleware(BaseHTTPMiddleware), TestGetActiveMatches, TestGetMatch, TestGetMatchState, TestGetBoard, TestSubmitMove, TestForfeitMatch, TestGetMatchHistory, TestGetMoveHistory, test_success_returns_list(self), test_empty_list(self), test_success(self), test_not_found(self), test_jwt_no_bot_hints(self), test_api_key_with_bot_hints(self), test_success(self), test_not_found(self), test_success_valid_move(self), test_validation_error_non_adjacent(self), test_success(self), test_already_completed(self), test_success_with_pagination(self), test_success(self)
  test_matchmaking_routes.py — FakeQueueEntry, FakeQueueStatus, FakeQueueStats, TestJoinQueue, TestLeaveQueue, TestGetQueueStatus, TestGetPoolStats, test_join_queue_success(self, client, mock_matchmaking_service), test_join_queue_human_pool(self, client, mock_matchmaking_service), test_join_queue_bot_pool(self, client, mock_matchmaking_service), test_join_queue_default_pool_type(self, client, mock_matchmaking_service), test_join_queue_already_in_queue(self, client, mock_matchmaking_service), test_join_queue_no_energy(self, client, mock_matchmaking_service), test_leave_queue_success_was_in_queue(self, client, mock_matchmaking_service), test_leave_queue_not_in_queue(self, client, mock_matchmaking_service), test_queue_status_in_queue(self, client, mock_matchmaking_service), test_queue_status_not_in_queue(self, client, mock_matchmaking_service), test_pool_stats_success(self, client, mock_matchmaking_service), test_pool_stats_with_zero_wait(self, client, mock_matchmaking_service), test_pool_stats_service_error(self, client, mock_matchmaking_service)
  test_middleware.py — TestCorrelationMiddleware, TestAuthMiddleware, _FakeAuthToken, _FakeAuthToken, _FakeAuthToken, TestRateLimitMiddleware, _RateStatus, SetApiKeyMiddleware(BaseHTTPMiddleware), TestErrorHandler, TestResolveStatusCode, test_endpoint(request), test_generates_correlation_id_when_none_provided(self, correlation_client), test_preserves_client_provided_correlation_id(self, correlation_client), test_correlation_id_appears_in_response_headers(self, correlation_client), test_client_id_echoed_in_response_header(self, correlation_client), test_generated_id_format(self, correlation_client), test_public_paths_skip_auth(self, auth_client), test_health_path_skips_auth(self, auth_client), test_missing_auth_header_returns_401(self, auth_client), test_invalid_bearer_format_returns_401(self, auth_client), test_valid_jwt_sets_request_state(self, auth_client, mock_auth_service), test_valid_api_key_sets_request_state(self, auth_client, mock_auth_service), test_invalid_token_returns_401(self, auth_client, mock_auth_service), test_invalid_api_key_returns_401(self, auth_client, mock_auth_service), test_api_key_checked_before_jwt(self, auth_client, mock_auth_service), test_health_paths_skip_rate_limiting(self, rate_client), test_rate_limit_exceeded_returns_429(self, rate_client, mock_auth_service), test_rate_limit_not_exceeded_passes_through(self, rate_client, mock_auth_service), test_validation_error_returns_400(self, error_client), test_auth_error_returns_401(self, error_client), test_forbidden_error_returns_403(self, error_client), test_not_found_error_returns_404(self, error_client), test_conflict_error_returns_409(self, error_client), test_rate_limit_error_returns_429(self, error_client), test_unhandled_exception_returns_500(self, error_client), test_error_response_includes_meta(self, error_client), test_unhandled_error_meta_has_correlation_id(self, error_client), test_validation_prefix(self), test_auth_prefix(self), test_forbidden_prefix(self), test_not_found_prefix(self), test_conflict_prefix(self), test_rate_limit_prefix(self), test_internal_prefix(self), test_unknown_prefix_defaults_to_500(self)
  test_payments_routes.py — _PurchaseStatus(Enum), _PaymentProvider(Enum), _PurchaseIntent, _ValidationResult, _RestoredPurchase, _RestoreResult, _PurchaseStatusResult, _PurchaseHistoryResult, _TestAuthMiddleware(BaseHTTPMiddleware), TestInitiatePurchase, TestValidatePurchase, TestRestorePurchases, TestGetPurchaseStatus, test_success_jwt(self), test_forbidden_api_key(self), test_success(self), test_invalid_receipt(self), test_success(self), test_success(self)
  test_player_routes.py — TestGetCurrentPlayer, TestGetPlayerById, TestUpdateCurrentPlayer, TestDeleteCurrentPlayer, TestGetPlayerStats, TestGetLeaderboard, test_get_current_player_success(self, client, mock_player_service), test_get_current_player_not_found(self, client, mock_player_service), test_get_player_by_id_success(self, client, mock_player_service), test_get_player_by_id_not_found(self, client, mock_player_service), test_get_player_by_id_invalid_uuid_format(self, client), test_update_username_success(self, client, mock_player_service), test_update_email_success(self, client, mock_player_service), test_update_invalid_username_returns_422(self, client), test_update_username_too_short_returns_422(self, client), test_update_conflict_username(self, client, mock_player_service), test_delete_success(self, client, mock_player_service), test_delete_player_not_found(self, client, mock_player_service), test_get_stats_success(self, client, mock_player_service), test_get_stats_not_found(self, client, mock_player_service), test_leaderboard_success(self, client, mock_player_service), test_leaderboard_empty(self, client, mock_player_service), test_leaderboard_pagination_params(self, client, mock_player_service), test_leaderboard_invalid_limit_returns_422(self, client)
  test_vault_routes.py — _ArtifactRarity(Enum), _ArtifactDefinition, _VaultArtifact, _Shield, _RaidResult, _CollectionProgress, _PaginatedResult, _VaultSummary, _Player, _PlayersResult, _TestAuthMiddleware(BaseHTTPMiddleware), TestGetArtifacts, TestGetArtifact, TestActivateShield, TestGetShieldStatus, TestAttemptRaid, TestGetCollectionProgress, TestGetRaidTargets, test_success(self), test_empty(self), test_success(self), test_not_found(self), test_success(self), test_already_active(self), test_active_shield(self), test_no_shield(self), test_success(self), test_protected_target(self), test_success(self), test_success_api_key(self), test_forbidden_jwt(self)

**tests/unit/modules/auth/**
  __init__.py
  test_api_key_generator.py — TestGenerateApiKey, TestHashAndVerifyApiKey, test_key_starts_with_prefix(self), test_returns_raw_key_and_hash(self), test_unique_keys_each_call(self), test_hash_verifies_against_raw_key(self), test_custom_prefix(self), test_hash_produces_bcrypt(self), test_verify_correct_key(self), test_verify_wrong_key(self), test_verify_invalid_hash_returns_false(self)
  test_auth_service.py — MockPlayerService, MockPasswordStore, MockSessionRepository, MockApiKeyRepository, TestAuthenticate, TestValidateToken, TestRefreshToken, TestLogout, TestCreateApiKey, TestRevokeApiKey, TestListApiKeys, TestRateLimiting, TestPasswordOperations, TestGetActiveSessions, test_successful_login(self, auth_service, mock_player_service, mock_password_store), test_username_not_found(self, auth_service), test_wrong_password(self, auth_service, mock_player_service, mock_password_store), test_bot_cannot_use_password(self, auth_service, mock_player_service), test_no_password_set(self, auth_service, mock_player_service), test_authorization_header_format(self, auth_service, mock_player_service, mock_password_store), test_valid_jwt_access_token(self, auth_service, mock_player_service, mock_password_store), test_invalid_jwt(self, auth_service), test_jwt_with_revoked_session(self, auth_service, mock_player_service, mock_password_store, mock_session_repo), test_valid_api_key(self, auth_service, mock_player_service, mock_api_key_repo), test_invalid_api_key(self, auth_service), test_revoked_api_key(self, auth_service, mock_player_service), test_successful_refresh(self, auth_service, mock_player_service, mock_password_store), test_refresh_with_already_used_token(self, auth_service, mock_player_service, mock_password_store), test_refresh_with_access_token_fails(self, auth_service, mock_player_service, mock_password_store), test_logout_all_sessions(self, auth_service, mock_player_service, mock_password_store, mock_session_repo), test_logout_nonexistent_player(self, auth_service), test_create_for_bot(self, auth_service, mock_player_service), test_create_for_human_fails(self, auth_service, mock_player_service), test_create_with_long_description_fails(self, auth_service, mock_player_service), test_create_for_nonexistent_player_fails(self, auth_service), test_revoke_own_key(self, auth_service, mock_player_service), test_revoke_nonexistent_key(self, auth_service), test_revoke_not_owner(self, auth_service, mock_player_service), test_list_active_keys(self, auth_service, mock_player_service), test_list_including_revoked(self, auth_service, mock_player_service), test_check_rate_limit_within_limit(self, auth_service, mock_player_service, mock_api_key_repo), test_record_request_decrements_remaining(self, auth_service, mock_player_service), test_rate_limit_exceeded(self, auth_service, mock_player_service, mock_redis), test_check_rate_limit_nonexistent_key(self, auth_service), test_hash_password_valid(self, auth_service), test_hash_password_weak_fails(self, auth_service), test_verify_password_correct(self, auth_service), test_verify_password_incorrect(self, auth_service), test_returns_active_sessions(self, auth_service, mock_player_service, mock_password_store), test_nonexistent_player_raises(self, auth_service)
  test_jwt_handler.py — TestCreateAccessToken, TestCreateRefreshToken, TestDecodeToken, test_creates_valid_jwt(self, handler), test_expiry_is_correct(self, handler), test_creates_refresh_type(self, handler), test_expiry_is_correct(self, handler), test_decode_valid_access_token(self, handler), test_decode_valid_refresh_token(self, handler), test_decode_expired_token_raises(self, handler), test_decode_invalid_signature_raises(self, handler), test_decode_malformed_token_raises(self, handler)
  test_password_handler.py — TestHashPassword, TestVerifyPassword, TestValidatePasswordStrength, test_produces_bcrypt_hash(self), test_different_passwords_different_hashes(self), test_same_password_different_hashes(self), test_respects_rounds_parameter(self), test_correct_password_returns_true(self), test_incorrect_password_returns_false(self), test_invalid_hash_returns_false(self), test_empty_hash_returns_false(self), test_valid_password_passes(self), test_too_short_fails(self), test_no_uppercase_fails(self), test_no_lowercase_fails(self), test_no_digit_fails(self), test_custom_min_length(self)

**tests/unit/modules/board/**
  __init__.py
  test_board_service.py — TestCreateBoard, TestSwapGems, TestDetectMatches, TestClearMatches, TestApplyGravity, TestFillEmpty, TestProcessMove, TestValidateBoard, TestHasValidMoves, test_create_board_dimensions(self, service), test_create_board_no_initial_matches(self, service), test_create_board_deterministic(self, service), test_create_board_different_seeds(self, service), test_create_board_only_standard_gems(self, service), test_create_board_no_matches_multiple_seeds(self, service), test_swap_gems_basic(self, service), test_swap_gems_out_of_bounds(self, service), test_swap_gems_not_adjacent(self, service), test_swap_gems_empty_cell(self, service), test_detect_matches_horizontal_3(self, service), test_detect_matches_vertical_3(self, service), test_detect_matches_no_matches(self, service), test_detect_matches_four_creates_special(self, service), test_detect_matches_five_creates_radial(self, service), test_detect_matches_t_shape_creates_chromatic_orb(self, service), test_detect_matches_only_standard_gems(self, service), test_detect_matches_vertical_four(self, service), test_clear_matches_sets_empty(self, service), test_apply_gravity_drops_gems(self, service), test_apply_gravity_no_change(self, service), test_fill_empty_fills_gaps(self, service), test_fill_empty_deterministic(self, service), test_process_move_valid(self, service), test_process_move_no_match(self, service), test_process_move_deterministic(self, service), test_process_move_board_immutability(self, service), test_validate_board_valid(self, service), test_validate_board_invalid_dimensions(self, service), test_validate_board_invalid_gem_value(self, service), test_has_valid_moves_with_moves(self, service), test_has_valid_moves_deadlock(self, service)

**tests/unit/modules/board_gen/**
  __init__.py
  test_board_gen_service.py — MockSpecialGemsService, TestGenerateBoard, TestGenerateBoardOptions, TestStartingSpecials, TestGenerateBoardForMatch, TestValidateSeed, TestRegenerateFromDeadlock, TestCalculateCascadePotential, TestCascadeTuning, TestValidationErrors, TestSeedEvolution, TestMetadata, TestEdgeCases, test_returns_generated_board(self), test_deterministic_same_seed(self), test_different_seeds_different_boards(self), test_no_initial_matches(self), test_has_valid_moves(self), test_default_dimensions(self), test_metadata_populated(self), test_seed_stored_in_result(self), test_only_standard_gems_by_default(self), test_custom_cascade_potential(self), test_custom_near_miss_factor(self), test_near_miss_disabled_via_config(self), test_zero_near_miss_factor(self), test_gem_distribution_weighted(self), test_custom_dimensions(self), test_explicit_position(self), test_random_position(self), test_too_many_specials_error(self), test_non_special_gem_type_error(self), test_out_of_bounds_position_error(self), test_adjacent_specials_error(self), test_multiple_specials_non_adjacent(self), test_standard(self), test_competitive(self), test_casual_has_starting_special(self), test_tutorial_low_near_miss(self), test_all_types_produce_valid_boards(self), test_competitive_deterministic(self), test_normal_seed_valid(self), test_multiple_seeds_valid(self), test_deterministic(self), test_preserves_special_gems(self), test_produces_valid_board(self), test_metadata_populated(self), test_deterministic(self), test_returns_float_in_range(self), test_different_boards_different_potentials(self), test_uniform_board_has_low_potential(self), test_higher_target_higher_actual(self), test_cascade_potential_too_high(self), test_cascade_potential_negative(self), test_near_miss_too_high(self), test_near_miss_negative(self), test_invalid_gem_distribution_zero_weights(self), test_invalid_gem_distribution_negative_weights(self), test_dimensions_too_small(self), test_evolve_seed_deterministic(self), test_evolve_seed_different(self), test_evolve_seed_chain(self), test_evolve_seed_positive(self), test_timing_positive(self), test_attempts_at_least_one(self), test_valid_moves_positive(self), test_cascade_potential_in_range(self), test_dimensions_match_options(self), test_seed_zero(self), test_large_seed(self), test_small_board_3x3(self), test_large_board_12x12(self), test_cascade_potential_boundary_zero(self), test_cascade_potential_boundary_one(self), test_near_miss_boundary_one(self)

**tests/unit/modules/bot_earnings/**
  __init__.py
  test_bot_earnings_service.py — test_get_earnings_balance_success(), test_get_earnings_balance_no_ledger(), test_get_earnings_balance_not_bot(), test_get_earnings_summary_success(), test_get_earnings_summary_not_bot(), test_get_attribution_entries_success(), test_get_attribution_entries_invalid_limit(), test_get_attribution_entries_invalid_date_range(), test_get_daily_earnings_success(), test_get_daily_earnings_date_range_too_large(), test_get_daily_earnings_end_before_start(), test_sync_attributions_success(), test_sync_attributions_no_new_data(), test_sync_attributions_not_bot(), test_sync_attributions_ads_error(), test_sync_attributions_dedup(), test_sync_all_attributions_success(), test_sync_all_attributions_partial_failure(), test_request_payout_success(), test_request_payout_not_bot(), test_request_payout_no_ledger(), test_request_payout_not_owner(), test_request_payout_pending_exists(), test_request_payout_below_threshold(), test_get_payout_requests_success(), test_get_payout_requests_not_bot(), test_get_payout_request_success(), test_get_payout_request_not_found(), test_cancel_payout_request_success(), test_cancel_payout_request_not_found(), test_cancel_payout_not_pending(), test_cancel_payout_not_owner(), test_process_payout_success(), test_process_payout_not_found(), test_process_payout_not_pending(), test_process_payout_ref_too_long(), test_reject_payout_success(), test_reject_payout_empty_reason(), test_reject_payout_reason_too_long(), test_reject_payout_not_found(), test_reject_payout_not_pending(), test_get_bot_owner_from_ledger(), test_get_bot_owner_no_ledger(), test_get_bot_owner_not_bot(), test_pagination_negative_offset(), test_pagination_zero_limit()

**tests/unit/modules/cards/**
  __init__.py
  test_card_service.py — FakePlayerCardRecord, MockPlayerCardRepository, MockPlayerService, TestCardDefinitions, TestGrantAndCollection, TestEquipUnequip, TestMerge, TestRemove, test_get_card_definition(self, card_service), test_get_card_definition_not_found(self, card_service), test_list_definitions_all(self, card_service), test_list_definitions_by_rarity(self, card_service), test_grant_card(self, card_service, player_id), test_grant_card_increments_position(self, card_service, player_id), test_grant_nonexistent_card_fails(self, card_service, player_id), test_get_player_cards(self, card_service, player_id), test_equip_card(self, card_service, player_id), test_equip_swaps_with_occupant(self, card_service, player_id), test_equip_invalid_slot_fails(self, card_service, player_id), test_equip_card_not_owned_fails(self, card_service, player_id), test_unequip_card(self, card_service, player_id), test_unequip_non_equipped_card_fails(self, card_service, player_id), test_merge_success(self, card_service, player_id), test_merge_not_enough_cards_fails(self, card_service, player_id), test_merge_mixed_rarities_fails(self, card_service, player_id), test_merge_legendary_fails(self, card_service, player_id), test_merge_clears_equipped(self, card_service, player_id), test_remove_card(self, card_service, player_id), test_remove_nonexistent_card_fails(self, card_service, player_id)

**tests/unit/modules/energy/**
  __init__.py
  test_energy_service.py — MockPlayerService, MockEnergyRepo, TestGetEnergy, TestConsumeHeart, TestCanPlay, TestApplyPendingRegeneration, TestGetTimeToNextHeart, TestRecordLogin, TestGetStreak, TestGrantBonusHearts, TestRefundHeart, test_basic_get(self, energy_service, mock_player_service), test_get_with_pending_regen(self, energy_service, mock_player_service), test_get_at_max(self, energy_service, mock_player_service), test_get_player_not_found(self, energy_service), test_consume_success(self, energy_service, mock_player_service), test_consume_insufficient_hearts(self, energy_service, mock_player_service), test_consume_with_regen_first(self, energy_service, mock_player_service), test_consume_amount_greater_than_one(self, energy_service, mock_player_service), test_consume_invalid_amount(self, energy_service, mock_player_service), test_consume_exact_hearts(self, energy_service, mock_player_service), test_can_play_with_energy(self, energy_service, mock_player_service), test_cannot_play_no_energy(self, energy_service, mock_player_service), test_can_play_after_regen(self, energy_service, mock_player_service), test_regen_with_pending(self, energy_service, mock_player_service), test_no_regen_pending(self, energy_service, mock_player_service), test_regen_at_max(self, energy_service, mock_player_service), test_regen_capped_at_max(self, energy_service, mock_player_service), test_is_full(self, energy_service, mock_player_service), test_time_remaining(self, energy_service, mock_player_service), test_first_login(self, energy_service, mock_player_service), test_consecutive_day_login(self, energy_service, mock_player_service), test_streak_break(self, energy_service, mock_player_service), test_same_day_login(self, energy_service, mock_player_service), test_login_with_streak_reward(self, energy_service, mock_player_service), test_login_with_day_14_reward(self, energy_service, mock_player_service), test_basic_streak_info(self, energy_service, mock_player_service), test_streak_started_at(self, energy_service, mock_player_service), test_grant_success(self, energy_service, mock_player_service), test_grant_overflow(self, energy_service, mock_player_service), test_grant_capped_at_overflow_limit(self, energy_service, mock_player_service), test_grant_idempotency_new(self, energy_service, mock_player_service, mock_redis), test_grant_idempotency_duplicate(self, energy_service, mock_player_service, mock_redis), test_grant_invalid_amount(self, energy_service, mock_player_service), test_grant_without_idempotency_key(self, energy_service, mock_player_service, mock_redis), test_basic_refund(self, energy_service, mock_player_service), test_refund_capped_at_max(self, energy_service, mock_player_service), test_refund_multiple(self, energy_service, mock_player_service), test_refund_capped_from_partial(self, energy_service, mock_player_service), test_refund_player_not_found(self, energy_service), test_refund_logs_reason(self, energy_service, mock_player_service, mock_logger)
  test_regen.py — TestCalculateRegeneratedHearts, TestCalculateTimeToNextHeart, test_no_regen_when_at_max(self), test_one_heart_after_one_interval(self), test_three_hearts_after_three_intervals(self), test_capped_at_max_hearts(self), test_partial_interval_preserved(self), test_no_regen_less_than_one_interval(self), test_zero_current_hearts(self), test_above_max_hearts_no_regen(self), test_negative_elapsed_time(self), test_exact_boundary_timing(self), test_none_when_at_max(self), test_full_interval_remaining(self), test_partial_time_remaining(self), test_just_before_regen(self), test_none_when_above_max(self)
  test_streak.py — TestCalculateStreakUpdate, TestCalculateStreakReward, TestCalculateNextRewardThreshold, test_first_login(self), test_same_day_no_change(self), test_consecutive_day_increments(self), test_two_days_missed_breaks_streak(self), test_many_days_missed_breaks_streak(self), test_streak_increment_from_one(self), test_no_reward_at_day_1(self), test_no_reward_at_day_6(self), test_reward_at_day_7(self), test_reward_at_day_14(self), test_reward_at_day_30(self), test_no_reward_at_day_31(self), test_repeat_reward_at_day_37(self), test_repeat_reward_at_day_44(self), test_no_reward_between_repeats(self), test_custom_thresholds(self), test_streak_0(self), test_streak_3(self), test_streak_7(self), test_streak_10(self), test_streak_14(self), test_streak_20(self), test_streak_30(self), test_streak_37(self), test_streak_35(self)

**tests/unit/modules/events/**
  __init__.py
  test_event_service.py — TestCreateEvent, TestGetEvent, TestListEvents, TestGetActiveEvents, TestJoinEvent, TestLeaveEvent, TestRecordEventMatch, TestGetLeaderboard, TestGetPlayerRank, TestGetPlayerEvents, TestGetEventParticipant, TestFinalizeEvent, TestCancelEvent, TestUpdateEvent, TestProcessScheduledEvents, TestHelperBehavior, test_create_event_success(self, event_service, mock_event_repo), test_create_event_name_too_short(self, event_service), test_create_event_name_too_long(self, event_service), test_create_event_end_before_start(self, event_service), test_create_event_empty_name(self, event_service), test_get_event_success(self, event_service, mock_event_repo), test_get_event_not_found(self, event_service, mock_event_repo), test_list_events_success(self, event_service, mock_event_repo), test_list_events_empty(self, event_service, mock_event_repo), test_list_events_invalid_limit_low(self, event_service), test_list_events_invalid_limit_high(self, event_service), test_list_events_with_status_filter(self, event_service, mock_event_repo), test_list_events_with_type_filter(self, event_service, mock_event_repo), test_get_active_events_success(self, event_service, mock_event_repo), test_get_active_events_empty(self, event_service, mock_event_repo), test_join_event_success(self, event_service, mock_event_repo, mock_participant_repo, mock_leaderboard_repo, mock_player_service), test_join_event_not_found(self, event_service, mock_event_repo), test_join_event_not_active(self, event_service, mock_event_repo), test_join_event_already_participant(self, event_service, mock_event_repo, mock_participant_repo), test_join_event_at_capacity(self, event_service, mock_event_repo, mock_participant_repo), test_join_event_race_condition_rollback(self, event_service, mock_event_repo, mock_participant_repo, mock_energy_service, mock_player_service), test_join_event_with_energy_cost(self, event_service, mock_event_repo, mock_participant_repo, mock_energy_service, mock_leaderboard_repo, mock_player_service), test_join_event_insufficient_energy(self, event_service, mock_event_repo, mock_participant_repo, mock_energy_service, mock_player_service), test_join_event_min_elo_requirement(self, event_service, mock_event_repo, mock_participant_repo, mock_player_service), test_join_event_max_elo_requirement(self, event_service, mock_event_repo, mock_participant_repo, mock_player_service), test_leave_event_success(self, event_service, mock_event_repo, mock_participant_repo, mock_leaderboard_repo), test_leave_event_not_found(self, event_service, mock_event_repo), test_leave_event_not_participant(self, event_service, mock_event_repo, mock_participant_repo), test_leave_event_already_left(self, event_service, mock_event_repo, mock_participant_repo), test_leave_event_after_match_forbidden(self, event_service, mock_event_repo, mock_participant_repo), test_leave_event_after_match_allowed_with_config(self, mock_logger, mock_errors, mock_data_ctx, mock_vault_service, mock_energy_service, mock_match_service, mock_player_service, mock_event_repo, mock_participant_repo, mock_leaderboard_repo), test_record_match_success(self, event_service, mock_event_repo, mock_participant_repo, mock_leaderboard_repo, mock_player_service), test_record_match_event_not_found(self, event_service, mock_event_repo), test_record_match_event_not_active(self, event_service, mock_event_repo), test_record_match_not_participant(self, event_service, mock_event_repo, mock_participant_repo), test_record_match_max_matches_reached(self, event_service, mock_event_repo, mock_participant_repo), test_record_match_scoring_multiplier(self, event_service, mock_event_repo, mock_participant_repo, mock_leaderboard_repo, mock_player_service), test_record_match_bonus_condition_met(self, event_service, mock_event_repo, mock_participant_repo, mock_leaderboard_repo, mock_player_service), test_record_match_bonus_condition_not_met(self, event_service, mock_event_repo, mock_participant_repo, mock_leaderboard_repo, mock_player_service), test_record_match_best_match_scoring(self, event_service, mock_event_repo, mock_participant_repo, mock_leaderboard_repo, mock_player_service), test_record_match_matches_played_scoring(self, event_service, mock_event_repo, mock_participant_repo, mock_leaderboard_repo, mock_player_service), test_get_leaderboard_success(self, event_service, mock_event_repo, mock_leaderboard_repo, mock_participant_repo, mock_player_service), test_get_leaderboard_not_found(self, event_service, mock_event_repo), test_get_leaderboard_invalid_limit(self, event_service), test_get_leaderboard_fallback_to_db(self, event_service, mock_event_repo, mock_leaderboard_repo, mock_participant_repo, mock_player_service), test_get_player_rank_success(self, event_service, mock_event_repo, mock_participant_repo, mock_leaderboard_repo), test_get_player_rank_event_not_found(self, event_service, mock_event_repo), test_get_player_rank_not_participant(self, event_service, mock_event_repo, mock_participant_repo), test_get_player_events_success(self, event_service, mock_participant_repo, mock_event_repo, mock_player_service), test_get_player_events_empty(self, event_service, mock_participant_repo, mock_player_service), test_get_player_events_invalid_limit(self, event_service), test_get_event_participant_success(self, event_service, mock_event_repo, mock_participant_repo, mock_player_service), test_get_event_participant_event_not_found(self, event_service, mock_event_repo), test_get_event_participant_not_found(self, event_service, mock_event_repo, mock_participant_repo), test_finalize_event_success(self, event_service, mock_event_repo, mock_participant_repo, mock_leaderboard_repo, mock_player_service), test_finalize_event_not_found(self, event_service, mock_event_repo), test_finalize_event_already_finalized(self, event_service, mock_event_repo), test_finalize_event_wrong_status(self, event_service, mock_event_repo), test_finalize_event_no_eligible(self, event_service, mock_event_repo, mock_participant_repo, mock_leaderboard_repo), test_finalize_event_artifact_reward(self, event_service, mock_event_repo, mock_participant_repo, mock_leaderboard_repo, mock_vault_service, mock_player_service), test_finalize_event_elo_bonus_reward(self, event_service, mock_event_repo, mock_participant_repo, mock_leaderboard_repo, mock_player_service), test_cancel_event_success(self, event_service, mock_event_repo, mock_leaderboard_repo), test_cancel_event_not_found(self, event_service, mock_event_repo), test_cancel_event_already_finalized(self, event_service, mock_event_repo), test_cancel_event_reason_too_long(self, event_service), test_cancel_event_refunds_energy(self, event_service, mock_event_repo, mock_participant_repo, mock_energy_service, mock_leaderboard_repo), test_update_event_success(self, event_service, mock_event_repo), test_update_event_not_found(self, event_service, mock_event_repo), test_process_activates_scheduled(self, event_service, mock_event_repo, mock_data_ctx), test_process_deactivates_active(self, event_service, mock_event_repo, mock_data_ctx), test_process_finalizes_ended(self, event_service, mock_event_repo, mock_participant_repo, mock_leaderboard_repo), test_process_no_events(self, event_service, mock_event_repo), test_process_activation_error_handled(self, event_service, mock_event_repo, mock_logger), test_record_to_event_parses_jsonb_fields(self, event_service, mock_event_repo), test_event_summary_time_remaining(self, event_service, mock_event_repo), test_event_summary_no_time_remaining_for_scheduled(self, event_service, mock_event_repo), test_calculate_level_from_stats(self, event_service, mock_event_repo, mock_participant_repo, mock_player_service), test_participant_average_score_calculation(self, event_service, mock_event_repo, mock_participant_repo, mock_player_service), test_participant_zero_matches_average_score(self, event_service, mock_event_repo, mock_participant_repo, mock_player_service), test_special_gems_bonus_condition(self, event_service, mock_event_repo, mock_participant_repo, mock_leaderboard_repo, mock_player_service), test_time_bonus_condition(self, event_service, mock_event_repo, mock_participant_repo, mock_leaderboard_repo, mock_player_service), test_determine_reward_tier_by_percentile(self, event_service, mock_event_repo, mock_participant_repo, mock_leaderboard_repo, mock_player_service), test_player_type_requirement_filter(self, event_service, mock_event_repo, mock_participant_repo, mock_player_service), test_logging_on_create_event(self, event_service, mock_event_repo, mock_logger), test_logging_on_cancel_event(self, event_service, mock_event_repo, mock_leaderboard_repo, mock_logger)

**tests/unit/modules/match/**
  __init__.py
  test_match_service.py — TestCreateMatch, TestSubmitMove, TestGetMatch, TestGetMatchState, TestGetPlayerBoard, TestGetActiveMatches, TestForfeitMatch, TestGetMatchHistory, TestGetMoveHistory, TestAbandonStaleMatches, TestFinalizeMatch, TestEdgeCases, test_create_match_success(self, match_service, mock_match_repo, mock_player_service, mock_energy_service), test_create_match_same_player_raises(self, match_service), test_create_match_player1_not_found(self, match_service, mock_player_service, mock_errors), test_create_match_player2_not_found(self, match_service, mock_player_service), test_create_match_concurrent_limit_player1(self, match_service, mock_match_repo), test_create_match_concurrent_limit_player2(self, match_service, mock_match_repo), test_create_match_insufficient_energy_player1(self, match_service, mock_energy_service), test_create_match_insufficient_energy_player2(self, match_service, mock_energy_service), test_create_match_custom_seed(self, match_service, mock_match_repo, mock_board_gen_service), test_create_match_custom_match_type(self, match_service, mock_match_repo, mock_board_gen_service), test_create_match_energy_consumed(self, match_service, mock_match_repo, mock_energy_service), test_create_match_concurrent_allowed(self, mock_logger, mock_errors, mock_data_ctx, mock_board_gen_service, mock_board_service, mock_scoring_service, mock_special_gems_service, mock_player_service, mock_auth_service, mock_energy_service, mock_match_repo, mock_move_repo), test_submit_move_success(self, match_service, mock_match_repo, mock_player_service, mock_move_repo), test_submit_move_match_not_found(self, match_service, mock_match_repo), test_submit_move_not_participant(self, match_service, mock_match_repo, mock_player_service), test_submit_move_match_completed(self, match_service, mock_match_repo, mock_player_service), test_submit_move_match_abandoned(self, match_service, mock_match_repo, mock_player_service), test_submit_move_no_moves_remaining(self, match_service, mock_match_repo, mock_player_service), test_submit_move_invalid_swap(self, match_service, mock_match_repo, mock_player_service, mock_board_service), test_submit_move_updates_score(self, match_service, mock_match_repo, mock_player_service, mock_scoring_service), test_submit_move_decrements_moves(self, match_service, mock_match_repo, mock_player_service), test_submit_move_transitions_pending_to_in_progress(self, match_service, mock_match_repo, mock_player_service), test_submit_move_player1_finishes(self, match_service, mock_match_repo, mock_player_service), test_submit_move_player2_finishes(self, match_service, mock_match_repo, mock_player_service), test_submit_move_both_finish_determines_winner(self, match_service, mock_match_repo, mock_player_service, mock_scoring_service), test_submit_move_both_finish_draw(self, match_service, mock_match_repo, mock_player_service, mock_scoring_service), test_submit_move_updates_longest_chain(self, match_service, mock_match_repo, mock_player_service, mock_board_service), test_submit_move_persists_move_record(self, match_service, mock_match_repo, mock_player_service, mock_move_repo), test_submit_move_special_gem_processing(self, match_service, mock_match_repo, mock_player_service, mock_board_service, mock_special_gems_service, mock_scoring_service), test_submit_move_deadlock_reshuffle(self, match_service, mock_match_repo, mock_player_service, mock_board_service, mock_board_gen_service), test_get_match_success(self, match_service, mock_match_repo), test_get_match_not_found(self, match_service, mock_match_repo), test_get_match_state_success(self, match_service, mock_match_repo), test_get_match_state_not_participant(self, match_service, mock_match_repo), test_get_player_board_player1(self, match_service, mock_match_repo, mock_board_service), test_get_player_board_player2(self, match_service, mock_match_repo, mock_board_service), test_get_player_board_not_found(self, match_service, mock_match_repo), test_get_player_board_not_participant(self, match_service, mock_match_repo), test_get_active_matches_success(self, match_service, mock_match_repo), test_get_active_matches_empty(self, match_service, mock_match_repo), test_forfeit_match_player1_forfeits(self, match_service, mock_match_repo, mock_player_service), test_forfeit_match_player2_forfeits(self, match_service, mock_match_repo, mock_player_service), test_forfeit_match_not_found(self, match_service, mock_match_repo), test_forfeit_match_not_participant(self, match_service, mock_match_repo), test_forfeit_match_already_completed(self, match_service, mock_match_repo), test_get_match_history_success(self, match_service, mock_match_repo, mock_player_service), test_get_match_history_invalid_limit_too_low(self, match_service), test_get_match_history_invalid_limit_too_high(self, match_service), test_get_match_history_empty(self, match_service, mock_match_repo), test_get_match_history_win_loss_draw(self, match_service, mock_match_repo, mock_player_service), test_get_move_history_success(self, match_service, mock_match_repo, mock_move_repo), test_get_move_history_not_found(self, match_service, mock_match_repo), test_get_move_history_filtered_by_player(self, match_service, mock_match_repo, mock_move_repo), test_abandon_stale_matches_success(self, match_service, mock_match_repo), test_abandon_stale_matches_none_stale(self, match_service, mock_match_repo), test_finalize_records_match_result_for_both_players(self, match_service, mock_match_repo, mock_player_service, mock_scoring_service), test_finalize_updates_elo_for_winner_and_loser(self, match_service, mock_match_repo, mock_player_service, mock_scoring_service), test_finalize_updates_elo_for_draw(self, match_service, mock_match_repo, mock_player_service, mock_scoring_service), test_forfeit_calls_finalize(self, match_service, mock_match_repo, mock_player_service), test_submit_move_player2_completes_match_p2_wins(self, match_service, mock_match_repo, mock_player_service, mock_scoring_service), test_submit_move_chain_not_updated_when_lower(self, match_service, mock_match_repo, mock_player_service, mock_board_service), test_submit_move_no_deadlock_reshuffle_when_no_moves_remain(self, match_service, mock_match_repo, mock_player_service, mock_board_service, mock_board_gen_service), test_create_match_generates_random_seed_when_none(self, match_service, mock_match_repo, mock_board_gen_service), test_get_match_state_without_player_validation(self, match_service, mock_match_repo), test_get_move_history_with_special_gems(self, match_service, mock_match_repo, mock_move_repo), test_submit_move_move_number_increments(self, match_service, mock_match_repo, mock_player_service), test_forfeit_abandoned_match_raises(self, match_service, mock_match_repo)

**tests/unit/modules/matchmaking/**
  __init__.py
  test_matchmaking_service.py — TestJoinQueue, TestLeaveQueue, TestGetQueueStatus, TestFindMatch, TestProcessQueue, TestCleanupStaleEntries, TestGetQueueStats, TestEloRangeExpansion, TestConfiguration, TestQueuePositionAndEstimation, TestErrorPropagation, TestEdgeCases, test_join_queue_success(self), test_join_queue_default_pool(self), test_join_queue_human_pool(self), test_join_queue_bot_in_human_pool_forbidden(self), test_join_queue_human_in_bot_pool_forbidden(self), test_join_queue_bot_in_bot_pool_success(self), test_join_queue_already_in_queue(self), test_join_queue_player_in_active_match(self), test_join_queue_player_not_found(self), test_join_queue_bot_in_mixed_pool_success(self), test_join_queue_logs_event(self), test_leave_queue_success(self), test_leave_queue_not_in_queue(self), test_leave_queue_logs_event(self), test_leave_queue_no_log_when_not_in_queue(self), test_get_queue_status_in_queue(self), test_get_queue_status_not_in_queue(self), test_get_queue_status_wait_time(self), test_find_match_success(self), test_find_match_not_in_queue(self), test_find_match_timeout(self), test_find_match_no_opponents(self), test_find_match_opponent_taken(self), test_find_match_tries_multiple_opponents(self), test_find_match_creation_fails_compensates(self), test_find_match_logs_match_found(self), test_find_match_logs_timeout(self), test_process_queue_empty(self), test_process_queue_single_player(self), test_process_queue_two_players_matched(self), test_process_queue_four_players_two_matches(self), test_process_queue_skips_already_matched(self), test_process_queue_logs_summary(self), test_cleanup_no_stale_entries(self), test_cleanup_removes_stale_entries(self), test_cleanup_logs_when_entries_removed(self), test_cleanup_no_log_when_zero(self), test_cleanup_uses_correct_cutoff(self), test_get_stats_specific_pool(self), test_get_stats_all_pools(self), test_get_stats_empty_queue(self), test_get_stats_calculates_wait_times(self), test_no_expansion_before_min_wait(self), test_no_expansion_before_interval(self), test_expansion_triggered(self), test_no_expansion_at_max_range(self), test_expansion_logs_debug(self), test_custom_initial_elo_range(self), test_custom_timeout(self), test_position_first_in_queue(self), test_position_third_in_queue(self), test_estimate_none_for_empty_queue(self), test_estimate_returns_int_for_populated_queue(self), test_player_not_found_propagates(self), test_forbidden_error_has_context(self), test_conflict_error_includes_match_id(self), test_internal_error_on_match_creation_failure(self), test_ec4_player_cannot_be_in_multiple_queues(self), test_ec6_bot_in_human_pool_rejected(self), test_ec8_empty_queue_returns_searching(self), test_ec3_match_creation_fails_compensates(self), test_ec2_atomic_remove_handles_race(self), test_leave_queue_idempotent(self), test_find_match_player_removed_between_expansion_and_search(self)

**tests/unit/modules/payments/**
  __init__.py
  test_payment_service.py — test_initiate_purchase_success(), test_initiate_purchase_player_not_found(), test_initiate_purchase_product_not_found(), test_validate_purchase_success(), test_validate_purchase_player_already_ad_free(), test_validate_purchase_duplicate_receipt(), test_validate_purchase_provider_error(), test_validate_purchase_invalid_receipt(), test_validate_purchase_wrong_product(), test_get_purchase_status_no_purchases(), test_get_purchase_status_with_purchase(), test_get_purchase_status_player_not_found(), test_get_purchase_history_success(), test_get_purchase_history_invalid_limit(), test_get_purchase_history_negative_offset(), test_process_refund_success(), test_process_refund_purchase_not_found(), test_process_refund_already_refunded(), test_process_refund_fallback_to_original_transaction(), test_process_refund_revoke_failure_still_succeeds(), test_restore_purchases_success(), test_restore_purchases_already_active(), test_restore_purchases_invalid_receipt(), test_restore_purchases_provider_error_counts_invalid(), test_get_products_success(), test_get_products_empty(), test_verify_webhook_signature_valid(), test_verify_webhook_signature_invalid(), test_verify_webhook_signature_error(), test_hash_receipt_deterministic(), test_hash_receipt_different_data()

**tests/unit/modules/player/**
  __init__.py
  test_elo.py — TestCalculateExpectedScore, TestCalculateEloChange, test_equal_ratings(self), test_higher_rated_has_higher_expected(self), test_lower_rated_has_lower_expected(self), test_expected_scores_sum_to_one(self), test_large_rating_gap(self), test_equal_ratings_win(self), test_equal_ratings_draw(self), test_higher_rated_wins_less(self), test_lower_rated_wins_more(self), test_changes_sum_to_zero(self), test_draw_changes_sum_to_zero(self), test_draw_higher_rated_loses_points(self), test_different_k_factor(self)
  test_player_service.py — MockPlayerRepository, MockPlayerStatsRepository, MockEnergyStateRepository, TestCreatePlayer, TestGetPlayer, TestGetPlayerByUsername, TestUpdatePlayer, TestSoftDeletePlayer, TestListPlayers, TestEloOperations, TestStatsOperations, TestEnergyStateOperations, test_create_player_human(self, player_service), test_create_player_bot(self, player_service), test_create_player_bot_with_password_rejected(self, player_service), test_create_player_duplicate_username(self, player_service), test_create_player_invalid_username(self, player_service), test_create_player_initializes_stats(self, player_service, stats_repo), test_create_player_initializes_energy(self, player_service, energy_repo), test_get_player_found(self, player_service), test_get_player_not_found(self, player_service), test_found(self, player_service), test_not_found(self, player_service), test_update_username(self, player_service), test_update_no_changes(self, player_service), test_soft_delete(self, player_service), test_list_all(self, player_service), test_list_with_type_filter(self, player_service), test_list_invalid_limit(self, player_service), test_get_elo(self, player_service), test_update_elo(self, player_service), test_update_elo_negative_rejected(self, player_service), test_calculate_elo_change(self, player_service), test_calculate_elo_change_same_player(self, player_service), test_get_stats(self, player_service), test_record_match_result_win(self, player_service), test_record_match_result_loss(self, player_service), test_record_match_result_draw(self, player_service), test_record_match_result_updates_highest_score(self, player_service), test_record_match_result_accumulates_gems(self, player_service), test_get_energy_state(self, player_service), test_update_energy_state(self, player_service), test_update_energy_state_negative_hearts_rejected(self, player_service), test_update_energy_state_over_max_rejected(self, player_service), test_update_energy_state_no_changes(self, player_service), test_initialize_energy_state(self, player_service)
  test_validation.py — TestValidateUsername, test_valid_username(self), test_valid_with_underscores(self), test_valid_minimum_length(self), test_valid_maximum_length(self), test_too_short(self), test_too_long(self), test_invalid_chars_spaces(self), test_invalid_chars_special(self), test_invalid_chars_hyphen(self), test_empty_string(self), test_all_numbers(self), test_all_underscores(self), test_custom_constraints(self)

**tests/unit/modules/scoring/**
  __init__.py
  test_scoring_service.py — TestCalculateMatchScore, TestCalculateMoveScore, TestCalculateSpecialGemBonus, TestMultiplierLookups, TestConfiguration, TestGetBasePoints, TestMoveScoreSummary, TestCombinedScoring, test_single_3_match(self, service), test_4_match_length_multiplier(self, service), test_5_match_length_multiplier(self, service), test_multiple_match_groups(self, service), test_chain_step_2_multiplier(self, service), test_chain_step_5_plus_capped(self, service), test_special_gem_creation_bonus(self, service), test_empty_matches_raises_error(self, service), test_chain_step_zero_raises_error(self, service), test_chain_step_negative_raises_error(self, service), test_single_cascade_step(self, service), test_triple_cascade(self, service), test_invalid_move_raises_error(self, service), test_total_gems_cleared_accumulated(self, service), test_highest_chain_multiplier_tracked(self, service), test_special_gems_created_counted(self, service), test_line_blast_h(self, service), test_line_blast_v(self, service), test_radial_bomb(self, service), test_chromatic_orb(self, service), test_non_special_gem_raises_error(self, service), test_gems_affected_zero_gives_base_only(self, service), test_negative_gems_affected_raises_error(self, service), test_empty_gem_type_raises_error(self, service), test_chain_multiplier_step_1(self, service), test_chain_multiplier_step_2(self, service), test_chain_multiplier_step_3(self, service), test_chain_multiplier_step_4(self, service), test_chain_multiplier_step_5(self, service), test_chain_multiplier_step_beyond_cap(self, service), test_chain_multiplier_invalid_raises(self, service), test_length_multiplier_3(self, service), test_length_multiplier_4(self, service), test_length_multiplier_5(self, service), test_length_multiplier_6(self, service), test_length_multiplier_7(self, service), test_length_multiplier_beyond_cap(self, service), test_length_multiplier_invalid_raises(self, service), test_custom_base_points(self, logger, errors), test_custom_chain_multipliers(self, logger, errors), test_custom_length_multipliers(self, logger, errors), test_negative_base_points_falls_back_to_default(self, logger, errors), test_zero_base_points_falls_back_to_default(self, logger, errors), test_custom_special_gem_config(self, logger, errors), test_standard_gem_returns_base_points(self, service), test_empty_gem_type_raises_error(self, service), test_special_gem_type_raises_error(self, service), test_summary_single_match(self, service), test_summary_double_chain(self, service), test_summary_triple_chain(self, service), test_summary_with_special_gems(self, service), test_4_match_chain_2_with_special(self, service), test_two_groups_different_lengths(self, service), test_frozen_types_immutable(self, service)

**tests/unit/modules/special_gems/**
  __init__.py
  test_special_gems_service.py — MockScoringService, TestIsSpecialGem, TestCalculateEffectLineBlastH, TestCalculateEffectLineBlastV, TestCalculateEffectRadialBomb, TestCalculateEffectChromaticOrb, TestCalculateEffectValidation, TestFusionCrossBlast, TestFusionTripleLine, TestFusionMegaBomb, TestFusionColorLineBlast, TestFusionColorBomb, TestFusionBoardClear, TestFusionValidation, TestApplyEffect, TestGetSpecialGemForMatch, TestFindTriggeredSpecialGems, TestEdgeCases, TestSpecialGemTypesConstant, test_line_blast_h_is_special(self, service), test_line_blast_v_is_special(self, service), test_radial_bomb_is_special(self, service), test_chromatic_orb_is_special(self, service), test_red_not_special(self, service), test_empty_not_special(self, service), test_blue_not_special(self, service), test_orange_not_special(self, service), test_clears_entire_row(self, service), test_description_mentions_row(self, service), test_bonus_score_calculated(self, service), test_detects_triggered_specials_in_row(self, service), test_clears_entire_column(self, service), test_description_mentions_column(self, service), test_detects_triggered_specials_in_column(self, service), test_clears_3x3_area_center(self, service), test_description_mentions_3x3(self, service), test_radial_bomb_at_corner(self, service), test_radial_bomb_at_edge(self, service), test_detects_triggered_specials_in_area(self, service), test_clears_all_target_color_gems(self, service), test_orb_itself_included_in_affected(self, service), test_description_mentions_color(self, service), test_out_of_bounds_raises(self, service), test_not_special_gem_raises(self, service), test_chromatic_without_target_raises(self, service), test_chromatic_with_invalid_target_raises(self, service), test_chromatic_with_special_gem_target_raises(self, service), test_line_blast_at_row_0(self, service), test_line_blast_at_last_column(self, service), test_cross_blast_clears_row_and_column(self, service), test_cross_blast_description(self, service), test_cross_blast_same_type(self, service), test_triple_line_horizontal(self, service), test_triple_line_vertical(self, service), test_triple_line_at_edge_clips(self, service), test_mega_bomb_5x5(self, service), test_mega_bomb_description(self, service), test_mega_bomb_at_corner(self, service), test_color_line_blast_horizontal(self, service), test_color_line_blast_requires_target(self, service), test_color_bomb(self, service), test_color_bomb_requires_target(self, service), test_board_clear(self, service), test_board_clear_description(self, service), test_not_adjacent_raises(self, service), test_first_not_special_raises(self, service), test_second_not_special_raises(self, service), test_out_of_bounds_raises(self, service), test_fusion_normalizes_order(self, service), test_apply_special_gem_effect_clears_positions(self, service), test_apply_effect_does_not_modify_original(self, service), test_apply_fusion_effect_clears_all(self, service), test_apply_effect_with_secondary_effects(self, service), test_apply_radial_bomb_effect(self, service), test_3_match_returns_none(self, service), test_4_horizontal_returns_line_blast_h(self, service), test_4_vertical_returns_line_blast_v(self, service), test_5_match_returns_radial_bomb(self, service), test_6_match_returns_radial_bomb(self, service), test_t_shape_returns_chromatic_orb(self, service), test_l_shape_returns_chromatic_orb(self, service), test_empty_matches_raises(self, service), test_t_shape_picks_first_overlap_deterministically(self, service), test_finds_specials_in_cleared_area(self, service), test_does_not_find_standard_gems(self, service), test_sorted_by_row_col(self, service), test_respects_chain_reaction_disabled(self, logger, errors, scoring), test_empty_cleared_set(self, service), test_out_of_bounds_positions_ignored(self, service), test_small_board(self, logger, errors, scoring), test_chromatic_orb_no_matching_color(self, service), test_line_blast_chain_reaction_disabled(self, logger, errors, scoring), test_custom_radial_bomb_radius(self, logger, errors, scoring), test_custom_mega_bomb_radius(self, logger, errors, scoring), test_custom_triple_line_count(self, logger, errors, scoring), test_apply_effect_returns_new_board_state(self, service), test_find_center_even_positions(self, service), test_find_center_odd_positions(self, service), test_fusion_board_clear_on_small_board(self, logger, errors, scoring), test_all_6_standard_colors_are_valid_targets(self, service), test_contains_all_special_types(self), test_does_not_contain_standard_types(self), test_exactly_four_types(self)

**tests/unit/modules/vault/**
  __init__.py
  test_collection.py — TestCalculateCollectionProgress, test_empty_set_all_owned(self), test_no_owned_items(self), test_partial_progress(self), test_complete_set(self), test_extra_owned_items_ignored(self), test_duplicate_owned_type_ids(self), test_set_name_and_artifact_set_stored(self), test_single_item_set_complete(self), test_single_item_set_missing(self), test_large_set_partial(self)
  test_raid_engine.py — FakeArtifact, TestCalculateRaidSuccess, TestSelectRaidTargetArtifact, TestIsRaidOnCooldown, TestCheckRaidProtection, test_always_succeeds_with_chance_1(self), test_always_fails_with_chance_0(self), test_success_at_boundary(self), test_failure_at_boundary(self), test_legendary_reduces_chance(self), test_legendary_still_can_succeed(self), test_rare_no_modifier(self), test_epic_no_modifier(self), test_unknown_rarity_no_modifier(self), test_empty_list_returns_none(self), test_single_item_always_selected(self), test_weighted_selection_is_deterministic_with_seed(self), test_common_weighted_more_than_legendary(self), test_all_rarities_have_correct_weights(self), test_unknown_rarity_gets_weight_1(self), test_uses_system_random_when_no_rng(self), test_none_timestamp_no_cooldown(self), test_expired_cooldown(self), test_active_cooldown(self), test_cooldown_just_expired(self), test_cooldown_just_started(self), test_zero_hour_cooldown(self), test_cooldown_expires_at_correct_time(self), test_no_cards_no_protection(self), test_full_protection_always_blocks(self), test_full_protection_blocks_with_any_seed(self), test_raid_block_succeeds_on_lucky_roll(self), test_raid_block_fails_on_unlucky_roll(self), test_full_protection_takes_priority_over_block(self), test_unrelated_cards_no_protection(self)
  test_vault_service.py — FakeArtifactRecord, FakeDefinitionRecord, FakeShieldRecord, FakeRaidLogRecord, MockPlayerService, MockVaultArtifactRepository, MockArtifactDefinitionRepository, MockVaultShieldRepository, MockRaidLogRepository, TestAddArtifact, TestGetArtifact, TestGetPlayerArtifacts, TestGetVaultSummary, TestRemoveArtifact, TestTransferArtifact, TestShieldOperations, TestRaidOperations, TestCanRaid, TestGetRaidHistory, TestGetRaidCooldown, TestCollectionProgress, TestArtifactCatalog, test_add_artifact_happy_path(self, vault_service, player_service, artifact_definition_repo), test_add_artifact_invalid_type(self, vault_service, player_service), test_add_artifact_player_not_found(self, vault_service), test_add_artifact_max_limit(self, vault_service, player_service, artifact_definition_repo, vault_artifact_repo, mock_config), test_get_artifact_found(self, vault_service, player_service, artifact_definition_repo), test_get_artifact_not_found(self, vault_service), test_get_player_artifacts(self, vault_service, player_service, artifact_definition_repo), test_get_player_artifacts_empty(self, vault_service, player_service), test_get_player_artifacts_invalid_limit(self, vault_service), test_vault_summary(self, vault_service, player_service, artifact_definition_repo, vault_artifact_repo), test_remove_artifact(self, vault_service, player_service, artifact_definition_repo), test_remove_artifact_not_found(self, vault_service), test_transfer_artifact_happy_path(self, vault_service, player_service, artifact_definition_repo), test_transfer_artifact_wrong_owner(self, vault_service, player_service, artifact_definition_repo), test_activate_shield(self, vault_service, player_service), test_activate_shield_custom_duration(self, vault_service, player_service), test_activate_shield_already_active(self, vault_service, player_service), test_activate_shield_invalid_duration(self, vault_service, player_service), test_get_shield_status_active(self, vault_service, player_service), test_get_shield_status_none(self, vault_service, player_service), test_get_shield_status_expired(self, vault_service, player_service, vault_shield_repo), test_deactivate_shield(self, vault_service, player_service), test_deactivate_shield_none_exists(self, vault_service, player_service), test_is_protected(self, vault_service, player_service), test_attempt_raid_success(self, vault_service, player_service, artifact_definition_repo), test_attempt_raid_failure(self, vault_service, player_service, artifact_definition_repo), test_attempt_raid_self_raid(self, vault_service, player_service), test_attempt_raid_shielded(self, vault_service, player_service, artifact_definition_repo), test_attempt_raid_cooldown(self, vault_service, player_service, artifact_definition_repo, raid_log_repo), test_attempt_raid_empty_vault_protection(self, vault_service, player_service), test_can_raid_eligible(self, vault_service, player_service, artifact_definition_repo), test_can_raid_self(self, vault_service, player_service), test_can_raid_shielded(self, vault_service, player_service), test_can_raid_cooldown(self, vault_service, player_service, raid_log_repo, artifact_definition_repo), test_can_raid_empty_vault(self, vault_service, player_service), test_get_raid_history_empty(self, vault_service, player_service), test_get_raid_history_with_entries(self, vault_service, player_service, raid_log_repo), test_no_cooldown(self, vault_service, player_service), test_active_cooldown(self, vault_service, player_service, raid_log_repo), test_collection_progress_complete(self, vault_service, player_service, artifact_definition_repo), test_collection_progress_partial(self, vault_service, player_service, artifact_definition_repo), test_get_definition(self, vault_service, artifact_definition_repo), test_get_definition_not_found(self, vault_service), test_list_definitions(self, vault_service, artifact_definition_repo)

