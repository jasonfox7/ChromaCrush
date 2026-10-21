#version 460 core

// Gem base shader — cut gemstone with refraction, Fresnel edges, fire,
// and shader-driven special gem effects.
//
// Special gem functions (u_function):
//   0: Neutral — standard gemstone
//   1: Line Blast H — horizontal energy streak pulsing through gem
//   2: Line Blast V — vertical energy streak pulsing through gem
//   3: Radial Bomb — pulsing core + concentric energy rings
//   4: Chromatic Orb — rotating rainbow prismatic fill
//   5-8: Mega gem variants (dominant special + golden aura overlay)
//        5=mega lineH, 6=mega lineV, 7=mega bomb, 8=mega orb
//
// All specials get a border glow aura and keep their base color.

precision mediump float;

#include <flutter/runtime_effect.glsl>

// Uniforms
uniform vec2 u_size;        // Component size in pixels
uniform float u_time;       // Elapsed time (seconds)
uniform float u_pulse_rate; // Heartbeat pulse rate (Hz)
uniform float u_pulse_amp;  // Pulse amplitude (0-1)
uniform float u_brightness; // Overall brightness multiplier
uniform float u_glow_radius;// Outer glow radius
uniform vec3 u_color;       // Gem RGB color (0-1)
uniform float u_selected;   // 1.0 if selected, 0.0 otherwise
uniform float u_shape;      // Shape index (0-5)
uniform float u_function;   // Special function (0-4)
uniform float u_scale;      // Render-to-gem scale (>1 when padded for glow)

out vec4 fragColor;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

vec3 hsv2rgb(vec3 c) {
    vec3 p = abs(fract(c.xxx + vec3(0.0, 2.0/3.0, 1.0/3.0)) * 6.0 - 3.0);
    return c.z * mix(vec3(1.0), clamp(p - 1.0, 0.0, 1.0), c.y);
}

// ---------------------------------------------------------------------------
// SDF shapes — Inigo Quilez analytical 2D SDFs (iquilezles.org)
//   0 (red):    Heart
//   1 (blue):   Pentagon
//   2 (green):  Emerald Cut (chamfered box)
//   3 (yellow): Circle
//   4 (purple): Hexagon
//   5 (orange): Octagon
// All use the same radius r for consistent sizing.
// ---------------------------------------------------------------------------

// Shape 0 (red): Circle.
float sdCircle(vec2 p, float r) {
    return length(p) - r;
}

// Shape 1 (blue): Hexagon — IQ analytical.
float sdHexagon(vec2 p, float r) {
    const vec3 k = vec3(-0.866025404, 0.5, 0.577350269);
    p = abs(p);
    p -= 2.0 * min(dot(k.xy, p), 0.0) * k.xy;
    p -= vec2(clamp(p.x, -k.z * r, k.z * r), r);
    return length(p) * sign(p.y);
}

// Shape 2 (green): Emerald Cut — chamfered box (original, untouched).
float sdChamferBox(vec2 p, vec2 b, float c) {
    p = abs(p) - b;
    if (p.y > p.x) p = p.yx;
    p.y += c;
    float k = 1.0 - sqrt(2.0);
    if (p.y < 0.0 && p.y + p.x * k < 0.0) return p.x;
    if (p.x < p.y) return (p.x + p.y) * sqrt(0.5);
    return length(p);
}

// Shape 3 (yellow): Octagon — IQ analytical.
float sdOctogon(vec2 p, float r) {
    const vec3 k = vec3(-0.9238795325, 0.3826834323, 0.4142135623);
    p = abs(p);
    p -= 2.0 * min(dot(vec2( k.x, k.y), p), 0.0) * vec2( k.x, k.y);
    p -= 2.0 * min(dot(vec2(-k.x, k.y), p), 0.0) * vec2(-k.x, k.y);
    p -= vec2(clamp(p.x, -k.z * r, k.z * r), r);
    return length(p) * sign(p.y);
}

// Shape 4 (purple): Heart — IQ analytical, scaled to radius r.
float sdHeart(vec2 p, float r) {
    p /= (r * 1.25);
    p.y = -p.y + 0.4;
    p.x = abs(p.x);
    float d;
    if (p.y + p.x > 1.0)
        d = sqrt(dot(p - vec2(0.25, 0.75), p - vec2(0.25, 0.75))) - sqrt(2.0) / 4.0;
    else
        d = sqrt(min(dot(p - vec2(0.0, 1.0), p - vec2(0.0, 1.0)),
                     dot(p - 0.5 * max(p.x + p.y, 0.0), p - 0.5 * max(p.x + p.y, 0.0)))) * sign(p.x - p.y);
    return d * r;
}

// Shape 5 (orange): Pentagon — IQ analytical.
float sdPentagon(vec2 p, float r) {
    const vec3 k = vec3(0.809016994, 0.587785252, 0.726542528);
    p.x = abs(p.x);
    p -= 2.0 * min(dot(vec2(-k.x, k.y), p), 0.0) * vec2(-k.x, k.y);
    p -= 2.0 * min(dot(vec2( k.x, k.y), p), 0.0) * vec2( k.x, k.y);
    p -= vec2(clamp(p.x, -r * k.z, r * k.z), r);
    return length(p) * sign(p.y);
}

