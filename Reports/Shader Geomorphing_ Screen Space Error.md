# **Mathematical Foundations and Perceptual Optimization of Geomorphing in Large-Scale Terrain Rendering**

## **Executive Summary**

The synthesis of high-fidelity terrain rendering in flight simulation requires a delicate balance between geometric precision, computational throughput, and perceptual stability. As virtual environments scale to planetary dimensions—incorporating constants such as the Earth's radius ($R\_{earth} \\approx 6,371$ km) and visibility ranges exceeding 20 kilometers—the management of geometric complexity becomes the primary bottleneck in the graphics pipeline.1 Level of Detail (LOD) algorithms mitigate this by simplifying mesh geometry as a function of distance; however, discrete transitions between these levels introduce "popping," a visual artifact that breaks temporal coherence and immersion.2  
Geomorphing, the continuous interpolation of vertex attributes between discrete LOD states, offers a solution to this discontinuity. This report provides a rigorous derivation of the mathematical framework linking Screen Space Error (SSE) to a normalized Morph Factor ($\\mu$), evaluates the architectural trade-offs between CPU-side and GPU-side implementations, and analyzes the psychophysical implications of visual linearization curves. The analysis confirms that a shader-based, per-vertex SSE calculation using global optical constants provides superior scalability and visual quality compared to CPU-based patch constants, while non-linear interpolation curves (specifically Cubic Hermite splines) are essential for masking the mechanics of the transition from the human visual system.

## **1\. Physical and Optical Configuration of the Virtual Lens**

To derive a robust Screen Space Error metric, one must first establish the optical properties of the simulation environment. The "SSE Threshold," often referred to as the "Holy Grail" constant in the provided documentation, is not an arbitrary value but a function of the display resolution, field of view, and the geometric relationship between the observer and the terrain surface.1

### **1.1 The Optical Derivation of the Projection Constant**

The fundamental objective of the SSE metric is to project a world-space geometric deviation ($\\delta$) onto the 2D plane of the viewport to determine its size in pixels ($\\rho$). This projection is governed by the angular resolution of the virtual camera.  
Based on the expert configuration provided:

* **Vertical Screen Resolution ($Res\_Y$):** 1024 pixels.  
* **Vertical Field of View ($FOV\_V$):** 12.0 degrees.  
* **Camera Pitch ($\\theta\_{pitch}$):** \-12.0 degrees.

The first step is converting the Field of View from degrees to radians to facilitate trigonometric operations:

$$fov\_{rad} \= FOV\_V \\cdot \\frac{\\pi}{180} \= 12.0 \\cdot \\frac{3.14159}{180} \\approx 0.20944 \\text{ radians}$$  
This value represents the total vertical angle subtended by the viewport. From this, we derive the angular density of the display, defined as the number of radians covered by a single pixel height at the center of the screen ($Rad\_{pixel}$):

$$Rad\_{pixel} \= \\frac{fov\_{rad}}{Res\_Y} \= \\frac{0.20944}{1024} \\approx 2.045 \\times 10^{-4} \\text{ radians/pixel}$$  
This constant, $Rad\_{pixel}$, is the inverse of the "Lens Constant" ($K$) utilized in projection formulas. It establishes the baseline sensitivity of the optical system: any geometric feature subtending an angle smaller than $Rad\_{pixel}$ is theoretically sub-pixel and thus invisible to the observer (ignoring aliasing artifacts).  
The projection constant $K$ (referred to as Const in the provided script logic) scales world-space error into pixel-space error. It is derived as follows, assuming a pinhole camera model where the projection plane is at a unit distance adjusted for field of view:

$$K \= \\frac{Res\_Y}{2 \\cdot \\tan(\\frac{fov\_{rad}}{2})}$$  
For small angles, $\\tan(\\theta) \\approx \\theta$. Given the narrow FOV of 12 degrees ($0.20944$ rads), the small-angle approximation holds with high precision. Thus, the relationship simplifies to the inverse of the angular resolution:

