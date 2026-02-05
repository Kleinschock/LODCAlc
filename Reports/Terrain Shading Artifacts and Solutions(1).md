# **Advanced Architectures for Artifact Suppression in Long-Range Terrain Rendering: A Comprehensive Analysis of Aliasing, Anisotropy, and Continuous Level of Detail**

## **Executive Summary**

The rendering of large-scale terrain in flight simulation environments presents a unique convergence of challenges in signal processing, optical physics, and graphics hardware architecture. As viewing distances extend to the horizon—defined in the provided specification as 20 kilometers—the geometric and textural information undergoes extreme perspective foreshortening. The provided lod\_expert\_optimizer.py script reveals a critical anisotropy ratio of approximately 200:1 at the limit of visibility.1 This extreme ratio indicates that a single screen pixel creates a footprint on the terrain that is 200 times longer in the longitudinal direction (depth) than in the lateral direction (width).  
Standard graphics pipeline configurations, which typically cap anisotropic filtering at 16x, are mathematically incapable of resolving this signal without introducing significant aliasing artifacts, manifesting as "shimmering" or temporal instability.2 Furthermore, the application of detail maps at these distances violates the Nyquist-Shannon sampling theorem, introducing high-frequency noise that cannot be reconstructed by the display device.3  
This report provides an exhaustive analysis of these phenomena and proposes a robust, physically-based shading and geometry architecture to eliminate these artifacts. The proposed solution integrates a dynamic, angle-dependent mip-map biasing strategy, a Toksvig-based geometric specular anti-aliasing model, and a continuous Level of Detail (LOD) system utilizing vertex shader geomorphing. These strategies are derived from the specific optical constants provided: a vertical Field of View (FOV) of 12 degrees and a vertical resolution of 1024 pixels.

## ---

**1\. The Optical Physics of Distant Terrain Rendering**

To effectively mitigate visual artifacts, one must first rigorously define the optical environment in which they occur. Artifacts such as shimmering and moiré patterns are not merely "glitches" but are the mathematical result of signal aliasing—where the frequency of the scene detail exceeds the sampling frequency of the screen pixels.3

### **1.1 Angular Resolution and Pixel Footprint Analysis**

The simulation configuration specifies a vertical resolution ($R\_y$) of 1024 pixels and a vertical FOV ($FOV\_v$) of 12 degrees.1 We can calculate the instantaneous field of view (IFOV), or angular resolution per pixel ($\\theta\_{px}$), as follows:

$$\\theta\_{px} \= \\frac{FOV\_v \\cdot \\frac{\\pi}{180}}{R\_y} \\approx \\frac{0.2094 \\text{ rad}}{1024} \\approx 0.0002045 \\text{ radians/pixel}$$  
This exceedingly high angular resolution drives the requirement for high-fidelity rendering but also narrows the margin for error. A single pixel represents a cone of vision that expands with distance.

#### **1.1.1 Lateral Ground Sample Distance (GSD)**

At a slant distance ($D$) of 20,000 meters (20km), the lateral footprint of a pixel ($GSD\_{lat}$)—the width of terrain covered by that pixel perpendicular to the view direction—is roughly linear to the distance:

$$GSD\_{lat} \\approx D \\cdot \\theta\_{px} \\approx 20,000 \\cdot 0.0002045 \\approx 4.09 \\text{ meters}$$  
This implies that at the horizon, a pixel is sampling information from a strip of terrain approximately 4 meters wide.1

#### **1.1.2 Longitudinal Ground Sample Distance**

The longitudinal footprint ($GSD\_{long}$)—the length of terrain covered along the view vector—is governed by the viewing angle relative to the terrain surface ($\\alpha$), often referred to as the grazing angle. Near the horizon, $\\alpha$ becomes extremely small. The relationship is defined as:

$$GSD\_{long} \\approx \\frac{GSD\_{lat}}{\\sin(\\alpha)}$$  
At an altitude of 100 meters and a distance of 20km, the viewing angle $\\alpha$ is approximately:

$$\\alpha \\approx \\arctan\\left(\\frac{100}{20000}\\right) \\approx 0.005 \\text{ radians} \\approx 0.28^\\circ$$  
Substituting this into the GSD equation:

$$GSD\_{long} \\approx \\frac{4.09}{\\sin(0.28^\\circ)} \\approx \\frac{4.09}{0.005} \\approx 818 \\text{ meters}$$  
This massive disparity is the root cause of the rendering artifacts. A single pixel on the horizon is attempting to represent a slice of terrain 4 meters wide by 818 meters long.

### **1.2 The Anisotropy Crisis**

The anisotropy ratio ($A$) is the ratio of the longitudinal to lateral footprint:

$$A \= \\frac{GSD\_{long}}{GSD\_{lat}} \\approx \\frac{818}{4.09} \\approx 200$$  
This confirms the calculation in the user's Python script (lod\_expert\_optimizer.py), which reports an anisotropy of \~200x.1  
Modern Graphics Processing Units (GPUs) utilizes Anisotropic Filtering (AF) to handle this texture distortion. AF works by taking multiple samples (taps) along the axis of elongation to integrate the texture color correctly.2 However, virtually all consumer and professional hardware caps AF at **16x**.2  
**The Artifact Mechanism:** When the required anisotropy (200x) exceeds the hardware limit (16x), the GPU is forced to compromise. It must either:

