#version 460 core

// Ripple background shader — layered scrolling cloud texture + ripple rings.
//
// Three layers of the same seamless cloud texture at different scales
// (100%, 75%, 50%) scrolling in different directions for parallax depth.
// Intensity drives scroll speed, cloud opacity, and storm color tint.
// Ripple rings overlay on gem matches (unchanged from original).
//
// Uniforms: 31 floats + 1 sampler.
//   0-1:   u_size (vec2)         — canvas size in pixels
//   2:     u_time (float)        — elapsed game time in seconds
//   3:     u_ripple_count (float) — number of active ripples (0-8)
//   4-27:  u_ripple0..7 (vec3)   — (originX, originY, startTime)
//   28:    u_intensity (float)   — game intensity (0.0 calm → 1.0 stormy)
//   29-30: u_tex_size (vec2)     — cloud texture size in pixels
//   sampler 0: u_texture         — seamless cloud tile (grayscale, alpha)

precision mediump float;

#include <flutter/runtime_effect.glsl>

uniform vec2 u_size;
uniform float u_time;
uniform float u_ripple_count;
uniform vec3 u_ripple0;
uniform vec3 u_ripple1;
uniform vec3 u_ripple2;
uniform vec3 u_ripple3;
uniform vec3 u_ripple4;
uniform vec3 u_ripple5;
uniform vec3 u_ripple6;
uniform vec3 u_ripple7;
uniform float u_intensity;
uniform vec2 u_tex_size;
uniform sampler2D u_texture;

out vec4 fragColor;

// Base background color — matches 0xFF0D0D14.
const vec3 BASE_COLOR = vec3(0.051, 0.051, 0.078);

// Ripple tint — barely perceptible, subconscious trigger.
const vec3 RIPPLE_TINT = vec3(0.025, 0.03, 0.045);

// Ripple expansion speed (pixels per second).
const float RIPPLE_SPEED = 300.0;

// Ripple lifetime in seconds.
const float RIPPLE_LIFETIME = 2.0;

// Gaussian ring width control (higher = thinner ring).
const float RING_SHARPNESS = 800.0;

// Spacing between concentric rings (pixels).
const float RING_SPACING = 60.0;

// Number of concentric rings per ripple.
const int NUM_RINGS = 4;

// ---------------------------------------------------------------------------
// Ripples
// ---------------------------------------------------------------------------

float rippleBrightness(vec2 fragCoord, vec3 ripple) {
    vec2 origin = ripple.xy;
    float startTime = ripple.z;
    float age = u_time - startTime;

    if (age < 0.0 || age > RIPPLE_LIFETIME) return 0.0;

    float dist = distance(fragCoord, origin);
    float decay = 1.0 - age / RIPPLE_LIFETIME;
    decay *= decay;

    float brightness = 0.0;
    for (int i = 0; i < NUM_RINGS; i++) {
        float ringRadius = age * RIPPLE_SPEED - float(i) * RING_SPACING;
        if (ringRadius < 0.0) continue;
        float ringDelta = dist - ringRadius;
        float ring = exp(-(ringDelta * ringDelta) / RING_SHARPNESS);
        float ringDecay = 1.0 / (1.0 + float(i) * 0.8);
        brightness += ring * ringDecay;
    }

    return brightness * decay;
}

// ---------------------------------------------------------------------------
// Cloud texture sampling with tiling
// ---------------------------------------------------------------------------

float sampleCloud(vec2 pixelCoord) {
    vec2 tc = mod(pixelCoord, u_tex_size);
    return texture(u_texture, tc).a;
}

void main() {
    vec2 fragCoord = FlutterFragCoord().xy;
    vec2 uv = fragCoord / u_size;

    // Dark base with radial vignette.
    vec2 center = uv - 0.5;
    float vignette = 1.0 - dot(center, center) * 0.3;
    vec3 color = BASE_COLOR * vignette;

    float intensity = clamp(u_intensity, 0.0, 1.0);
    float speed = mix(0.3, 1.0, intensity);

    // --- Three cloud layers at different scales and drift directions ---

    // Layer 1: 100% scale — drifts right and slightly down.
    vec2 scroll1 = vec2(u_time * 8.0, u_time * 4.0) * speed;
    float cloud1 = sampleCloud(fragCoord + scroll1);

    // Layer 2: 75% apparent size (1.333x UV) — drifts left (opposite).
    vec2 scroll2 = vec2(u_time * -12.0, u_time * 3.0) * speed;
    float cloud2 = sampleCloud(fragCoord * 1.333 + scroll2);

    // Layer 3: 50% apparent size (2x UV) — drifts right and upward.
    vec2 scroll3 = vec2(u_time * 7.0, u_time * -10.0) * speed;
    float cloud3 = sampleCloud(fragCoord * 2.0 + scroll3);

    // Weighted blend — front layer most visible, back layer subtlest.
    float cloud = cloud1 * 0.45 + cloud2 * 0.35 + cloud3 * 0.20;

    // Intensity controls overall cloud visibility.
    float cloudOpacity = mix(0.4, 0.8, intensity);
    cloud *= cloudOpacity;

    // Storm tint — shifts from visible gray-purple to vivid stormy purple.
    vec3 stormTint = mix(
        vec3(0.18, 0.14, 0.25),
        vec3(0.40, 0.20, 0.50),
        intensity
    );

    // Additive cloud color.
    color += stormTint * cloud * vignette;

    // Depth shadow in dense cloud areas.
    color *= 1.0 - cloud * 0.3;

    // Tension breathing — subtle pulse that scales with intensity.
    float pulseSpeed = mix(0.5, 2.0, intensity);
    float pulseDepth = mix(0.03, 0.10, intensity);
    float pulse = 1.0 + sin(u_time * pulseSpeed) * pulseDepth;
    color *= pulse;

    // --- Ripple rings (unchanged) ---
    float totalBrightness = 0.0;
    int count = int(u_ripple_count);

    if (count > 0) totalBrightness += rippleBrightness(fragCoord, u_ripple0);
    if (count > 1) totalBrightness += rippleBrightness(fragCoord, u_ripple1);
    if (count > 2) totalBrightness += rippleBrightness(fragCoord, u_ripple2);
    if (count > 3) totalBrightness += rippleBrightness(fragCoord, u_ripple3);
    if (count > 4) totalBrightness += rippleBrightness(fragCoord, u_ripple4);
    if (count > 5) totalBrightness += rippleBrightness(fragCoord, u_ripple5);
    if (count > 6) totalBrightness += rippleBrightness(fragCoord, u_ripple6);
    if (count > 7) totalBrightness += rippleBrightness(fragCoord, u_ripple7);

    color += RIPPLE_TINT * totalBrightness;

    fragColor = vec4(color, 1.0);
}
