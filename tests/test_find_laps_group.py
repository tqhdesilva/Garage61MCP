
import unittest
from unittest.mock import patch, AsyncMock
import sys
import os
import json
import asyncio
from datetime import date

# Ensure we can import from root
sys.path.append(os.getcwd())

# Import the module to be tested
from garage61_mcp import server

class TestFindLaps(unittest.IsolatedAsyncioTestCase):
    async def test_find_laps_group_param(self):
        # Mock the client.find_laps method
        with patch('garage61_mcp.server.client.find_laps', new_callable=AsyncMock) as mock_find:
            mock_find.return_value = []
            
            func = server.find_laps
            if hasattr(func, 'fn'):
                func = func.fn
            
            # Test default group
            await func()
            args, _ = mock_find.call_args
            self.assertEqual(args[0].get('group'), 'driver', "Default group should be 'driver'")
            
            # Test explicit group
            await func(group='none')
            args, _ = mock_find.call_args
            self.assertEqual(args[0].get('group'), 'none', "Group parameter should be passed correctly")
            
            # Test other group
            await func(group='driver-car')
            args, _ = mock_find.call_args
            self.assertEqual(args[0].get('group'), 'driver-car', "Group parameter should be passed correctly")

if __name__ == '__main__':
    unittest.main()