$$K \\approx \\frac{1}{Rad\_{pixel}} \= \\frac{1024}{0.20944} \\approx 4889.2$$  
This value, $K \\approx 4889.2$, is the scalar that relates the ratio of error-to-distance ($\\delta/D$) to screen pixels. It implies that for every unit of angular error (in radians), the screen renders approximately 4889 pixels.

### **1.2 The Role of Camera Pitch and Altitude**

The provided configuration includes camera altitude ($Z\_{cam} \= 100.0$m) and pitch ($\\theta\_{pitch} \= \-12.0^\\circ$). In terrain rendering, particularly for flight simulators, these parameters are critical for determining the "Horizon Distance" and the validity of flat-earth approximations.  
With an Earth radius $R\_{earth} \= 6,371,000$ meters, the horizon distance $d\_{horizon}$ is calculated as:

$$d\_{horizon} \\approx \\sqrt{2 \\cdot R\_{earth} \\cdot Z\_{cam}} \\approx \\sqrt{2 \\cdot 6,371,000 \\cdot 100} \\approx 35,696 \\text{ meters}$$  
The configured Max\_Vis is 20,000 meters, which is well within the geometric horizon.1 However, the camera pitch of \-12 degrees suggests a downward-looking view (e.g., landing approach or ground targeting). This orientation affects the screen-space error distribution. Pixels at the bottom of the screen represent geometry significantly closer than pixels at the top (the horizon). A robust SSE implementation must account for this by calculating distance $D$ per vertex rather than per tile, as the depth gradient across a tile can be extreme in grazing-angle scenarios.4

## **2\. Derivation of the Screen Space Error (SSE) Formula**

The core mathematical task is to derive the link between the Screen Space Error metric and the morph factor used in the vertex shader. We begin with the fundamental projection equation provided in the system logic.

### **2.1 The Geometric Error Projection**

Let $\\delta$ be the world-space geometric error. This value represents the maximum vertical deviation between the current LOD mesh and the true surface (or the next highest LOD). In continuous LOD schemes like CDLOD or Geometry Clipmaps, $\\delta$ is typically precomputed for each level of the quadtree.6  
The projected screen-space error $\\rho$ (in pixels) for a vertex at distance $D$ from the camera is given by:

$$\\rho \= \\frac{\\delta}{D} \\cdot K$$  
Where:

* $\\delta$: World-space error (meters).  
* $D$: Linear distance from the camera viewpoint to the vertex (meters).  
* $K$: The projection constant derived in Section 1.1 ($\\approx 4889.2$).

This formula aligns with the logic snippet provided: Error\_Projected \= Error\_World \* (1/D) \* Const.1 It assumes a worst-case scenario where the error displacement is perpendicular to the view vector.

### **2.2 Solving for Transition Distances**

To optimize the LOD transitions, we must solve for the distance $D\_{transition}$ at which the projected error $\\rho$ exactly equals the allowable threshold $\\tau\_{sse}$ (1.0 pixel).  
Rearranging the projection formula:

$$\\tau\_{sse} \= \\frac{\\delta}{D\_{transition}} \\cdot K$$

$$D\_{transition} \= \\frac{\\delta \\cdot K}{\\tau\_{sse}}$$  
For a target threshold $\\tau\_{sse} \= 1.0$:

$$D\_{transition} \= \\delta \\cdot K$$  
This linear relationship implies that the transition distance for a given LOD level is directly proportional to the geometric error of that level. If LOD 0 has an error of 0.1m, it can be maintained until $D \= 0.1 \\cdot 4889.2 \\approx 489$ meters. If LOD 1 has an error of 0.2m, it is valid until $D \\approx 978$ meters. This provides the mathematical basis for the "LOD Transition Table" referenced in the optimizer script.1

## **3\. Deriving the Morph Factor Logic**

The user requirement specifies a distinct logic for the morph factor $\\mu$ (a value between 0.0 and 1.0):

* morph \= 0 when Error \< 0.5px.  
* morph \= 1 when Error approaches 1.0px.

