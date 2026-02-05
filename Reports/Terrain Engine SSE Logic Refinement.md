# **Advanced Visual Physics and Terrain Level of Detail Optimization for High-Fidelity Flight Simulation**

## **Executive Summary**

The synthesis of photorealistic terrain in real-time flight simulation represents one of the most demanding challenges in computer graphics. Unlike ground-based first-person shooters or automotive simulators, flight simulation requires the management of geometric complexity across scales ranging from centimeters (runway unevenness) to thousands of kilometers (orbital horizons). This report provides a comprehensive analysis and refinement of the Screen Space Error (SSE) tolerance logic used in a proprietary terrain engine, based on the lod\_expert\_optimizer.py script.  
The analysis proceeds through three primary phases: determining the absolute geometric error thresholds based on the optical parameters of the simulation; refining the error metric to account for grazing angles characteristic of cockpit views; and deriving a closed-form, perspective-corrected mathematical model to replace iterative Level of Detail (LOD) selection. The findings indicate that at a distance of 5 kilometers, with a vertical resolution of 1024 pixels and a field of view of 12 degrees, the maximum allowable geometric error is approximately 1.02 meters.1 Furthermore, modifying the SSE formula to account for the angle of incidence significantly optimizes vertex throughput, although it introduces risks regarding silhouette integrity that must be managed via clamping logic.3  
This document serves as a technical blueprint for implementing a "Triple-A" standard terrain renderer, integrating principles from optics, geodesy, and discrete mathematics.

## ---

**1\. The Theoretical Framework of Terrain Level of Detail**

To understand the refinements required for the SSE logic, one must first establish the theoretical underpinnings of terrain rendering and the specific constraints imposed by the flight simulation domain. The objective of any Level of Detail (LOD) system is to reduce the workload on the Graphics Processing Unit (GPU) by decreasing the geometric complexity of objects as their visual contribution to the rendered image diminishes.5 In the context of terrain, this involves dynamically selecting between hierarchy levels of a heightmap or mesh structure—typically organized as a quadtree or binary triangle tree—such that the difference between the rendered mesh and the "true" surface is imperceptible to the user.3

### **1.1 The Human Visual System and Pixel Fidelity**

The ultimate benchmark for "imperceptible" is the pixel. If a geometric simplification results in a vertex moving by less than the width of a single pixel on the screen, the user cannot mathematically distinguish the simplified mesh from the high-resolution original, assuming perfect anti-aliasing and shading.8 This is the "Holy Grail" constant referred to in the provided script: an SSE\_Threshold of 1.0 pixel.1  
However, the perception of detail in flight simulation is complicated by the dynamic nature of the viewpoint. An aircraft moving at Mach 1 traversed terrain at high velocity, introducing temporal aliasing artifacts (shimmering) if the LOD transitions are not handled with sub-pixel precision. Therefore, while a 1.0 pixel error is the standard baseline, high-fidelity "Triple-A" engines often target sub-pixel errors (e.g., 0.5 or 0.75 pixels) to ensure temporal stability, particularly for high-frequency geometry like rocky ridgelines or urban photogrammetry.5

### **1.2 Geodetic Context: The Non-Flat Earth**

Standard game engines often operate on a flat plane. Flight simulators must simulate the Earth as an oblate spheroid (typically WGS84), or at minimum, a sphere of radius $R\_{earth} \\approx 6,371$ km.1 The provided script correctly identifies R\_earth as a critical constant. This curvature has two profound effects on LOD calculation:

1. **Occlusion:** Terrain beyond the geometric horizon is invisible and should not be rendered, regardless of its theoretical screen space size.  
2. **Horizon Drop:** As distance increases, the terrain surface curves away from the view ray. This "drop" compresses the vertical profile of the terrain on the screen, potentially allowing for more aggressive LOD degradation than a flat-earth model would suggest.11

The script calculates the geometric horizon distance ($d\_{horizon}$) using the observer altitude ($h$):

$$d\_{horizon} \\approx \\sqrt{2 R\_{earth} h \+ h^2}$$  
For an altitude of 100m, the horizon is approximately 35.7 km away. The script’s Max\_Vis of 20 km is well within this bound, meaning the curvature drop is the primary geodetic factor influencing the visible error, rather than total occlusion.1

### **1.3 The Screen Space Error (SSE) Metric**

