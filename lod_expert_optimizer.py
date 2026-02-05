import math

# --- EXPERT PHYSICALLY BASED CONFIGURATION ---
CONSTANTS = {
    'R_earth': 6371000.0,       # Earth Radius in meters
    'ScreenRes_Y': 1024,        # Vertical pixels
    'FOV_V_deg': 12.0,          # Vertical Field of View
    'Camera_Z': 100.0,          # Altitude (m)
    'Pitch_deg': -12.0,         # Camera Pitch
    'Max_Vis': 20000.0,         # Max Visibility (m)
    'Tile_Size': 1024.0,        # Terrain Tile Dim (m)
    'SSE_Threshold': 1.0        # Allowable Screen Space Error (pixels) - The "Holy Grail" constant
}

def calculate_lod_strategy():
    print("--- TRIPLE-A FLIGHT SIM LOD OPTIMIZER ---")
    print(f"Target SSE: {CONSTANTS['SSE_Threshold']} pixel(s) error")
    
    # 1. OPTICAL CALCULATIONS (The "Lens")
    # ------------------------------------
    # Calculate angular resolution at the center of the screen
    fov_v_rad = math.radians(CONSTANTS['FOV_V_deg'])
    rad_per_pixel = fov_v_rad / CONSTANTS['ScreenRes_Y']
    
    pitch_rad = math.radians(abs(CONSTANTS['Pitch_deg']))
    
    # 2. EARTH CURVATURE & HORIZON
    # ------------------------------------
    r_e = CONSTANTS['R_earth']
    h = CONSTANTS['Camera_Z']
    # Geometric horizon distance: d = sqrt(2Rh + h^2)
    horizon_dist_geo = math.sqrt(2 * r_e * h + h**2)
    
    # Curvature drop at Max Visibility (20km)
    # drop approx d^2 / 2R
    drop_at_20km = (CONSTANTS['Max_Vis']**2) / (2 * r_e)
    
    print(f"\n[PHYSICS CHECK]")
    print(f"Geometric Horizon: {horizon_dist_geo/1000:.2f} km")
    print(f"Curvature Drop at 20km: {drop_at_20km:.2f} m")
    
    if CONSTANTS['Max_Vis'] < horizon_dist_geo:
        print(f"Reachable Visibility (20km) is NOT occluded by Earth curvature.")
    else:
        print(f"!] WARNING: Max Visibility exceeds horizon line.")

    # 3. SCREEN SPACE ERROR (SSE) INVERSE SOLVER
    # ------------------------------------
    # We want to find the distance 'D' where the 'World Error' (Geometric Error)
    # projects to exactly 'SSE_Threshold' pixels on screen.
    #
    # Formula for Projected Size (Height) P_h in pixels:
    # P_h = (ObjectHeight / D_slant) / rad_per_pixel
    #
    # However, we must account for the VIEWING ANGLE (Grazing Angle).
    # When looking at the ground at shallow angles, terrain height errors (bumps)
    # appear full size (perpendicular to view mostly), but flat texture errors are foreshortened.
    # For LOD switching (mesh simplification), the error is usually vertical (height map diff).
    #
    # Let's assume the error is a vertical displacement (delta Z).
    # Effective projected height depends on the depression angle 'alpha' to that point.
    # alpha = atan(H / D_ground)
    #
    # But simpler approximation for LOD engines:
    # Distance = (GeometricError * ScreenHeight) / (SSE_Threshold * 2 * tan(FOV/2))
    # This is the standard isotropic formula. 
    # For flight sims with pitch, we use Slant Range.
    
    # Define Geometric Error per LOD. 
    # Usually LOD 0 is the reference. LOD 1 removes every 2nd vertex, so max error depends on terrain ruggedness.
    # We assume a standard heuristic: Error doubles each level.
    # Let's estimate Base Error for LOD 1 as approximate 0.1m (10cm) deviation.
    # LOD 0 -> LOD 1 transition happens when LOD 1's error becomes less than 1px.
    
    base_geometric_error = 0.05 # meters (This is a tunable 'quality' knob)
    # If the terrain is very rough, this needs to be higher.
    
    print(f"\n[LOD TRANSITION TABLE (SSE Method)]")
    print(f"Using Base Geometric Error estimate: ±{base_geometric_error*2:.2f}m")
    
    current_dist = 0
    transitions = []
    
    # Pre-calculated constant factor for SSE
    # D = (WorldError / PixelError) * (1 / RadPerPixel)
    # Using small angle approx for individual pixels
    k_res = 1.0 / rad_per_pixel
    
    for level in range(5): # LOD 0 to 4
        # The error introduced by switching TO this level from the previous one
        # effectively, we stick to the PREVIOUS level until the NEXT level's error is acceptable.
        # Wait, standard logic: Stick to LOD 0 until LOD 1's error is < 1px.
        
        # Error of LOD 'level+1' approximation
        # We assume error doubles with stride. 
        # LOD 1 has 2x stride -> error approx 2x base? No, usually power of two scaling implies specific error metrics.
        # Let's use a simpler heuristic common in industry:
        # Distance = C * (2^level)
        # But we want to derive C from the SSE.
        
        # Let's calculate the distance where an error of size 'E' projects to 1 pixel.
        # Error E for LOD n.
        # Let's say LOD 0 is perfect.
        # Transition LOD 0 -> 1: When LOD 1 (Error E1) projects to < 1px.
        # Transition LOD 1 -> 2: When LOD 2 (Error E2) projects to < 1px.
        
        next_level = level + 1
        # Model: Error grows with world-space post spacing.
        # LOD 0: stride 1m -> Error ~0 (Reference)
        # LOD 1: stride 2m -> Max geometric error approx 0.10m
        # LOD 2: stride 4m -> Max geometric error approx 0.20m
        # ...
        
        if level == 4: # Cap
             print(f"LOD 4+: Remaining distance up to {CONSTANTS['Max_Vis']}m")
             break
             
        error_val = base_geometric_error * (2**(next_level)) 
        
        # Solve for Distance
        # D_slant = (Error / SSE_Threshold) * k_res
        
        req_slant_dist = (error_val / CONSTANTS['SSE_Threshold']) * k_res
        
        # Correct for pitch? 
        # The derivation D = Size / Angle assumes the object is perpendicular to view.
        # Vertical terrain errors ARE largely perpendicular to a shallow view (camera looking at horizon).
        # So using Slant Distance directly is the correct approach for Vertical Error.
        
        # Convert Slant Range to Ground Distance (approx) for the editor
        # D_ground = sqrt(D_slant^2 - Altitude^2)
        try:
            ground_dist = math.sqrt(req_slant_dist**2 - CONSTANTS['Camera_Z']**2)
        except ValueError:
            ground_dist = 0 # Below aircraft
            
        # Clamp to Max Vis
        if ground_dist > CONSTANTS['Max_Vis']:
            ground_dist = CONSTANTS['Max_Vis']
            
        transitions.append(ground_dist)
        
        print(f"Transition LOD {level} -> {next_level}:")
        print(f"  Simulated Geom Error: {error_val:.3f}m")
        print(f"  Switch Distance: {ground_dist:.1f}m")
        
    # 4. GROUND SAMPLE DISTANCE (GSD) ANALYSIS
    # ----------------------------------------
    # "Calculate GSD specifically for a perspective view"
    print(f"\n[PERSPECTIVE GSD ANALYSIS]")
    # We calculate GSD at Near, Mid, and Far points
    check_points = [500, 5000, 20000] 
    
    for d in check_points:
        # Slant Range
        slant = math.sqrt(d**2 + CONSTANTS['Camera_Z']**2)
        
        # Lateral GSD (Perpendicular to view direction): (Slant * FOV) / Res
        gsd_lat = slant * rad_per_pixel
        
        # Longitudinal GSD (Along the ground receding from view):
        # This is strictly affected by the grazing angle beta.
        # beta = atan(Height / Distance) + Pitch (roughly)
        # More accurately, angle between view vector and ground plane.
        
        angle_to_ground = math.atan2(CONSTANTS['Camera_Z'], d) # Angle of depression
        # View vector is pitched up by 12 deg from straight down? 
        # No, Pitch -12 means 12 deg below horizon.
        # Angle of depression to point d is atan(H/d).
        # Angle of incidence = Angle of depression (since ground is flat effectively locally)
        # Wait, if we look at horizon (0 deg depression), incidence is 0.
        # Incidence angle alpha = atan(H/d).
        
        alpha = math.atan2(CONSTANTS['Camera_Z'], d)
        
        # Long GSD = Lat GSD / sin(alpha)
        # If alpha is small, GSD becomes HUGE (pixels stretch to infinity)
        gsd_long = gsd_lat / math.sin(alpha)
        
        # Anisotropy ratio
        aniso = gsd_long / gsd_lat
        
        print(f"At {d}m:")
        print(f"  Lateral GSD: {gsd_lat:.3f} m/px")
        print(f"  Longit. GSD: {gsd_long:.3f} m/px")
        print(f"  Anisotropy : {aniso:.1f}x (Requires MIP bias tuning)")

    # 5. EXPERT RECOMMENDATIONS
    # -------------------------
    print(f"\n[EXPERT CONFIGURATION OUTPUT]")
    print(f"LOD_DISTANCES = {convertToIntegerList(transitions)}")
    print(f"MIP_MAP_BIAS = -1.0 (High Quality) or -0.5 (Balanced)")
    print(f"NOTE: At -12deg pitch, ground textures are viewed at grazing angles.")
    print(f"      Standard Trilinear filtering will blur significantly.")
    print(f"      Enable ANISOTROPIC FILTERING (16x) immediately.")
    
def convertToIntegerList(floats):
    return [int(x) for x in floats]

if __name__ == "__main__":
    calculate_lod_strategy()