This introduces a **Transition Window** in screen space, defined by a lower bound $\\rho\_{min} \= 0.5$ and an upper bound $\\rho\_{max} \= 1.0$.

### **3.1 The Linear Interpolation (Lerp) Derivation**

We need a function $f(\\rho) \\rightarrow $ that maps the projected error $\\rho$ to the morph weight $\\mu$. The simplest form is a linear remapping within the transition window.

$$\\mu \= \\frac{\\rho \- \\rho\_{min}}{\\rho\_{max} \- \\rho\_{min}}$$  
Substituting the defined thresholds:

$$\\mu \= \\frac{\\rho \- 0.5}{1.0 \- 0.5} \= \\frac{\\rho \- 0.5}{0.5} \= 2\\rho \- 1$$  
To ensure the value stays within valid bounds (saturating the morph at 0 below the start threshold and 1 above the end threshold), we apply a clamp operation:

$$\\mu \= \\text{clamp}(2\\rho \- 1, 0.0, 1.0)$$

### **3.2 Linking Morph Factor to Vertex Displacement**

In the vertex shader, this morph factor $\\mu$ drives the linear interpolation between the current vertex position ($P\_{LOD}$) and the target position in the next (coarser) LOD level ($P\_{NextLOD}$).

$$P\_{final} \= (1 \- \\mu) \\cdot P\_{LOD} \+ \\mu \\cdot P\_{NextLOD}$$  
Or equivalently:

$$P\_{final} \= \\text{mix}(P\_{LOD}, P\_{NextLOD}, \\mu)$$  
When $\\rho \< 0.5$ (error is small), $\\mu \= 0$, and the geometry remains at high detail ($P\_{LOD}$). As the error grows from 0.5px to 1.0px (as the camera moves away), the vertex slowly migrates toward $P\_{NextLOD}$. At $\\rho \= 1.0$, the vertex effectively occupies the position it will hold in the coarser LOD, allowing for an instantaneous swap of index buffers without a visual "pop".2

## **4\. Shader Efficiency: Per-Vertex SSE vs. CPU Constants**

The architectural question posed is whether to calculate the SSE and morph factor per-vertex in the shader or per-patch on the CPU. The analysis strongly favors the **Per-Vertex Shader Approach** for modern hardware architectures.

### **4.1 Option A: Per-Patch CPU Calculation**

In this approach, the CPU iterates over the quadtree, calculates the distance $D$ to the center (or bounding box) of each tile, derives a single morph constant $\\mu\_{tile}$, and passes it to the shader as a uniform.9

* **Pros:**  
  * Reduces ALU instructions in the vertex shader.  
  * Ensures all vertices in a tile morph synchronously.  
* **Cons:**  
  * **Visual Artifacts (The "Swimming" Effect):** Because the morph factor is constant across the entire tile ($1024m \\times 1024m$), vertices at the near edge of the tile morph at the same rate as vertices at the far edge. In a flight simulator with a grazing view angle ($12^\\circ$ FOV, $-12^\\circ$ pitch), the depth disparity across a single tile can be massive. Vertices near the camera will appear to "wait" for the far vertices to reach the error threshold, then morph abruptly, or morph prematurely.10  
  * **Batching Inefficiency:** Passing a unique uniform per tile breaks draw call batching (instancing). You cannot draw 100 tiles in a single call if each requires a different u\_MorphFactor uniform update.12

### **4.2 Option B: Per-Vertex Shader Calculation**

In this approach, the CPU passes only the global camera position and projection constants ($K$). The vertex shader calculates its own distance $D$, projects its own error $\\rho$, and derives its own $\\mu$.8

* **Pros:**  
  * **Visual Precision:** Every vertex morphs based on its specific distance. This eliminates "swimming" artifacts and allows for a seamless wave of morphing that travels across the terrain surface exactly matching the view frustum's depth gradient.8  
  * **Massive Instancing:** Since the logic is procedural and depends only on vertex position (which is an attribute) and globals, thousands of terrain tiles can be rendered in a single instanced draw call (or via MultiDrawIndirect), drastically reducing CPU overhead.3  
  * **Seamlessness:** Shared vertices between adjacent tiles will calculate the exact same distance $D$ (and thus the same $\\mu$), ensuring no cracks appear at tile boundaries without requiring complex stitching logic.6  
