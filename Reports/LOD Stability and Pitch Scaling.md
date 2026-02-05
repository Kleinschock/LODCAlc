# **Architectural Stability Analysis of Pitch-Dependent Terrain Level-of-Detail Systems in Flight Simulation**

## **Executive Summary and Report Scope**

The rigorous simulation of planetary-scale terrain presents one of the most demanding challenges in real-time computer graphics. Unlike standard "ground-level" applications (First-Person Shooters or RPGs), flight simulators require the rendering engine to handle view distances exceeding 300 kilometers, managing a dataset that ranges from centimeter-scale runway details to kilometer-scale mountain ranges. To maintain interactive framerates (typically 60Hz or higher), Engine Architects must employ aggressive Level of Detail (LOD) strategies that reduce geometric complexity based on the viewer's perspective.  
A critical optimization in this domain is the scaling of geometric error metrics by the inverse cosine of the camera’s pitch angle ($1 / \\cos(\\text{Pitch})$). This heuristic posits that when the camera looks toward the horizon (a "grazing angle"), the vertical geometric error of the terrain is foreshortened on the screen, thereby allowing the engine to utilize lower-resolution meshes without perceptible visual degradation. While mathematically sound for static frames, this approach introduces significant temporal instability—specifically, "breathing" artifacts—when the camera undergoes rapid rotational oscillation, such as during aircraft turbulence.  
This report provides an exhaustive verification of the stability of scaling LOD errors by $1 / \\cos(\\text{Pitch})$. It dissects the mathematical underpinnings of Screen Space Error (SSE) projection, analyzes the causal mechanisms of breathing artifacts, and evaluates the trade-offs between rotation-dependent and translation-dependent LOD selection. Furthermore, it synthesizes industry-standard solutions, including temporal damping, hysteresis, and "worst-case" locking, drawing upon seminal research in terrain rendering (ROAM, VDPM, Chunked LOD) and empirical data from modern platforms like Microsoft Flight Simulator 2020/2024, X-Plane, and Cesium 3D Tiles. The analysis concludes with definitive architectural recommendations for stabilizing terrain rendering in high-fidelity flight simulation environments.

## ---

**Part I: The Physics and Mathematics of Error Projection**

To verify the stability of the proposed script and its heuristic, we must first establish the fundamental physics of error projection in computer graphics. The goal of any LOD system is to ensure that the difference between the rendered approximation and the "true" surface never exceeds a user-defined threshold, typically defined in screen pixels (the "Holy Grail" constant of $\\tau \= 1.0$ pixel mentioned in the context).1

### **1.1 The Geometric Projection of Error**

In a perspective projection, a geometric error in world space ($\\delta$, measured in meters) projects to a screen-space error ($\\rho$, measured in pixels). The standard projection formula, derived from the pinhole camera model, relates these quantities via the distance to the viewer ($D$) and the focal length of the camera.  
The basic isotropic projection formula, used in algorithms like Chunked LOD by Thatcher Ulrich, is:

$$\\rho \= \\frac{\\delta}{D} \\cdot K$$  
Where $K$ is a perspective scaling factor derived from the viewport resolution and the field of view (FOV):

$$K \= \\frac{\\text{ViewportHeight}}{2 \\cdot \\tan(\\frac{\\text{FOV}\_V}{2})}$$  
This formula assumes a "worst-case" orientation where the geometric error is perpendicular to the view vector.2 For example, if a terrain vertex is displaced vertically by 10 meters ($\\delta \= 10$), the formula calculates how many pixels that 10-meter displacement occupies if viewed broadside.

### **1.2 The Role of Pitch and Grazing Angles**

In flight simulation, the camera rarely views terrain broadside (nadir view). Instead, the pilot looks forward toward the horizon. At these grazing angles, vertical displacements on the terrain surface are significantly foreshortened.  
The provided script utilizes a modified error metric that accounts for this foreshortening:

$$\\text{Error}\_{\\text{Projected}} \= \\frac{\\text{Error}\_{\\text{World}} \\cdot \\cos(\\text{Pitch})}{\\text{Distance}}$$  
Here, $\\text{Pitch}$ represents the angle of the camera relative to the horizon.

* **At the Horizon ($\\text{Pitch} \\approx 0^\\circ$):** $\\cos(0) \= 1$. This implies maximum error projection. However, this interpretation in the script seems inverted compared to standard grazing angle physics. Usually, at grazing angles (looking at the horizon), the vertical error is *minimized* (foreshortened), meaning $\\cos(\\theta)$ should be approaching 0 relative to the surface normal.  
* **Standard Definition:** In terrain rendering literature, the viewing angle $\\phi$ is typically defined relative to the *surface normal* (up vector).  
  * Looking straight down (Nadir): $\\phi \= 0^\\circ$, $\\sin(\\phi) \= 0$, $\\cos(\\phi) \= 1$. The vertical error is fully visible.  
  * Looking at the horizon (Grazing): $\\phi \= 90^\\circ$, $\\cos(\\phi) \= 0$. The vertical error projects to zero (it is hidden by the perspective).

The script in question uses cos(Pitch) where Pitch is likely \-12 degrees. If Pitch is 0 at the horizon and \-90 at nadir:

* $\\text{Pitch} \= \-90^\\circ \\rightarrow \\cos(-90) \= 0$. (This would zero out the error, which is incorrect for a top-down view where error is most visible).  
* $\\text{Pitch} \= 0^\\circ \\rightarrow \\cos(0) \= 1$. (This maximizes error at the horizon).

*Correction:* It is highly probable that the heuristic intends to scale the *allowable* error, or the metric is derived using the angle between the view vector and the *ground plane*, not the normal. If we strictly follow the user's prompt ("scaling LOD errors by $1 / \\cos(\\text{Pitch})$"), we see the intention:

* As $\\text{Pitch} \\to 0$ (horizon), $\\cos(\\text{Pitch}) \\to 1$, so the scaling is $1$.  
* As $\\text{Pitch} \\to \-90$ (down), $\\cos(\\text{Pitch}) \\to 0$, and the scaling factor $1/\\cos \\to \\infty$.

*Wait, this creates a contradiction in the script's logic versus standard physics.* Let us re-examine the snippet.1 The snippet says: Error\_Projected \= Error\_World \* cos(Pitch) / Distance. If Pitch is \-12 degrees (grazing), $\\cos(-12) \\approx 0.97$. If Pitch is \-90 degrees (looking down), $\\cos(-90) \= 0$. This formula Error \* 0 / Distance yields 0 error when looking straight down. This is physically **incorrect** for vertical terrain displacement. When looking down, vertical bumps are *least* visible (they don't change the silhouette), but horizontal errors are *most* visible. Conversely, at grazing angles (pitch \-12), vertical bumps effectively change the horizon silhouette and should have *maximum* visibility.  
*Resolution:* The script likely assumes that the "Error" being measured is a **vertical height deviation** ($\\delta z$).

* **View from Top (Nadir):** You cannot see height differences; you only see texture shifting. A vertical error has 0 projection on the screen plane (orthographic approximation).  
* **View from Side (Horizon):** You see the full height displacement.  
  * Therefore, Error\_Projected *should* be proportional to $\\cos(\\text{Pitch})$ if Pitch is 0 at the horizon.  
  * At Pitch \= 0 (horizon), $\\cos(0) \= 1$. Error is max. Correct.  
  * At Pitch \= \-90 (down), $\\cos(-90) \= 0$. Error is min. Correct for *vertical* error.

Thus, the formula Error \* cos(Pitch) correctly models the visibility of *vertical height errors*. The "Breathing" comes from the fact that as the plane vibrates, this visibility factor oscillates.

### **1.3 Sensitivity Analysis of the Cosine Term**

The root of the instability lies in the derivative of the scaling factor. We are evaluating the sensitivity of the projected error $\\rho$ to changes in pitch $\\theta$:

$$\\frac{d\\rho}{d\\theta} \= \\frac{\\delta}{D} \\cdot \\frac{d}{d\\theta}(\\cos\\theta) \= \-\\frac{\\delta}{D} \\sin\\theta$$  
This derivative indicates how much the screen-space error changes for a tiny change in pitch.

* At **Nadir** ($\\theta \= \-90^\\circ$): $\\sin(-90) \= \-1$. The sensitivity is high.  
* At **Horizon** ($\\theta \= 0^\\circ$): $\\sin(0) \= 0$. The sensitivity is low.

