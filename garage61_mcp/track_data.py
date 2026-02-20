import os
import json
import logging
import difflib
from typing import Dict, Optional, List, Any
from .models import TrackMapData, TrackSector, TrackCorner

logger = logging.getLogger("garage61_mcp.track_data")

class TrackDataManager:
    def __init__(self, data_dir: Optional[str] = None):
        """
        Initialize the TrackDataManager.
        Loads track JSON files from the Git submodule into memory.
        """
        # Default to the submodule directory relative to this file
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.data_dir = data_dir or os.path.join(base_dir, "external", "lovely-track-data", "data", "iracing")
        self.tracks: Dict[str, TrackMapData] = {}
        self.track_names: List[str] = []
        
        self.load_tracks()

    def load_tracks(self):
        """Load all track JSON files from the data directory."""
        if not os.path.exists(self.data_dir):
            logger.warning(f"Track data directory not found: {self.data_dir}. "
                           "Ensure the submodule is checked out.")
            return

        for filename in os.listdir(self.data_dir):
            if not filename.endswith('.json'):
                continue
                
            filepath = os.path.join(self.data_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    track_map = self._parse_lovely_json(data)
                    if track_map:
                        self.tracks[track_map.track_name.lower()] = track_map
                        self.track_names.append(track_map.track_name)
            except Exception as e:
                logger.error(f"Failed to load track data from {filename}: {e}")

        logger.info(f"Loaded {len(self.tracks)} tracks from {self.data_dir}")

    def _parse_lovely_json(self, data: Dict[str, Any]) -> Optional[TrackMapData]:
        """Convert the Lovely-Sim-Racing JSON structure to TrackMapData."""
        track_name = data.get('name')
        track_id = data.get('trackId')
        
        if not track_name or not track_id:
            return None

        # Parse corners (turns)
        corners = []
        for t in data.get('turn', []):
            corners.append(TrackCorner(
                number=t.get('name', ''), # e.g. "T1"
                start_pct=t.get('start', 0.0),
                end_pct=t.get('end', 0.0)
            ))
            
        # Parse sectors
        # Lovely defines sectors differently than absolute starts. 
        # S1 marker is the end of S1 / start of S2. 
        # So S1 starts at 0.0, S2 starts at S1 marker, S3 starts at S2 marker.
        sectors = []
        raw_sectors = data.get('sector', [])
        
        current_start = 0.0
        for i, s in enumerate(raw_sectors):
            # lovely-track-data sectors usually mark the end of the current sector
            sector_name = s.get('name', f"S{i+1}")
            sector_num = i + 1
            sectors.append(TrackSector(
                sector_num=sector_num,
                sector_start_pct=current_start
            ))
            current_start = float(s.get('marker', current_start))
        
        # Add the final sector (from the last marker to the finish line)
        if raw_sectors:
            sectors.append(TrackSector(
                sector_num=len(raw_sectors) + 1,
                sector_start_pct=current_start
            ))
        else:
            # Fallback if no sectors defined
            sectors.append(TrackSector(sector_num=1, sector_start_pct=0.0))

        return TrackMapData(
            track_id=track_id,
            track_name=track_name,
            corners=corners,
            sectors=sectors
        )

    def normalize_name(self, name: str) -> str:
        """Normalize a track name for better matching."""
        name = name.lower()
        # Remove common suffixes/words that might differ between sources
        stopwords = ['circuit', 'gp', 'grand prix', 'international', 'motorsport', 'park', 'raceway', 'street']
        for word in stopwords:
            name = name.replace(word, '')
        # Remove extra whitespace and special characters
        name = ' '.join(name.split())
        name = name.replace('-', ' ')
        return name.strip()

    def get_track_data(self, query_name: str) -> Optional[TrackMapData]:
        """
        Find track data by name using fuzzy matching.
        """
        if not query_name or not self.tracks:
            return None

        # Exact match (case insensitive)
        query_lower = query_name.lower()
        if query_lower in self.tracks:
            return self.tracks[query_lower]

        # Normalized exact match
        query_norm = self.normalize_name(query_name)
        for key, track in self.tracks.items():
            if query_norm == self.normalize_name(key):
                return track
                
        # Fuzzy match using difflib
        # Match against normalized original names
        matches = difflib.get_close_matches(query_lower, [t.lower() for t in self.track_names], n=1, cutoff=0.5)
        
        if matches:
            best_match = matches[0]
            logger.info(f"Fuzzy matched track '{query_name}' to '{best_match}'")
            return self.tracks.get(best_match)
            
        # Try fuzzy match against normalized names as fallback
        normalized_keys = {self.normalize_name(k): k for k in self.tracks.keys()}
        norm_matches = difflib.get_close_matches(query_norm, normalized_keys.keys(), n=1, cutoff=0.5)
        
        if norm_matches:
            best_match_key = normalized_keys[norm_matches[0]]
            logger.info(f"Fuzzy matched track '{query_name}' to '{best_match_key}' (via normalization)")
            return self.tracks.get(best_match_key)

        logger.warning(f"Could not find matching track data for: '{query_name}'")
        return None
