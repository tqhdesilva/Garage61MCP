import unittest
import json
import os
import sys
import re
import pytest
from dotenv import load_dotenv

# Ensure repo root is in path
sys.path.append(os.getcwd())

from garage61_mcp.server import (
    get_me, get_my_stats, list_teams, get_team_stats,
    list_cars, list_tracks, find_laps, get_lap_details,
    get_lap_telemetry, analyze_telemetry, plot_telemetry
)

load_dotenv()

@pytest.mark.integration
class TestGarage61ServerIntegration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.token = os.environ.get('GARAGE61_TOKEN')
        if not self.token:
            self.skipTest("GARAGE61_TOKEN not found in environment.")

    async def call_tool(self, tool, *args, **kwargs):
        """Helper to call MCP tool functions directly."""
        if hasattr(tool, 'fn'):
            return await tool.fn(*args, **kwargs)
        else:
            return await tool(*args, **kwargs)

    async def test_server_basic_info(self):
        """Verify basic info tools via the server entry points."""
        me_json = await self.call_tool(get_me)
        self.assertIsNotNone(me_json)
        me = json.loads(me_json)
        self.assertIn('slug', me)
        
        cars_json = await self.call_tool(list_cars)
        self.assertGreater(len(json.loads(cars_json)), 0)
        
        tracks_json = await self.call_tool(list_tracks)
        self.assertGreater(len(json.loads(tracks_json)), 0)

    async def test_server_lap_and_telemetry_workflow(self):
        """Verify the full lap discovery to telemetry analysis workflow."""
        # 1. Find a lap (Daytona track 57 is used as a reliable baseline in tests)
        laps_json = await self.call_tool(find_laps, tracks=[57], limit=1, age=90)
        laps = json.loads(laps_json)
        if not laps:
            self.skipTest("No laps found for testing workflow.")
            
        lap_id = laps[0]['id']
        
        # 2. Get details
        details_json = await self.call_tool(get_lap_details, lap_id=lap_id)
        self.assertIsNotNone(details_json)
        
        # 3. Download telemetry
        telemetry_result = await self.call_tool(get_lap_telemetry, lap_id=lap_id)
        self.assertIn("Path:", telemetry_result)
        
        match = re.search(r"Path: (.*)", telemetry_result)
        self.assertTrue(match, "Could not parse file path from telemetry tool output")
        csv_path = match.group(1).strip()
        
        # 4. Analyze
        analysis_json = await self.call_tool(analyze_telemetry, filepath=csv_path)
        analysis = json.loads(analysis_json)
        self.assertIn('summary', analysis)
        self.assertIn('max_speed', analysis['summary'])
        
        # 5. Plot
        plot_result = await self.call_tool(plot_telemetry, filepath=csv_path)
        self.assertIn("Plot generated at", plot_result)

if __name__ == '__main__':
    unittest.main()
