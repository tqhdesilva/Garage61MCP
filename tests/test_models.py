import unittest
from pydantic import ValidationError
from garage61_mcp.models import FindLapsParams

class TestModels(unittest.TestCase):
    def test_find_laps_params_validation(self):
        """Verify FindLapsParams strictly requires tracks."""
        
        # 1. Should fail when no track is provided
        with self.assertRaises(ValidationError) as cm:
            FindLapsParams(limit=10)
        
        self.assertIn("Field required", str(cm.exception))
        self.assertIn("tracks", str(cm.exception))

        # 2. Should pass with tracks
        params = FindLapsParams(tracks=[1])
        self.assertEqual(params.tracks, [1])

        # 3. Should still pass with tracks and drivers
        params = FindLapsParams(tracks=[1], drivers=['me'])
        self.assertEqual(params.tracks, [1])
        self.assertEqual(params.drivers, ['me'])

        # 4. Should fail with cars but no tracks
        with self.assertRaises(ValidationError) as cm:
            FindLapsParams(cars=[1])
        self.assertIn("Field required", str(cm.exception))
        self.assertIn("tracks", str(cm.exception))

if __name__ == '__main__':
    unittest.main()
