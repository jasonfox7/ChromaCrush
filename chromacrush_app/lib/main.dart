/// ChromaCrush — Match-3 versus game.
///
/// Composition root: all services created here and injected via MultiProvider.
/// No service is created inside a Widget or Component.
///
/// NOTE: The backend ads module (src/modules/ads/) is a stub from original
/// agentic code generation and is not yet integrated into the game. The
/// current compensation model is leaning toward purchaseable gold rather
/// than ad-supported revenue. The ads module will need architectural review
/// if/when ads are implemented.
library;

import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'audio/soloud_audio_engine.dart';
import 'config.dart';
import 'config/visual_theme_service.dart';
import 'services/audio_engine.dart';
import 'services/bot_player_service.dart';
import 'services/debug_logger.dart';
import 'services/event_bus.dart';
import 'services/haptics_engine.dart';
import 'services/http_api_client.dart';
import 'services/api_client.dart';
import 'services/intensity_service.dart';
import 'services/session_manager.dart';
import 'services/iap_service.dart';
import 'services/token_storage.dart';
import 'navigation/app_router.dart';
import 'theme/chroma_theme.dart';
import 'view_models/campaign_view_model.dart';
import 'view_models/match_view_model.dart';

/// Set to true to enable end-to-end debug logging (JSON + console).
const bool kDebugGame = false;

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Create services at the composition root.
  final tokenStorage = TokenStorage();
  final sessionManager = SessionManager();
  final apiClient = HttpApiClient(
    tokenStorage: tokenStorage,
    sessionManager: sessionManager,
  );
  // SoLoud uses native FFI — works on iOS/Windows/macOS/Android.
  // On web (WASM), it needs COOP/COEP headers the dev server doesn't provide.
  final AudioEngineBase audioEngine = kIsWeb
      ? StubAudioEngine()
      : SoLoudAudioEngine();
  await audioEngine.initialize();
  await audioEngine.discoverMenuTracks();
  audioEngine.playMenuMusic();
  final visualTheme = await VisualThemeService.load();
  final hapticsEngine = StubHapticsEngine();
  final eventBus = EventBus();
  final debugLogger = DebugLogger(enabled: kDebugGame);
  final intensityService = IntensityService(eventBus: eventBus);

  // Bot opponent — always available, receives per-match JWT tokens dynamically.
  final botPlayerService = BotPlayerService(
    baseUrl: AppConfig.apiUrl,
    eventBus: eventBus,
    debugLogger: debugLogger,
  );

  // In-app purchases — real StoreKit on iOS, stub on Windows/web.
  final iapService = createIapService(
    apiClient: apiClient,
    sessionManager: sessionManager,
    debugLogger: debugLogger,
  );
  await iapService.init();

  final matchViewModel = MatchViewModel(
    apiClient: apiClient,
    eventBus: eventBus,
    sessionManager: sessionManager,
    botPlayerService: botPlayerService,
  );

  final campaignViewModel = CampaignViewModel(
    apiClient: apiClient,
    eventBus: eventBus,
    sessionManager: sessionManager,
  );

  runApp(
    MultiProvider(
      providers: [
        Provider<ApiClientBase>.value(value: apiClient),
        Provider<AudioEngineBase>.value(value: audioEngine),
        Provider<HapticsEngineBase>.value(value: hapticsEngine),
        ChangeNotifierProvider<SessionManager>.value(value: sessionManager),
        Provider<EventBus>.value(value: eventBus),
        Provider<DebugLogger>.value(value: debugLogger),
        ChangeNotifierProvider<IntensityService>.value(value: intensityService),
        ChangeNotifierProvider<MatchViewModel>.value(value: matchViewModel),
        ChangeNotifierProvider<CampaignViewModel>.value(value: campaignViewModel),
        Provider<IapServiceBase>.value(value: iapService),
        Provider<VisualThemeBase>.value(value: visualTheme),
      ],
      child: const ChromaCrushApp(),
    ),
  );
}

class ChromaCrushApp extends StatelessWidget {
  const ChromaCrushApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'ChromaCrush',
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: ChromaColors.bgBase,
        colorScheme: const ColorScheme.dark(
          primary: ChromaColors.accent,
          surface: ChromaColors.bgSurface,
        ),
      ),
      routerConfig: createAppRouter(),
    );
  }
}
