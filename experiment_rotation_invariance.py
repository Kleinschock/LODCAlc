import math
import random

# ==============================================================================
# EXPERIMENT A: ROTATION INVARIANCE
# Comparing "Locked Pitch" vs "Bounding Sphere" Approaches
# ==============================================================================

class ExperimentConfig:
    def __init__(self):
        self.SCREEN_H = 1024.0
        self.FOV_V_DEG = 12.0
        fov_rad = math.radians(self.FOV_V_DEG)
        self.K_PERSPECTIVE = self.SCREEN_H / (2.0 * math.tan(fov_rad / 2.0))
        
        # Test Object: A 10m tall hill at 5000m distance
        self.GEOM_ERROR = 10.0 # meters
        self.DISTANCE = 5000.0 # meters
        
        # The "True" projected size depends on exact viewing angle.
        # At horizon (0 deg), we see full 10m.
        # At nadir (-90 deg), we see 0m (top down).
        
    def get_true_projected_error(self, pitch_deg):
        """
        Calculates the physically accurate error in pixels for a given pitch.
        This is the Ground Truth we want to match.
        """
        # Visibility scales with cos(viewing_angle)
        # Assuming Pitch=0 is Horizon (View scale = 1.0)
        # Assuming Pitch=-90 is Down (View scale = 0.0)
        view_scale = abs(math.cos(math.radians(pitch_deg)))
        return (self.GEOM_ERROR * view_scale * self.K_PERSPECTIVE) / self.DISTANCE

    def get_locked_pitch_error(self, pitch_deg_ignored):
        """
        Strategy 1: Locked Pitch
        We ignore the real pitch and assume -15 degrees always.
        """
        locked_pitch = -15.0
        view_scale = abs(math.cos(math.radians(locked_pitch)))
        return (self.GEOM_ERROR * view_scale * self.K_PERSPECTIVE) / self.DISTANCE

    def get_bounding_sphere_error(self, pitch_deg_ignored):
        """
        Strategy 2: Bounding Sphere
        We measure the error of the *radius* of the chunk's bounding sphere.
        This is constant regardless of rotation.
        BUT, a vertical displacement of 10m implies a Sphere Radius of at least 5m?
        Conservatively, we assume the error IS the diameter.
        Sphere projection is just (Radius / Distance) * K.
        It doesn't use Cosine. It assumes Worst Case (broadside) always.
        """
        # Worst case: We see the full error (Horizon view)
        view_scale = 1.0 
        return (self.GEOM_ERROR * view_scale * self.K_PERSPECTIVE) / self.DISTANCE

def run_simulation():
    sim = ExperimentConfig()
    
    print("--- EXPERIMENT A: ROTATION INVARIANCE ---")
    print(f"Target: 10m Error at 5000m. K={sim.K_PERSPECTIVE:.2f}")
    print(f"{'Pitch(deg)':<10} | {'True(px)':<10} | {'Locked(px)':<10} | {'Sphere(px)':<10} | {'Status'}")
    print("-" * 65)
    
    # Simulate a dive from Horizon (0) to Down (-90) with Turbulence
    pitch_values = [0, -10, -15, -30, -45, -60, -80, -90]
    
    previous_sphere = 0
    previous_locked = 0
    
    for p in pitch_values:
        # Add turbulence (+/- 2 deg)
        turb = random.uniform(-2.0, 2.0)
        p_turb = p + turb
        
        err_true = sim.get_true_projected_error(p_turb)
        err_locked = sim.get_locked_pitch_error(p_turb) # Input is ignored
        err_sphere = sim.get_bounding_sphere_error(p_turb) # Input is ignored
        
        # Analyze correctness
        # Locked is optimized for -15 deg.
        # Sphere is optimized for 0 deg (Worst Case).
        
        status = ""
        if err_locked < err_true:
            status = "UNDER (Popping Risk)"
        elif err_locked > err_true * 1.5:
             status = "OVER (Wasteful)"
        else:
            status = "Good"
            
        print(f"{p_turb:<10.2f} | {err_true:<10.2f} | {err_locked:<10.2f} | {err_sphere:<10.2f} | {status}")
        
    print("-" * 65)
    print("CONCLUSIONS:")
    print("1. 'True' error fluctuates wildly with turbulence (The Breathing Problem).")
    print("2. 'Locked' error is stable, but underestimates error at the Horizon (Pitch 0).")
    print("   -> Risk: If we lock to -15, but fly level at 0, mountains might pop.")
    print("3. 'Sphere' error is stable, but equals Maximum True Error.")
    print("   -> Safe: Never pops.")
    print("   -> Wasteful: When looking down (-90), we calculate 10px error when True is 0px.")

if __name__ == "__main__":
    run_simulation()
