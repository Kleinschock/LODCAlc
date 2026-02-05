#version 450 core

// =============================================================================
// EXPERT TERRAIN FRAGMENT SHADER
// Implements Toksvig Smoothing, Anisotropic Bias, & Detail Fading
// Based on "Master Design Document"
// =============================================================================

in float v_MorphFactor;
in vec3 v_WorldPos;
in float v_Distance;

uniform vec3 u_CameraPos;
uniform sampler2D u_AlbedoMap;
uniform sampler2D u_NormalMap;
uniform sampler2D u_DetailMap;

// Material constants
uniform float u_RoughnessBase; // e.g. 0.8

out vec4 FragColor;

void main() {
    vec3 V = normalize(u_CameraPos - v_WorldPos);
    
    // -------------------------------------------------------------------------
    // 1. ANISOTROPY BIAS LOGIC (Checklist Item 4)
    // -------------------------------------------------------------------------
    // We need the geometric normal for the N dot V check
    // Assuming flat terrain or varying normal passed from VS
    vec3 N_geom = vec3(0, 1, 0); // Placeholder for Up vector
    
    float NdotV = max(dot(N_geom, V), 0.0);
    
    // Grazing Logic
    // If NdotV < 0.25, we are at grazing angle.
    // Bias ramps from 0.0 to 3.0.
    float anisotropyZone = 1.0 - smoothstep(0.0, 0.25, NdotV);
    float bias = anisotropyZone * 3.0; // Max Bias +3.0 from checklist
    
    // Sample Base Textures with Bias
    vec4 albedo = texture(u_AlbedoMap, v_WorldPos.xz * 0.01, bias);
    
    // -------------------------------------------------------------------------
    // 2. TOKSVIG SMOOTHING (Specular AA) (Checklist Item 4)
    // -------------------------------------------------------------------------
    // Sample Normal Map - DO NOT NORMALIZE YET - We need the length!
    vec3 rawNormalSample = texture(u_NormalMap, v_WorldPos.xz * 0.01, bias).rgb;
    vec3 mapNormal = rawNormalSample * 2.0 - 1.0;
    
    // Key Feature: Length represents variance
    float len = length(mapNormal); 
    
    // Toksvig Formula
    float r = u_RoughnessBase;
    float specExp = 2.0 / (r * r + 0.001) - 2.0;
    float ft = len / mix(specExp, 1.0, len);
    
    // "Corrected Roughness" - The output we want
    float correctedRoughness = sqrt(2.0 / (specExp * ft + 2.0));
    
    // -------------------------------------------------------------------------
    // 3. DETAIL MAP FADING (Checklist Item 4)
    // -------------------------------------------------------------------------
    // Start Fade: 1000m, End Fade: 2000m
    float detailFade = 1.0 - smoothstep(1000.0, 20000.0, v_Distance); // Wait, checklist said 2km?
    // Checklist: "End Fade: 2000.0 m"
    // My code above says 20000.0. Typo detection.
    
    // Correction based on Checklist:
    float detailFadeCorrected = 1.0 - smoothstep(1000.0, 2000.0, v_Distance);
    
    vec3 detail = texture(u_DetailMap, v_WorldPos.xz * 1.0).rgb;
    vec3 finalAlbedo = mix(albedo.rgb, albedo.rgb * detail * 2.0, detailFadeCorrected);
    
    // -------------------------------------------------------------------------
    // FINAL OUTPUT (Visualization)
    // -------------------------------------------------------------------------
    // For prototype, just output structure
    
    // Debug: Visualize bias
    // FragColor = vec4(vec3(bias/3.0), 1.0);
    
    // Debug: Visualize Toksvig
    // FragColor = vec4(vec3(correctedRoughness), 1.0);
    
    FragColor = vec4(finalAlbedo * (NdotV + 0.2), 1.0);
}
