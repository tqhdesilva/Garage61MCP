
import unittest
from unittest.mock import patch, AsyncMock
import sys
import os
import json
import asyncio

# Ensure we can import from root
sys.path.append(os.getcwd())

# Import the module to be tested
from garage61_mcp import server

class TestFindLaps(unittest.IsolatedAsyncioTestCase):
    async def test_find_laps_after_date_only(self):
        # Mock the client.find_laps method
        with patch('garage61_mcp.server.client.find_laps', new_callable=AsyncMock) as mock_find:
            mock_find.return_value = []
            
            # Call find_laps with only date string
            # We access the raw function because find_laps is decorated
            # Wait, verify if we need to access .fn or if decorating works different in test
            # If server.py is imported, find_laps is the decorated function.
            # FastMCP tools usually are callable if they are just functions, but let's check.
            # Based on test_repro, we needed .fn
            
            func = server.find_laps
            if hasattr(func, 'fn'):
                func = func.fn
            
            await func(after='2026-02-11')
            
            # specific assertions
            # expected filters should have T00:00:00Z appended
            mock_find.assert_called_once()
            call_args = mock_find.call_args
            filters = call_args[0][0] # first arg is filters dict
            
            self.assertEqual(filters['after'], '2026-02-11T00:00:00Z', "Should append time component to date string")

    async def test_find_laps_after_datetime(self):
         with patch('garage61_mcp.server.client.find_laps', new_callable=AsyncMock) as mock_find:
            mock_find.return_value = []
            func = server.find_laps
            if hasattr(func, 'fn'):
                func = func.fn
            
            # If already full iso, should not change
            iso_str = '2026-02-11T12:00:00Z'
            await func(after=iso_str)
            
            filters = mock_find.call_args[0][0]
            self.assertEqual(filters['after'], iso_str, "Should preserve full ISO string")

    async def test_find_laps_invalid_format(self):
         with patch('garage61_mcp.server.client.find_laps', new_callable=AsyncMock) as mock_find:
            func = server.find_laps
            if hasattr(func, 'fn'):
                func = func.fn
            
            with self.assertRaises(ValueError):
                await func(after="invalid-date-format")

if __name__ == '__main__':
    unittest.main()