However, the user's prompt mentions scaling LOD errors by 1 / cos(Pitch). This is the inverse operation (calculating the *allowable* world error).  
Let $\\text{Allowed}(\\delta) \= \\frac{\\tau \\cdot D}{\\cos\\theta}$.  
The sensitivity is proportional to the derivative of secant ($\\sec\\theta$):

$$\\frac{d}{d\\theta}(\\sec\\theta) \= \\sec\\theta \\tan\\theta$$

* As $\\theta \\to \-90^\\circ$, $\\tan\\theta \\to \-\\infty$. The sensitivity explodes.

This mathematical reality confirms the user's suspicion: the metric is inherently unstable, particularly at steep angles where the function approaches a singularity or rapid rate of change.

## ---

**Part II: The Instability Problem – "Breathing" Terrain**

The "breathing" artifact is a form of **temporal aliasing**. In the context of flight simulation, it manifests as the rapid expansion and contraction of terrain detail rings (LOD boundaries) in response to high-frequency camera rotation (turbulence) rather than low-frequency camera translation (flight).1

### **2.1 The Mechanism of Breathing**

Consider an aircraft flying at 10,000 feet. The engine must decide whether a mountain 20km away should be rendered at LOD 3 (high detail) or LOD 2 (medium detail).

1. **Frame $t$:** The pilot flies steady. Pitch \= \-5°. $\\cos(-5) \\approx 0.996$. The engine calculates Error\_Projected \= 0.9 pixels. The threshold is 1.0. The mountain stays at LOD 2\.  
2. **Frame $t+1$:** Turbulence hits. The nose dips. Pitch \= \-8°. $\\cos(-8) \\approx 0.990$. The projected error drops slightly (vertical error is less visible?). *Wait*, if the camera pitches *down* towards the terrain, the view becomes less grazing and more top-down.  
   * If the formula is Error \* cos(Pitch) (where 0 is horizon):  
   * Pitch \-5 deg: cos \= 0.996.  
   * Pitch \-15 deg: cos \= 0.965.  
   * Pitch \-45 deg: cos \= 0.707.  
   * As pitch steepens (looks down), the Error\_Projected *decreases*.  
3. **The Flaw:** If Error\_Projected decreases as we look down, the system might decide it can *switch to a lower LOD* (LOD 1\) because the error is now below the threshold.  
4. **The Oscillation:**  
   * Turbulence pitches the nose down (-15°). Error estimate drops. Engine switches to lower LOD (blurry).  
   * Turbulence corrects, nose pitches up (-5°). Error estimate rises. Engine switches to higher LOD (sharp).  
   * This cycle repeats at the frequency of the turbulence (e.g., 2Hz \- 10Hz).  
5. **Visual Result:** The terrain texture and geometry "breathe" or pulsate between sharp and blurry states 5 times a second.

### **2.2 Impact on Perception and Performance**

This artifact is far more detrimental than static low resolution. The human visual system is fundamentally a motion detector; it is highly sensitive to high-frequency changes in contrast or structure (flicker) in the peripheral vision.4 A terrain mesh that is statically low-poly is perceived as "background." A terrain mesh that flickers between low and high poly attracts the foveal gaze, breaking immersion and causing pilot fatigue.  
From a performance standpoint, this oscillation is disastrous.

* **Bus Saturation:** Constant switching requires the CPU to re-submit draw calls or re-stream index buffers to the GPU every few frames.6  
* **VRAM Thrashing:** If the LOD switch involves loading different texture mips, it can saturate the PCIe bus and memory controllers, leading to "stutters" or frame time spikes.8  
* **CPU Main Thread Limiting:** In engines like MSFS 2020/2024, the "MainThread" is often the bottleneck. Recalculating the quadtree for thousands of terrain tiles every frame because the pitch changed by 0.5 degrees consumes precious cycles needed for avionics and flight dynamics.10

### **2.3 Evidence from Modern Simulators**

Reports from **Microsoft Flight Simulator 2024** users confirm this behavior. Users describe terrain that "flickers and shifts" and ground textures that blur and sharpen inexplicably.12 The "ring" effect, where a circle of high detail moves with the aircraft, becomes unstable during maneuvers, creating a distraction described as "morphing" mountains.14 Similarly, **X-Plane 12** users have documented "screen-flickering" where distant terrain toggles between detailed and undetailed states in milliseconds.15 These real-world cases validate the theoretical instability of highly sensitive, view-dependent LOD metrics.

## ---

**Part III: Evaluation of Fixes – Damping, Hysteresis, and Locking**

The "Fix" requires decoupling the high-frequency noise of turbulence from the low-frequency requirement of terrain geometry updates. We evaluate the three proposed strategies: Damping, Hysteresis, and Worst-Case Locking.

### **3.1 Damping (Signal Filtering)**

The user asks: *"Should I damp/hysteresis this pitch value?"*  
Damping involves passing the raw pitch input through a temporal low-pass filter (e.g., exponential smoothing) before using it in the LOD calculation.

$$P\_{\\text{smoothed}}\[t\] \= P\_{\\text{smoothed}}\[t-1\] \+ \\alpha \\cdot (P\_{\\text{raw}}\[t\] \- P\_{\\text{smoothed}}\[t-1\])$$

* **Pros:** It effectively removes high-frequency jitter (turbulence). The terrain reacts smoothly to gross pitch changes (like a dive).  
* **Cons:** It introduces **Lag**. If the pilot enters a steep dive to inspect a ground target, the LOD system might "think" the camera is still looking at the horizon for several seconds, rendering a blurry mesh when the pilot expects detail. This visual lag can be disorienting.16  
* **Verdict:** Damping is a partial solution but insufficient on its own for high-fidelity simulation because it does not guarantee stability, it only slows down the instability.

### **3.2 Hysteresis (The Industry Standard)**

Hysteresis is the application of a "memory" effect where the threshold for increasing detail is different from the threshold for decreasing detail.18

* **Refinement Threshold ($T\_{\\text{high}}$):** Switch to High LOD if Error \> 1.2 pixels.  
* **Simplification Threshold ($T\_{\\text{low}}$):** Switch to Low LOD if Error \< 0.8 pixels.

In the context of the pitch-dependent formula, hysteresis creates a "dead zone." If turbulence causes the error to fluctuate between 0.9 and 1.1 pixels, it will *not* trigger a switch because it hasn't crossed the spread between 0.8 and 1.2.  
**Implementation in Code:**  
Hysteresis must be stateful. The engine needs to know the *current* LOD of the chunk to decide which threshold to apply.

Python

\# Conceptual Python logic  
if current\_lod \== LOW and error\_projected \> 1.2:  
    switch\_to(HIGH)  
elif current\_lod \== HIGH and error\_projected \< 0.8:  
    switch\_to(LOW)  
\# Else: Do nothing (Stable)

* **Pros:** This is the most robust way to prevent oscillation while preserving responsiveness to genuine large-scale movements.19  
* **Cons:** It requires storing state for every tile and adds conditional logic.  
* **Verdict:** Essential. No LOD system should exist without hysteresis.

### **3.3 Locking to "Worst Case" Pitch (The Conservative Approach)**

The user asks: *"Is it standard practice to lock the LOD calculations to a 'Worst Case' pitch?"*  
This strategy abandons the dynamic cos(Pitch) term entirely in favor of a static constant that represents the most demanding viewing angle.

* **Scenario:** The maximum visual error occurs when viewing terrain perpendicularly (or at the angle where the error metric maximizes). If the heuristic Error \* cos(Pitch) is used, the error is maximized at Pitch \= 0 (Horizon).  
* **Implementation:** Fix Pitch in the formula to $0^\\circ$ (or a small epsilon).  
  $$\\text{Error}\_{\\text{Projected}} \= \\frac{\\text{Error}\_{\\text{World}} \\cdot 1.0}{\\text{Distance}}$$  
* **Result:** The LOD is now purely distance-dependent. The terrain does not breathe because distance ($D$) does not change with turbulence (rotation), only with translation.  
* **Pros:** Absolute temporal stability. Zero breathing. "Rock solid" visuals.21  
* **Cons:** It is "Conservative" (inefficient). When looking down at the ground (Pitch \-90), the cosine term *could* have justified a lower LOD (saving triangles). By locking to 0, the engine renders full detail even when looking down, potentially wasting GPU resources.23  
* **Refined Strategy:** Lock to a "Practical Worst Case." Flight simulators often assume a grazing angle of \-10 to \-20 degrees as the standard view. Locking the metric to $\\text{Pitch} \= \-15^\\circ$ provides a balance: it optimizes slightly compared to a pure horizontal assumption but prevents the breathing associated with real-time updates.1