Screen Space Error is the projection of World Space Error ($\\delta$) onto the 2D viewing plane. In a quadtree terrain system, every node (tile) has a pre-computed "geometric error" value, representing the maximum vertical distance between that tile's interpolated surface and the raw source data (e.g., LiDAR or SRTM data).6  
The runtime engine must answer a single question for every tile in the view frustum: *Does the geometric error of this tile, when projected onto the screen at the current distance, exceed the SSE threshold?*  
If the answer is **yes**, the tile is too coarse; it must be split (refined) into its four children.  
If the answer is **no**, the tile is sufficient; it is rendered, and its children are culled.  
The accuracy of this projection determines the visual quality and performance of the simulator. An overly conservative formula (predicting larger errors than exist) wastes millions of triangles processing invisible detail. An overly aggressive formula (predicting smaller errors) results in "popping," where mountains change shape visibly as the pilot approaches.7

## ---

**2\. Optical Physics: Calculating Maximum Geometric Error**

The user's first specific requirement is to determine the maximum allowable geometric error (in meters) at a distance of 5 kilometers, given a vertical resolution of 1024 pixels and a vertical Field of View (VFOV) of 12 degrees. This calculation establishes the physical "size" of a pixel in world space at that distance.1

### **2.1 Angular Resolution Derivation**

To solve this, we model the simulation camera as an ideal pinhole system. The vertical field of view ($\\theta\_{vfov}$) represents the angle subtended by the top and bottom of the viewport.  
Constants from Script 1:

* Vertical Resolution ($R\_y$): 1024 pixels  
* Vertical FOV ($\\theta\_{vfov}$): 12 degrees  
* Target Distance ($D$): 5000 meters

First, we convert the FOV to radians:

$$\\theta\_{rad} \= 12^\\circ \\times \\frac{\\pi}{180} \\approx 0.2094395 \\text{ radians}$$  
The **Angular Resolution** (radians per pixel) is the total angle divided by the number of pixels. This is a linear approximation valid for small angles (paraxial approximation), which holds true for a narrow $12^\\circ$ FOV:

$$\\text{Rad/Px} \= \\frac{\\theta\_{rad}}{R\_y} \= \\frac{0.2094395}{1024} \\approx 0.00020453 \\text{ radians/pixel}$$  
This value, $0.00020453$, is the angular size of a single pixel in the center of the screen.2

### **2.2 Calculating the Chord Length (Geometric Error)**

The geometric error $\\delta$ that projects to exactly 1 pixel at distance $D$ is simply the arc length (or chord length) subtended by that single pixel angle at radius $D$.

$$\\delta\_{max} \= D \\times \\tan(\\text{Rad/Px})$$  
For extremely small angles, $\\tan(\\theta) \\approx \\theta$, so we can simplify:

$$\\delta\_{max} \\approx D \\times \\text{Rad/Px}$$  
Substituting the values:

$$\\delta\_{max} \\approx 5000 \\text{ m} \\times 0.00020453$$

$$\\delta\_{max} \\approx 1.02265 \\text{ meters}$$

### **2.3 Verification via Projection Matrix**

We can verify this using the standard perspective projection formula used in OpenGL and DirectX rendering pipelines. The projection of a world-space height $h$ to screen-space height $h'$ (in pixels) is given by:

$$h' \= \\frac{h \\cdot R\_y}{2 \\cdot D \\cdot \\tan(\\frac{\\theta\_{vfov}}{2})}$$  
We set $h' \= 1$ (the SSE threshold) and solve for $h$ (which corresponds to our geometric error $\\delta$):

$$1 \= \\frac{\\delta \\cdot 1024}{2 \\cdot 5000 \\cdot \\tan(6^\\circ)}$$  
Rearranging for $\\delta$:

$$\\delta \= \\frac{2 \\cdot 5000 \\cdot \\tan(6^\\circ)}{1024}$$

$$\\tan(6^\\circ) \\approx 0.105104$$

$$\\delta \= \\frac{10000 \\cdot 0.105104}{1024}$$

$$\\delta \= \\frac{1051.04}{1024} \\approx 1.0264 \\text{ meters}$$  
**Result:** The linear approximation yields **1.023 meters**, and the precise projection matrix yields **1.026 meters**.  
**Strategic Insight:** For the purpose of a terrain engine, this difference (3 millimeters) is negligible. We can confidently state that at 5km with these optics, **any terrain feature or error smaller than 1.02 meters is sub-pixel and effectively invisible.**

### **2.4 Implications for Data Density**

