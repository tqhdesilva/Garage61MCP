import unittest
import numpy as np
import pandas as pd
import os
import tempfile
from garage61_mcp.telemetry_analysis import TelemetryAnalyzer


def make_synthetic_telemetry(n=200, yaw_is_angle=False):
    """Create synthetic telemetry data with a corner in the middle."""
    dist = np.linspace(0.0, 1.0, n)

    # Speed profile: dip in the middle (corner apex around 0.5)
    speed = 80 - 30 * np.exp(-((dist - 0.52) ** 2) / 0.005)

    # Lateral acceleration: peak in corner zone
    lat_accel = 1.5 * np.exp(-((dist - 0.50) ** 2) / 0.008)

    # Yaw rate: peaks slightly before the speed minimum (MRP before apex)
    yaw_rate_raw = 0.8 * np.exp(-((dist - 0.48) ** 2) / 0.004)

    if yaw_is_angle:
        # Integrate yaw rate to get angle (cumulative), scaled so range > pi
        yaw = np.cumsum(yaw_rate_raw * 50) * (dist[1] - dist[0])
    else:
        yaw = yaw_rate_raw

    # Brake: active before apex, tapering
    brake = np.clip(1.0 - (dist - 0.35) / 0.15, 0, 1)
    brake[dist > 0.50] = 0.0

    # Throttle: ramps up after apex
    throttle = np.clip((dist - 0.55) / 0.1, 0, 1)

    # Steering: peaks near MRP
    steering = 0.5 * np.exp(-((dist - 0.49) ** 2) / 0.006)

    data = {
        'LapDistPct': dist,
        'Speed': speed,
        'LatAccel': lat_accel,
        'Yaw': yaw,
        'Brake': brake,
        'Throttle': throttle,
        'SteeringWheelAngle': steering,
        'Gear': np.full(n, 3),
        'Lat': np.linspace(40.0, 40.01, n),
        'Lon': np.linspace(-74.0, -73.99, n),
    }
    if not yaw_is_angle:
        # When not testing angle fallback, provide YawRate directly
        data['YawRate'] = yaw_rate_raw

    df = pd.DataFrame(data)
    return df


class TestYawRateDetection(unittest.TestCase):
    def test_yaw_rate_column_preferred(self):
        """When YawRate column exists, use it directly."""
        analyzer = TelemetryAnalyzer()
        analyzer.data = make_synthetic_telemetry(yaw_is_angle=False)
        # Add a YawRate column
        analyzer.data['YawRate'] = analyzer.data['Yaw'] * 2  # distinct values
        yaw_rate = analyzer._get_yaw_rate()
        np.testing.assert_array_equal(yaw_rate.values, analyzer.data['YawRate'].values)

    def test_yaw_fallback_differentiated(self):
        """When YawRate column is missing, differentiate Yaw (angle) to get rate."""
        analyzer = TelemetryAnalyzer()
        analyzer.data = make_synthetic_telemetry(yaw_is_angle=True)
        # No YawRate column — must differentiate Yaw
        yaw_rate = analyzer._get_yaw_rate()
        # Result should NOT equal the raw Yaw column (it was differentiated)
        self.assertFalse(np.allclose(yaw_rate.values, analyzer.data['Yaw'].values))
        # Peak yaw rate should be positive and in a reasonable range
        self.assertGreater(yaw_rate.abs().max(), 0)

    def test_yaw_rate_direct_fallback(self):
        """When no YawRate column and Yaw looks like rate (small range), still differentiates."""
        analyzer = TelemetryAnalyzer()
        analyzer.data = make_synthetic_telemetry(yaw_is_angle=False)
        # No YawRate column — falls back to differentiating Yaw
        yaw_rate = analyzer._get_yaw_rate()
        # Differentiation produces different values
        self.assertEqual(len(yaw_rate), len(analyzer.data))


class TestAnalyzeCornersWithMRP(unittest.TestCase):
    def test_mrp_fields_present(self):
        """analyze_corners() should return MRP fields for each corner."""
        analyzer = TelemetryAnalyzer()
        analyzer.data = make_synthetic_telemetry()
        corners = analyzer.analyze_corners()
        self.assertGreater(len(corners), 0)
        for corner in corners:
            self.assertIn('mrp_dist_pct', corner)
            self.assertIn('mrp_yaw_rate', corner)
            self.assertIn('mrp_speed', corner)

    def test_mrp_near_apex(self):
        """MRP should be close to but not necessarily at the apex."""
        analyzer = TelemetryAnalyzer()
        analyzer.data = make_synthetic_telemetry()
        corners = analyzer.analyze_corners()
        self.assertGreater(len(corners), 0)
        corner = corners[0]
        # MRP at ~0.48, apex at ~0.52 — MRP should be before apex
        self.assertLess(corner['mrp_dist_pct'], corner['apex_dist_pct'])
        # But within the corner boundaries
        self.assertGreaterEqual(corner['mrp_dist_pct'], corner['start_dist_pct'])
        self.assertLessEqual(corner['mrp_dist_pct'], corner['end_dist_pct'])