* **Cons:**  
  * **ALU Cost:** Adds a square root (distance()) and a few multiplications per vertex. However, on modern GPUs (which handle millions of vertices per frame easily), this cost is negligible compared to the bandwidth savings of reduced draw calls.14

### **4.3 Conclusion on Efficiency**

**The recommendation is to pass CameraPosition, CameraPitch, and ScreenResolution (wrapped in the constant $K$) to the shader and calculate SSE per-vertex.**  
Modern GPU architectures are ALU-heavy and bandwidth-limited. Offloading the perspective calculation to the vertex shader allows the CPU to focus on culling and streaming, while the GPU handles the fine-grained visual transitions. The bandwidth cost of updating uniforms per-patch significantly outweighs the trivial instruction cost of calculating $D \= \\text{length}(P \- P\_{cam})$ in the shader.7

## **5\. Visual Linearization: The Case for Non-Linear Morph Curves**

The user asks if the morph curve should be non-linear (e.g., exponential) to match the visual "pop" magnitude. This touches on the psychophysics of perception—specifically, how the human eye perceives geometric change over distance.

### **5.1 The Problem with Linear Interpolation**

While the mapping from $\\rho$ to $\\mu$ derived in Section 3.1 is mathematically linear ($2\\rho \- 1$), the *perception* of that change is not.

1. **Perspective Non-Linearity:** The screen-space size of an object scales with $1/D$. A linear displacement in world space ($P\_{final} \= P\_{LOD} \+ \\mu \\Delta$) results in a non-linear displacement in screen space as the camera moves.19  
2. **Weber-Fechner Law:** Human sensory perception is logarithmic. We notice changes relative to the magnitude of the stimulus. A 1cm shift is noticeable at 1 meter, but invisible at 1 kilometer.21

If we use a linear interpolator ($\\mu\_{linear}$), the morph might appear to start slowly and then accelerate suddenly as the error threshold is reached, or vice versa, creating a "pulsing" effect rather than a smooth fade.22

### **5.2 Smoothstep (Cubic Hermite Interpolation)**

The standard industry solution for visual linearization in geomorphing is the **Smoothstep** function (or a Cubic Hermite spline). This curve has a derivative of zero at both $\\mu=0$ and $\\mu=1$, which creates an "ease-in / ease-out" behavior.24

$$\\mu\_{smooth} \= \\mu^2 (3 \- 2\\mu)$$  
**Why Smoothstep?**

* **Velocity Masking:** By slowing down the rate of change near the start and end of the transition (where the eye is most sensitive to the sudden onset of motion), Smoothstep hides the mechanical nature of the LOD switch.23  
* **Visual Continuity:** It prevents the "mach band" effect where the derivative of the motion changes abruptly at the transition boundaries ($0.5$ and $1.0$ px).24

### **5.3 Exponential Curves**

The user suggested an exponential curve. While exponential functions ($e^x$) can compensate for the $1/D$ perspective scaling, they are often too aggressive for terrain morphing.27 An exponential curve tends to keep the vertex close to its original position for a long time and then snaps it to the new position at the very end, effectively re-introducing the pop it was meant to hide.23

### **5.4 Recommendation: Visual Linearization Strategy**

The recommended approach is to use the **Linear Mapping** for the error threshold normalization (to get $\\mu \\in $) and then apply a **Smoothstep** function to the result before using it for vertex interpolation.  
**Shader Implementation Logic:**

OpenGL Shading Language

// 1\. Calculate linear morph factor based on SSE  
float morphLinear \= clamp((sse \- 0.5) / 0.5, 0.0, 1.0);

// 2\. Apply non-linear curve for visual smoothness (Ease-In/Ease-Out)  
float morphVisual \= smoothstep(0.0, 1.0, morphLinear);

// 3\. Interpolate Geometry  
vec3 position \= mix(posHigh, posLow, morphVisual);