1. **Undersample:** Take only 16 samples along a vector that requires 200\. This leads to **aliasing**, where high-frequency details (like a repeating grass texture) create temporal noise or "shimmering" as the sample points slide across the terrain during camera movement.7  
2. **Over-blur:** Select a lower-resolution Mip-Map level where the footprint is smaller in texture space, effectively blurring the image to hide the aliasing. This leads to the "muddy" terrain look often complained about in flight simulators.9

Therefore, reliance on standard hardware filtering alone is insufficient for this specific optical configuration. Software-based intervention in the shader pipeline is required.

## ---

**2\. Advanced Mip-Map Bias Strategies for High Anisotropy**

The first requirement of the request is to propose a Mip-Map Bias strategy beyond 16x Anisotropic Filtering. The core dilemma is choosing between a bias based on **distance** or **viewing angle**.

### **2.1 Theoretical Framework of Texture LOD Bias**

Texture Level of Detail (LOD) bias is an offset applied to the computed Mip-Map level ($\\lambda$).

* **Negative Bias ($\< 0$):** Forces the GPU to select a larger, higher-resolution texture map. This increases sharpness but significantly increases aliasing and shimmering if the sampling rate is insufficient (Nyquist violation).11  
* **Positive Bias ($\> 0$):** Forces the GPU to select a smaller, lower-resolution texture map. This reduces aliasing by pre-filtering high-frequency details but reduces visual sharpness.11

In the context of a flight simulator, users often apply a global negative bias (e.g., \-1.0) to make the cockpit and near-field terrain look crisp.14 However, at 20km with 200x anisotropy, this negative bias is catastrophic. It forces the GPU to sample high-frequency noise from a high-res texture when it should be sampling a smooth average from a low-res mip.15

### **2.2 Viewing Angle vs. Distance: The Optimal Approach**

The research explicitly supports a **viewing angle ($N \\cdot V$) based strategy** over a pure distance-based strategy for handling anisotropy.17

* **Why Distance Fails:** A hill viewed face-on at 20km has low anisotropy (1:1 ratio). It *should* be rendered with a high-resolution texture because the pixel footprint is square. If we bias based solely on distance, we would blur this hill unnecessarily.19  
* **Why Angle Succeeds:** The anisotropy correlates directly with the angle of incidence. As the view vector becomes perpendicular to the normal (grazing angle), the footprint stretches. This is where the 200x ratio occurs. Therefore, the bias should be applied *only* when the viewing angle is shallow.15

### **2.3 Proposed Shader Implementation: Anisotropic Compensation Bias**

We propose a dynamic bias function implemented in the fragment shader that applies a positive (blurring) bias only as the anisotropy exceeds the hardware limit.  
The logic uses the dot product of the View Vector ($V$) and the World Normal ($N$). Let $\\theta\_{grazing} \= |N \\cdot V|$.

* When $\\theta\_{grazing} \\approx 1.0$ (looking straight down), anisotropy is 1x. No bias needed.  
* When $\\theta\_{grazing} \\approx 0.0$ (looking at horizon), anisotropy approaches $\\infty$. Positive bias is required to suppress shimmering.

**Derived Formula for 200x Compensation:**  
Hardware handles up to 16x. We need to compensate for the ratio $\\frac{200}{16} \= 12.5$.  
Texture LOD scales logarithmically ($2^L$). The number of mip levels required to reduce resolution by 12.5x is $\\log\_2(12.5) \\approx 3.64$.  
Therefore, at the extreme horizon (20km), we essentially need to bias the LOD by approximately **\+3.0 to \+3.5** to bring the signal bandwidth back within the capabilities of 16x AF.17

#### **2.3.1 GLSL / HLSL Implementation Logic**

The following logic should be integrated into the terrain fragment shader. It calculates a bias that scales non-linearly as the viewing angle approaches the horizon.

OpenGL Shading Language

// Inputs  
vec3 N \= normalize(v\_WorldNormal);  
vec3 V \= normalize(u\_CameraPosition \- v\_WorldPosition);

// Calculate grazing angle (N dot V)  
// Use max to prevent backface artifacts  
float NdotV \= max(dot(N, V), 0.0);

// Define the "Critical Anisotropy Threshold"  
// Anisotropy typically becomes problematic below 10 degrees (NdotV \< 0.17)  
// We map the range \[0.0, 0.2\] to a bias of  
float anisotropyZone \= 1.0 \- smoothstep(0.0, 0.25, NdotV);

// Max bias calculation:  
// We determined \~3.5 is needed for 200x correction vs 16x hardware  
float maxBias \= 3.0; 

// Calculate final dynamic bias  
float anisotropicBias \= anisotropyZone \* maxBias;

// Apply to texture lookup  
// Note: Some engines allow global bias, but per-sample bias is preferred here  
vec4 albedo \= texture(u\_AlbedoMap, v\_UV, anisotropicBias);

**Refinement for Distance:**  
While angle is primary, distance acts as a multiplier. Shimmering is less objectionable at 10 meters than at 20km because the pixel density is higher. We can modulate maxBias by a distance factor derived from the user's script (max visibility 20km).

OpenGL Shading Language

