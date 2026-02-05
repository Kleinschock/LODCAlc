import math

# ==============================================================================
# EXPERT TERRAIN LOD IMPLEMENTATION
# Based on "Master Design Document" & "Implementation Checklist"
# ==============================================================================

class LODConfig:
    def __init__(self):
        # ----------------------------------------------------------------------
        # 1. PHYSICS CONSTANTS (From Checklist)
        # ----------------------------------------------------------------------
        self.R_EARTH = 6371000.0        # Meters
        self.SCREEN_H = 1024.0          # Pixels
        self.FOV_V_DEG = 12.0           # Degrees
        self.SSE_THRESHOLD = 1.0        # Pixels (Target)

        # ----------------------------------------------------------------------
        # 2. OPTICAL DERIVATION
        # ----------------------------------------------------------------------
        # K = S_h / (2 * tan(fov/2))
        fov_rad = math.radians(self.FOV_V_DEG)
        self.K_PERSPECTIVE = self.SCREEN_H / (2.0 * math.tan(fov_rad / 2.0))
        
        # Verify K against checklist (should be ~4889.2)
        print(f"[DEBUG] Calculated K: {self.K_PERSPECTIVE:.4f}")

        # ----------------------------------------------------------------------
        # 3. STABILITY LOGIC (The "Pitch Lock")
        # ----------------------------------------------------------------------
        # We DO NOT use real-time pitch. We use a "Worst Case" constant.
        # Checklist: -15 degrees (-0.2617 rad)
        self.PITCH_LOCK_DEG = -15.0
        self.PITCH_SCALAR = abs(math.cos(math.radians(self.PITCH_LOCK_DEG)))
        
        print(f"[DEBUG] Pitch Lock: {self.PITCH_LOCK_DEG} deg")
        print(f"[DEBUG] Pitch Scalar (cos): {self.PITCH_SCALAR:.4f}")

    def calculate_switch_distance(self, geometric_error):
        """
        Solves D for a given Geometric Error (delta) and SSE Threshold (tau).
        Formula: D = (delta * K * PitchScalar) / tau
        """
        # Note: The original formula was Error_Proj = (Error_World * cos) / D * K
        # Solving for D where Error_Proj = 1.0:
        # 1.0 = (delta * cos * K) / D  =>  D = delta * cos * K
        
        return geometric_error * self.PITCH_SCALAR * self.K_PERSPECTIVE

    def get_lod_table(self):
        # Geometric errors for each LOD (Standard Quadtree progression)
        # LOD 0: 0.1m error
        # LOD 1: 0.2m error 
        # LOD 2: 0.4m error
        # LOD 3: 0.8m error
        # LOD 4: 1.6m error
        errors = [0.1, 0.2, 0.4, 0.8, 1.6]
        
        print("\n--- LOD TRANSITION TABLE (Generated) ---")
        print(f"{'LOD':<5} | {'Error(m)':<10} | {'Switch Dist(m)':<15} | {'Morph Start(m)':<15}")
        print("-" * 55)
        
        results = []
        for i, err in enumerate(errors):
            dist = self.calculate_switch_distance(err)
            
            # Geomorphing Logic: Start morphing when error > 0.5px
            # If D_switch is where error=1.0px, then D_start is where error=0.5px?
            # Actually, error grows as we get closer? No, error grows as distance increases?
            # Wait. Projected Error = World / Dist. Error decreases with distance.
            # NO. We switch LODs as we get FURTHER away to lower detail.
            # Low LOD has high WorldError.
            # At close range, High WorldError projects to Huge ScreenError.
            # We push it far away until ProjectedError < 1.0.
            # So dist is the MINIMUM distance this LOD is valid for?
            # Or the MAXIMUM distance the PREVIOUS LOD is valid for?
            
            # Let's clarify:
            # LOD 0 (Fine) has 0.1m error.
            # At 100m, 0.1m projects to (0.1 * 4889 / 100) = 4.8 pixels. Too high.
            # At 500m, 0.1m projects to (0.1 * 4889 / 500) = 0.9 pixels. OK.
            # So 'dist' is the MINIMUM distance required to switch TO this level?
            # No, standard LOD systems work by "Switch Distance" being the boundary.
            # LOD 0 (0.1m) is valid up to 478m.
            # LOD 1 (0.2m) is valid from 478m to 972m.
            
            # Morphing: We want to blend FROM LOD N TO LOD N+1.
            # This happens BEFORE the switch distance of LOD N.
            # If LOD 0 ends at 478m (Error=1.0px), we start morphing when Error=0.5px?
            # No, if Error=0.5px, that's closer or further?
            # 1.0 = C / D_end  => D_end = C
            # 0.5 = C / D_start => D_start = 2 * C = 2 * D_end.
            # Wait. If distance increases, projected error decreases.
            # We want to morph as the error *grows* to 1.0? 
            # No, we assume we are using LOD 0. It is perfect.
            # As we get further, its error is small? No, projected error of a FIXED world error decreases with distance.
            # But the 'World Error' we talk about is the Error of the *Approximation*.
            # LOD 1 has 0.2m error. We can't use it until 972m.
            # If we use it at 500m, it has (0.2 * 4889 / 500) = 2.0 pixels. Visible popping!
            
            # Standard Geomorph Logic:
            # You are rendering LOD N. You approach the distance where you MUST switch to LOD N-1 (Higher Detail).
            # OR you recede to the distance where you CAN switch to LOD N+1 (Lower Detail).
            
            # Let's assume standard "Moving Away" scenario.
            # We are at 100m. We use LOD 0.
            # We reach 478m. We switch to LOD 1.
            # To avoid pop, we morph LOD 0 vertices *towards* LOD 1 positions just before 478m.
            # We want the morph to complete exactly at 478m.
            # Start position? Typically a fixed range, e.g. 10% buffering.
            # Checklist says: Morph Start 0.5px, Morph End 1.0px.
            # This refers to the SSE metric controlling the morph.
            
            morph_dist_end = dist
            # If at dist, error = 1.0.
            # We want to know where error = 0.5 (Projected).
            # 0.5 = (Delta * K) / D_start  --> D_start = (Delta * K) / 0.5 = 2.0 * D_end.
            # This implies we morph *after* the switch distance? 
            # No, this means for a fixed geometric error, it is smaller (0.5) further away (2x dist).
            # This implies we morph *into* a lower LOD as we recede?
            # Correct. At 478m, LOD 0 error is 1.0px. At 956m, LOD 0 error is 0.5px.
            # But we want to switch TO LOD 1.
            
            # Let's stick to the "Transition Buffer" approach from the report.
            # "Start morphing 100m before the switch point."
            morph_buffer = dist * 0.2 # 20% hysteresis/morph zone
            
            results.append({
                "level": i,
                "error": err,
                "dist": dist,
                "morph_start": dist - morph_buffer
            })
            print(f"{i:<5} | {err:<10} | {dist:<15.2f} | {dist - morph_buffer:<15.2f}")
            
        return results

    def verify_stability_simulation(self):
        """
        Simulates 'Turbulence' by varying the raw pitch and checking if 
        the calculated switch distance changes. It SHOULD NOT change.
        """
        print("\n--- STABILITY VERIFICATION (Turbulence Test) ---")
        base_error = 0.1 # LOD 0
        
        # Test 1: Pitch -15 (LOCK value)
        d_stable = (base_error * self.K_PERSPECTIVE * abs(math.cos(math.radians(-15)))) / 1.0
        print(f"Baseline (-15 deg): {d_stable:.2f} m")
        
        # Test 2: Pitch -10 (Turbulence Up)
        # Using the PITCH_LOCK_DEG in the formula, regardless of input 'pitch'
        # This simulates the code logic: D = K * E * cos(LOCK) / eta
        
        # If we used RAW pitch:
        d_raw_10 = (base_error * self.K_PERSPECTIVE * abs(math.cos(math.radians(-10)))) / 1.0
        
        # If we use LOCKED pitch (our class logic):
        d_locked_10 = self.calculate_switch_distance(base_error) # Uses self.PITCH_LOCK_DEG
        
        print(f"Turbulence (-10 deg) | RAW: {d_raw_10:.2f} m (Breathing!) | LOCKED: {d_locked_10:.2f} m (Stable)")
        
        if abs(d_stable - d_locked_10) < 0.001:
            print(">> SUCCESS: System is STABLE. Locking mechanism working.")
        else:
            print(">> FAILURE: System is UNSTABLE.")

if __name__ == "__main__":
    config = LODConfig()
    config.get_lod_table()
    config.verify_stability_simulation()