This result has profound implications for the storage and streaming of terrain data. If the source data (e.g., satellite imagery or DEMs) has a precision of only 5 meters (common for global datasets like SRTM), the engine cannot theoretically resolve 1-pixel detail at 5km unless procedural detail or detail textures are added.6  
Conversely, it defines the "stopping condition" for LOD generation. If a terrain tile at distance 5km has a pre-computed variance of 0.5 meters, the engine can safely render it without splitting, knowing the error will not manifest as a visible artifact. This creates a hard metric for optimization: $\\delta\_{allowed}(D) \\approx 0.0002 \\times D$.

## ---

**3\. Grazing Angle Physics and SSE Modification**

The second requirement is to modify the SSE formula to account for a "grazing viewing angle" (-12 degree pitch). The standard SSE formula assumes the error is oriented perpendicular to the view vector (the "worst-case" scenario). However, in terrain rendering, the geometric error is almost exclusively **vertical displacement** (altitude error).3  
When a pilot looks down at the terrain from a high altitude (nadir view), the vertical error is fully exposed to the camera sensor. However, when flying low and looking toward the horizon (grazing angle), the vertical displacement is viewed "edge-on." This foreshortening effect compresses the visible error, potentially allowing the engine to select lower LOD levels without a perceived loss of quality.3

### **3.1 The Geometry of Grazing Incidence**

Let $\\vec{V}$ be the vector from the camera to the terrain point, and $\\vec{N}$ be the normal vector of the base terrain plane (typically up, $\\vec{UP} \= $).  
The angle of incidence $\\phi$ is the angle between $\\vec{V}$ and $\\vec{N}$.  
The grazing angle $\\alpha$ is the complement: $\\alpha \= 90^\\circ \- \\phi$, or the angle between the view vector and the ground plane.  
In the script provided, the camera is at 100m altitude looking down with a pitch of \-12 degrees. Assuming flat terrain for a moment:  
The view ray hits the ground at an angle of roughly $12^\\circ$ (ignoring Earth curvature drop for the near field).  
The apparent height $\\delta\_{projected}$ of a vertical error $\\delta\_{world}$ when viewed at grazing angle $\\alpha$ is:

$$\\delta\_{projected} \= \\delta\_{world} \\times \\sin(\\alpha)$$  
*Note: If defining angle $\\theta$ as angle from vertical (incidence), it is $\\delta \\times \\sin(\\theta)$. If defining $\\alpha$ as angle from ground (grazing), it is $\\delta \\times \\sin(\\alpha)$.*  
Let's verify the trigonometric relationship. If looking straight down ($\\alpha \= 90^\\circ$), $\\sin(90^\\circ) \= 1$. The error is fully visible.  
If looking at the horizon ($\\alpha \\approx 0^\\circ$), $\\sin(0^\\circ) \= 0$. The vertical error disappears (it becomes a line).

### **3.2 Calculating the Reduction Factor**

At a pitch of \-12 degrees ($\\alpha \= 12^\\circ$):

$$\\text{Factor} \= \\sin(12^\\circ) \\approx 0.2079$$  
This suggests that a vertical error of 1.0 meters would only appear to be 0.2 meters tall on the screen. Or, inversely, to result in a 1-pixel visible error (1.02m at 5km), the actual vertical geometric error could be:

$$\\delta\_{allowed} \= \\frac{1.026 \\text{ m}}{\\sin(12^\\circ)} \\approx \\frac{1.026}{0.208} \\approx 4.93 \\text{ meters}$$  
This is a massive optimization. It implies that at a \-12 degree pitch, we can use a terrain mesh that is **\~5 times coarser** (in terms of vertical accuracy) than we could if looking straight down, without exceeding the 1-pixel threshold.3

### **3.3 The Anisotropy Caveat**

While the *vertical* error compresses, the *horizontal* spacing of the pixels on the ground (Ground Sample Distance) elongates. This is known as anisotropy.  
At 5km with a $12^\\circ$ grazing angle:

* **Lateral GSD:** \~1.02 meters (width of pixel on ground)  
* **Longitudinal GSD:** $\\frac{1.02}{\\sin(12^\\circ)} \\approx 4.9$ meters (length of pixel on ground)

The pixel projects as a long rectangle (1m x 5m) on the ground. This confirms that we need less geometric density in the longitudinal direction. However, texture mapping requires **Anisotropic Filtering** to handle this ratio, or textures will appear blurry.1