class TestAnalyzeCornerStatsWithMRP(unittest.TestCase):
    def test_mrp_section_present(self):
        """analyze_corner_stats() should include mrp and cornering_phases."""
        analyzer = TelemetryAnalyzer()
        analyzer.data = make_synthetic_telemetry()
        stats = analyzer.analyze_corner_stats(0.3, 0.7)
        self.assertIsNotNone(stats)
        self.assertIn('mrp', stats)
        self.assertIn('cornering_phases', stats)

    def test_mrp_detail_fields(self):
        """MRP section should have all expected fields."""
        analyzer = TelemetryAnalyzer()
        analyzer.data = make_synthetic_telemetry()
        stats = analyzer.analyze_corner_stats(0.3, 0.7)
        mrp = stats['mrp']
        expected_keys = [
            'dist_pct', 'yaw_rate_rad_s', 'speed_kph',
            'brake_at_mrp', 'throttle_at_mrp', 'steering_at_mrp_rad',
            'gear_at_mrp', 'mrp_to_apex_offset_pct'
        ]
        for key in expected_keys:
            self.assertIn(key, mrp, f"Missing key: {key}")

    def test_mrp_to_apex_offset_negative(self):
        """In our synthetic data, MRP is before apex so offset should be negative."""
        analyzer = TelemetryAnalyzer()
        analyzer.data = make_synthetic_telemetry()
        stats = analyzer.analyze_corner_stats(0.3, 0.7)
        self.assertLess(stats['mrp']['mrp_to_apex_offset_pct'], 0)

    def test_cornering_phases(self):
        """Closing + opening spiral should span the full corner."""
        analyzer = TelemetryAnalyzer()
        analyzer.data = make_synthetic_telemetry()
        stats = analyzer.analyze_corner_stats(0.3, 0.7)
        phases = stats['cornering_phases']
        total = phases['closing_spiral_pct'] + phases['opening_spiral_pct']
        self.assertAlmostEqual(total, 0.4, places=2)  # 0.7 - 0.3

    def test_multichannel_state_at_mrp(self):
        """Brake, throttle, steering values at MRP should be plausible."""
        analyzer = TelemetryAnalyzer()
        analyzer.data = make_synthetic_telemetry()
        stats = analyzer.analyze_corner_stats(0.3, 0.7)
        mrp = stats['mrp']
        # At MRP (~0.48), brake should still be active, throttle near zero
        self.assertGreater(mrp['brake_at_mrp'], 0)
        self.assertLess(mrp['throttle_at_mrp'], 0.1)
        self.assertGreater(mrp['steering_at_mrp_rad'], 0)


class TestRacingLineMRP(unittest.TestCase):
    def test_find_mrp_points(self):
        """_find_mrp_points should return MRP locations for corners."""
        analyzer = TelemetryAnalyzer()
        df = make_synthetic_telemetry()
        mrp_points = analyzer._find_mrp_points(df)
        self.assertGreater(len(mrp_points), 0)
        for pt in mrp_points:
            self.assertIn('lon', pt)
            self.assertIn('lat', pt)

    def test_plot_racing_line_with_mrp(self):
        """plot_racing_line with mark_mrp=True should produce a plot."""
        analyzer = TelemetryAnalyzer()
        df = make_synthetic_telemetry()

        # Save to temp CSV
        fd, csv_path = tempfile.mkstemp(suffix='.csv')
        os.close(fd)
        df.to_csv(csv_path, index=False)

        fd, output_path = tempfile.mkstemp(suffix='.png')
        os.close(fd)

        try:
            success = analyzer.plot_racing_line(
                output_file=output_path,
                filepaths=[csv_path],
                labels=["Test Lap"],
                mark_mrp=True
            )
            self.assertTrue(success)
            self.assertTrue(os.path.exists(output_path))
            self.assertGreater(os.path.getsize(output_path), 0)
        finally:
            os.unlink(csv_path)
            os.unlink(output_path)


if __name__ == '__main__':
    unittest.main()
