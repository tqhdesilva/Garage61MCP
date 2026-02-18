import unittest
from pydantic import ValidationError
from garage61_mcp.models import FindLapsParams

class TestModels(unittest.TestCase):
    def test_find_laps_params_validation(self):
        """Verify FindLapsParams requires at least one of drivers, cars, or tracks."""
        
        # 1. Should fail when no filters are provided
        with self.assertRaises(ValidationError) as cm:
            FindLapsParams(limit=10)
        
        self.assertIn("You will always need to supply at least a track, a car or a driver (user).", str(cm.exception))

        # 2. Should pass with drivers
        params = FindLapsParams(drivers=['me'])
        self.assertEqual(params.drivers, ['me'])

        # 3. Should pass with cars
        params = FindLapsParams(cars=[1])
        self.assertEqual(params.cars, [1])

        # 4. Should pass with tracks
        params = FindLapsParams(tracks=[1])
        self.assertEqual(params.tracks, [1])

if __name__ == '__main__':
    unittest.main()