float dist \= distance(u\_CameraPosition, v\_WorldPosition);  
float distFactor \= smoothstep(1000.0, 20000.0, dist); // Ramp up bias from 1km to 20km

// Final combined bias strategy  
float finalBias \= anisotropicBias \* distFactor; 

**Conclusion on Mip-Map Bias:** The solution is a **hybrid Grazing-Angle/Distance strategy**. Pure distance bias blurs distant mountains that should be sharp. Pure angle bias blurs nearby runway markings viewed at shallow angles. Combining them ensures that only **distant, oblique surfaces** (the exact scenario generating 200x anisotropy) receive the positive bias required to eliminate shimmering.18

## ---

**3\. Geometric Specular Anti-Aliasing (Toksvig Smoothing)**

The user reports "specular shimmering" specifically. This is distinct from texture aliasing. It occurs when a normal map contains high-frequency variations (bumps) that are averaged away in the color mip-maps but are not correctly accounted for in the lighting equation.21  
At 20km, a pixel covers 800+ meters. The normal map for that area might contain millions of micro-facets (waves, rocks, trees). If the shader simply samples the averaged normal (which might be a perfectly vertical vector if the bumps cancel out), the surface will appear perfectly smooth and essentially mirror-like (high specularity). As the camera moves slightly, the sampled normal might shift, causing the sun reflection to flash on and off. This is "fireflies" or specular aliasing.21

### **3.1 The Toksvig Factor Implementation**

To solve this, we must use **Geometric Specular Anti-Aliasing**, commonly known as **Toksvig Smoothing**.23 This technique adjusts the surface roughness based on the variance of the normals within the pixel footprint.  
**The Principle:**  
When we sample a normal map at a low mip level, the length of the normal vector ($|N\_a|$) decreases.

* If the surface is flat, all normals point the same way. The average has length 1.0.  
* If the surface is rough (noisy), the normals point in all directions. The average vector is short (length \< 1.0).23

We can use this length to calculate a Toksvig Factor ($f\_t$) that automatically dampens the specular highlight when the normals are noisy (i.e., at long distances).  
**The Formula:**  
The user's script and context suggest a Blinn-Phong or PBR workflow. The Toksvig scaling factor $f\_t$ for a specular exponent $s$ (shininess) is derived as:

$$f\_t \= \\frac{|N\_a|}{|N\_a| \+ s(1 \- |N\_a|)}$$  
However, for a modern PBR workflow (Roughness based), we adjust the Roughness parameter directly. A lower normal length implies we should increase roughness effectively.

### **3.2 Shader Implementation for Terrain**

We propose implementing this logic in the terrain fragment shader. This is mathematically more robust than simple mip-bias for specular issues because it preserves the *energy conservation* of the lighting model.23

OpenGL Shading Language

// GLSL Implementation of Toksvig Smoothing for Terrain

// 1\. Sample the normal map (which includes mip-mapping)  
// Note: Do NOT normalize this immediately. The length is the signal we need.  
vec3 rawNormal \= texture(u\_NormalMap, v\_UV).rgb \* 2.0 \- 1.0; 

// 2\. Calculate the length (variance metric)  
float len \= length(rawNormal); 

// 3\. Toksvig Factor Calculation  
// 'roughness' is the material roughness (0.0 \- 1.0)  
// We map roughness to a specular exponent approximation for the math  
float specExp \= 2.0 / (roughness \* roughness \+ 0.001) \- 2.0;

// Calculate the dampening factor  
// mix(specExp, 1.0, len) is a lerp based on the normal length  
float ft \= len / mix(specExp, 1.0, len);

// 4\. Apply Toksvig scaling to the Roughness  
// As ft goes to 0 (high variance), roughness increases  
float correctedRoughness \= sqrt(2.0 / (specExp \* ft \+ 2.0));

// 5\. Use 'correctedRoughness' in your BRDF (e.g., GGX)  
// Also scale the specular intensity to prevent energy gain  
float intensityScale \= (1.0 \+ ft \* specExp) / (1.0 \+ specExp);  
vec3 finalSpecular \= lighting\_BRDF(N, V, L, correctedRoughness) \* intensityScale;

**Why this fixes the problem:** At 20km, the anisotropy causes massive averaging of the normal map. rawNormal will become very short (e.g., length 0.2). This causes ft to drop, which drastically increases correctedRoughness. The terrain transforms from a shimmering, shiny surface into a smooth, matte surface at a distance. This mathematically mimics the behavior of light interacting with sub-pixel geometry, completely eliminating specular shimmer without the artifacts of TAA (ghosting).23

## ---

**4\. The Effectiveness of Detail Mapping at 20km**

The user asks: *"Would Detail Mapping (adding a noise texture overlay) help hide low-res textures at 20km, or will it just add more noise?"*  
**Verdict: It will just add more noise.** Detail mapping at 20km is strictly counter-productive and should be disabled via distance-based fading.3

### **4.1 The Nyquist Frequency Violation**

Detail maps are typically high-frequency tiling textures (e.g., a 2m x 2m texture representing grass blades or asphalt grain).

* **Tile Frequency:** A 2m texture repeats 10,000 times over a 20km distance.  
* **Pixel Frequency:** At the horizon, we have established that one longitudinal pixel covers \~800 meters.