This combination ensures the transition triggers predictably based on pixel error (linear thresholding) but executes with a perceptual smoothness that hides the motion (non-linear interpolation).23

## **6\. Advanced Implementation Nuances**

To fully satisfy the "Triple-A" requirement, the report must address several implementation details that arise from the interaction of SSE, geomorphing, and large-scale rendering.

### **6.1 Lighting Stability During Morphing**

A critical insight often overlooked is that morphing vertex positions changes the geometric normals of the triangles. If shading is calculated using these dynamic normals, the terrain will appear to "shimmer" or "crawl" as the lighting calculation fluctuates during the transition.30  
**Solution:** Decouple shading normals from geometric normals.

* Use a high-resolution normal map for lighting that does *not* morph. Since texture coordinates (UVs) remain stable during the vertex morph, the lighting remains consistent even as the underlying polygon shape changes.3  
* Alternatively, interpolate the normals in the shader: $N\_{final} \= \\text{mix}(N\_{high}, N\_{low}, \\mu)$. However, this can still cause specular highlights to slide. The normal map approach is superior for visual stability.3

### **6.2 Earth Curvature and Distance Calculations**

For a flight simulator with $R\_{earth} \= 6,371$ km, the flat-Earth distance formula $D \= \\sqrt{\\Delta x^2 \+ \\Delta y^2 \+ \\Delta z^2}$ introduces errors at long distances. A vertex at the horizon is technically "lower" due to curvature, which might affect the $\\delta$ error estimation.33  
However, because SSE is a *conservative* metric intended to guarantee visual quality, using the straight-line chord distance (standard Euclidean distance) is acceptable and actually results in slightly higher quality (closer LOD switch) than using the arc distance. The critical optimization is ensuring that the height calculations are **camera-relative**. To avoid floating-point jitter (the "trembling" of vertices at large coordinates), all vertex positions should be subtracted from the camera position on the CPU (using double precision) and passed to the GPU as float relative offsets.34

### **6.3 Handling T-Junctions (Cracks)**

When adjacent tiles are at different LOD levels, the shared edge vertices of the higher-detail tile will morph while the edge vertices of the lower-detail tile (which are already at the target position) do not. This creates mathematical alignment, but if the morph is not perfectly synchronized, T-junctions can appear.3  
To prevent holes:

1. **Vertical Skirts:** Append "skirts" (downward facing geometry) to the edges of all tiles. This is the cheapest and most robust solution for geomorphing systems, as it hides any temporary misalignment during the morph.5  
2. **Locked Edges:** Enforce that boundary vertices on a tile edge always morph using the logic of the *coarser* neighbor. This requires passing neighbor LOD information to the shader, which increases complexity and breaks batching. Skirts are generally preferred in modern engines.5

## **7\. Conclusions and Recommendations**

The derivation of the Screen Space Error for the provided flight simulator configuration establishes that the transition distance is linearly proportional to the geometric error $\\delta$ scaled by the optical constant $K \\approx 4889.2$. This relationship allows for the precise construction of LOD transition tables that guarantee sub-pixel accuracy.  
To address the user's specific questions:

1. **Morph Factor Calculation:** The correct mathematical linkage is a clamped linear remapping of the projected error $\\rho$ from the range $\[0.5, 1.0\]$ to $\[0.0, 1.0\]$.  
   $$\\mu \= \\text{clamp}(2 \\cdot (\\frac{\\delta \\cdot K}{D}) \- 1, 0.0, 1.0)$$  
2. **Shader Efficiency:** Calculating SSE per-vertex in the shader is the superior architectural choice. It maximizes GPU parallelism, enables massive instancing, and eliminates the visual artifacts (swimming) associated with per-patch CPU constants.  
3. **Visual Linearization:** A linear interpolator is mathematically sufficient but perceptually inferior. The use of a **Smoothstep** curve ($3\\mu^2 \- 2\\mu^3$) is strongly recommended to linearize the perception of the transition and mask the onset of geometric popping.

