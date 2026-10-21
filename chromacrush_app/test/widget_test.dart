import 'package:flutter_test/flutter_test.dart';
import 'package:provider/provider.dart';

import 'package:chromacrush_app/services/api_client.dart';
import 'package:chromacrush_app/services/audio_engine.dart';
import 'package:chromacrush_app/services/debug_logger.dart';
import 'package:chromacrush_app/services/event_bus.dart';
import 'package:chromacrush_app/services/haptics_engine.dart';
import 'package:chromacrush_app/services/intensity_service.dart';
import 'package:chromacrush_app/services/session_manager.dart';
import 'package:chromacrush_app/view_models/match_view_model.dart';
import 'package:chromacrush_app/main.dart';

void main() {
  testWidgets('ChromaCrushApp builds without crashing', (
    WidgetTester tester,
  ) async {
    final eventBus = EventBus();
    final apiClient = StubApiClient();
    final sessionManager = SessionManager();

    await tester.pumpWidget(
      MultiProvider(
        providers: [
          Provider<ApiClientBase>.value(value: apiClient),
          Provider<AudioEngineBase>.value(value: StubAudioEngine()),
          Provider<HapticsEngineBase>.value(value: StubHapticsEngine()),
          ChangeNotifierProvider<SessionManager>.value(value: sessionManager),
          Provider<EventBus>.value(value: eventBus),
          Provider<DebugLogger>.value(value: DebugLogger(enabled: false)),
          ChangeNotifierProvider<IntensityService>.value(
            value: IntensityService(eventBus: eventBus),
          ),
          ChangeNotifierProvider<MatchViewModel>.value(
            value: MatchViewModel(
              apiClient: apiClient,
              eventBus: eventBus,
              sessionManager: sessionManager,
            ),
          ),
        ],
        child: const ChromaCrushApp(),
      ),
    );

    // Pump a frame — GoRouter initial route '/login' shows LoginScreen with LOGIN button.
    await tester.pump(const Duration(milliseconds: 100));

    expect(find.text('Sign in with Apple'), findsOneWidget);
  });
}