This means a single pixel contains **400 repetitions** of the detail texture ($800m / 2m$). This is a massive violation of the Nyquist limit (which requires sampling at 2x the frequency of the signal). No amount of mip-mapping can correctly represent 400 cycles of data in a single sample without devolving into noise or uniform grey.3  
If a detail map is applied at 20km:

1. **Moiré Patterns:** The interference between the pixel grid and the texture repeat rate will create "bands" or waves of false patterns that crawl across the terrain.3  
2. **Shimmering:** As the camera moves by a fraction of a meter, the sampling phase shifts, causing the pixel to flash between the peaks and troughs of the detail noise.3

### **4.2 Distance-Based Fade Solution**

The solution is to implement a **Distance Fade Logic** for the detail map layer. The detail map should only be visible where the texel density is roughly 1:1 with the pixel density (typically \< 1000m). Beyond this, the shader should transition to the "Macro Texture" (satellite imagery or splat map) alone.  
**Shader Logic:**  
We calculate a fade factor based on the distance calculated in the vertex shader. We use a smoothstep function to create a soft transition zone, avoiding a hard "line" where detail pops off.

OpenGL Shading Language

// Fragment Shader Detail Map Fading

// Constants derived from user script  
float detailStart \= 0.0;  
float detailEnd \= 2000.0; // Fade out completely by 2km

// Calculate distance to fragment  
float dist \= distance(u\_CameraPosition, v\_WorldPosition);

// Calculate fade factor (1.0 \= full detail, 0.0 \= no detail)  
// smoothstep returns 0.0 if dist \< detailStart, 1.0 if dist \> detailEnd  
// We invert it to get 1.0 \-\> 0.0  
float detailFade \= 1.0 \- smoothstep(detailStart, detailEnd, dist);

// Sample textures  
vec3 macroColor \= texture(u\_MacroMap, v\_UV).rgb;  
vec3 detailColor \= texture(u\_DetailMap, v\_UV \* tileFactor).rgb;

// Overlay blend mode (or similar) dampened by detailFade  
vec3 finalColor \= mix(macroColor, macroColor \* detailColor \* 2.0, detailFade);

By fading the detail map to 0.0 at 2km, we ensure that at 20km, the renderer is only processing the low-frequency macro texture, which is stable and appropriate for that viewing distance.26

## ---

**5\. Geomorphing Logic: Continuous LOD in the Vertex Shader**

The final requirement addresses geometric popping. The provided script calculates discrete LOD switch distances (e.g., LOD 0 ends at 476.4m, LOD 1 at 954.5m). If the mesh instantly snaps from LOD 0 (high poly) to LOD 1 (low poly) at exactly 476.4m, the user will see the terrain shape change.28  
Geomorphing solves this by gradually interpolating the vertex positions between the current LOD shape and the next LOD shape over a transition buffer zone.28

### **5.1 The Geomorphing Strategy**

To implement this in a vertex shader, the geometry data structure must be prepared specifically:

1. **Vertex Data:** Each vertex must "know" its position in the *current* LOD and its position in the *next* (coarser) LOD.  
   * In a heightmap-based terrain, vertices usually reside on a grid (X, Z are fixed). Only the Y (Height) changes.  
   * Therefore, we only need to morph the **Height** value.  
2. **The Morph Factor:** A uniform or attribute that tells the shader how far the vertex is into the transition zone.

### **5.2 Vertex Shader Logic Implementation**

The script defines transition distances based on SSE. We define a morph\_range (e.g., 50 meters) *before* the switch distance where the morphing occurs.  
**Data Requirements:**

* height\_LOD0: The accurate height from the high-res heightmap.  
* height\_LOD1: The height from the lower-res heightmap (sampled at the same X,Z location, usually bilinear filtered or nearest neighbor depending on the mesh topology).

**The Algorithm:**

1. Calculate horizontal distance from camera to vertex.  
2. Check if distance is within the transition zone (e.g., 426m to 476m for the LOD 0-\>1 transition).  
3. Calculate a morph\_t value (0.0 to 1.0) within this zone.  
4. Interpolate final\_height \= mix(height\_LOD0, height\_LOD1, morph\_t).

**GLSL Code Snippet:**

OpenGL Shading Language

// Vertex Shader \- Continuous Geomorphing

uniform vec3 u\_CameraPos;  
uniform vec2 u\_LOD\_Range; // x \= start of morph (e.g. 426m), y \= end of morph (e.g. 476m)

in vec3 a\_Position;       // X, Z are grid coords, Y is Height\_Fine  
in float a\_Height\_Coarse; // The height this vertex effectively has in the next LOD

void main() {  
    // 1\. Calculate Distance (Horizontal distance often sufficient for terrain)  
    float dist \= distance(u\_CameraPos.xz, a\_Position.xz);  
      
    // 2\. Calculate Morph Factor  
    // This creates a ramp from 0.0 to 1.0 as we move through the transition zone  
    // clamp ensures we stay at 0 before the zone and 1 after (though we likely swap meshes after)  
    float morph\_t \= clamp((dist \- u\_LOD\_Range.x) / (u\_LOD\_Range.y \- u\_LOD\_Range.x), 0.0, 1.0);  
      
    // Optional: Smooth the transition using a Hermite curve to prevent linear 'kinks'  
    morph\_t \= morph\_t \* morph\_t \* (3.0 \- 2.0 \* morph\_t);   
      
    // 3\. Blend Heights  
    float finalHeight \= mix(a\_Position.y, a\_Height\_Coarse, morph\_t);  
      
    // 4\. Output Position  
    vec4 worldPos \= vec4(a\_Position.x, finalHeight, a\_Position.z, 1.0);  
    gl\_Position \= u\_ViewProjection \* worldPos;  
      
    // Pass logic to fragment shader if needed (e.g. for fading textures)  
    v\_MorphFactor \= morph\_t;  
}

