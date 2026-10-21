#version 460 core

// Card art shader — procedural backgrounds driven by card tags.
//
// Each card's art is unique, seeded by card_id and shaped by its tags.
// Element tags (bits 0-6) drive the primary visual pattern and palette.
// Role tags (bits 7-9) modulate shape language and animation tempo.
// Rarity scales brightness and visual complexity.

precision mediump float;

#include <flutter/runtime_effect.glsl>

uniform vec2 u_size;       // Widget size in pixels
uniform float u_time;      // Elapsed time (seconds)
uniform float u_seed;      // card_id as float (pattern uniqueness)
uniform float u_rarity;    // 0=common, 1=rare, 2=epic, 3=legendary
uniform float u_tags;      // Bitmask: bits 0-6 elements, 7-9 roles
uniform vec3 u_color;      // Base rarity color (RGB 0-1)

out vec4 fragColor;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

// Hash function for seed-based variation.
float hash(vec2 p) {
    vec3 p3 = fract(vec3(p.xyx) * 0.1031);
    p3 += dot(p3, p3.yzx + 33.33);
    return fract((p3.x + p3.y) * p3.z);
}

// 2D value noise.
float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f); // smoothstep
    float a = hash(i);
    float b = hash(i + vec2(1.0, 0.0));
    float c = hash(i + vec2(0.0, 1.0));
    float d = hash(i + vec2(1.0, 1.0));
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

// Fractional Brownian motion (3 octaves).
float fbm(vec2 p) {
    float v = 0.0;
    float a = 0.5;
    vec2 shift = vec2(100.0);
    for (int i = 0; i < 3; i++) {
        v += a * noise(p);
        p = p * 2.0 + shift;
        a *= 0.5;
    }
    return v;
}

// Voronoi distance (for ice/crystal patterns).
float voronoi(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    float minDist = 1.0;
    for (int y = -1; y <= 1; y++) {
        for (int x = -1; x <= 1; x++) {
            vec2 neighbor = vec2(float(x), float(y));
            vec2 point = hash(i + neighbor + u_seed) * vec2(1.0);
            // Animate cell centers slightly.
            point = 0.5 + 0.5 * sin(u_time * 0.3 + 6.2832 * vec2(
                hash(i + neighbor + u_seed),
                hash(i + neighbor + u_seed + 17.0)
            ));
            float d = length(neighbor + point - f);
            minDist = min(minDist, d);
        }
    }
    return minDist;
}

// HSV to RGB.
vec3 hsv2rgb(vec3 c) {
    vec3 p = abs(fract(c.xxx + vec3(0.0, 2.0/3.0, 1.0/3.0)) * 6.0 - 3.0);
    return c.z * mix(vec3(1.0), clamp(p - 1.0, 0.0, 1.0), c.y);
}

// Extract a bit from the tag bitmask.
float tagBit(float tags, int bit) {
    return mod(floor(tags / pow(2.0, float(bit))), 2.0);
}

// ---------------------------------------------------------------------------
// Element patterns (bits 0-6)
// ---------------------------------------------------------------------------

// Fire: warm plasma waves, upward flicker.
vec3 firePattern(vec2 uv, float t, float seed) {
    float n = fbm(vec2(uv.x * 3.0 + seed, uv.y * 4.0 - t * 1.5));
    float flicker = sin(uv.x * 8.0 + t * 3.0) * 0.15;
    n += flicker;
    vec3 col = mix(vec3(0.8, 0.2, 0.0), vec3(1.0, 0.7, 0.1), n);
    col = mix(col, vec3(1.0, 0.95, 0.5), smoothstep(0.7, 1.0, n));
    return col * (0.6 + 0.4 * n);
}

// Ice: crystalline Voronoi facets.
vec3 icePattern(vec2 uv, float t, float seed) {
    float v = voronoi(uv * 4.0 + seed);
    float edge = smoothstep(0.0, 0.08, v);
    float shimmer = 0.5 + 0.5 * sin(v * 20.0 + t * 0.8);
    vec3 col = mix(vec3(0.7, 0.9, 1.0), vec3(0.2, 0.5, 0.8), edge);
    col += vec3(1.0) * (1.0 - edge) * 0.3 * shimmer;
    return col * 0.8;
}