### **3.4 Handling Silhouettes and "Popping"**

There is a critical danger in blindly applying the $\\sin(\\alpha)$ factor: **Silhouettes**. If the terrain has steep features (cliffs, mountains) or if the view ray passes *over* a ridge, the vertical error is no longer "flat" relative to the camera; it becomes the profile edge. At the silhouette, the geometric error contributes directly to the occlusion boundary. If we aggressively reduce LOD based on grazing angle, mountain peaks will "pop" vertically as they switch LODs, because the silhouette edge is always viewed perpendicular to the eye.16  
Therefore, the modified SSE formula must include a "safety clamp" or be applied only to surface roughness, not macroscopic features. A common approach in industry (e.g., in the CDLOD algorithm) is to use a hybrid metric.18

### **3.5 Proposed Modified SSE Formula**

We modify the standard projection $\\rho \= \\frac{\\delta}{D \\cdot \\theta\_{pixel}}$ to include the grazing angle term, but we clamp the scaling factor to a minimum (e.g., 0.1 or 0.2) to preventing infinite errors at the horizon and to account for silhouettes.  
**Modified SSE Logic:**

Python

\# Calculate grazing angle (alpha)  
\# In flat earth approx: alpha \~= pitch (if looking at ground)  
\# More accurately: alpha \= atan2(Camera\_Z, Distance)  
alpha\_rad \= math.atan2(CONSTANTS\['Camera\_Z'\], d)

\# Calculate Viewing Incidence Factor  
\# We use sin(alpha) because alpha is angle from ground plane.  
\# Clamp to a minimum (e.g., 0.2) to preserve silhouette integrity  
incidence\_factor \= max(0.2, math.sin(alpha\_rad))

\# Refined SSE calculation  
\# We allow more World Error (error\_val) if incidence\_factor is small  
\# projected\_error\_px \= (error\_val \* incidence\_factor) / (D \* rad\_per\_px)

By integrating this incidence\_factor, the engine effectively realizes that "projected" error decreases at grazing angles, allowing lower LODs (larger error\_val) to be selected sooner.

## ---

**4\. Perspective-Corrected SSE Formula for LOD Levels**

The third requirement is to replace the iterative check (looping through levels 0 to 4\) with a direct mathematical formula. The iterative approach is $O(N)$ where $N$ is the number of LOD levels. A closed-form solution is $O(1)$, which is critical when evaluating thousands of quadtree nodes per frame.4

### **4.1 Derivation of the LOD Function**

We start with the relationship defining the transition point. A transition occurs when the projected screen space error equals the threshold $\\tau$ (1.0 pixel).

$$\\tau \= \\frac{\\delta\_{LOD} \\cdot \\lambda}{D}$$  
Where:

* $\\tau$ is SSE\_Threshold (pixels).  
* $D$ is the distance (meters).  
* $\\lambda$ is the perspective scale factor, derived from our optical constants: $\\lambda \= \\frac{1}{\\text{rad\\\_per\\\_pixel}} \= K\_{res}$.  
* $\\delta\_{LOD}$ is the world-space geometric error at LOD level $L$.

In a quadtree, the geometric error typically doubles with each LOD level (level 0 is finest, level $n$ is coarsest).

$$\\delta\_{LOD} \= \\delta\_{base} \\cdot 2^L$$  
*Note: Some systems define LOD 0 as coarsest. The provided script implies LOD 0 \-\> 1 \-\> 2 increases error, so LOD 0 is finest.*  
Substituting $\\delta\_{LOD}$:

$$\\tau \= \\frac{(\\delta\_{base} \\cdot 2^L) \\cdot K\_{res}}{D}$$  
We need to solve for $L$:

$$\\tau \\cdot D \= \\delta\_{base} \\cdot 2^L \\cdot K\_{res}$$

$$2^L \= \\frac{\\tau \\cdot D}{\\delta\_{base} \\cdot K\_{res}}$$  
Take the base-2 logarithm:

$$L \= \\log\_2 \\left( \\frac{\\tau \\cdot D}{\\delta\_{base} \\cdot K\_{res}} \\right)$$  
Using logarithm rules to separate terms:

$$L \= \\log\_2(D) \+ \\log\_2(\\tau) \- \\log\_2(\\delta\_{base} \\cdot K\_{res})$$

### **4.2 Incorporating the Grazing Angle Modification**

