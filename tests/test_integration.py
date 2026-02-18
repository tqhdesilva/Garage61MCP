import unittest
import os
import sys
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Ensure repo root is in path
sys.path.append(os.getcwd())

from garage61_mcp.client import Garage61Client
from garage61_mcp.models import FindLapsParams, GroupBy

load_dotenv()

class TestGarage61Integration(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.token = os.environ.get('GARAGE61_TOKEN')
        if not self.token:
            self.skipTest("GARAGE61_TOKEN not found in environment.")
        self.client = Garage61Client(token=self.token)

    async def test_00_get_me(self):
        """Verify get_me endpoint returns valid Me object."""
        print("\n  - Testing get_me...")
        me = await self.client.get_me()
        self.assertIsNotNone(me.id)
        self.assertIsNotNone(me.slug)
        print(f"    Authenticated as: {me.firstName} {me.lastName} ({me.slug})")

    async def test_01_content_endpoints(self):
        """Verify content discovery endpoints (cars, tracks, platforms)."""
        print("\n  - Testing content endpoints...")
        
        cars = await self.client.list_cars()
        self.assertGreater(len(cars), 0, "Should return at least one car")
        print(f"    Found {len(cars)} cars.")

        tracks = await self.client.list_tracks()
        self.assertGreater(len(tracks), 0, "Should return at least one track")
        print(f"    Found {len(tracks)} tracks.")

        platforms = await self.client.list_platforms()
        self.assertGreater(len(platforms), 0, "Should return at least one platform")
        print(f"    Found {len(platforms)} platforms.")

    async def test_02_find_laps_recent(self):
        """Verify searching for recent laps (last 7 days)."""
        print("\n  - Testing find_laps (recent)...")
        # Try to find something broader if 7 days returns nothing, or just accept empty list as valid result
        # 'age=30' gives us a better chance of hitting data for a casual user
        params = FindLapsParams(drivers=["me"], tracks=[57], age=30, limit=5, group=GroupBy.DRIVER)
        laps = await self.client.find_laps(params)
        print(f"    Found {len(laps)} laps (last 30 days).")
        
        if laps:
            lap = laps[0]
            self.assertIsNotNone(lap.id)
            self.assertIsNotNone(lap.car)
            self.assertIsNotNone(lap.track)
            print(f"    Sample: {lap.id} | {lap.track.name} | {lap.car.name}")

    async def test_03_find_laps_after_date(self):
        """Verify searching for laps after a specific date."""
        print("\n  - Testing find_laps (after date)...")
        # 6 months ago to ensure we get data
        date_filter = (datetime.now() - timedelta(days=180)).strftime("%Y-%m-%d")
        params = FindLapsParams(drivers=["me"], tracks=[57], after=date_filter, limit=5)
        laps = await self.client.find_laps(params)
        print(f"    Found {len(laps)} laps after {date_filter}.")
        # We don't assert len > 0 because user might be new, but we assert no error raised

    async def test_04_telemetry_download(self):
        """Verify we can download telemetry for a lap."""
        print("\n  - Testing telemetry download...")
        # First find a lap
        params = FindLapsParams(drivers=["me"], tracks=[57], age=90, limit=1)
        laps = await self.client.find_laps(params)
        
        if not laps:
            self.skipTest("No laps found in last 90 days, cannot test telemetry download.")
            
        lap_id = laps[0].id
        print(f"    Downloading telemetry for lap {lap_id}...")
        csv_data = await self.client.get_lap_telemetry(lap_id)
        
        self.assertTrue(len(csv_data) > 0, "Telemetry CSV should not be empty")
        # Check for standard CSV header or content
        self.assertTrue("Time" in csv_data or "Speed" in csv_data or "," in csv_data)
        print(f"    Success. Size: {len(csv_data)} bytes.")

    async def test_05_teams(self):
        """Verify team related endpoints."""
        print("\n  - Testing team endpoints...")
        teams = await self.client.list_teams()
        print(f"    Found {len(teams)} teams.")
        
        if teams:
            team = teams[0]
            print(f"    Testing details for team: {team.name} ({team.id})")
            
            # Get specific team
            team_details = await self.client.get_team(team.id)
            self.assertEqual(team_details.id, team.id)
            self.assertEqual(team_details.name, team.name)
            
            # Get team stats
            print(f"    Testing stats for team: {team.id}")
            stats = await self.client.get_team_stats(team.id)
            self.assertIsNotNone(stats.drivingStatistics)
            self.assertIsInstance(stats.drivingStatistics, list)
            
    async def test_06_my_stats(self):
        """Verify user statistics."""
        print("\n  - Testing get_my_stats...")
        stats = await self.client.get_my_stats()
        self.assertIsNotNone(stats.drivingStatistics)
        print(f"    Retrieved stats with {len(stats.drivingStatistics)} entries.")

    async def test_07_lap_details(self):
        """Verify get_lap_details."""
        print("\n  - Testing get_lap_details...")
        # Need a lap ID first
        params = FindLapsParams(drivers=["me"], tracks=[57], limit=1, age=30)
        laps = await self.client.find_laps(params)
        
        if not laps:
            self.skipTest("No recent laps found to test details.")
            
        lap_id = laps[0].id
        print(f"    Fetching details for lap {lap_id}...")
        lap = await self.client.get_lap_details(lap_id)
        
        self.assertEqual(lap.id, lap_id)
        self.assertIsNotNone(lap.sectors)
        print(f"    Success. Lap time: {lap.lapTime}")

if __name__ == '__main__':
    unittest.main()