// Wind: flowing air currents with swirl.
vec3 windPattern(vec2 uv, float t, float seed) {
    vec2 q = uv;
    q.x += sin(uv.y * 5.0 + t * 1.2 + seed) * 0.15;
    q.y += cos(uv.x * 3.0 + t * 0.8) * 0.1;
    float n = fbm(q * 5.0 + seed);
    float streaks = sin(q.x * 12.0 + q.y * 4.0 - t * 2.0) * 0.5 + 0.5;
    streaks *= smoothstep(0.3, 0.7, n);
    vec3 col = mix(vec3(0.6, 0.8, 0.65), vec3(0.85, 0.95, 0.9), n);
    col += vec3(1.0) * streaks * 0.15;
    return col * 0.7;
}

// Earth: rocky fracture patterns.
vec3 earthPattern(vec2 uv, float t, float seed) {
    float n = fbm(uv * 6.0 + seed);
    // Cracks via sharp noise thresholding.
    float crack = smoothstep(0.48, 0.50, n) - smoothstep(0.50, 0.52, n);
    float pulse = 0.8 + 0.2 * sin(t * 0.5);
    vec3 base = mix(vec3(0.35, 0.25, 0.1), vec3(0.55, 0.45, 0.2), n);
    vec3 col = base + vec3(0.6, 0.4, 0.1) * crack * pulse;
    // Amber glow in cracks.
    col += vec3(0.8, 0.5, 0.1) * crack * 0.5;
    return col * 0.75;
}

// Storm: electric arc patterns, jagged pulses.
vec3 stormPattern(vec2 uv, float t, float seed) {
    float n = noise(uv * 8.0 + seed + t * 0.5);
    // Jagged lightning-like streaks.
    float bolt = 0.0;
    for (int i = 0; i < 3; i++) {
        float fi = float(i);
        float y = uv.y * 3.0 + fi * 1.5;
        float x = uv.x + sin(y * 8.0 + t * 4.0 + seed + fi) * 0.15;
        float d = abs(x - 0.5);
        bolt += exp(-d * d * 80.0) * (0.5 + 0.5 * sin(t * 6.0 + fi * 2.0));
    }
    vec3 col = mix(vec3(0.15, 0.1, 0.3), vec3(0.4, 0.3, 0.6), n);
    col += vec3(0.9, 0.85, 1.0) * bolt * 0.6;
    col += vec3(1.0, 1.0, 0.5) * bolt * 0.2; // yellow flash
    return col * 0.8;
}

// Time: concentric spirals and rotating rings.
vec3 timePattern(vec2 uv, float t, float seed) {
    vec2 center = uv - 0.5;
    float angle = atan(center.y, center.x);
    float dist = length(center);
    // Concentric rings.
    float rings = sin(dist * 20.0 - t * 1.5) * 0.5 + 0.5;
    // Spiral.
    float spiral = sin(angle * 3.0 + dist * 12.0 - t * 2.0 + seed) * 0.5 + 0.5;
    float n = mix(rings, spiral, 0.5);
    vec3 col = mix(vec3(0.1, 0.4, 0.4), vec3(0.7, 0.6, 0.3), n);
    col = mix(col, vec3(0.8, 0.75, 0.5), smoothstep(0.7, 1.0, n));
    // Center glow.
    col += vec3(0.6, 0.5, 0.2) * exp(-dist * dist * 6.0) * (0.6 + 0.4 * sin(t * 1.0));
    return col * 0.75;
}

