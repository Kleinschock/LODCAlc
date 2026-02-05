import math

# ==============================================================================
# EXPERIMENT B: CULLING EFFICIENCY SIMULATOR
# Comparing 512m vs 1024m Tile Granularity
# ==============================================================================

class CullingSim:
    def __init__(self):
        self.FOV_DEG = 12.0
        self.VISIBILITY = 20000.0 # 20km
        self.CAM_POS = (0, 100) # x, z
        self.CAM_DIR = (0, 1) # Looking North
        
        # Frustum Planes (Simplified 2D Wedge)
        half_fov = math.radians(self.FOV_DEG / 2.0)
        self.FRUSTUM_LEFT = math.radians(90 + half_fov)
        self.FRUSTUM_RIGHT = math.radians(90 - half_fov)

    def is_tile_visible(self, tx, ty, t_size):
        # Function to check if a square tile intersects with the 2D frustum triangle
        # Simplified: Check if any corner is in frustum? Or frustum in tile?
        # For this sim, conservative "Center in Frustum or close" is enough.
        
        # Tile Center
        cx = tx + t_size/2
        cy = ty + t_size/2
        
        dx = cx - self.CAM_POS[0]
        dy = cy - self.CAM_POS[1]
        dist = math.sqrt(dx*dx + dy*dy)
        
        if dist > self.VISIBILITY + t_size: return False # Distance Cull
        if dist < t_size: return True # Too close to miss
        
        angle = math.atan2(dy, dx) # -pi to pi
        angle_deg = math.degrees(angle)
        
        # Camera is looking North (90 deg)
        # FOV is 12 deg (+/- 6 deg) -> [84, 96]
        fov_half = self.FOV_DEG / 2.0
        
        # Check angle against 90 +/- fov (with some padding for tile width)
        # At distance D, tile covers angle Alpha = atan(Size/D)
        angular_width_deg = math.degrees(math.atan(t_size / dist))
        
        if (90 - fov_half - angular_width_deg) <= angle_deg <= (90 + fov_half + angular_width_deg):
            return True
            
        return False

    def run_benchmark(self, tile_size):
        print(f"\n--- Testing Tile Size: {tile_size}m ---")
        
        # Grid Size
        # 20km radius -> 40km box
        range_min = -20000
        range_max = 20000
        
        total_tiles = 0
        visible_tiles = 0
        
        for x in range(range_min, range_max, tile_size):
            for y in range(0, range_max, tile_size): # Only simulate front hemisphere
                total_tiles += 1
                if self.is_tile_visible(x, y, tile_size):
                    visible_tiles += 1
                    
        print(f"Total Tiles in Horizon: {total_tiles}")
        print(f"Visible Tiles (Draw Calls): {visible_tiles}")
        
        # Draw Call Overhead metric (Abstract Cost)
        # Using typical modern cost: 1 DC = 0.01ms CPU time?
        cost_cpu = visible_tiles * 1.0 
        
        # GPU Vertex Cost
        # Assume 1024m tile has 256x256 verts (65k)
        # 512m tile has 128x128 verts (16k)
        # Wait, if we keep density constant (0.5m spacing), then:
        # 1024m -> 2048x2048 grid? No, that's insane.
        # Let's assume constant screen density.
        # Usually, 1024m tile is one DrawCall.
        # If we split it into 4x 512m tiles, we have 4 DrawCalls.
        # But we might cull 1 or 2 of them.
        
        print(f"Draw Call Score (Lower is better): {cost_cpu}")
        return visible_tiles

if __name__ == "__main__":
    sim = CullingSim()
    
    # Test 512m vs 1024m
    dc_512 = sim.run_benchmark(512)
    dc_1024 = sim.run_benchmark(1024) # Expect fewer calls
    dc_2048 = sim.run_benchmark(2048) # Expect fewest
    
    print("\n--- COMPARISON ---")
    print(f"512m -> 1024m: {(dc_512/dc_1024):.2f}x more draw calls")
    print(f"1024m -> 2048m: {(dc_1024/dc_2048):.2f}x more draw calls")
    
    print("\nCONCLUSION:")
    if (dc_512 / dc_1024) > 3.0:
        print("Using 512m tiles triples the CPU overhead. Likely NOT worth the culling gain.")
    else:
        print("Using 512m tiles is efficient.")
    
    print("Recommendation: Use Hybrid.")
    print("Near the camera (0-2km): Use 512m for culling.")
    print("Far field (2km+): Use 1024m or 2048m to batch draw calls.")