### **5.3 Integrating with the Python Script Constants**

The script provided lod\_expert\_optimizer.py calculates specific switch distances. To implement geomorphing, you must define a **Morph Buffer** or **Hysteresis Zone** for each level.  
Using the script's output:

* **LOD 0 Switch:** 476.4m.  
* **Recommendation:** Start morphing at **376.4m**.  
* **Shader Uniform u\_LOD\_Range:** vec2(376.4, 476.4).

When the camera is at 300m, morph\_t is 0\. The mesh is purely LOD 0\. When the camera moves to 426.4m (midpoint), morph\_t is 0.5. The vertices are halfway between their fine and coarse positions. When the camera reaches 476.4m, morph\_t is 1.0. The vertices are now geometrically identical to LOD 1\. *Critically*, at 476.4m, the engine can swap the mesh index buffer from LOD 0 to LOD 1 instantly. Because the geometry has already morphed to match LOD 1 perfectly, there is **zero visual pop**.28

## ---

**6\. Summary of Recommendations**

To eliminate the aliasing and shimmering described in 03\_shader\_artifacts.txt for a flight simulator viewing terrain at 20km:

1. **Mip-Map Bias:** Do **not** use a static negative bias. Implement an **Angle-Dependent Positive Bias** in the shader. Detect grazing angles ($N \\cdot V \< 0.1$) and apply a bias of roughly **\+3.0** to account for the 200x anisotropy vs 16x hardware limit. Combine this with distance attenuation to keep near-field terrain sharp.  
2. **Detail Mapping:** Disable detail mapping beyond **2km**. It is the primary source of high-frequency noise at 20km. Use a shader-based fade (smoothstep) to blend it out, leaving only the macro texture at the horizon.  
3. **Specular Shimmering:** Implement **Toksvig Smoothing** in the fragment shader. Use the length of the filtered normal vector to increase material roughness dynamically at distance, suppressing sub-pixel specular flickers.  
4. **Geomorphing:** Implement vertex-height blending using the distances from your script. Set a transition buffer (e.g., 100m) *before* the switch distance calculated by your SSE solver. Interpolate between Height\_Fine and Height\_Coarse based on viewer distance to ensure 100% geometric continuity during LOD swaps.

## ---

**7\. Extended Theoretical Analysis: Signal Processing in Terrain Rendering**

### **7.1 The Sampling Theorem and Terrain Representation**

The fundamental issue described in the user's prompt is a manifestation of the **Sampling Theorem**. A digital terrain model is a continuous signal $f(x, y)$ representing elevation and color. The rasterization process attempts to reconstruct this signal into a discrete grid of pixels $I\[i, j\]$.  
Perfect reconstruction requires that the sampling frequency $f\_s$ be greater than twice the highest frequency component $f\_{max}$ of the signal ($f\_s \> 2f\_{max}$).  
At a 20km distance with a grazing angle, the "signal" of the terrain texture is compressed. A texture oscillating every 1 meter (e.g., a detail map) effectively has a frequency of 1 cycle/meter.  
However, the projected sampling rate of the screen pixels along the longitudinal axis is:

$$\\text{Sampling Rate} \= \\frac{1 \\text{ pixel}}{818 \\text{ meters}} \\approx 0.0012 \\text{ samples/meter}$$  
The requirement for reconstruction is $f\_s \> 2 \\cdot 1.0 \= 2.0$.  
We have $0.0012$.  
We are undersampling by a factor of roughly **1600x** relative to the detail map frequency.  
This massive undersampling results in **aliasing**, where high-frequency texture details fold back into the lower frequencies as noise.

* **Spatial Aliasing:** Moiré patterns (static ripples).  
* **Temporal Aliasing:** Shimmering (scintillation) as the sampling grid moves relative to the signal (camera motion).

**Why Mip-Maps Fail (Without Bias):**  
Mip-maps are pre-filtered, band-limited versions of the texture. Level 0 contains all frequencies. Level $N$ contains only frequencies $\\frac{1}{2^N}$ of the original.  
Standard hardware selection for anisotropy computes the mip level based on the *minor axis* (lateral width) to preserve detail. In our case:

* Lateral footprint: 4m. Requires roughly Mip Level 2\.  
* Longitudinal footprint: 818m. Requires roughly Mip Level 9\.

If the hardware selects Mip Level 2 (to keep the 4m width sharp), it is exposing the longitudinal axis to frequencies that are valid for 4m sampling but completely invalid for 818m sampling. The 16x AF tries to smooth this, but it can only span a fraction of the 818m length. The remaining signal is aliased.  
**Conclusion:** The only mathematical solution is to force the rejection of those high frequencies.

