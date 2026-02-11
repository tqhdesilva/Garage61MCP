import asyncio
import json
import os
import sys
import re

# Add src to sys.path
sys.path.append(os.path.join(os.getcwd(), 'src'))

from garage61_mcp.server import (
    get_me, get_my_stats, list_teams, get_team_stats,
    list_cars, list_tracks, find_laps, get_lap_details,
    get_lap_telemetry, analyze_telemetry, plot_telemetry
)

async def run_test():
    print("=== Garage61 MCP Python Server Test ===\n")

    # Helper to call tool
    async def call(tool, *args, **kwargs):
        try:
            if hasattr(tool, 'fn'):
                return await tool.fn(*args, **kwargs)
            else:
                return await tool(*args, **kwargs)
        except Exception as e:
            name = getattr(tool, 'name', str(tool))
            print(f"Error calling {name}: {e}")
            return None

    # 1. Basic Info
    print("--- Basic Info ---")
    me = await call(get_me)
    if me: print(f"User: {json.loads(me)['slug']}")
    
    cars = await call(list_cars)
    if cars: print(f"Cars found: {len(json.loads(cars))}")
    
    tracks = await call(list_tracks)
    if tracks: print(f"Tracks found: {len(json.loads(tracks))}")

    # 2. Find a Lap
    print("\n--- Finding Laps ---")
    laps_json = await call(find_laps, limit=1)
    if not laps_json:
        print("No laps found or error.")
        return

    laps = json.loads(laps_json)
    if not laps:
        print("No laps returned.")
        return

    lap = laps[0]
    lap_id = lap['id']
    print(f"Found Lap ID: {lap_id}, Driver: {lap['driver']['slug']}, Car: {lap['car']['name']}, Track: {lap['track']['name']}")

    # 3. Lap Details
    print(f"\n--- Getting Details for Lap {lap_id} ---")
    details = await call(get_lap_details, lap_id=lap_id)
    if details:
        print("Details retrieved successfully.")

    # 4. Telemetry
    print(f"\n--- Getting Telemetry for Lap {lap_id} ---")
    telemetry_result = await call(get_lap_telemetry, lap_id=lap_id)
    if not telemetry_result:
        print("Failed to get telemetry.")
        return

    print("Telemetry Result Preview:", telemetry_result[:100].replace('\n', ' '))
    
    # Extract path from result string
    match = re.search(r"Path: (.*)", telemetry_result)
    if not match:
        print("Could not parse file path from result.")
        return
        
    csv_path = match.group(1).strip()
    print(f"CSV Path: {csv_path}")

    # 5. Analysis
    print(f"\n--- Analyzing Telemetry from {csv_path} ---")
    analysis_json = await call(analyze_telemetry, filepath=csv_path)
    if analysis_json:
        analysis = json.loads(analysis_json)
        print("Analysis Summary:", json.dumps(analysis.get('summary'), indent=2))
        print(f"Braking Zones: {len(analysis.get('braking_zones', []))}")
        print(f"Corners: {len(analysis.get('corners', []))}")

    # 6. Plotting
    print(f"\n--- Plotting Telemetry ---")
    plot_result = await call(plot_telemetry, filepath=csv_path)
    if plot_result:
        print("Plot Result:", plot_result)

if __name__ == "__main__":
    asyncio.run(run_test())