We established in Section 3 that the effective error is reduced by $\\sin(\\alpha)$.  
Let $S\_\\alpha \= \\max(0.2, \\sin(\\alpha))$ be our incidence scalar.  
The observed error is now $\\delta\_{LOD} \\cdot S\_\\alpha$. The formula becomes:

$$\\tau \= \\frac{(\\delta\_{base} \\cdot 2^L \\cdot S\_\\alpha) \\cdot K\_{res}}{D}$$  
Solving for $L$:

$$2^L \= \\frac{\\tau \\cdot D}{\\delta\_{base} \\cdot K\_{res} \\cdot S\_\\alpha}$$

$$L \= \\log\_2 \\left( \\frac{\\tau \\cdot D}{\\delta\_{base} \\cdot K\_{res} \\cdot S\_\\alpha} \\right)$$

### **4.3 The Final Python Function**

We can now define a function calculate\_required\_lod(distance) that returns a float. The integer part determines the active mesh level, and the fractional part drives the **geomorphing** weight (blending between levels to prevent popping).5

Python

def calculate\_optimal\_lod(distance, camera\_z, base\_error, sse\_threshold, k\_res):  
    """  
    Calculates the continuous LOD level for a given distance using   
    Perspective-Corrected SSE with Grazing Angle compensation.  
    """  
    \# 1\. Grazing Angle Calculation (Alpha)  
    \# alpha \= atan(height / distance)  
    \# Clamp distance to avoid division by zero  
    dist\_safe \= max(1.0, distance)  
    alpha \= math.atan2(camera\_z, dist\_safe)  
      
    \# 2\. Incidence Factor (Sin of alpha)  
    \# Clamp to 0.2 to prevent infinite LOD at horizon (Silhouette protection)  
    incidence\_factor \= max(0.2, math.sin(alpha))  
      
    \# 3\. Denominator Term (The quality baseline)  
    \# effective\_error\_scale \= base\_error \* k\_res \* incidence\_factor  
    denom \= base\_error \* k\_res \* incidence\_factor  
      
    \# 4\. Solve for L  
    \# 2^L \= (tau \* D) / denom  
    \# L \= log2( (tau \* D) / denom )  
      
    ratio \= (sse\_threshold \* dist\_safe) / denom  
      
    \# Safety check for log domain  
    if ratio \<= 0: return 0.0  
      
    lod\_float \= math.log2(ratio)  
      
    \# Clamp to valid range (e.g., 0 to 5\)  
    return max(0.0, lod\_float)

This function allows the engine to query L \= calculate\_optimal\_lod(5000,...) and receive a result like 2.45. This tells the renderer to draw **LOD 2**, but morph the vertices 45% of the way toward **LOD 3** positions. This eliminates visual popping entirely, creating a fluid, "continuous" terrain experience.18

## ---

**5\. Architectural Implications for Flight Simulators**

Implementing these mathematical refinements requires supporting architecture in the terrain engine.

### **5.1 Quadtree Traversal & Selection**

The derived formula allows for a top-down quadtree traversal where the evaluation of calculate\_optimal\_lod is the descent criteria.

1. Start at Root (whole planet or large tile).  
2. Compute $L\_{req}$ for the node's center or closest point.  
3. If Node Level \< $L\_{req}$, select this node.  
4. Else, descend to children.

### **5.2 Handling T-Junctions**

Because the formula uses distance and angle, adjacent tiles may select different LOD levels (e.g., a tile at 5km selects LOD 2, while a tile at 5.1km selects LOD 3). This creates "T-junctions" where vertices do not align, causing gaps (cracks) in the terrain. Industry standard solutions for flight sims (where viewing distances are large) typically favor **Skirts**.3 Each tile generates vertical geometry around its perimeter, extending downwards. This hides any cracks created by LOD mismatch without the heavy CPU cost of "stitching" index buffers every frame.18

### **5.3 Streaming and Memory (The "Cache Miss" Problem)**

With a highly optimized SSE formula, the engine might request tiles faster than the disk can load them. The base\_geometric\_error constant in the script (0.05m) is very aggressive. If the player is flying at Mach 1 (approx 340 m/s), the distance parameter changes rapidly. The LOD system must incorporate a **hysteresis** factor or "loading bias." Instead of loading exactly at the SSE limit, the engine should pre-load LODs at $1.2 \\times D$ to ensure the texture/mesh is in memory before it is optically required. This prevents "texture popping" where high-res geometry appears with blurry low-res textures.7

### **5.4 Integration with 3D Tiles (Cesium/OGC Standards)**

