#version 460 core

// Holographic foil shader for card overlays.
//
// Creates an animated iridescent rainbow shimmer that sweeps across
// the card surface. Intensity controls the strength of the effect
// (lower for epic, higher for legendary).

precision mediump float;

#include <flutter/runtime_effect.glsl>

uniform vec2 u_size;       // Widget size in pixels
uniform float u_time;      // Elapsed time (seconds)
uniform float u_intensity; // Effect strength (0.0–1.0)

out vec4 fragColor;

vec3 hsv2rgb(vec3 c) {
    vec3 p = abs(fract(c.xxx + vec3(0.0, 2.0/3.0, 1.0/3.0)) * 6.0 - 3.0);
    return c.z * mix(vec3(1.0), clamp(p - 1.0, 0.0, 1.0), c.y);
}

void main() {
    vec2 fragCoord = FlutterFragCoord().xy;
    vec2 uv = fragCoord / u_size;

    // Diagonal sweep direction (top-left to bottom-right).
    float diag = (uv.x + uv.y) * 0.5;

    // Primary rainbow band — sweeps diagonally with time.
    float sweep = diag - u_time * 0.15;
    float hue = fract(sweep * 1.5);

    // Secondary shimmer — faster, perpendicular.
    float shimmer = sin((uv.x - uv.y) * 12.0 + u_time * 2.5) * 0.5 + 0.5;

    // Fresnel-like edge brightening.
    float edgeDist = min(min(uv.x, 1.0 - uv.x), min(uv.y, 1.0 - uv.y));
    float edgeGlow = smoothstep(0.0, 0.15, edgeDist);
    float edgeBright = 1.0 + (1.0 - edgeGlow) * 0.3;

    // Combine: rainbow with varying saturation.
    float sat = 0.5 + shimmer * 0.3;
    float val = (0.6 + shimmer * 0.4) * edgeBright;
    vec3 rainbow = hsv2rgb(vec3(hue, sat, val));

    // Specular highlight — a bright band that sweeps across.
    float specSweep = fract(u_time * 0.08);
    float specDist = abs(diag - specSweep);
    float specular = exp(-specDist * specDist * 60.0) * 0.7;

    vec3 color = rainbow + vec3(specular);

    // Alpha: the foil effect overlays the card content.
    float alpha = u_intensity * (0.15 + shimmer * 0.1 + specular * 0.3);

    fragColor = vec4(color * alpha, alpha);
}