1. **Detail Map Removal:** Manually removing the high-frequency source (detail map) at distance removes the $f\_{max}$ component entirely.  
2. **Toksvig/Roughness:** Physically-based BRDFs produce high-frequency specular spikes. Increasing roughness (Toksvig) effectively acts as a low-pass filter on the BRDF response, spreading the energy and lowering the frequency of the specular reflection to match the sampling rate.  
3. **Positive Bias:** Forces the selection of Mip Level 9 (or intermediate), ensuring the texture signal contains no frequencies higher than what the longitudinal projection can resolve.

### **7.2 Earth Curvature Implications**

The Python script calculates a curvature drop of \~31 meters at 20km. This is significant for grazing angles.  
On a flat plane, the grazing angle $\\alpha \\approx \\frac{h}{d}$.  
With curvature, the surface tilts *away* from the viewer. The effective grazing angle $\\alpha\_{eff}$ is:

$$\\alpha\_{eff} \\approx \\frac{h}{d} \- \\frac{d}{2R\_{earth}}$$

$$\\approx 0.005 \- 0.00157 \\approx 0.0034 \\text{ radians}$$  
This reduction in grazing angle ($0.005 \\to 0.0034$) increases the longitudinal footprint by another factor of roughly 1.5x ($0.005 / 0.0034$).  
This means the anisotropy is likely **worse** than the flat-earth calculation of 200x suggests. It could be closer to **300x**.  
This validates the need for aggressive mitigation strategies. The horizon isn't just far away; it is geometrically curving out of the sampling ability of the display.

## ---

**8\. Implementation Architectures**

### **8.1 Data Structures for Geomorphing**

To support the geomorphing vertex shader described in Section 5, the terrain data structure must be organized typically as a **Quadtree of Clipmaps** or **Chunked LOD**.30  
**Heightmap Organization:**

* Height data is usually stored in textures (R16F or R32F) for modern GPU displacement.  
* Instead of storing "Coarse Height" as a separate vertex attribute (which bloats memory), effective implementations often use **Texture Gather** or multiple texture samplers in the vertex shader.

**Vertex Shader optimization:**

OpenGL Shading Language

// Optimized Geomorphing using Heightmap Textures  
uniform sampler2D u\_HeightMap;  
uniform float u\_LOD\_Level; // Current level, e.g., 0, 1, 2

void main() {  
    // 1\. Sample Height for Current LOD  
    // UV coordinates aligned to current grid  
    float h\_fine \= textureLod(u\_HeightMap, uv\_fine, 0).r;  
      
    // 2\. Sample Height for Next LOD  
    // We can simulate the coarser LOD by sampling slightly offset UVs   
    // or simply relying on linear filtering of the heightmap at a lower mip/resolution  
    // For exact geomorphing, we often sample the parent node's heightmap  
    float h\_coarse \= textureLod(u\_HeightMap\_Parent, uv\_coarse, 0).r;  
      
    // 3\. Blend based on distance (as established)  
    float h\_final \= mix(h\_fine, h\_coarse, morph\_t);  
}

*Note: Storing vertex data explicitly (as in 5.2) is faster for static meshes. Sampling textures in VS (Vertex Texture Fetch) is more flexible for Clipmaps but requires careful cache management.*

### **8.2 Anisotropy Bias Lookup Table (LUT)**

Instead of calculating the complex bias formula in real-time for every pixel, a 2D Lookup Table (LUT) can be efficient.

* **X-Axis:** Distance (0 to MaxVis)  
* **Y-Axis:** Viewing Angle ($N \\cdot V$)  
* **Output:** Bias Value (R channel), Toksvig Scale (G channel)

This allows artists to "paint" the stability they need. They can force extreme blur at the horizon (bottom-right of LUT) while keeping the near-field sharp. This is similar to the BRDF Integration LUT used in PBR implementations.32

## ---

**9\. Conclusion**

The visual artifacts observed in the flight simulator—shimmering horizon, noisy terrain, and popping geometry—are the inevitable result of projecting high-frequency data onto a discrete grid at extreme grazing angles. The anisotropy ratio of \~200x identified in the user's physics check confirms that standard hardware filtering (16x) is insufficient.  
To resolve this, the rendering pipeline must transition from a passive approach (relying on hardware defaults) to an active signal-processing approach:

1. **Active Filtering:** Use Angle-Dependent Mip-Bias to forcefully band-limit texture data at the horizon.  
2. **Active Smoothing:** Use Toksvig factors to band-limit specular interactions.  
3. **Active Compositing:** Fade out detail maps to respect the Nyquist limit.  
4. **Active Geometry:** Geomorph vertices to respect temporal continuity.

Implementing these four pillars will transform the chaotic "soup of pixels" at the 20km horizon into a stable, coherent, and visually pleasing representation of the earth, matching the high standards of a "Triple-A" simulation.

### **Tables & Data Reference**

**Table 1: LOD Transition Table (Derived from lod\_expert\_optimizer.py)**

| LOD Level | Geometric Error Tolerance | Switch Distance (Ground) | Recommended Morph Start |
| :---- | :---- | :---- | :---- |
| **0** | 0.10 m | 476.4 m | \~375 m |
| **1** | 0.20 m | 954.5 m | \~800 m |
| **2** | 0.40 m | 1909.6 m | \~1700 m |
| **3** | 0.80 m | 3819.5 m | \~3400 m |
| **4** | 1.60 m | 20000.0 m (Cap) | \~18000 m |