// Void: dark swirling vortex, inward pull.
vec3 voidPattern(vec2 uv, float t, float seed) {
    vec2 center = uv - 0.5;
    float angle = atan(center.y, center.x);
    float dist = length(center);
    // Swirl distortion.
    float swirl = 3.0 / (dist + 0.3);
    vec2 distorted = vec2(
        cos(angle + swirl + t * 0.5) * dist,
        sin(angle + swirl + t * 0.5) * dist
    ) + 0.5;
    float n = fbm(distorted * 4.0 + seed);
    vec3 col = mix(vec3(0.1, 0.0, 0.15), vec3(0.35, 0.1, 0.4), n);
    // Dark center.
    col *= smoothstep(0.0, 0.35, dist);
    // Edge glow.
    col += vec3(0.5, 0.1, 0.6) * exp(-abs(dist - 0.4) * 8.0) * 0.4;
    return col * 0.8;
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

void main() {
    vec2 fragCoord = FlutterFragCoord().xy;
    vec2 uv = fragCoord / u_size;

    float tags = u_tags;
    float seed = u_seed * 7.31; // spread seed values

    // Rarity-based intensity and animation speed.
    float intensity = 0.4 + u_rarity * 0.2; // 0.4, 0.6, 0.8, 1.0

    // Role-based tempo modifier (bits 7-9).
    float isOffensive = tagBit(tags, 7);
    float isDefensive = tagBit(tags, 8);
    float isUtility   = tagBit(tags, 9);
    float tempo = 1.0 + isOffensive * 0.5 - isDefensive * 0.3;
    float t = u_time * tempo;

    // Accumulate element patterns (bits 0-6).
    vec3 color = vec3(0.0);
    float elementCount = 0.0;

    float isFire      = tagBit(tags, 0);
    float isIce       = tagBit(tags, 1);
    float isWind      = tagBit(tags, 2);
    float isEarth     = tagBit(tags, 3);
    float isStorm     = tagBit(tags, 4);
    float isTime      = tagBit(tags, 5);
    float isVoid      = tagBit(tags, 6);

    color += firePattern(uv, t, seed)  * isFire;   elementCount += isFire;
    color += icePattern(uv, t, seed)   * isIce;    elementCount += isIce;
    color += windPattern(uv, t, seed)  * isWind;   elementCount += isWind;
    color += earthPattern(uv, t, seed) * isEarth;  elementCount += isEarth;
    color += stormPattern(uv, t, seed) * isStorm;  elementCount += isStorm;
    color += timePattern(uv, t, seed)  * isTime;   elementCount += isTime;
    color += voidPattern(uv, t, seed)  * isVoid;   elementCount += isVoid;

    // Average if multiple elements (shouldn't happen with current data, but safe).
    if (elementCount > 1.0) color /= elementCount;

    // Fallback: if no element tag, use rarity color with noise.
    if (elementCount < 0.5) {
        float n = fbm(uv * 5.0 + seed);
        color = u_color * (0.3 + 0.4 * n);
    }

    // Role modifier overlays.
    // Offensive: angular facet overlay.
    if (isOffensive > 0.5) {
        vec2 center = uv - 0.5;
        float angle = atan(center.y, center.x);
        float facet = abs(sin(angle * 3.0)) * 0.12;
        color += vec3(1.0, 0.9, 0.7) * facet * intensity;
    }
    // Defensive: soft radial vignette brightening at edges.
    if (isDefensive > 0.5) {
        float dist = length(uv - 0.5);
        float ring = smoothstep(0.2, 0.5, dist) * 0.15;
        color += u_color * ring * intensity;
    }
    // Utility: subtle grid overlay.
    if (isUtility > 0.5) {
        float grid = smoothstep(0.48, 0.50, abs(fract(uv.x * 6.0) - 0.5))
                   + smoothstep(0.48, 0.50, abs(fract(uv.y * 6.0) - 0.5));
        color += vec3(1.0) * grid * 0.06 * intensity;
    }

    // Apply rarity intensity.
    color *= intensity;

    // Subtle seed-based hue shift so same-element cards look distinct.
    float hueShift = fract(seed * 0.137) * 0.08 - 0.04;
    // Apply in a simple way: rotate R/G slightly.
    float cs = cos(hueShift * 6.2832);
    float sn = sin(hueShift * 6.2832);
    color.rg = vec2(color.r * cs - color.g * sn, color.r * sn + color.g * cs);

    // Vignette: darken edges slightly for depth.
    float vignette = smoothstep(0.0, 0.4, length(uv - 0.5));
    color *= 1.0 - vignette * 0.25;

    // Output premultiplied alpha.
    float alpha = 1.0;
    fragColor = vec4(color * alpha, alpha);
}
