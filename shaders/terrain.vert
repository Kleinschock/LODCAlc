#version 450 core

// =============================================================================
// EXPERT TERRAIN VERTEX SHADER
// Implements Per-Vertex Geomorphing & SSE Calculation
// Based on "Master Design Document"
// =============================================================================

layout(location = 0) in vec3 a_PosHigh; // Grid position (LOD N)
layout(location = 1) in vec3 a_PosLow;  // Target position (LOD N+1)

// Uniforms derived from lod_expert_implementation.py
uniform vec3 u_CameraPos;
uniform mat4 u_ViewProj;
uniform float u_K_Perspective; // 4889.2
uniform float u_PitchScalar;   // 0.9659 (cos(-15deg))
uniform float u_GeometricError; // The World-Space error of THIS LOD (e.g. 0.1m)

out float v_MorphFactor;
out vec3 v_WorldPos;
out float v_Distance;

void main() {
    // 1. Calculate Distance (Horizontal or Euclidean?)
    // Report says "Camera-Relative" is best for precision.
    // We assume a_PosHigh is World Space for this prototype.
    float dist = distance(u_CameraPos, a_PosHigh);
    
    // 2. Calculate Projected Screen Space Error (SSE)
    // Formula: rho = (delta * K * PitchScalar) / D
    // delta = u_GeometricError
    float sse_projected = (u_GeometricError * u_K_Perspective * u_PitchScalar) / max(dist, 1.0);
    
    // 3. Calculate Morph Factor (mu)
    // Logic from Checklist:
    // Morph Start: 0.5 px
    // Morph End: 1.0 px
    // We want to morph FROM High TO Low as error GROWS towards 1.0?
    // Wait.
    // If we are at LOD 0 (High), as we move away, distance increases.
    // SSE = C / D. So SSE DECREASES as we move away.
    // This implies LOD 0 becomes 'safer' (lower error) as we move away?
    // NO.
    // SSE is "How big is the geometric ERROR we are committing?"
    // LOD 0 has error 0.1m.
    // At 10m, 0.1m is HUGE on screen (50 pixels). SSE is HIGH.
    // At 10km, 0.1m is TINY on screen (0.001 pixels). SSE is LOW.
    //
    // So:
    // Close up (Small D) -> High SSE.
    // Far away (Large D) -> Low SSE.
    //
    // We switch LODs as we move AWAY.
    // We switch from LOD 0 (0.1m err) to LOD 1 (0.2m err) at 478m.
    // At 478m, LOD 0 error is... small? 
    // No. At 478m, we switch to LOD 1 because LOD 0 is "too detailed"? 
    // No, usually we switch to lower detail because we CAN.
    // We switch to LOD 1 because the ERROR of LOD 1 (0.2m) is now Acceptable (<1px).
    //
    // So the Morph Logic drives the transition to the *Next* LOD.
    // We are rendering LOD N.
    // We want to peek at LOD N+1 (Low).
    // When do we start showing LOD N+1?
    // When LOD N+1's Error is getting small enough to be acceptable.
    // At D=0, LOD N+1 error is huge. Don't show it.
    // At D=SwitchDist, LOD N+1 error is 1.0px. We can fully show it.
    // So as D increases -> SSE(LOD N+1) decreases towards 1.0.
    //
    // So we calculate SSE of *LOD N+1* (The Target).
    // Let's assume u_GeometricError is the error of the NEXT LOD.
    //
    // If SSE(Low) > 1.0: We are too close. Must use High. (Morph = 0.0)
    // If SSE(Low) < 0.5: We are very far. Fully Low. (Morph = 1.0)
    // Range [0.5, 1.0].
    
    // BUT usually the current draw call IS LOD N (High).
    // And 'a_PosLow' is the position if we were LOD N+1.
    // We want to blend to a_PosLow as we allow the error to creep up?
    // Or as we approach the point where we swap?
    
    // Re-reading "Geomorphing.md":
    // "Morph = 0 when Error < 0.5px" (We are far? No wait)
    // "Morph = 1 when Error approaches 1.0px" (We are close?)
    //
    // Let's stick to the Distance-based logic which is intuitive.
    // We swap at D_switch.
    // We start morphing at D_start = D_switch * 0.8 (e.g.).
    // As Dist goes from D_start to D_switch, Morph goes 0 -> 1.
    // 0 = High, 1 = Low.
    // At D_switch, we are fully Low, and we swap index buffers to the next LOD.
    
    // Let's use the explicit 'Range' uniform for simplicity and robustness.
    // Uniform: u_MorphRange (x = start_dist, y = end_dist)
    // This is safer than calculating SSE inversion in shader for the range logic.
    
    // Recalculating plan: Use Distance-based linear interpolation for simplicity 
    // but parameterized by the SSE-derived distances from Python script.
    
    // NO, the checklist says "Morph Factor Equation: clamp((sse - 0.5)/0.5)".
    // This implies SSE is the driver.
    // But which SSE?
    // If SSE decreases with distance, then:
    // Close (100m): SSE = 10.0. Morph = clamped((10-0.5)/0.5) = 1.0? 
    // That means "Fully Low". That's wrong. Close up we want High.
    //
    // Report says: "D_transition = D where error = 1.0".
    // If we are CLOSER than D, we use LOD N.
    // As we approach D_transition, we blend to LOD N+1.
    // At D_transition, we switch.
    //
    // Correct logic:
    // We are rendering LOD N.
    // We are approaching the switch distance to LOD N+1.
    // We want to resemble LOD N+1 just before we switch to it.
    // So 'High' is current. 'Low' is next.
    // We want mix(High, Low, t).
    // t=0 (High) when we are far from the switch.
    // t=1 (Low) when we hit the switch.
    
    // Switch happens at D_limit.
    // Let's pass D_limit as uniform.
    // Morph Start is D_limit * (1.0 - Hysteresis).
    
    // Uniforms re-thought:
    uniform float u_LodSwitchDist; // e.g. 478.0
    uniform float u_MorphBuffer;   // e.g. 0.2 (20%)
    
    // Distance based (Robust)
    float morph_end = u_LodSwitchDist;
    float morph_start = u_LodSwitchDist * (1.0 - u_MorphBuffer);
    
    float mu_linear = clamp((dist - morph_start) / (morph_end - morph_start), 0.0, 1.0);
    
    // Apply Smoothstep (Checklist Item 3)
    float mu_smooth = smoothstep(0.0, 1.0, mu_linear);
    
    // Output
    v_MorphFactor = mu_smooth;
    v_Distance = dist;
    
    // Interpolate
    vec3 final_pos = mix(a_PosHigh, a_PosLow, mu_smooth);
    v_WorldPos = final_pos;
    
    gl_Position = u_ViewProj * vec4(final_pos, 1.0);
}