**Table 2: Anisotropy Analysis**

| Distance | Anisotropy Ratio | Hardware Limit (16x) Status | Remediation |
| :---- | :---- | :---- | :---- |
| 500 m | 5.1x | Within Limits | None |
| 5000 m | 50.1x | Exceeded (3x) | Light Bias (+1.5) |
| 20000 m | 200.0x | **Critical Failure (12.5x)** | Heavy Bias (+3.5), Toksvig AA |

1

#### **Works cited**

1. 03\_shader\_artifacts.txt  
2. Anisotropic filtering \- Wikipedia, accessed on February 6, 2026, [https://en.wikipedia.org/wiki/Anisotropic\_filtering](https://en.wikipedia.org/wiki/Anisotropic_filtering)  
3. Artifacts in distance of landscape : r/unrealengine \- Reddit, accessed on February 6, 2026, [https://www.reddit.com/r/unrealengine/comments/1731h64/artifacts\_in\_distance\_of\_landscape/](https://www.reddit.com/r/unrealengine/comments/1731h64/artifacts_in_distance_of_landscape/)  
4. 1.18 Mipmapping and Anisotropic Filtering \- WebGPU Unleashed: A Practical Tutorial, accessed on February 6, 2026, [https://shi-yan.github.io/webgpuunleashed/Basics/mipmapping\_and\_anisotropic\_filtering.html](https://shi-yan.github.io/webgpuunleashed/Basics/mipmapping_and_anisotropic_filtering.html)  
5. Understanding Anisotropic Filtering: Enhancing Game Visuals \- Oreate AI Blog, accessed on February 5, 2026, [https://www.oreateai.com/blog/understanding-anisotropic-filtering-enhancing-game-visuals/ee2c1a4f4ce7ba6939f2a81c1f5dff2e](https://www.oreateai.com/blog/understanding-anisotropic-filtering-enhancing-game-visuals/ee2c1a4f4ce7ba6939f2a81c1f5dff2e)  
6. What Is Anisotropic Filtering? \- Intel, accessed on February 5, 2026, [https://www.intel.com/content/www/us/en/gaming/resources/what-is-anisotropic-filtering.html](https://www.intel.com/content/www/us/en/gaming/resources/what-is-anisotropic-filtering.html)  
7. Need to stop the 'shimmering' \- Virtual Reality (VR) \- Microsoft Flight Simulator Forums, accessed on February 5, 2026, [https://forums.flightsimulator.com/t/need-to-stop-the-shimmering/478955](https://forums.flightsimulator.com/t/need-to-stop-the-shimmering/478955)  
8. Shimmering with Normandy update? \- Virtual Reality and VR Controllers \- IL-2 Sturmovik Forum, accessed on February 5, 2026, [https://forum.il2sturmovik.com/topic/81003-shimmering-with-normandy-update/](https://forum.il2sturmovik.com/topic/81003-shimmering-with-normandy-update/)  
9. anisotropic filter on texture for small grazing angle \- Unreal Engine Forums, accessed on February 6, 2026, [https://forums.unrealengine.com/t/anisotropic-filter-on-texture-for-small-grazing-angle/880115](https://forums.unrealengine.com/t/anisotropic-filter-on-texture-for-small-grazing-angle/880115)  
10. Poor rendering of mountains, even with TLOD at 200 \-400 \- Install, Performance & Graphics \- Microsoft Flight Simulator Forums, accessed on February 6, 2026, [https://forums.flightsimulator.com/t/poor-rendering-of-mountains-even-with-tlod-at-200-400/726195](https://forums.flightsimulator.com/t/poor-rendering-of-mountains-even-with-tlod-at-200-400/726195)  
11. What exactly does 'Mip Bias'? : r/assettocorsa \- Reddit, accessed on February 6, 2026, [https://www.reddit.com/r/assettocorsa/comments/1fkvtnm/what\_exactly\_does\_mip\_bias/](https://www.reddit.com/r/assettocorsa/comments/1fkvtnm/what_exactly_does_mip_bias/)  
12. Scripting API: Texture.mipMapBias \- Unity \- Manual, accessed on February 6, 2026, [https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Texture-mipMapBias.html](https://docs.unity3d.com/6000.3/Documentation/ScriptReference/Texture-mipMapBias.html)  
13. Mipmaps introduction \- Unity \- Manual, accessed on February 6, 2026, [https://docs.unity3d.com/2020.3/Documentation/Manual/texture-mipmaps-introduction.html](https://docs.unity3d.com/2020.3/Documentation/Manual/texture-mipmaps-introduction.html)  
14. How to fix shimmering buildings and landscape in the distant ? : r/MicrosoftFlightSim, accessed on February 6, 2026, [https://www.reddit.com/r/MicrosoftFlightSim/comments/p042nz/how\_to\_fix\_shimmering\_buildings\_and\_landscape\_in/](https://www.reddit.com/r/MicrosoftFlightSim/comments/p042nz/how_to_fix_shimmering_buildings_and_landscape_in/)  
15. mipmap blur/flickering at grazing angle, help plz\!\! \- Rendering \- Unreal Engine Forums, accessed on February 5, 2026, [https://forums.unrealengine.com/t/mipmap-blur-flickering-at-grazing-angle-help-plz/1220007](https://forums.unrealengine.com/t/mipmap-blur-flickering-at-grazing-angle-help-plz/1220007)  
16. MipMap level drops too quickly on steep view angle, causing noticable blurry textures, accessed on February 6, 2026, [https://forums.unrealengine.com/t/mipmap-level-drops-too-quickly-on-steep-view-angle-causing-noticable-blurry-textures/2013348](https://forums.unrealengine.com/t/mipmap-level-drops-too-quickly-on-steep-view-angle-causing-noticable-blurry-textures/2013348)  
17. Mipmap selection in too much detail \- pema.dev, accessed on February 5, 2026, [https://pema.dev/2025/05/09/mipmaps-too-much-detail/](https://pema.dev/2025/05/09/mipmaps-too-much-detail/)  
18. Mipmaps \- Unity \- Manual, accessed on February 6, 2026, [https://docs.unity3d.com/6000.3/Documentation/Manual/texture-mipmaps-introduction.html](https://docs.unity3d.com/6000.3/Documentation/Manual/texture-mipmaps-introduction.html)  
19. Mipmapping with Bidirectional Techniques \- Code & Visuals, accessed on February 6, 2026, [https://blog.yiningkarlli.com/2018/10/bidirectional-mipmap.html](https://blog.yiningkarlli.com/2018/10/bidirectional-mipmap.html)  
20. Mipmaps introduction \- Unity \- Manual, accessed on February 6, 2026, [https://docs.unity3d.com/2023.2/Documentation/Manual/texture-mipmaps-introduction.html](https://docs.unity3d.com/2023.2/Documentation/Manual/texture-mipmaps-introduction.html)  
21. Improved Geometric Specular Antialiasing, accessed on February 6, 2026, [https://www.jp.square-enix.com/tech/library/pdf/ImprovedGeometricSpecularAA.pdf](https://www.jp.square-enix.com/tech/library/pdf/ImprovedGeometricSpecularAA.pdf)  
22. Filtering Distributions of Normals for Shading Antialiasing \- Research at NVIDIA, accessed on February 6, 2026, [https://research.nvidia.com/sites/default/files/pubs/2016-06\_Filtering-Distributions-of/NDFFiltering.pdf](https://research.nvidia.com/sites/default/files/pubs/2016-06_Filtering-Distributions-of/NDFFiltering.pdf)  
23. Specular Showdown in the Wild West \- Self Shadow, accessed on February 6, 2026, [https://blog.selfshadow.com/2011/07/22/specular-showdown/](https://blog.selfshadow.com/2011/07/22/specular-showdown/)  
24. Rock-Solid Shading \- Advances in Real-Time Rendering in Games, accessed on February 6, 2026, [https://advances.realtimerendering.com/s2012/Ubisoft/Rock-Solid%20Shading.pdf](https://advances.realtimerendering.com/s2012/Ubisoft/Rock-Solid%20Shading.pdf)  
25. Weird shimmering / moiré patterns on distant terrain (SDL2 \+ OpenGL voxel engine) \- Reddit, accessed on February 5, 2026, [https://www.reddit.com/r/VoxelGameDev/comments/1qqfy4g/weird\_shimmering\_moir%C3%A9\_patterns\_on\_distant/](https://www.reddit.com/r/VoxelGameDev/comments/1qqfy4g/weird_shimmering_moir%C3%A9_patterns_on_distant/)  
26. Terrain settings \- Unity \- Manual, accessed on February 6, 2026, [https://docs.unity3d.com/2018.1/Documentation/Manual/terrain-OtherSettings.html](https://docs.unity3d.com/2018.1/Documentation/Manual/terrain-OtherSettings.html)  
27. detail texture fading out into distance \- OpenGL: Advanced Coding \- Khronos Forums, accessed on February 6, 2026, [https://community.khronos.org/t/detail-texture-fading-out-into-distance/45848](https://community.khronos.org/t/detail-texture-fading-out-into-distance/45848)  
28. Terrain Geomorphing in the Vertex Shader \- Interactive Media Systems, TU Wien, accessed on February 6, 2026, [https://www.ims.tuwien.ac.at/publications/tuw-138077.pdf](https://www.ims.tuwien.ac.at/publications/tuw-138077.pdf)  
29. Implement Geomorphing between LODs · Issue \#158 · TokisanGames/Terrain3D \- GitHub, accessed on February 6, 2026, [https://github.com/TokisanGames/Terrain3D/issues/158](https://github.com/TokisanGames/Terrain3D/issues/158)  
30. Terrain \- OpenGL: Advanced Coding \- Khronos Forums, accessed on February 6, 2026, [https://community.khronos.org/t/terrain/34477](https://community.khronos.org/t/terrain/34477)  
31. Rendering of Large Scale Continuous Terrain Using Mesh Shading Pipeline \- Diva-portal.org, accessed on February 6, 2026, [https://www.diva-portal.org/smash/get/diva2:1676474/FULLTEXT01.pdf](https://www.diva-portal.org/smash/get/diva2:1676474/FULLTEXT01.pdf)  
32. Specular IBL \- LearnOpenGL, accessed on February 5, 2026, [https://learnopengl.com/PBR/IBL/Specular-IBL](https://learnopengl.com/PBR/IBL/Specular-IBL)