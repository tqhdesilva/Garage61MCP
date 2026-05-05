import os
import tempfile
import unittest

import numpy as np
import pandas as pd

from garage61_mcp.telemetry_analysis import TelemetryAnalyzer
from tests.test_mrp import make_synthetic_telemetry


def make_loop_telemetry(n=400):
    """Synthetic telemetry shaped as a clockwise circular loop.

    Useful for visually verifying that direction arrows point the right way:
    starting at the rightmost point and going clockwise, the arrows at the top
    of the loop should point left.
    """
    dist = np.linspace(0.0, 1.0, n)
    theta = -2 * np.pi * dist  # negative = clockwise when plotted with y up
    lat = 40.0 + 0.005 * np.sin(theta)
    lon = -74.0 + 0.005 * np.cos(theta)
    return pd.DataFrame({
        'LapDistPct': dist,
        'Lat': lat,
        'Lon': lon,
        'Speed': np.full(n, 80.0),
        'Brake': np.zeros(n),
        'Throttle': np.ones(n),
        'LatAccel': np.zeros(n),
        'Yaw': np.zeros(n),
        'YawRate': np.zeros(n),
        'Gear': np.full(n, 3),
        'SteeringWheelAngle': np.zeros(n),
    })


class TestPlotRacingLine(unittest.TestCase):
    def test_plot_racing_line_has_direction_arrows(self):
        """plot_racing_line should still produce a non-empty PNG with arrows enabled."""
        analyzer = TelemetryAnalyzer()
        df = make_synthetic_telemetry()

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
            )
            self.assertTrue(success)
            self.assertTrue(os.path.exists(output_path))
            self.assertGreater(os.path.getsize(output_path), 0)
        finally:
            os.unlink(csv_path)
            os.unlink(output_path)

    def test_plot_racing_line_loop(self):
        """A clockwise loop renders successfully — geometry sanity check."""
        analyzer = TelemetryAnalyzer()
        df = make_loop_telemetry()

        fd, csv_path = tempfile.mkstemp(suffix='.csv')
        os.close(fd)
        df.to_csv(csv_path, index=False)

        fd, output_path = tempfile.mkstemp(suffix='.png')
        os.close(fd)

        try:
            success = analyzer.plot_racing_line(
                output_file=output_path,
                filepaths=[csv_path],
                labels=["Loop"],
            )
            self.assertTrue(success)
            self.assertGreater(os.path.getsize(output_path), 0)
        finally:
            os.unlink(csv_path)
            os.unlink(output_path)


if __name__ == '__main__':
    unittest.main()
