import math

# --- INPUT PARAMETERS ---
CameraZ = 100            # Altitude (meters)
Camera_Pitch = -12       # Tilt angle (degrees). 0 = Horizontal, -90 = Straight Down
VertFoV = 12             # Vertical Field of View (degrees)
VertPixel = 1024         # Screen Vertical Resolution
TileSize = 1024          # Physical size of one terrain tile (meters)
max_LOD_range = 20000    # Maximum visibility distance (meters)
LOD_stages = 4           # Increased to 4 for smoother transitions

def calculate_optimized_lod():
    print(f"--- Terrain LOD Optimization Report ---")
    
    # 1. Calculate Visual Acuity (Radians per pixel)
    # This tells us how much "world" one pixel on your screen covers.
    rad_per_pixel = math.radians(VertFoV) / VertPixel
    
    # 2. Account for Pitch Angle (Perspective Distortion)
    # When looking at an angle, the ground pixels are "stretched."
    # We use the sine of the pitch to find the slant range.
    pitch_rad = math.radians(abs(Camera_Pitch))
    if pitch_rad == 0: pitch_rad = 0.01 # Prevent division by zero
    
    # 3. Calculate Base Ground Sample Distance (GSD) at the center of view
    # GSD = (Altitude / sin(pitch)) * radians_per_pixel
    slant_range_center = CameraZ / math.sin(pitch_rad)
    gsd_at_target = slant_range_center * rad_per_pixel
    
    print(f"Altitude: {CameraZ}m | Pitch: {Camera_Pitch}°")
    print(f"Base Ground Resolution: {gsd_at_target:.3f} meters/pixel\n")

    # 4. Generate LOD Stages
    # We use a 2^n scaling factor. This is the "Golden Rule" for terrain engines
    # because it prevents "texture swimming" and aliasing.
    lod_ranges = [0]
    
    for stage in range(LOD_stages):
        # The resolution of each stage doubles to save memory
        # LOD 0 (Highest Detail), LOD 1 (Half Detail), etc.
        stage_res = gsd_at_target * (2**stage)
        
        # Calculate the ideal distance for this LOD
        # Distance = Resolution / rad_per_pixel
        distance = stage_res / rad_per_pixel
        
        # Apply the pitch correction to the distance
        effective_distance = distance * math.sin(pitch_rad)
        
        # Cap at max visibility
        if effective_distance > max_LOD_range:
            effective_distance = max_LOD_range
            
        lod_ranges.append(round(effective_distance, 2))
        
        print(f"LOD {stage}:")
        print(f"  - Texture Res: {stage_res:.2f} m/pixel")
        print(f"  - Range: {lod_ranges[stage]}m to {effective_distance}m")
        
        if effective_distance == max_LOD_range:
            break

    print(f"\n--- Final Settings for Terrain Editor ---")
    for i in range(len(lod_ranges)-1):
        print(f"Level {i}: {lod_ranges[i]}m - {lod_ranges[i+1]}m")

if __name__ == "__main__":
    calculate_optimized_lod()