// Dispatch to the correct shape SDF.
float sdf(vec2 p, float r, float shape) {
    int s = int(shape + 0.5);
    if (s == 0) return sdHeart(p, r);
    if (s == 1) return sdPentagon(p, r);
    if (s == 3) return sdCircle(p, r);
    if (s == 4) return sdHexagon(p, r);
    if (s == 5) return sdOctogon(p, r);
    // Default (2): emerald chamfered box.
    vec2 b = vec2(r / 1.4, r);
    float c = (sqrt(2.0) - 1.0) * b.x;
    return sdChamferBox(p, b, c);
}

void main() {
    vec2 fragCoord = FlutterFragCoord().xy;
    vec2 uv = fragCoord / u_size;
    vec2 center = (uv - 0.5) * 2.0 * u_scale; // scaled so gem body maps to ±1

    float radius = 0.7;

    // Pulse: modulate radius slightly
    float pulse = sin(u_time * u_pulse_rate * 6.2832) * u_pulse_amp * 0.05;
    radius += pulse;

    float d = sdf(center, radius, u_shape);

    // --- Special function setup ---
    float fn = u_function;
    // Mega gems arrive as 5-8 (dominant + 4). Detect and remap to base effect.
    float isMega = step(4.5, fn);
    float effectFn = mix(fn, fn - 4.0, isMega);  // 5->1, 6->2, 7->3, 8->4
    float isSpecial = step(0.5, effectFn);
    float isLineH = step(0.5, effectFn) * step(effectFn, 1.5);
    float isLineV = step(1.5, effectFn) * step(effectFn, 2.5);
    float isBomb  = step(2.5, effectFn) * step(effectFn, 3.5);
    float isOrb   = step(3.5, effectFn);

    // Effective gem color — chromatic orb rotates through rainbow
    vec3 gemColor = u_color;
    float orbHue = mod(atan(center.y, center.x) / 6.2832 + u_time * 0.15, 1.0);
    gemColor = mix(gemColor, hsv2rgb(vec3(orbHue, 0.85, 1.0)), isOrb);

    // --- Layer 1: Outer glow ---
    float glowFalloff = exp(-max(d, 0.0) * (8.0 / max(u_glow_radius, 0.01)));
    float glowPulse = 0.8 + 0.2 * sin(u_time * u_pulse_rate * 6.2832);
    vec3 glow = gemColor * glowFalloff * 0.4 * glowPulse;

    // --- Special border glow — wide colored aura for all specials ---
    float specialGlowFalloff = exp(-max(d, 0.0) * 4.5);
    float specialGlowPulse = 0.55 + 0.45 * sin(u_time * 2.5);
    vec3 specialGlow = gemColor * specialGlowFalloff * 0.55 * specialGlowPulse * isSpecial;

    // --- Layer 2: Body fill — deep saturated color with directional lighting ---
    float fillMask = 1.0 - smoothstep(-0.02, 0.02, d);
    vec2 lightDir = normalize(vec2(-0.6, -0.8));
    float directional = 0.8 + 0.2 * dot(normalize(-center), lightDir);
    float depthDarken = 0.85 + 0.15 * smoothstep(0.0, 0.5, length(center));
    vec3 fill = gemColor * directional * depthDarken * u_brightness;

    // --- Layer 3: Fresnel edge transparency ---
    float edgeDepth = smoothstep(0.0, -0.18, d);
    float bodyAlpha = fillMask * mix(0.55, 0.92, edgeDepth);

    // --- Layer 4: Inner shadow ---
    float shadow = smoothstep(-0.3, 0.1, dot(center, vec2(0.5, 0.6)));
    vec3 shadowTint = gemColor * (-0.3 * shadow);

    // --- Layer 5: Facet lines ---
    float angle = atan(center.y, center.x);
    float facetAngle = mod(angle + 3.14159 / 8.0, 3.14159 / 4.0) - 3.14159 / 8.0;
    float facetLine = 1.0 - smoothstep(0.0, 0.04, abs(facetAngle));
    float facetRadial = smoothstep(0.1, 0.35, length(center)) * smoothstep(0.0, -0.15, d);
    vec3 facet = vec3(1.0) * facetLine * facetRadial * 0.06;

    // --- Layer 6: Primary specular ---
    vec2 specPos = center - vec2(-0.28, -0.38);
    float spec1 = exp(-dot(specPos, specPos) * 7.0);

    // --- Layer 7: Secondary specular ("fire") ---
    vec2 firePos = center - vec2(-0.12, -0.2);
    float spec2 = exp(-dot(firePos, firePos) * 30.0);

    float specTotal = spec1 * 0.5 + spec2 * 0.35;

    // --- Layer 8: Rim light ---
    float rimDist = smoothstep(-0.08, 0.0, d) - smoothstep(0.0, 0.04, d);
    float rimAngle = dot(normalize(-center), lightDir);
    float rim = rimDist * max(rimAngle, 0.0) * 0.4;

    // --- Special effects (inside gem body) ---
    vec3 specialFx = vec3(0.0);
    float specialFxAlpha = 0.0;

    // Line Blast H: horizontal energy streak
    float streakPulse = 0.4 + 0.6 * sin(u_time * 3.5);
    float hStreak = exp(-center.y * center.y * 28.0) * streakPulse;
    // Traveling wave along the streak
    float hWave = 0.5 + 0.5 * sin(center.x * 8.0 - u_time * 6.0);
    hStreak *= 0.7 + 0.3 * hWave;
    specialFx += vec3(1.0, 0.95, 0.8) * hStreak * 0.4 * isLineH;
    specialFxAlpha += hStreak * 0.4 * isLineH;

    // Line Blast V: vertical energy streak
    float vStreak = exp(-center.x * center.x * 28.0) * streakPulse;
    float vWave = 0.5 + 0.5 * sin(center.y * 8.0 - u_time * 6.0);
    vStreak *= 0.7 + 0.3 * vWave;
    specialFx += vec3(1.0, 0.95, 0.8) * vStreak * 0.4 * isLineV;
    specialFxAlpha += vStreak * 0.4 * isLineV;

    // Radial Bomb: pulsing core + expanding energy rings
    float bombDist = length(center);
    float bombCore = exp(-bombDist * bombDist * 6.0);
    float bombCorePulse = 0.6 + 0.4 * sin(u_time * 4.0);
    // Concentric rings expanding outward
    float bombRings = sin(bombDist * 16.0 - u_time * 5.0) * 0.5 + 0.5;
    bombRings *= smoothstep(0.55, 0.15, bombDist); // fade near edge
    vec3 bombColor = vec3(1.0, 0.8, 0.3); // warm gold core
    specialFx += bombColor * bombCore * bombCorePulse * 0.5 * isBomb;
    specialFx += vec3(1.0, 0.9, 0.5) * bombRings * 0.15 * isBomb;
    specialFxAlpha += (bombCore * bombCorePulse * 0.5 + bombRings * 0.15) * isBomb;

    // Chromatic Orb: prismatic sparkle overlay
    float orbSparkle = sin(angle * 6.0 + u_time * 2.5) * 0.5 + 0.5;
    orbSparkle *= smoothstep(0.55, 0.1, length(center));
    float orbShimmer = sin(angle * 12.0 - u_time * 1.8) * 0.5 + 0.5;
    orbShimmer *= smoothstep(0.45, 0.2, length(center)) * 0.5;
    specialFx += vec3(1.0) * (orbSparkle * 0.2 + orbShimmer * 0.1) * isOrb;
    specialFxAlpha += (orbSparkle * 0.2 + orbShimmer * 0.1) * isOrb;

    specialFx *= fillMask;
    specialFxAlpha *= fillMask;

    // --- Mega gem golden aura overlay ---
    vec3 megaGold = vec3(1.0, 0.84, 0.0);
    float megaPulse = 0.5 + 0.5 * sin(u_time * 2.0);
    // Inner golden glow radiating from center
    float megaAura = exp(-d * d * 3.0) * megaPulse * 0.35 * isMega;
    // Outer pulsing golden ring
    float megaRing = exp(-abs(d + 0.08) * 18.0) * (0.6 + 0.4 * sin(u_time * 3.0)) * isMega;
    specialFx += megaGold * (megaAura + megaRing) * fillMask;
    specialFxAlpha += (megaAura + megaRing) * fillMask;
    // Wider outer glow for mega gems
    float megaOuterGlow = exp(-max(d, 0.0) * 3.5) * megaPulse * 0.3 * isMega;
    glow += megaGold * megaOuterGlow;

    // --- Layer 9: Selection ring ---
    float ringWidth = 0.06;
    float ringDist = abs(d + ringWidth * 0.5) - ringWidth * 0.5;
    float ringMask = 1.0 - smoothstep(0.0, 0.03, ringDist);
    vec3 ring = vec3(1.0) * ringMask * u_selected;

    // --- Composite (premultiplied alpha) ---
    vec3 bodyColor = (fill + shadowTint + facet) * bodyAlpha;
    vec3 surfaceColor = vec3(1.0) * (specTotal + rim) * fillMask;

    vec3 color = glow + specialGlow + bodyColor + surfaceColor + specialFx + ring;
    float alpha = max(bodyAlpha, glowFalloff * 0.3);
    alpha = max(alpha, specialGlowFalloff * 0.5 * isSpecial); // border glow alpha
    alpha = max(alpha, megaOuterGlow); // mega outer glow alpha
    alpha = max(alpha, (specTotal + rim) * fillMask);
    alpha = max(alpha, specialFxAlpha);
    alpha = max(alpha, ringMask * u_selected);

    fragColor = vec4(color, alpha);
}
