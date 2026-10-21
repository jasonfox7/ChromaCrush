/// GoRouter configuration — screen flow for ChromaCrush.
///
/// Routes:
///   /              → MainMenuScreen
///   /matchmaking    → MatchmakingScreen
///   /vault          → VaultScreen
///   /game           → GameContainerWidget
///   /post-match     → PostMatchScreen
///   /settings       → SettingsScreen
///   /barter         → BarterScreen
///   /tutorial       → TutorialScreen
///   /campaign       → CampaignScreen
///   /campaign/level/:id → CampaignLevelScreen
///   /campaign/play  → CampaignGameContainer
library;

import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../theme/chroma_theme.dart';
import '../widgets/game/game_container.dart';
import '../widgets/post_match/post_match_screen.dart';
import '../widgets/shell/choose_username_screen.dart';
import '../widgets/shell/login_screen.dart';
import '../widgets/shell/main_menu_screen.dart';
import '../widgets/shell/matchmaking_screen.dart';
import '../widgets/shell/settings_screen.dart';
import '../widgets/barter/barter_screen.dart';
import '../widgets/campaign/campaign_game_container.dart';
import '../widgets/campaign/campaign_level_screen.dart';
import '../widgets/campaign/campaign_screen.dart';
import '../widgets/tutorial/tutorial_screen.dart';
import '../widgets/vault/vault_screen.dart';

GoRouter createAppRouter() {
  return GoRouter(
    initialLocation: '/login',
    routes: [
      GoRoute(
        path: '/login',
        pageBuilder: (context, state) =>
            const CupertinoPage(child: LoginScreen()),
      ),
      GoRoute(
        path: '/',
        pageBuilder: (context, state) =>
            const CupertinoPage(child: MainMenuScreen()),
      ),
      GoRoute(
        path: '/matchmaking',
        pageBuilder: (context, state) =>
            const CupertinoPage(child: MatchmakingScreen()),
      ),
      GoRoute(
        path: '/game',
        pageBuilder: (context, state) =>
            const CupertinoPage(child: GameContainerWidget()),
      ),
      GoRoute(
        path: '/post-match',
        pageBuilder: (context, state) =>
            const CupertinoPage(child: PostMatchScreen()),
      ),
      GoRoute(
        path: '/choose-username',
        pageBuilder: (context, state) =>
            const CupertinoPage(child: ChooseUsernameScreen()),
      ),
      GoRoute(
        path: '/settings',
        pageBuilder: (context, state) =>
            const CupertinoPage(child: SettingsScreen()),
      ),
      GoRoute(
        path: '/vault',
        pageBuilder: (context, state) =>
            const CupertinoPage(child: VaultScreen()),
      ),
      GoRoute(
        path: '/barter',
        pageBuilder: (context, state) =>
            const CupertinoPage(child: BarterScreen()),
      ),
      GoRoute(
        path: '/tutorial',
        pageBuilder: (context, state) =>
            const CupertinoPage(child: TutorialScreen()),
      ),
      GoRoute(
        path: '/campaign',
        pageBuilder: (context, state) =>
            const CupertinoPage(child: CampaignScreen()),
      ),
      GoRoute(
        path: '/campaign/level/:id',
        pageBuilder: (context, state) {
          final levelId = int.parse(state.pathParameters['id']!);
          return CupertinoPage(
            child: CampaignLevelScreen(levelNumber: levelId),
          );
        },
      ),
      GoRoute(
        path: '/campaign/play',
        pageBuilder: (context, state) =>
            const CupertinoPage(child: CampaignGameContainer()),
      ),
    ],
    errorBuilder: (context, state) => Scaffold(
      backgroundColor: ChromaColors.bgBase,
      body: const Center(
        child: Text(
          'Page not found',
          style: TextStyle(color: Colors.white70, fontSize: 18),
        ),
      ),
    ),
  );
}