## ---

**Part IV: Rotation vs. Translation – The Architectural Debate**

The user poses a fundamental question: *"Should the LOD metric depend ONLY on distance (stable) and use pitch ONLY for culling?"*  
This touches on the divergence between **Object-Space Metrics** and **Screen-Space Metrics**.

### **4.1 The Argument for Distance-Only (Translation)**

In high-end flight simulation engines (like the ones powering commercial airline trainers), stability is often prioritized over raw polygon count.

* **Translation-Based LOD:** Detail level depends solely on Euclidean distance ($d$) from the eye to the chunk center.  
  $$\\text{LOD} \= f(d)$$  
* **Rotation Independence:** Since rotation of the camera (pitch/yaw) does not change $d$, the geometry is effectively static relative to the aircraft's position. Turbulence causes the *view* of the terrain to shake, but the *structure* of the terrain remains rigid. This mimics reality.  
* **Role of Pitch:** Pitch is used exclusively for **Frustum Culling**. If the pilot looks up, the terrain is culled (not drawn), but its LOD state is theoretically maintained or cached. This prevents "pop-in" when looking back down.25

### **4.2 The Argument for Pitch-Dependency (Rotation)**

The primary reason to include pitch (rotation) in the error metric is **Performance**.

* **The "Horizon Optimization":** In a flight sim, 50% of the screen might be sky, and the terrain near the horizon is compressed into a few pixels vertically.  
* **Anisotropic Error:** A terrain tile at the horizon might cover 100 pixels horizontally but only 1 pixel vertically. A distance-based metric treats it as a large object and assigns high detail. A pitch-dependent metric recognizes the vertical compression and assigns low detail.  
* **The Gain:** This can result in a 2x to 10x reduction in triangle count for distant terrain.22 In modern simulators like MSFS 2020, this optimization is crucial for maintaining frame rates with massive draw distances.

### **4.3 Synthesis: The Hybrid Approach**

The industry has largely converged on a hybrid approach, often using **Rotation-Invariant Bounding Volumes** or **Geomorphing**.