By integrating these mathematical principles with camera-relative rendering and stable normal mapping, the system will achieve the "Holy Grail" of artifact-free, infinite-view terrain rendering suitable for Triple-A simulation standards.

| Metric | Derived Value / Recommendation |
| :---- | :---- |
| **Projection Constant ($K$)** | $\\approx 4889.2$ pixels/radian |
| **Transition Start ($\\rho\_{start}$)** | 0.5 pixels |
| **Transition End ($\\rho\_{end}$)** | 1.0 pixels |
| **Interpolation Curve** | Smoothstep (Cubic Hermite) |
| **Compute Location** | Vertex Shader (Per-Vertex) |
| **Coordinate System** | Camera-Relative (High Precision) |

This framework provides a mathematically rigorous and perceptually optimized foundation for the implementation of geomorphing in high-performance terrain engines.

#### **Works cited**

1. 05\_integration\_geomorphing.txt  
2. Terrain Rendering \- TUM, accessed on February 6, 2026, [https://www.cs.cit.tum.de/fileadmin/w00cfj/cg/Research/Tutorials/Terrain.pdf](https://www.cs.cit.tum.de/fileadmin/w00cfj/cg/Research/Tutorials/Terrain.pdf)  
3. Terrain Geomorphing in the Vertex Shader \- Interactive Media Systems, TU Wien, accessed on February 6, 2026, [https://www.ims.tuwien.ac.at/publications/tuw-138077.pdf](https://www.ims.tuwien.ac.at/publications/tuw-138077.pdf)  
4. Screen-space error: how can I compute? : r/GraphicsProgramming \- Reddit, accessed on February 6, 2026, [https://www.reddit.com/r/GraphicsProgramming/comments/1d1mso3/screenspace\_error\_how\_can\_i\_compute/](https://www.reddit.com/r/GraphicsProgramming/comments/1d1mso3/screenspace_error_how_can_i_compute/)  
5. Adaptive Hardware-accelerated Terrain Tessellation, accessed on February 6, 2026, [https://media.contentapi.ea.com/content/dam/eacom/frostbite/files/adaptive-terrain-tessellation.pdf](https://media.contentapi.ea.com/content/dam/eacom/frostbite/files/adaptive-terrain-tessellation.pdf)  
6. Continuous Distance-Dependent Level of Detail for Rendering Heightmaps (CDLOD) \- AggroBird, accessed on February 5, 2026, [https://aggrobird.com/files/cdlod\_latest.pdf](https://aggrobird.com/files/cdlod_latest.pdf)  
7. Chapter 2\. Terrain Rendering Using GPU-Based Geometry Clipmaps | NVIDIA Developer, accessed on February 6, 2026, [https://developer.nvidia.com/gpugems/gpugems2/part-i-geometric-complexity/chapter-2-terrain-rendering-using-gpu-based-geometry](https://developer.nvidia.com/gpugems/gpugems2/part-i-geometric-complexity/chapter-2-terrain-rendering-using-gpu-based-geometry)  
8. Procedural Terrain Generation using a Level of Detail System and Stereoscopic Visualization \- Bournemouth University, accessed on February 5, 2026, [https://nccastaff.bournemouth.ac.uk/jmacey/MastersProject/MSc13/21/Procedural\_Terrain\_Generator.pdf](https://nccastaff.bournemouth.ac.uk/jmacey/MastersProject/MSc13/21/Procedural_Terrain_Generator.pdf)  
9. Should calculations be done on the CPU or GPU? \- Game Development Stack Exchange, accessed on February 5, 2026, [https://gamedev.stackexchange.com/questions/176137/should-calculations-be-done-on-the-cpu-or-gpu](https://gamedev.stackexchange.com/questions/176137/should-calculations-be-done-on-the-cpu-or-gpu)  
10. Irregular Morphing for Real-Time Rendering of Large Terrain \- Semantic Scholar, accessed on February 6, 2026, [https://pdfs.semanticscholar.org/72bc/b0ad854a9692071b503fb611075d89c196a2.pdf](https://pdfs.semanticscholar.org/72bc/b0ad854a9692071b503fb611075d89c196a2.pdf)  
11. The Geomorph Tools \- SourceForge, accessed on February 5, 2026, [https://geomorph.sourceforge.io/tools/en/tools\_index.html](https://geomorph.sourceforge.io/tools/en/tools_index.html)  
12. Is it more efficient to transform vertices on the CPU or the GPU? \- Game Development Stack Exchange, accessed on February 5, 2026, [https://gamedev.stackexchange.com/questions/90834/is-it-more-efficient-to-transform-vertices-on-the-cpu-or-the-gpu](https://gamedev.stackexchange.com/questions/90834/is-it-more-efficient-to-transform-vertices-on-the-cpu-or-the-gpu)  
13. Geometric Transformations on the CPU vs GPU \- Game Development Stack Exchange, accessed on February 6, 2026, [https://gamedev.stackexchange.com/questions/3300/geometric-transformations-on-the-cpu-vs-gpu](https://gamedev.stackexchange.com/questions/3300/geometric-transformations-on-the-cpu-vs-gpu)  
14. On Vertex Shader Performance, accessed on February 5, 2026, [https://paroj.github.io/gltut/Positioning/Tut03%20On%20Vertex%20Shader%20Performance.html](https://paroj.github.io/gltut/Positioning/Tut03%20On%20Vertex%20Shader%20Performance.html)  
15. Rendering of Large Scale Continuous Terrain Using Mesh Shading Pipeline \- Diva-portal.org, accessed on February 6, 2026, [https://www.diva-portal.org/smash/get/diva2:1676474/FULLTEXT01.pdf](https://www.diva-portal.org/smash/get/diva2:1676474/FULLTEXT01.pdf)  
16. Per vertex shading vs per fragment shading on large models \- Stack Overflow, accessed on February 5, 2026, [https://stackoverflow.com/questions/19292893/per-vertex-shading-vs-per-fragment-shading-on-large-models](https://stackoverflow.com/questions/19292893/per-vertex-shading-vs-per-fragment-shading-on-large-models)  
17. When to make LODs. Understanding model costs | by Jason Booth | Medium, accessed on February 5, 2026, [https://medium.com/@jasonbooth\_86226/when-to-make-lods-c3109c35b802](https://medium.com/@jasonbooth_86226/when-to-make-lods-c3109c35b802)  
18. Implement Geomorphing between LODs · Issue \#158 · TokisanGames/Terrain3D \- GitHub, accessed on February 6, 2026, [https://github.com/TokisanGames/Terrain3D/issues/158](https://github.com/TokisanGames/Terrain3D/issues/158)  
19. Voxels and Seamless LOD Transitions \- dexyfex.com, accessed on February 6, 2026, [https://dexyfex.com/2016/07/14/voxels-and-seamless-lod-transitions/](https://dexyfex.com/2016/07/14/voxels-and-seamless-lod-transitions/)  
20. Rendering Massive Terrains using Chunked Level of, accessed on February 6, 2026, [https://www.classes.cs.uchicago.edu/archive/2015/fall/23700-1/final-project/chunked-lod.pdf](https://www.classes.cs.uchicago.edu/archive/2015/fall/23700-1/final-project/chunked-lod.pdf)  
21. Linear and nonlinear coding \- Charles Poynton, accessed on February 6, 2026, [https://poynton.ca/notes/Timo/index.html](https://poynton.ca/notes/Timo/index.html)  
22. Continuous LOD Terrain Meshing Using Adaptive Quadtrees \- Duke Computer Science, accessed on February 6, 2026, [https://courses.cs.duke.edu/cps124/fall02/notes/12\_datastructures/lod\_terrain.html](https://courses.cs.duke.edu/cps124/fall02/notes/12_datastructures/lod_terrain.html)  
23. glsl \- What's the difference of using smoothstep and linear interpolation for antialiasing?, accessed on February 6, 2026, [https://computergraphics.stackexchange.com/questions/14285/whats-the-difference-of-using-smoothstep-and-linear-interpolation-for-antialias](https://computergraphics.stackexchange.com/questions/14285/whats-the-difference-of-using-smoothstep-and-linear-interpolation-for-antialias)  
24. Smoothstep \- Wikipedia, accessed on February 5, 2026, [https://en.wikipedia.org/wiki/Smoothstep](https://en.wikipedia.org/wiki/Smoothstep)  
25. Smoothstep Node | Shader Graph | 6.9.2 \- Unity \- Manual, accessed on February 6, 2026, [https://docs.unity3d.com/Packages/com.unity.shadergraph@6.9/manual/Smoothstep-Node.html](https://docs.unity3d.com/Packages/com.unity.shadergraph@6.9/manual/Smoothstep-Node.html)  
26. Why were Linear, SmoothStep and SmootherStep interpolation functions defined the way they were? : r/askmath \- Reddit, accessed on February 5, 2026, [https://www.reddit.com/r/askmath/comments/14mkp1m/why\_were\_linear\_smoothstep\_and\_smootherstep/](https://www.reddit.com/r/askmath/comments/14mkp1m/why_were_linear_smoothstep_and_smootherstep/)  
27. Both, Exponential and Linear scale are impractical; What's practical? : r/visualization \- Reddit, accessed on February 6, 2026, [https://www.reddit.com/r/visualization/comments/1g865m9/both\_exponential\_and\_linear\_scale\_are\_impractical/](https://www.reddit.com/r/visualization/comments/1g865m9/both_exponential_and_linear_scale_are_impractical/)  
28. Human perception of exponentially increasing data displayed on a log scale evaluated through experimental graphics tasks | Emily A. Robinson, accessed on February 6, 2026, [https://www.emilyarobinson.com/talk/2021-07-22-phd-proposal-oral-comprehensive-exam/](https://www.emilyarobinson.com/talk/2021-07-22-phd-proposal-oral-comprehensive-exam/)  
29. Learn with me: Getting Started with Shader Functions (step, mix, smoothstep), accessed on February 5, 2026, [https://rherault.dev/articles/learn-with-me-shaders-functions](https://rherault.dev/articles/learn-with-me-shaders-functions)  
30. CDLOD issue with lighting while morphing triangles \- Stack Overflow, accessed on February 5, 2026, [https://stackoverflow.com/questions/56969269/cdlod-issue-with-lighting-while-morphing-triangles](https://stackoverflow.com/questions/56969269/cdlod-issue-with-lighting-while-morphing-triangles)  
31. 3D View issues | Substance 3D Designer \- Adobe Help Center, accessed on February 6, 2026, [https://helpx.adobe.com/substance-3d-designer/technical-issues/3d-view-issues.html](https://helpx.adobe.com/substance-3d-designer/technical-issues/3d-view-issues.html)  
32. Improved Persistent Grid Mapping \- Research Unit of Computer Graphics | TU Wien, accessed on February 6, 2026, [https://www.cg.tuwien.ac.at/research/publications/2020/houska-2020-IPGM/houska-2020-IPGM-thesis.pdf](https://www.cg.tuwien.ac.at/research/publications/2020/houska-2020-IPGM/houska-2020-IPGM-thesis.pdf)  
33. Question about CDLOD quad tree \- Game Development Stack Exchange, accessed on February 5, 2026, [https://gamedev.stackexchange.com/questions/177378/question-about-cdlod-quad-tree](https://gamedev.stackexchange.com/questions/177378/question-about-cdlod-quad-tree)  
34. Terrain Rendering (Part 1\) 1 Summary 2 Heightfields, accessed on February 6, 2026, [https://www.classes.cs.uchicago.edu/archive/2015/fall/23700-1/docs/project-5.pdf](https://www.classes.cs.uchicago.edu/archive/2015/fall/23700-1/docs/project-5.pdf)  
35. Terrain Optimization... \- OpenGL: Advanced Coding \- Khronos Forums, accessed on February 5, 2026, [https://community.khronos.org/t/terrain-optimization/46569](https://community.khronos.org/t/terrain-optimization/46569)