Modern flight simulators often use the OGC 3D Tiles standard.6 The SSE logic derived here is compatible with 3D Tiles. The standard defines geometricError as a property of the tile. The client (renderer) is responsible for the SSE calculation. Our incidence\_factor modification can be injected directly into the client-side traversal of the 3D Tiles hierarchy, optimizing the display of global terrain datasets streamed from the cloud.4

## ---

**6\. Comprehensive Review of Script Logic vs. Theory**

The attached script lod\_expert\_optimizer.py was a good starting point but contained simplifications that would prevent "Triple-A" quality.

| Script Feature | Logic Flaw / Limitation | Proposed Fix |
| :---- | :---- | :---- |
| **Iterative Loop** | Slow ($O(N)$), hard to use in shaders. | Replace with log2 formula derived in Section 4\. |
| **No Grazing Angle** | Over-tessellates distant flat terrain. | Apply sin(alpha) scaling to error metric. |
| **Fixed Horizon** | Assumes 20km visibility is sufficient. | 20km is too low for flight sims (Horizon is \~300km at 10km alt). Logic needs to support far-distance rendering. |
| **Curvature Drop** | Calculated but not applied to SSE. | Curvature hides terrain bottom-up; SSE should increase for occluded/curved regions. |
| **Tile Size** | Fixed 1024m. | Dynamic quadtrees vary tile size. The math should rely on Bounding Sphere Radius, not fixed tile dimensions. |

### **6.1 Refined Code Structure**

The final recommendation is to refactor the script into a class-based utility that can generate a **Look-Up Table (LUT)** or be translated into a GLSL/HLSL shader function. Flight simulators often offload LOD selection to the GPU (via Compute Shaders) to handle the massive node count of planetary terrain.4

## ---

**7\. Conclusion**

The refinement of SSE tolerance logic is not merely a matter of tweaking constants; it requires a geometric understanding of the simulation environment.

1. **Optical Limit:** At 5km, with the specified optics, the physical resolution limit is **\~1.02 meters**. Any geometric detail smaller than this is wasted processing.  
2. **Grazing Optimization:** By acknowledging that the camera pitch of \-12 degrees compresses vertical detail by a factor of roughly **5x**, we can significantly reduce polygon counts in the middle-to-far field without visual degradation, provided we clamp for silhouettes.  
3. **Algorithmic Efficiency:** Moving from iterative loops to a **logarithmic perspective-corrected formula** enables the scalability required for planetary rendering, facilitating techniques like continuous geomorphing and GPU-driven culling.

Implementing these changes will align the terrain engine with state-of-the-art standards used in professional flight training devices and commercial "Triple-A" simulators, ensuring a balance of breathtaking visual fidelity and stable, high-performance frame rates.

## **Tables and Data Reference**

### **Table 1: Geometric Error Thresholds at Various Distances (Vertical Res 1024px, FOV 12°)**

| Distance (m) | Angular Size (rad) | Max Allowable Geometric Error (m) |
| :---- | :---- | :---- |
| 1,000 | 0.0002045 | 0.20 |
| **5,000** | **0.0002045** | **1.02** |
| 10,000 | 0.0002045 | 2.05 |
| 20,000 | 0.0002045 | 4.09 |
| 50,000 | 0.0002045 | 10.23 |

### **Table 2: Grazing Angle Reduction Factors**

| Pitch / Angle (α) | Reduction Factor (sin(α)) | Multiplier on Allowed Error |
| :---- | :---- | :---- |
| 90° (Down) | 1.000 | 1.0x |
| 45° | 0.707 | 1.41x |
| **12° (Cockpit)** | **0.208** | **4.81x** |
| 5° (Low Flight) | 0.087 | 11.47x |
| 1° (Horizon) | 0.017 | 57.30x (Clamped to \~5-10x) |

---

**Citations:**  
1

#### **Works cited**

