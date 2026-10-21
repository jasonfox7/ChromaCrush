// HapticsChannel.swift — Core Haptics platform channel for ChromaCrush.
//
// Receives haptic pattern data from Dart via MethodChannel and plays
// them using CHHapticEngine. Supports transient and continuous events.
//
// Register in AppDelegate.swift:
//   HapticsChannel.register(with: controller.binaryMessenger)

import CoreHaptics
import Flutter

class HapticsChannel {
    private static var engine: CHHapticEngine?
    private static var supportsHaptics = false

    static func register(with messenger: FlutterBinaryMessenger) {
        let channel = FlutterMethodChannel(
            name: "com.chromacrush/haptics",
            binaryMessenger: messenger
        )

        channel.setMethodCallHandler { call, result in
            switch call.method {
            case "initialize":
                initialize(result: result)
            case "playPattern":
                guard let args = call.arguments as? [String: Any] else {
                    result(FlutterError(code: "INVALID_ARGS", message: "Expected map", details: nil))
                    return
                }
                playPattern(args: args, result: result)
            case "dispose":
                dispose(result: result)
            default:
                result(FlutterMethodNotImplemented)
            }
        }
    }

    // MARK: - Initialize

    private static func initialize(result: @escaping FlutterResult) {
        guard CHHapticEngine.capabilitiesForHardware().supportsHaptics else {
            supportsHaptics = false
            result(false)
            return
        }

        do {
            let eng = try CHHapticEngine()
            eng.resetHandler = {
                try? eng.start()
            }
            eng.stoppedHandler = { _ in }
            try eng.start()
            engine = eng
            supportsHaptics = true
            result(true)
        } catch {
            supportsHaptics = false
            result(false)
        }
    }

    // MARK: - Play Pattern

    private static func playPattern(args: [String: Any], result: @escaping FlutterResult) {
        guard supportsHaptics, let engine = engine else {
            result(nil)
            return
        }

        guard let events = args["events"] as? [[String: Any]] else {
            result(nil)
            return
        }

        let intensityScale = args["intensityScale"] as? Double ?? 1.0

        var hapticEvents: [CHHapticEvent] = []

        for eventData in events {
            guard let typeStr = eventData["type"] as? String else { continue }
            let intensity = (eventData["intensity"] as? Double ?? 0.5) * intensityScale
            let sharpness = eventData["sharpness"] as? Double ?? 0.5
            let durationMs = eventData["durationMs"] as? Int ?? 0
            let delayMs = eventData["delayMs"] as? Int ?? 0

            let eventType: CHHapticEvent.EventType = typeStr == "continuous"
                ? .hapticContinuous
                : .hapticTransient

            let duration = typeStr == "continuous"
                ? Double(durationMs) / 1000.0
                : 0.0

            let relativeTime = Double(delayMs) / 1000.0

            let params = [
                CHHapticEventParameter(
                    parameterID: .hapticIntensity,
                    value: Float(intensity.clamped(to: 0...1))
                ),
                CHHapticEventParameter(
                    parameterID: .hapticSharpness,
                    value: Float(sharpness.clamped(to: 0...1))
                ),
            ]

            let event = CHHapticEvent(
                eventType: eventType,
                parameters: params,
                relativeTime: relativeTime,
                duration: duration
            )
            hapticEvents.append(event)
        }

        guard !hapticEvents.isEmpty else {
            result(nil)
            return
        }

        do {
            let pattern = try CHHapticPattern(events: hapticEvents, parameters: [])
            let player = try engine.makePlayer(with: pattern)
            try player.start(atTime: CHHapticTimeImmediate)
            result(nil)
        } catch {
            result(nil)
        }
    }

    // MARK: - Dispose

    private static func dispose(result: @escaping FlutterResult) {
        engine?.stop()
        engine = nil
        supportsHaptics = false
        result(nil)
    }
}

// Helper extension for Double clamping.
private extension Double {
    func clamped(to range: ClosedRange<Double>) -> Double {
        return min(max(self, range.lowerBound), range.upperBound)
    }
}