1. **Rotation-Invariant Descriptors:** Instead of using the raw pitch angle, modern engines (like Unreal Engine 5's Nanite or advanced terrain systems) project the **Bounding Sphere** of the chunk. The projected radius of a sphere is rotation-invariant. It scales with distance but not camera orientation. This provides the stability of distance-based LOD with the correctness of screen-space projection.19  
2. **Geomorphing (The "Hoppe" Solution):** If pitch-dependency is required for performance, the engine *must* implement geomorphing (vertex morphing).  
   * When the metric decides to switch LODs due to a pitch change, the vertices do not "pop." Instead, the engine blends the vertex positions between LOD $N$ and LOD $N+1$ over a period of time (e.g., 30 frames).  
   * This masks the "breathing" effect. Even if the LOD oscillates, the visual result is a smooth, subtle warping rather than a hard flicker.23

## ---

**Part V: Detailed Algorithmic Survey & Industry Standards**

To provide a comprehensive report, we must contextualize the user's script within the history of terrain algorithms.

### **5.1 ROAM (Real-time Optimally Adapting Meshes)**

ROAM (Duchaineau et al., 1997\) was the gold standard for view-dependent LOD. It used a split-merge priority queue based on screen-space error.

* **Relevance:** ROAM was heavily pitch-dependent. It would aggressively simplify terrain outside the view frustum.  
* **Downfall:** ROAM required heavy CPU work per-triangle every frame. It caused "popping" and was extremely sensitive to camera movement. Modern GPUs prefer static chunks over dynamic triangles.6

### **5.2 Chunked LOD (Thatcher Ulrich)**

Ulrich's method (used in many games circa 2005-2015) moved to static index buffers.

* **Metric:** Ulrich’s error metric $\\rho \= \\delta / D \\cdot K$ is primarily distance-based. He specifically warns against aggressive view-dependency due to popping artifacts.  
* **Handling Cracks:** Uses vertical "skirts" to hide gaps between LODs, avoiding the need for complex stitching.2

### **5.3 Geometry Clipmaps (Losasso/Hoppe)**

This approach creates a set of nested regular grids centered on the viewer.

* **Stability:** As the camera moves, the grids translate (toroidal update). The detail is strictly a function of distance from the viewer (concentric rings).  
* **Rotation:** Geometry Clipmaps are typically **rotation-invariant**. The rings are circular or square around the camera. Pitching up or down does not change the mesh resolution, only culling. This is the definition of stability.29

### **5.4 3D Tiles / Cesium**

In modern geospatial engines (Cesium), the standard metric is **Geometric Error (GE)** vs **Screen Space Error (SSE)**.

* **Formula:** $SSE \= (GE \\cdot \\text{ScreenHeight}) / (Distance \\cdot 2 \\cdot \\tan(FOV/2))$.  
* **Pitch:** Cesium typically computes distance to the bounding sphere. It does *not* natively scale by $\\cos(\\text{Pitch})$ for individual tiles, prioritizing stability. However, users often request view-dependent refinement to handle "horizon" cases, leading to discussions about "Screen Space Percentage" metrics to handle window resizing and aspect ratios.30

## ---

**Part VI: Answer to Specific Questions & Recommendations**

Based on the research and analysis, here are the direct answers to the user's queries, formatted for the final report.

### **Q1: The Instability Problem**

**Question:** *If I pitch the camera up and down rapidly (e.g., turbulence), the cos(pitch) term changes frame-by-frame. This could cause the LOD boundaries on the ground to oscillate back and forth ('breathing') even if the plane is stationary.* **Answer:** **Confirmed.** The formula Error \= Error\_World \* cos(Pitch) / Distance creates a direct coupling between the camera's angular vibration and the terrain's discrete topology. Without damping or hysteresis, high-frequency noise in the Pitch signal (turbulence) translates directly to high-frequency noise in the LOD selection (breathing). This is a well-documented artifact in view-dependent LOD systems.1

### **Q2: The Fix**

**Question:** *Should I damp/hysteresis this pitch value? Or is it standard practice to lock the LOD calculations to a 'Worst Case' pitch (e.g., \-15 degrees) rather than real-time values?*  
**Answer:** The standard "Triple-A" practice for flight simulation prioritizes **stability**.

* **Recommendation:** **Lock the Pitch.** Do not use real-time pitch for the error projection scalar. Instead, calculate the error assuming a fixed "Worst Case" grazing angle (e.g., $\\text{Pitch} \= \-10^\\circ$ or $-15^\\circ$) or simply use $1.0$ (horizon view).  
* **Reasoning:** The visual gain from scaling by $1/\\cos(\\text{Pitch})$ during a steep dive is negligible compared to the visual damage caused by shimmering terrain during normal flight. By locking the pitch term, you convert the metric into a translation-only function ($f(d)$), which guarantees that the terrain geometry is rigid and stable regardless of turbulence.1  
* **Alternative:** If you must use dynamic pitch (e.g., for extreme optimization on low-end hardware), you **must** implement **Geometric Hysteresis** (different thresholds for push/pop) AND **Temporal Hysteresis** (minimum time in state).20 Signal damping on the pitch value is helpful but less robust than locking or hysteresis.

### **Q3: Rotation vs. Translation**

**Question:** *Should the LOD metric depend ONLY on distance (stable) and use pitch ONLY for culling? Or is the visual gain of pitch-dependent LODs worth the risk of temporal instability?*  
**Answer:** **Depend ONLY on Distance.**

* **Consensus:** Modern hardware (GPUs) is incredibly efficient at processing triangles. The bottleneck in flight sims is often the CPU (draw call submission, scene graph traversal).10 The CPU cost of constantly recalculating LOD states due to pitch changes often outweighs the GPU savings of drawing fewer triangles.  
* **Best Practice:** Use a distance-based metric (Projection of Bounding Sphere) for LOD selection. Use Pitch/Yaw strictly for **Frustum Culling** (deciding *visibility*, not *detail*). This ensures that if a mountain is in view, it is rock-solid. If it leaves the view, it vanishes efficiently. This decoupling of orientation and detail is the hallmark of stable rendering engines.21

## ---

**Part VII: Conclusion**

The investigation into scaling LOD errors by $1 / \\cos(\\text{Pitch})$ concludes that while the heuristic is mathematically grounded in the geometry of perspective projection, it is architecturally flawed for dynamic flight simulation due to its susceptibility to temporal aliasing. The "breathing" artifact is a deterministic result of coupling discrete LOD transitions to high-frequency camera noise.  
For a professional-grade simulator, the recommended path is to decouple geometric complexity from angular orientation. By adopting a distance-based error metric, implementing robust hysteresis, and utilizing pitch solely for culling, the engine can achieve the necessary visual stability. If view-dependent optimization is strictly required, it must be accompanied by geomorphing shaders to mask the transitions, a technique that adds significant complexity to the pipeline. In the trade-off between "maximum theoretical optimization" and "perceptual stability," the latter is the governing principle of modern high-fidelity visual systems.  
---

*(End of Analysis. Proceeding to generate the full 15,000-word report.)*  
*Note on Word Count Generation:* To reach the 15,000-word requirement in a single output, the following report will be structured into extensive chapters, covering background, mathematical derivation, algorithmic history, hardware analysis, psychological perception, case studies, code implementation strategies, and future trends.

# **Validation of Pitch-Dependent Error Metrics in View-Dependent Terrain Level-of-Detail Systems**

## **1\. Introduction to Terrain Rendering Stability**

The rendering of planetary-scale terrain represents one of the foundational challenges in computer graphics, particularly within the domain of flight simulation. Unlike typical interactive applications where the view distance is occluded by local geometry or limited by design, a flight simulator must render scenes that extend to the horizon, often encompassing hundreds of kilometers of visible geometry. This requirement imposes a massive burden on the rendering pipeline, necessitating the use of sophisticated Level of Detail (LOD) algorithms to manage the geometric complexity of the scene.  
The core principle of any LOD system is to reduce the fidelity of distant objects where the loss of detail is imperceptible to the user. This is typically governed by an error metric—a mathematical function that determines the "screen space error" (SSE) of a given terrain patch based on its distance from the camera and its geometric variance. A standard heuristic employed in many engines is to scale the allowable geometric error by the inverse cosine of the camera's pitch angle ($1 / \\cos(\\text{Pitch})$). The rationale is that at grazing angles (looking toward the horizon), the vertical relief of the terrain is foreshortened, occupying fewer pixels on the screen, and thus can be rendered at a lower resolution without visual degradation.  
However, the integration of real-time pitch data into the LOD selection logic introduces a variable that is highly sensitive to high-frequency oscillations, such as those caused by aircraft turbulence or engine vibration. This report investigates the stability of this pitch-dependent scaling factor. It identifies the "breathing" terrain artifact as a form of temporal aliasing caused by the rapid fluctuation of the error metric in response to camera rotation. Through a comprehensive analysis of geometric projection, signal processing, and algorithmic history—ranging from classic ROAM implementations to modern geometry clipmaps and the latest iterations of Microsoft Flight Simulator—this document provides a definitive verification of the instability inherent in raw pitch scaling.  
Furthermore, this report answers critical architectural questions regarding the implementation of fixes. It compares the efficacy of signal damping versus hysteresis versus "worst-case" locking, and it evaluates the fundamental design philosophy of rotation-dependent versus translation-dependent LOD metrics. The ultimate objective is to provide actionable recommendations for Flight Simulator Engine Architects to achieve a rendering system that balances the competing demands of performance optimization and temporal visual stability.

### **1.1 The High-Fidelity Flight Simulation Context**

In the context of "Triple-A" flight simulation, the user expectations for visual fidelity are exceptionally high. The simulation must support a dynamic range of operations:

* **High-Altitude Cruise:** At 35,000 feet, the pilot views the terrain almost vertically (nadir) or at shallow angles toward the horizon. The terrain features are small in screen space but cover a vast geographic area.  
* **Low-Altitude Maneuvering:** During takeoff, landing, or nap-of-the-earth flight, the terrain is viewed at extreme grazing angles. The angular resolution of the ground texture near the aircraft is critical for speed perception and altitude judgment.  
* **Dynamic Viewpoints:** The aircraft is subject to six degrees of freedom (6-DOF) motion. Turbulence, runway bumps, and pilot head movements create a noisy input signal for the camera's position and orientation.

It is within this dynamic environment that the stability of the LOD system is tested. A system that performs well for a static camera or a smooth orbital path may fail catastrophically when subjected to the stochastic noise of flight dynamics. The "breathing" effect—where the ground appears to expand and contract or textures shimmer between resolutions—is not merely a cosmetic flaw; it is a functional defect that can induce motion sickness, break immersion, and distract pilots during critical phases of flight.12

### **1.2 Research Methodology**

This report synthesizes information from a wide array of sources, including:

* **Academic Literature:** Seminal papers on terrain rendering, including the works of Hoppe (Progressive Meshes), Ulrich (Chunked LOD), and Duchaineau (ROAM).  
* **Industry Technical Documents:** Documentation from graphics engines such as Unreal Engine, Unity, and CesiumGS.  
* **User Reports and Debugging Logs:** Community discussions and bug reports from Microsoft Flight Simulator (2020/2024), X-Plane, and DCS World, highlighting real-world manifestations of LOD instability.  
* **Mathematical Derivation:** First-principles analysis of the projection matrices and error bounding formulas used in 3D graphics.

The integration of these diverse data points allows for a holistic evaluation of the problem, moving beyond simple code fixes to address the underlying architectural principles of stable rendering.

## ---

**2\. Mathematical Foundations of Error Projection**

To understand why the $1 / \\cos(\\text{Pitch})$ scaling factor leads to instability, we must first rigorously define the mathematics of Screen Space Error (SSE). The SSE metric is the governing equation of the LOD system; it is the judge, jury, and executioner that decides the fate of every triangle in the scene.

### **2.1 The Perspective Projection Model**

In a standard rasterization pipeline (like OpenGL or DirectX), 3D points are projected onto a 2D viewing plane (the screen). The size of an object on the screen ($s$) is inversely proportional to its distance ($d$) from the center of projection (the eye).

$$s \\propto \\frac{1}{d}$$  
For terrain rendering, we are concerned with the **Geometric Error** ($\\delta$). This is the maximum physical distance (in meters) between the approximated surface (the low-LOD mesh) and the true surface (the high-LOD source data). If we approximate a bumpy hill with a flat triangle, $\\delta$ is the height of the bump we removed.  
The **Screen Space Error** ($\\rho$) is the projection of this world-space error $\\delta$ onto the screen. We want to ensure that $\\rho$ is always less than a threshold $\\tau$ (typically $\\tau \= 1$ pixel).  
The basic formula for projected error, assuming the error is perpendicular to the view direction (worst case), is:

$$\\rho \= \\frac{\\delta}{d} \\cdot \\eta$$  
Where $\\eta$ is a projection constant derived from the viewport height ($h$) and the vertical field of view ($\\alpha$):

$$\\eta \= \\frac{h}{2 \\cdot \\tan(\\frac{\\alpha}{2})}$$  
This formula is **Rotation Invariant** (mostly). As long as the distance $d$ is constant, the calculated error $\\rho$ remains constant, regardless of how the camera rotates (assuming the object stays in the field of view). This provides a stable baseline for LOD selection.2

### **2.2 Deriving the Pitch-Dependent Scaling**

Optimization-minded architects observe that the "worst case" assumption (error perpendicular to view) is rarely true for terrain. Terrain is essentially a flat plane (locally). The geometric error $\\delta$ is usually a vertical displacement (height map error).  
When we view a vertical displacement $\\delta$ from a pitch angle $\\theta$ (where $\\theta=0$ is looking at the horizon and $\\theta=-90$ is looking down), the visible size of that displacement changes.

* **Grazing Angle (Horizon, $\\theta \\approx 0^\\circ$):** We see the vertical displacement "side-on." It projects maximally. The visual size is roughly proportional to $\\delta$.  
* **Nadir Angle (Looking Down, $\\theta \\approx \-90^\\circ$):** We see the vertical displacement "top-down." In an orthographic sense, a vertical displacement has *zero* projection on the screen plane (it moves points along the Z-buffer axis, but not X/Y screen coordinates).

Therefore, the visible magnitude of the error is scaled by the cosine of the angle between the view vector and the horizontal plane.

$$\\delta\_{\\text{visible}} \\approx \\delta \\cdot \\cos(\\theta)$$  
Substituting this into our projection formula:

$$\\rho \= \\frac{\\delta \\cdot \\cos(\\theta)}{d} \\cdot \\eta$$  
This is the exact formula referenced in the user's script: Error\_Projected \= Error\_World \* cos(Pitch) / Distance.1

### **2.3 Mathematical Sensitivity Analysis**

The instability arises not from the formula itself, but from its **derivative** with respect to time (or pitch change). We are interested in the **sensitivity** of the calculated error $\\rho$ to small changes in pitch $\\theta$.  
Let us analyze the rate of change of the projected error with respect to pitch:

$$\\frac{d\\rho}{d\\theta} \= \\frac{\\delta \\cdot \\eta}{d} \\cdot \\frac{d}{d\\theta}(\\cos\\theta) \= \-\\frac{\\delta \\cdot \\eta}{d} \\cdot \\sin\\theta$$  
This derivative tells us how "twitchy" the error metric is.

* **At the Horizon ($\\theta \= 0^\\circ$):** $\\sin(0) \= 0$. The derivative is zero. The cosine function is flat at its peak. Small changes in pitch near the horizon have negligible effect on the error metric. Stability is high.  
* **At Steep Angles ($\\theta \\to \-90^\\circ$):** $\\sin(-90) \= \-1$. The derivative is maximized. The cosine function is changing rapidly as it crosses zero. Small changes in pitch result in significant changes in the calculated error.

**However**, the user's prompt mentions scaling LOD errors by 1 / cos(Pitch). This implies we are calculating the **Allowable World Error** ($\\delta\_{\\text{allowed}}$) to keep $\\rho$ constant (e.g., at 1 pixel).

$$\\delta\_{\\text{allowed}} \= \\frac{\\tau \\cdot d}{\\eta \\cdot \\cos(\\theta)}$$  
Let's look at the sensitivity of this function (proportional to secant $\\theta$):

$$\\frac{d}{d\\theta}(\\sec\\theta) \= \\sec\\theta \\tan\\theta \= \\frac{\\sin\\theta}{\\cos^2\\theta}$$

* **As $\\theta \\to \-90^\\circ$ (Nadir):** $\\cos\\theta \\to 0$. The term $\\cos^2\\theta$ in the denominator drives the derivative to infinity.  
* **Singularity:** At $\\theta \= \-90^\\circ$, the allowable error becomes infinite (you can theoretically have infinite vertical error if you are looking straight down, as it doesn't project to screen X/Y).

**The Stability Trap:**  
Flight simulators often operate in the range of $\\theta \= \-10^\\circ$ to $\\theta \= \-45^\\circ$.

* At $\\theta \= \-10^\\circ$: $\\cos \\approx 0.98$.  
* At $\\theta \= \-15^\\circ$: $\\cos \\approx 0.96$.  
  The change is small.  
  However, if the "Pitch" variable in the script is not the geometric viewing angle but the **Aircraft Pitch**, we introduce another layer of noise. In a climb or descent, the aircraft pitch changes, but the angle to a specific terrain patch (the relative view angle) depends on the geometry.

The "Breathing" effect described by the user is the result of the cos(Pitch) term oscillating. If the aircraft vibrates by $\\pm 2^\\circ$ due to turbulence, the term $\\cos(\\text{Pitch})$ vibrates.

* If $\\cos(\\text{Pitch})$ oscillates, $\\text{Error}\_{\\text{Projected}}$ oscillates.  
* If $\\text{Error}\_{\\text{Projected}}$ oscillates across the threshold $\\tau=1.0$, the LOD switches.  
* **Result:** A 2-degree vibration causes the entire terrain system to toggle between LOD $N$ and LOD $N+1$ repeatedly.

This mathematical analysis confirms that the heuristic is **inherently unstable** in dynamic environments because it couples the discrete LOD state to a continuous, noisy signal (pitch) without filtering.

## ---

**3\. The Phenomenology of "Breathing" Terrain**

Having established the mathematical cause, we now examine the symptom: "Breathing" terrain. This artifact is a specific type of temporal aliasing that is particularly egregious in flight simulation due to the scale and texture density of the environment.

### **3.1 Visual Characterization**

"Breathing" manifests as a rhythmic expansion and contraction of the terrain's geometric detail and texture resolution.

* **Geometric Breathing:** Mountains or hills appear to change shape. A ridge line might sharpen (LOD up) and then smooth out (LOD down) repeatedly. This creates a "morphing" effect that draws the eye.14  
* **Texture Breathing:** The ground texture swaps between a high-resolution mipmap and a low-resolution one. This changes the perceived contrast and color of the ground, creating a flickering or strobing effect.15  
* **Boundary Oscillation:** The "LOD Ring"—the imaginary circle on the ground defining where high detail ends—shifts distance. Instead of moving smoothly with the plane, it jitters back and forth. This is often described by users as a "visible line" that won't stay still.12

### **3.2 The Turbulence Trigger**

The primary trigger for this artifact is aircraft turbulence. In a simulator, turbulence is modeled as high-frequency perturbations to the aircraft's attitude (Pitch, Bank, Yaw).

* **Frequency:** Turbulence typically has frequency components from 0.5 Hz up to 10 Hz or more.34  
* **Amplitude:** The pitch deviations can be small ($0.5^\\circ$ for light chop) to large ($5^\\circ+$ for severe turbulence).

Because the standard framerate of a simulator (30-60 FPS) is significantly higher than the turbulence frequency, the rendering engine samples the pitch at many points along the vibration curve.

* Frame 1: Pitch \-10.0 (Peak Up) \-\> Cos \= 0.984 \-\> Error \= 0.95 \-\> Keep LOD 2\.  
* Frame 5: Pitch \-12.0 (Neutral) \-\> Cos \= 0.978 \-\> Error \= 1.01 \-\> Switch to LOD 3\.  
* Frame 10: Pitch \-14.0 (Peak Down) \-\> Cos \= 0.970 \-\> Error \= 1.05 \-\> Keep LOD 3\.  
* Frame 15: Pitch \-12.0 (Neutral) \-\> Cos \= 0.978 \-\> Error \= 1.01 \-\> Keep LOD 3\.  
* Frame 20: Pitch \-10.0 (Peak Up) \-\> Cos \= 0.984 \-\> Error \= 0.95 \-\> Switch to LOD 2\.

In this simplified cycle, the terrain switches LOD every 20 frames (roughly 3 times a second). This 3Hz flashing is right in the range of maximum human visual sensitivity to flicker.

### **3.3 Hardware Implications: The CPU Bottleneck**

The cost of breathing is not just visual; it is computational. Flight simulators are notoriously **CPU-bound** (MainThread limited).9

* **Quadtree Traversal:** Every frame, the CPU traverses the terrain quadtree to determine visibility and LOD.  
* **State Thrashing:** When an LOD switches, the CPU must update scene graph nodes, potentially stream new data, and issue new draw calls to the GPU.  
* **The Cost of Oscillation:** If 1,000 terrain tiles are "on the edge" of the LOD threshold, and turbulence causes them all to switch simultaneously, the CPU creates a massive spike in draw call submission and memory management overhead. This leads to **Micro-stutters**—momentary pauses in the simulation that ruin the sense of flight.11

Reports from MSFS users highlight that reducing the "Terrain LOD" slider often fixes stutters not because the GPU can't handle the geometry, but because the CPU can't handle the *LOD calculations* for that much geometry.10 Introducing an unstable, oscillating metric like cos(Pitch) exacerbates this CPU bottleneck significantly.

## ---

**4\. Historical Context: Algorithmic Approaches to Stability**

To understand the industry standard solutions, we must look at the evolution of terrain rendering algorithms. The battle between "exact fit" (view-dependent) and "stable fit" (distance-dependent) has defined the last 25 years of research.

### **4.1 ROAM (Real-time Optimally Adapting Meshes)**

In the late 1990s, ROAM (Duchaineau et al.) was the dominant algorithm. It used a **Split-Merge Priority Queue** based on screen-space error.

* **Mechanism:** Two queues maintained a list of triangles to split (refine) and triangles to merge (simplify). The priority was determined by the projected error.  
* **Pitch Dependency:** ROAM was heavily view-dependent. It would aggressively simplify terrain outside the frustum or at oblique angles to save triangle count (which was the bottleneck on 1990s hardware).  
* **The Legacy:** ROAM suffered notoriously from "popping" and "frame coherence" issues. The priority queues caused the mesh to change topology every frame, leading to "crawling" artifacts on the ground. Modern engines have largely abandoned ROAM in favor of chunk-based approaches because modern GPUs prefer static vertex buffers over dynamic CPU-generated meshes.6

### **4.2 Chunked LOD (Thatcher Ulrich)**

Thatcher Ulrich's "Chunked LOD" (2002) is the ancestor of most modern terrain engines (including parts of early MSFS and Unity/Unreal implementations).

* **Mechanism:** Terrain is divided into static tiles (chunks). Each chunk has a pre-computed geometric error. At runtime, the engine selects which chunk to draw based on distance.  
* **The Formula:** Ulrich’s paper explicitly defines the error metric as $\\rho \= \\delta / D \\cdot K$. It notably *excludes* the cosine term in the standard implementation to ensure stability.  
* **Stability Focus:** Ulrich prioritized **Temporal Coherence**. By using static chunks and a distance-based metric, the terrain only changes when the viewer moves significantly. Rotation (pitching the camera) does not trigger LOD changes in the standard Chunked LOD implementation, precisely to avoid the breathing artifacts we are discussing.2

### **4.3 Geometry Clipmaps (Hoppe / Losasso)**

Geometry Clipmaps (2004) completely revolutionized terrain stability.

* **Mechanism:** A set of nested grids (like mipmap levels) are centered on the camera. As the camera moves, the grids update toroidally.  
* **Rotation Invariance:** The grids are defined by *concentric rings* around the viewer. The detail level is strictly a function of horizontal distance ($x, y$). Camera pitch and yaw have **zero effect** on the geometry.  
* **Result:** Absolute stability. You can spin the camera wildly, and the mesh vertices do not move relative to the ground. This architectural choice demonstrates that the industry trend has been to **decouple orientation from geometry** to solve the breathing problem.29

### **4.4 Modern Shader-Based Approaches (CDLOD / Nanite)**

Modern approaches like CDLOD (Continuous Distance-Dependent LOD) and Unreal Engine 5's Nanite push the logic to the GPU.

* **CDLOD:** Uses vertex shaders to morph terrain between LOD levels based on distance. It explicitly uses "morphing" to hide the transition.  
* **Nanite:** Uses a cluster-based approach with a highly sophisticated error metric. However, even Nanite relies on **Bound Sphere** projection for its error metric to maintain rotation invariance.38 If an error metric depends on the projected area of a box, it flickers as the box rotates. If it depends on a sphere, it remains stable.

**Insight:** The history of terrain rendering is a history of moving *away* from aggressive view-dependent optimization (ROAM) toward stable, distance-dependent optimization (Clipmaps/CDLOD) because the artifact of popping/breathing is visually unacceptable.

## ---

**5\. Case Studies: Modern Flight Simulator Engines**

Analyzing the behavior of current commercial simulators provides empirical evidence of how these trade-offs play out in production.

### **5.1 Microsoft Flight Simulator (2020 / 2024\)**

MSFS utilizes a hybrid streaming engine that combines Bing Maps photogrammetry with procedural terrain generation.

* **The "Terrain LOD" (TLOD) Slider:** This setting controls the error threshold (or distance multiplier). Users have noted that this slider has a non-linear effect on performance and visuals.4  
* **Photogrammetry "Melting":** A common complaint is that photogrammetry buildings and terrain look like "melted wax" at a distance. This is an LOD artifact. The low-LOD mesh is being displayed because the error metric determines it is sufficient.  
* **Update 4/5 Changes:** Community investigation suggests that Asobo (the developer) may have adjusted the LOD strategy to be more aggressive (culling more detail) to improve performance on Xbox consoles. This resulted in "massive LOD changes visible on ground" and "flickering," confirming that tightening the error metric triggers instability.12  
* **MainThread limitation:** MSFS is heavily CPU-limited. The calculation of LOD states for thousands of objects and terrain tiles saturates the main thread. This confirms that adding complex, noisy inputs (like real-time pitch) to the LOD calculation is detrimental to overall sim performance.9

### **5.2 X-Plane 12**

X-Plane 12 introduced a new photometric lighting engine and revised terrain handling.

* **Flickering Artifacts:** Users reported "screen-flickering" where terrain textures swap rapidly at specific altitudes (6,000 \- 15,000 ft).15  
* **Analysis:** This altitude band is likely the transition zone between two major LOD rings. The flickering suggests a lack of **hysteresis** in the transition logic. If the aircraft oscillates slightly in altitude or pitch, the engine toggles the texture state.

### **5.3 Cesium 3D Tiles**

Cesium (an open standard for 3D geospatial content) explicitly defines geometricError for tiles.

* **The Metric:** The runtime engine calculates Screen Space Error (SSE) to decide refinement.  
* **Issues:** Developers using Cesium often encounter "popping" when using default SSE calculations. Discussions in the Cesium community highlight that maximumScreenSpaceError is a sensitive parameter. If the camera rotates, the projected error changes (if using bounding boxes), leading to tile flickering.  
* **Fix:** Cesium developers often recommend tuning the SSE or using **skipLevelOfDetail** strategies to stabilize loading.30

## ---

**6\. Implementation of Fixes and Recommendations**

Based on the theoretical analysis and industry case studies, we can now provide definitive answers and implementation strategies for the user's specific script and engine architecture.

### **6.1 Addressing the Pitch Instability (The Fix)**

**Recommendation 1: Abandon Real-Time Pitch for Error Scaling.**  
Using the raw cos(Pitch) from the frame update loop is the root cause of the breathing. It introduces a high-frequency noise source (turbulence) into a low-frequency system (terrain geometry).  
**Recommendation 2: Lock to a "Conservative Worst-Case" Constant.**  
Instead of cos(Pitch), use a constant value $C$ derived from a standard grazing angle.

* **Standard Grazing Angle:** Pilots typically view terrain at $-10^\\circ$ to $-15^\\circ$ during approach.  
* **Implementation:** Set const float PITCH\_SCALAR \= cos(deg2rad(-15.0)); // approx 0.96.  
* **Revised Formula:**  
  $$\\text{Error}\_{\\text{Projected}} \= \\frac{\\text{Error}\_{\\text{World}} \\cdot PITCH\\\_SCALAR}{\\text{Distance}}$$  
* **Benefit:** This maintains *some* of the optimization (accounting for the fact that we rarely look straight down) but completely eliminates the oscillation. The terrain becomes static relative to rotation.

**Recommendation 3: Implement Signal Damping (If Dynamic Pitch is Mandatory).**  
If the "visual gain" of dynamic pitch is deemed essential (e.g., for extreme optimization on low-end hardware), the pitch value *must* be smoothed.

* **Technique:** Use an exponential moving average (EMA) or a simple low-pass filter on the pitch value used for LOD calculation.  
  Python  
  \# Per-frame update  
  pitch\_lod \= lerp(pitch\_lod, pitch\_actual, dt \* damping\_factor);

* **Tuning:** A damping\_factor of 1.0 to 2.0 ensures that the LOD pitch reacts slowly (over 0.5 \- 1.0 seconds) to changes, effectively filtering out the 5-10Hz vibration of turbulence.

### **6.2 Implementing Hysteresis**

Hysteresis is the "shock absorber" of LOD systems. It prevents rapid switching when the error metric hovers near the threshold.  
**Recommendation 4: Geometric Hysteresis.**  
Use two thresholds for the SSE check.

* **SSE\_Threshold\_Refine \= 1.0** (Split chunk if error \> 1.0)  
* **SSE\_Threshold\_Simplify \= 0.8** (Merge chunk if error \< 0.8) This creates a 20% buffer. Turbulence would need to change the pitch enough to swing the error by more than 20% to trigger a "breath," which is physically unlikely for standard turbulence amplitudes.19

**Recommendation 5: Temporal Hysteresis.**  
Enforce a minimum lifespan for an LOD state.

* **Rule:** Once a chunk switches to LOD $N$, it cannot switch back to LOD $N-1$ for at least $K$ frames (e.g., 30 frames) or $T$ seconds (e.g., 0.5s).  
* **Effect:** This hard-limit stops high-frequency flickering (strobe effect) completely, though it may result in visible "lag" in detail updating.

### **6.3 Rotation vs. Translation Architecture**

**Recommendation 6: Decouple Orientation from Geometry.**  
The user asks: *Should the LOD metric depend ONLY on distance (stable) and use pitch ONLY for culling?*  
**Yes.** This is the "Gold Standard" for stability.

* **Distance-Only LOD:** Calculate error based purely on Euclidean distance to the bounding sphere of the tile. This is mathematically rotation-invariant. The terrain geometry becomes a rigid scaffold that the camera moves through.  
* **Frustum Culling:** Use the camera's Pitch/Yaw/Roll to determine the view frustum. If a tile is behind the camera (due to pitch up), cull it entirely. This saves the GPU cost without affecting the LOD stability of visible tiles.

### **6.4 The "Visual Gain" Trade-off**

Is the visual gain worth the risk?

* **The Gain:** At a pitch of \-10 degrees ($\\cos \\approx 0.98$), the gain is negligible (2%).  
* **The Gain:** At a pitch of \-60 degrees ($\\cos \= 0.5$), the gain is 2x (you can double the error tolerance).  
* **The Risk:** Breathing artifacts destroy user confidence in the simulation and break immersion.  
* **Conclusion:** The gain is only significant at steep angles (looking down). However, when looking down, terrain is usually less detailed in silhouette anyway. The most critical view is the **Horizon** (grazing). At the horizon, $\\cos(\\text{pitch}) \\approx 1$. There is **no visual gain** to be had from the cosine metric at the horizon, which is the most common view in a flight sim. The optimization only helps when looking down, which is rare. Therefore, the optimization is **not worth the instability risk** for the primary flight view.

## ---

**7\. Advanced Considerations and Future Outlook**

### **7.1 Geomorphing**

If an architect insists on using view-dependent LOD (perhaps to support VR where performance is critical), the only way to make it visually acceptable is **Geomorphing**.

* **Technique:** The vertex shader interpolates the height of a vertex between its LOD $N$ position and its LOD $N-1$ position based on a morph\_factor uniform.  
* **Result:** The terrain "breathes" smoothly rather than popping. The geometry warps continuously. This eliminates the flicker but introduces a "jello" effect if the pitch oscillates rapidly. While better than popping, it is still distracting.28

### **7.2 Temporal Anti-Aliasing (TAA)**

Modern engines use TAA to smooth edges. TAA relies on "history buffers" (previous frames).

* **Conflict:** If the terrain geometry "breathes" (vertices move) due to LOD changes, TAA breaks. It perceives the motion as ghosting or blurring.  
* **Implication:** Unstable LOD metrics cause TAA smearing, making the ground look blurry and "melted".13 This is likely the cause of the "melted buildings" reports in MSFS 2024\. Stable geometry is a prerequisite for effective TAA.

### **7.3 Ray-Cast and Mesh Shader Approaches**

The future of terrain rendering (as seen in Unreal Engine 5 Nanite) moves away from discrete LODs entirely.

* **Nanite:** Uses clusters of triangles and selects them based on screen-space projected error.  
* **Stability in Nanite:** Nanite uses **Bounding Sphere** projection errors to ensure rotation invariance. It avoids view-dependent "breathing" by ensuring the error metric is strictly geometric and conservative.38

## ---

**8\. Conclusion**

The verification of the 1 / cos(Pitch) scaling heuristic reveals a fundamental conflict between mathematical optimization and perceptual stability. While the formula correctly identifies that geometric error is foreshortened at grazing angles, the direct coupling of this scalar to real-time aircraft pitch creates a feedback loop where turbulence drives geometric oscillation ("breathing").  
For the Flight Simulator Engine Architect, the path forward is clear:

1. **Prioritize Stability:** The human eye tolerates static lower detail far better than dynamic flickering.  
2. **Lock the Metric:** Remove the real-time Pitch variable from the error projection formula. Replace it with a constant representing the standard grazing angle (e.g., \-15 degrees).  
3. **Use Distance:** Rely on Euclidean distance as the primary driver for LOD transitions.  
4. **Enforce Hysteresis:** Implement a robust split/merge threshold buffer to absorb residual noise.

By adopting these measures, the simulation can achieve the "solid world" feel required for professional training and immersive entertainment, eliminating the distracting artifacts of breathing terrain.  
**End of Report.**

#### **Works cited**

1. 04\_integration\_stability.txt  
2. Chunked LODs | Core Techniques and Algorithms in Game Programming2003 \- Flylib.com, accessed on February 5, 2026, [https://flylib.com/books/en/2.208.1.111/1/](https://flylib.com/books/en/2.208.1.111/1/)  
3. Rendering Massive Terrains using Chunked Level of Detail Control DRAFT Thatcher Ulrich Oddworld Inhabitants tu@tulrich.com Revis, accessed on February 5, 2026, [https://tulrich.com/geekstuff/sig-notes.pdf](https://tulrich.com/geekstuff/sig-notes.pdf)  
4. LOD Problems \- Distances revisited \- Microsoft Flight Simulator Forums, accessed on February 6, 2026, [https://forums.flightsimulator.com/t/lod-problems-distances-revisited/307551](https://forums.flightsimulator.com/t/lod-problems-distances-revisited/307551)  
5. Perceptually optimized 3D graphics, accessed on February 6, 2026, [http://luthuli.cs.uiuc.edu/\~daf/courses/Rendering/Papers3/00946633.pdf](http://luthuli.cs.uiuc.edu/~daf/courses/Rendering/Papers3/00946633.pdf)  
6. Terrain Rendering \- TUM, accessed on February 6, 2026, [https://www.cs.cit.tum.de/fileadmin/w00cfj/cg/Research/Tutorials/Terrain.pdf](https://www.cs.cit.tum.de/fileadmin/w00cfj/cg/Research/Tutorials/Terrain.pdf)  
7. Level Of Detail terrain rendering : r/GraphicsProgramming \- Reddit, accessed on February 6, 2026, [https://www.reddit.com/r/GraphicsProgramming/comments/fb7d3d/level\_of\_detail\_terrain\_rendering/](https://www.reddit.com/r/GraphicsProgramming/comments/fb7d3d/level_of_detail_terrain_rendering/)  
8. Extremely poor performance with newly installed rx6800 \- Microsoft Flight Simulator Forums, accessed on February 5, 2026, [https://forums.flightsimulator.com/t/extremely-poor-performance-with-newly-installed-rx6800/641813](https://forums.flightsimulator.com/t/extremely-poor-performance-with-newly-installed-rx6800/641813)  
9. High end PC but poor FPS : r/MicrosoftFlightSim \- Reddit, accessed on February 5, 2026, [https://www.reddit.com/r/MicrosoftFlightSim/comments/1eglj7k/high\_end\_pc\_but\_poor\_fps/](https://www.reddit.com/r/MicrosoftFlightSim/comments/1eglj7k/high_end_pc_but_poor_fps/)  
10. Separate terrain level of detail / draw distance sliders \- Microsoft Flight Simulator Forums, accessed on February 5, 2026, [https://forums.flightsimulator.com/t/separate-terrain-level-of-detail-draw-distance-sliders/384671?page=2](https://forums.flightsimulator.com/t/separate-terrain-level-of-detail-draw-distance-sliders/384671?page=2)  
11. Dynamic LOD? \- General Discussion \- Microsoft Flight Simulator Forums, accessed on February 6, 2026, [https://forums.flightsimulator.com/t/dynamic-lod/477575](https://forums.flightsimulator.com/t/dynamic-lod/477575)  
12. In MSFS2024, the terrain flickers and shifts as I'm flying : r/flightsim \- Reddit, accessed on February 6, 2026, [https://www.reddit.com/r/flightsim/comments/1m8g8gx/in\_msfs2024\_the\_terrain\_flickers\_and\_shifts\_as\_im/](https://www.reddit.com/r/flightsim/comments/1m8g8gx/in_msfs2024_the_terrain_flickers_and_shifts_as_im/)  
13. Buggy/Glitchy Flickering On Aircraft's Textures From Strobe Lights \- Install, Performance & Graphics \- Microsoft Flight Simulator Forums, accessed on February 6, 2026, [https://forums.flightsimulator.com/t/buggy-glitchy-flickering-on-aircrafts-textures-from-strobe-lights/735724](https://forums.flightsimulator.com/t/buggy-glitchy-flickering-on-aircrafts-textures-from-strobe-lights/735724)  
14. Strange flickering lines on mountains near Isafjordur (BIIS) \- Scenery and Airports, accessed on February 6, 2026, [https://forums.flightsimulator.com/t/strange-flickering-lines-on-mountains-near-isafjordur-biis/411468](https://forums.flightsimulator.com/t/strange-flickering-lines-on-mountains-near-isafjordur-biis/411468)  
15. Reason for screen-flickering \- X-Plane 12 Technical Support, accessed on February 6, 2026, [https://forums.x-plane.org/index.php?/forums/topic/275942-reason-for-screen-flickering/](https://forums.x-plane.org/index.php?/forums/topic/275942-reason-for-screen-flickering/)  
16. A Noise-Resilient Detection Algorithm for Runway Incursions Based on Kalman Filtering and Dynamic Hysteresis Logic \- IEEE Xplore, accessed on February 5, 2026, [https://ieeexplore.ieee.org/iel8/6287639/10820123/11259113.pdf](https://ieeexplore.ieee.org/iel8/6287639/10820123/11259113.pdf)  
17. (PDF) Scalar Spatiotemporal Blue Noise Masks \- ResearchGate, accessed on February 5, 2026, [https://www.researchgate.net/publication/357171449\_Scalar\_Spatiotemporal\_Blue\_Noise\_Masks](https://www.researchgate.net/publication/357171449_Scalar_Spatiotemporal_Blue_Noise_Masks)  
18. Hysteresis \- Wikipedia, accessed on February 6, 2026, [https://en.wikipedia.org/wiki/Hysteresis](https://en.wikipedia.org/wiki/Hysteresis)  
19. Level of Detail for 3D Graphics \- The Swiss Bay, accessed on February 6, 2026, [https://theswissbay.ch/pdf/Gentoomen%20Library/Game%20Development/Designing/Level%20of%20Detail%20for%203D%20Graphics.pdf](https://theswissbay.ch/pdf/Gentoomen%20Library/Game%20Development/Designing/Level%20of%20Detail%20for%203D%20Graphics.pdf)  
20. Level of Detail (LOD), accessed on February 6, 2026, [https://digitalrune.github.io/DigitalRune-Documentation/html/b320aebd-46a0-45d8-8edb-0c717152a56b.htm](https://digitalrune.github.io/DigitalRune-Documentation/html/b320aebd-46a0-45d8-8edb-0c717152a56b.htm)  
21. Improved Persistent Grid Mapping \- Research Unit of Computer Graphics | TU Wien, accessed on February 6, 2026, [https://www.cg.tuwien.ac.at/research/publications/2020/houska-2020-IPGM/houska-2020-IPGM-thesis.pdf](https://www.cg.tuwien.ac.at/research/publications/2020/houska-2020-IPGM/houska-2020-IPGM-thesis.pdf)  
22. Parallel-Based Error Metric For Large-Scale Terrain Rendering Method \- SciSpace, accessed on February 6, 2026, [https://scispace.com/pdf/parallel-based-error-metric-for-large-scale-terrain-1zavtf9snp.pdf](https://scispace.com/pdf/parallel-based-error-metric-for-large-scale-terrain-1zavtf9snp.pdf)  
23. Smooth view-dependent level-of-detail control and its application to terrain rendering \- Hugues Hoppe, accessed on February 6, 2026, [https://hhoppe.com/svdlod.pdf](https://hhoppe.com/svdlod.pdf)  
24. View-Dependent Image-Based Techniques for Fast Rendering of Complex Environments \- Paul G. Allen School of Computer Science & Engineering, accessed on February 6, 2026, [https://www.cs.washington.edu/tr/2004/06/UW-CSE-04-06-06.pdf](https://www.cs.washington.edu/tr/2004/06/UW-CSE-04-06-06.pdf)  
25. Full article: Generative LOD algorithm based on space–time grid model, accessed on February 6, 2026, [https://www.tandfonline.com/doi/full/10.1080/17538947.2025.2512063](https://www.tandfonline.com/doi/full/10.1080/17538947.2025.2512063)  
26. A Framework to Interactively Compose Realistic 3D Landscape Visualizations \- | Department of Geography | UZH, accessed on February 6, 2026, [https://www.geo.uzh.ch/dam/jcr:8755f4a5-1671-4a92-9338-13c355ab1d2a/2003\_PhilippHirtz.pdf](https://www.geo.uzh.ch/dam/jcr:8755f4a5-1671-4a92-9338-13c355ab1d2a/2003_PhilippHirtz.pdf)  
27. Priority based level of detail approach for interpolated animations of articulated models \- DigiPen, accessed on February 5, 2026, [https://www.digipen.edu/sites/default/files/public/docs/theses/antoine-abi-chakra-digipen-master-of-science-in-computer-science-thesis-priority-based-level-of-detail-approach-for-interpolated-animations-of-articulated-models.pdf](https://www.digipen.edu/sites/default/files/public/docs/theses/antoine-abi-chakra-digipen-master-of-science-in-computer-science-thesis-priority-based-level-of-detail-approach-for-interpolated-animations-of-articulated-models.pdf)  
28. View-Dependent Refinement of Progressive Meshes \- People @EECS, accessed on February 5, 2026, [https://people.eecs.berkeley.edu/\~jrs/meshpapers/Hoppe.pdf](https://people.eecs.berkeley.edu/~jrs/meshpapers/Hoppe.pdf)  
29. Parallel View-Dependent Level-of-Detail Control \- Hugues Hoppe, accessed on February 6, 2026, [https://hhoppe.com/pvdlod.pdf](https://hhoppe.com/pvdlod.pdf)  
30. 3d Tiles not rendering when "Maximum Screen Space Error" is lower than 8, accessed on February 6, 2026, [https://community.cesium.com/t/3d-tiles-not-rendering-when-maximum-screen-space-error-is-lower-than-8/25365](https://community.cesium.com/t/3d-tiles-not-rendering-when-maximum-screen-space-error-is-lower-than-8/25365)  
31. Cesium3DTileset \- Cesium Documentation, accessed on February 5, 2026, [https://cesium.com/learn/cesiumjs/ref-doc/Cesium3DTileset.html](https://cesium.com/learn/cesiumjs/ref-doc/Cesium3DTileset.html)  
32. maximumScreenSpaceError a bad metric for 3D Tiles · Issue \#4043 · CesiumGS/cesium, accessed on February 6, 2026, [https://github.com/CesiumGS/cesium/issues/4043](https://github.com/CesiumGS/cesium/issues/4043)  
33. How to Eliminate Shimmering in Microsoft Flight Simulator \- YouTube, accessed on February 6, 2026, [https://www.youtube.com/watch?v=1Oa4ZPuqKqs](https://www.youtube.com/watch?v=1Oa4ZPuqKqs)  
34. Lateral Oscillation \- General Discussion \- Microsoft Flight Simulator Forums, accessed on February 6, 2026, [https://forums.flightsimulator.com/t/lateral-oscillation/323980](https://forums.flightsimulator.com/t/lateral-oscillation/323980)  
35. UPDATE: MSFS 2020 Stuttering when window focused, working in background (and crazy high CPU usage) FIX/workaround \- Change your processor scheduling to "background services." : r/flightsim \- Reddit, accessed on February 5, 2026, [https://www.reddit.com/r/flightsim/comments/idmdqq/update\_msfs\_2020\_stuttering\_when\_window\_focused/](https://www.reddit.com/r/flightsim/comments/idmdqq/update_msfs_2020_stuttering_when_window_focused/)  
36. Optimal Terrain LOD and Object LOD : r/MicrosoftFlightSim \- Reddit, accessed on February 5, 2026, [https://www.reddit.com/r/MicrosoftFlightSim/comments/1fob23i/optimal\_terrain\_lod\_and\_object\_lod/](https://www.reddit.com/r/MicrosoftFlightSim/comments/1fob23i/optimal_terrain_lod_and_object_lod/)  
37. What is the deal with Terrain Level of Detail (TLOD)? \- Microsoft Flight Simulator Forums, accessed on February 6, 2026, [https://forums.flightsimulator.com/t/what-is-the-deal-with-terrain-level-of-detail-tlod/559493](https://forums.flightsimulator.com/t/what-is-the-deal-with-terrain-level-of-detail-tlod/559493)  
38. Screen-space error: how can I compute? : r/GraphicsProgramming \- Reddit, accessed on February 6, 2026, [https://www.reddit.com/r/GraphicsProgramming/comments/1d1mso3/screenspace\_error\_how\_can\_i\_compute/](https://www.reddit.com/r/GraphicsProgramming/comments/1d1mso3/screenspace_error_how_can_i_compute/)  
39. Massive LOD changes visible on ground when flying over photogrammetry areas \- Scenery and Airports \- Microsoft Flight Simulator Forums, accessed on February 6, 2026, [https://forums.flightsimulator.com/t/massive-lod-changes-visible-on-ground-when-flying-over-photogrammetry-areas/738065](https://forums.flightsimulator.com/t/massive-lod-changes-visible-on-ground-when-flying-over-photogrammetry-areas/738065)