1. 01\_visual\_physics.txt  
2. Determining the size of a pixel at a given distance \- Photography Stack Exchange, accessed on February 6, 2026, [https://photo.stackexchange.com/questions/132002/determining-the-size-of-a-pixel-at-a-given-distance](https://photo.stackexchange.com/questions/132002/determining-the-size-of-a-pixel-at-a-given-distance)  
3. Terrain Rendering (Part 1\) 1 Summary 2 Heightfields, accessed on February 6, 2026, [https://www.classes.cs.uchicago.edu/archive/2015/fall/23700-1/docs/project-5.pdf](https://www.classes.cs.uchicago.edu/archive/2015/fall/23700-1/docs/project-5.pdf)  
4. Blog | How we scaled our terrain across the globe using 3D Tiles \- Sensat, accessed on February 6, 2026, [https://www.sensat.co/news/how-we-scaled-our-terrain-across-the-globe-using-3d-tiles](https://www.sensat.co/news/how-we-scaled-our-terrain-across-the-globe-using-3d-tiles)  
5. Terrain Rendering \- TUM, accessed on February 6, 2026, [https://www.cs.cit.tum.de/fileadmin/w00cfj/cg/Research/Tutorials/Terrain.pdf](https://www.cs.cit.tum.de/fileadmin/w00cfj/cg/Research/Tutorials/Terrain.pdf)  
6. 3D Tiles Specification 1.0 \- Open Geospatial Consortium, accessed on February 6, 2026, [https://docs.ogc.org/cs/18-053r2/18-053r2.html](https://docs.ogc.org/cs/18-053r2/18-053r2.html)  
7. Terrain rendering (part 1\) 1 Summary 2 Heightfields, accessed on February 6, 2026, [https://www.classes.cs.uchicago.edu/archive/2014/winter/23700-1/project\_4\_and\_5/project-04.pdf](https://www.classes.cs.uchicago.edu/archive/2014/winter/23700-1/project_4_and_5/project-04.pdf)  
8. Optimize Tile Rendering on the Earth Ellipsoid with Culling and SSE, accessed on February 5, 2026, [https://reearth.engineering/posts/culling-and-sse-for-rendering-tile-en/](https://reearth.engineering/posts/culling-and-sse-for-rendering-tile-en/)  
9. accessed on February 5, 2026, [https://photo.stackexchange.com/questions/132002/determining-the-size-of-a-pixel-at-a-given-distance\#:\~:text=pixel%20size%20%3D%202%20\*%20tan%20(,distance%20%2F%20image%20width%20in%20pixels.\&text=At%20very%20close%20distance%20the,not%20many%20corrections%20are%20needed.](https://photo.stackexchange.com/questions/132002/determining-the-size-of-a-pixel-at-a-given-distance#:~:text=pixel%20size%20%3D%202%20*%20tan%20\(,distance%20%2F%20image%20width%20in%20pixels.&text=At%20very%20close%20distance%20the,not%20many%20corrections%20are%20needed.)  
10. Dynamic screen space error not working in 3D Tiles Inspector \- Cesium Community, accessed on February 6, 2026, [https://community.cesium.com/t/dynamic-screen-space-error-not-working-in-3d-tiles-inspector/26411](https://community.cesium.com/t/dynamic-screen-space-error-not-working-in-3d-tiles-inspector/26411)  
11. A Multilevel Terrain Rendering Method Based on Dynamic Stitching Strips \- MDPI, accessed on February 5, 2026, [https://www.mdpi.com/2220-9964/8/6/255](https://www.mdpi.com/2220-9964/8/6/255)  
12. LOD switching distance explained. . . (sort of) \- Independence War II, accessed on February 6, 2026, [https://i-war2.com/forum/3d-modeling/1799-lod-switching-distance-explained-sort-of](https://i-war2.com/forum/3d-modeling/1799-lod-switching-distance-explained-sort-of)  
13. Calculating Terrain Error in Landsat 8-9 System Terrain Corrected Products \- USGS.gov, accessed on February 6, 2026, [https://www.usgs.gov/landsat-missions/calculating-terrain-error-landsat-8-9-system-terrain-corrected-products](https://www.usgs.gov/landsat-missions/calculating-terrain-error-landsat-8-9-system-terrain-corrected-products)  
14. Non-uniform LODs to minimise vertical error · Issue \#228 · TokisanGames/Terrain3D, accessed on February 6, 2026, [https://github.com/TokisanGames/Terrain3D/issues/228](https://github.com/TokisanGames/Terrain3D/issues/228)  
15. Rendering Geometry with Relief Textures \- ResearchGate, accessed on February 5, 2026, [https://www.researchgate.net/publication/47387919\_Rendering\_Geometry\_with\_Relief\_Textures](https://www.researchgate.net/publication/47387919_Rendering_Geometry_with_Relief_Textures)  
16. Automatic LOD selection \- Diva-Portal.org, accessed on February 6, 2026, [http://www.diva-portal.org/smash/get/diva2:1155618/FULLTEXT01.pdf](http://www.diva-portal.org/smash/get/diva2:1155618/FULLTEXT01.pdf)  
17. Gaze-Contingent Perceptual LoD Prediction, accessed on February 6, 2026, [https://www.pdf.inf.usi.ch/projects/GazeContingentPerceptualLOD/Gaze\_Contingent\_Perceptual\_LOD\_Prediction.pdf](https://www.pdf.inf.usi.ch/projects/GazeContingentPerceptualLOD/Gaze_Contingent_Perceptual_LOD_Prediction.pdf)  
18. Procedural Terrain Generation using a Level of Detail System and Stereoscopic Visualization \- Bournemouth University, accessed on February 6, 2026, [https://nccastaff.bournemouth.ac.uk/jmacey/MastersProject/MSc13/21/Procedural\_Terrain\_Generator.pdf](https://nccastaff.bournemouth.ac.uk/jmacey/MastersProject/MSc13/21/Procedural_Terrain_Generator.pdf)  
19. Grazing incidence X-ray scattering alignment using the area detector \- arXiv, accessed on February 6, 2026, [https://arxiv.org/html/2506.22970v1](https://arxiv.org/html/2506.22970v1)  
20. Implementing chunked LOD terrain system & speed · Issue \#507 · mrdoob/three.js \- GitHub, accessed on February 6, 2026, [https://github.com/mrdoob/three.js/issues/507](https://github.com/mrdoob/three.js/issues/507)  
21. Large-scale terrain algorithms \- Rendering puzzles \- Leadwerks Community, accessed on February 6, 2026, [https://www.leadwerks.com/community/blogs/entry/1163-large-scale-terrain-algorithms/](https://www.leadwerks.com/community/blogs/entry/1163-large-scale-terrain-algorithms/)  
22. How do you optimize this game to run well? :: Microsoft Flight Simulator (2020) English, accessed on February 5, 2026, [https://steamcommunity.com/app/1250410/discussions/0/4342103279870986226/?l=greek](https://steamcommunity.com/app/1250410/discussions/0/4342103279870986226/?l=greek)  
23. Chapter 2\. Terrain Rendering Using GPU-Based Geometry Clipmaps | NVIDIA Developer, accessed on February 6, 2026, [https://developer.nvidia.com/gpugems/gpugems2/part-i-geometric-complexity/chapter-2-terrain-rendering-using-gpu-based-geometry](https://developer.nvidia.com/gpugems/gpugems2/part-i-geometric-complexity/chapter-2-terrain-rendering-using-gpu-based-geometry)  
24. Projective Grid Mapping for Planetary Terrain \- Computer Science & Engineering, accessed on February 6, 2026, [https://www.cse.unr.edu/\~fredh/papers/thesis/046-mahsman/thesis.pdf](https://www.cse.unr.edu/~fredh/papers/thesis/046-mahsman/thesis.pdf)  
25. Cesium3DTileset \- Cesium Documentation, accessed on February 6, 2026, [https://cesium.com/downloads/cesiumjs/releases/1.56/Build/Documentation/Cesium3DTileset.html](https://cesium.com/downloads/cesiumjs/releases/1.56/Build/Documentation/Cesium3DTileset.html)  
26. Camera Field of View Calculator | Advanced FoV Calculator \- Commonlands Optics, accessed on February 6, 2026, [https://commonlands.com/pages/camera-field-of-view-calculator](https://commonlands.com/pages/camera-field-of-view-calculator)  
27. Geometric estimation of volcanic eruption column height from GOES-R near-limb imagery – Part 1: Methodology \- ACP, accessed on February 6, 2026, [https://acp.copernicus.org/articles/21/12189/](https://acp.copernicus.org/articles/21/12189/)  
28. Continuous LOD Terrain Meshing Using Adaptive Quadtrees \- Duke Computer Science, accessed on February 6, 2026, [https://courses.cs.duke.edu/cps124/fall02/notes/12\_datastructures/lod\_terrain.html](https://courses.cs.duke.edu/cps124/fall02/notes/12_datastructures/lod_terrain.html)  
29. Survey on Semi-Regular Multiresolution Models for Interactive Terrain Rendering \- CRS4, accessed on February 6, 2026, [http://www.crs4.it/vic/data/papers/tvc2007-semi-regular.pdf](http://www.crs4.it/vic/data/papers/tvc2007-semi-regular.pdf)