/// Settings screen — audio/haptics volume controls.
///
/// Custom header with Cupertino back chevron, glass-grouped controls.
library;

import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../services/audio_engine.dart';
import '../../services/haptics_engine.dart';
import '../../services/session_manager.dart';
import '../../theme/chroma_theme.dart';
import '../../theme/glass_panel.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  double _sfxVolume = 0.8;
  double _musicVolume = 0.4;
  bool _hapticsEnabled = true;

  @override
  Widget build(BuildContext context) {
    final audioEngine = context.read<AudioEngineBase>();
    final hapticsEngine = context.read<HapticsEngineBase>();

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: ChromaGradients.screen),
        child: SafeArea(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const SizedBox(height: 8),

                // Custom header.
                Row(
                  children: [
                    GestureDetector(
                      onTap: () => context.pop(),
                      child: const Icon(
                        CupertinoIcons.chevron_back,
                        color: ChromaColors.accentGlow,
                        size: 28,
                      ),
                    ),
                    const SizedBox(width: 12),
                    Text('Settings', style: ChromaText.headlineMedium),
                  ],
                ),

                const SizedBox(height: 32),

                // Account section.
                Text(
                  'ACCOUNT',
                  style: ChromaText.labelSmall.copyWith(
                    color: ChromaColors.textTertiary,
                  ),
                ),
                const SizedBox(height: 12),
                GlassPanel(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 12,
                  ),
                  child: GestureDetector(
                    onTap: () => context.push('/choose-username'),
                    behavior: HitTestBehavior.opaque,
                    child: Row(
                      children: [
                        const Expanded(
                          child: Text(
                            'Username',
                            style: TextStyle(
                              color: ChromaColors.textSecondary,
                              fontSize: 16,
                            ),
                          ),
                        ),
                        Text(
                          context.watch<SessionManager>().player?.username ??
                              '',
                          style: TextStyle(
                            color: Colors.white.withValues(alpha: 0.38),
                            fontSize: 14,
                          ),
                        ),
                        const SizedBox(width: 8),
                        Icon(
                          CupertinoIcons.chevron_right,
                          color: Colors.white.withValues(alpha: 0.38),
                          size: 18,
                        ),
                      ],
                    ),
                  ),
                ),

                const SizedBox(height: 24),

                // Audio section.
                Text(
                  'AUDIO',
                  style: ChromaText.labelSmall.copyWith(
                    color: ChromaColors.textTertiary,
                  ),
                ),
                const SizedBox(height: 12),
                GlassPanel(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 12,
                  ),
                  child: Column(
                    children: [
                      // SFX volume.
                      Row(
                        children: [
                          const Expanded(
                            child: Text(
                              'SFX Volume',
                              style: TextStyle(
                                color: ChromaColors.textSecondary,
                                fontSize: 16,
                              ),
                            ),
                          ),
                          SizedBox(
                            width: 180,
                            child: CupertinoSlider(
                              value: _sfxVolume,
                              onChanged: (v) {
                                setState(() => _sfxVolume = v);
                                audioEngine.setSfxVolume(v);
                              },
                              activeColor: ChromaColors.accent,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      const Divider(color: Colors.white12, height: 1),
                      const SizedBox(height: 8),

                      // Music volume.
                      Row(
                        children: [
                          const Expanded(
                            child: Text(
                              'Music Volume',
                              style: TextStyle(
                                color: ChromaColors.textSecondary,
                                fontSize: 16,
                              ),
                            ),
                          ),
                          SizedBox(
                            width: 180,
                            child: CupertinoSlider(
                              value: _musicVolume,
                              onChanged: (v) {
                                setState(() => _musicVolume = v);
                                audioEngine.setMusicVolume(v);
                              },
                              activeColor: ChromaColors.accent,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 24),

                // Haptics section.
                Text(
                  'HAPTICS',
                  style: ChromaText.labelSmall.copyWith(
                    color: ChromaColors.textTertiary,
                  ),
                ),
                const SizedBox(height: 12),
                GlassPanel(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 12,
                  ),
                  child: Row(
                    children: [
                      const Expanded(
                        child: Text(
                          'Haptics',
                          style: TextStyle(
                            color: ChromaColors.textSecondary,
                            fontSize: 16,
                          ),
                        ),
                      ),
                      CupertinoSwitch(
                        value: _hapticsEnabled,
                        onChanged: (v) {
                          setState(() => _hapticsEnabled = v);
                          hapticsEngine.isEnabled = v;
                        },
                        activeTrackColor: ChromaColors.accent,
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
