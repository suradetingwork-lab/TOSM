"""Map level loader - loads map levels from JSON file."""

import json
import os
from typing import Dict, Optional, Tuple, Any


# Map coordinates for mini-map schematic markers
# Positions are normalized (0.0-1.0) as ratio of image width/height
MAP_COORDINATES: Dict[str, Dict[str, Any]] = {
    "Alemeth Forest": {
        "boss_spawn": (0.75, 0.35),
        "entrance": (0.25, 0.75),
        "level_range": "95",
    },
}


def get_map_coordinates(map_name: str) -> Dict[str, Any]:
    """Get marker coordinates for a map image.
    
    Returns:
        Dict with boss_spawn (x, y), entrance (x, y), level_range
        or empty dict if map not found.
    """
    if not map_name:
        return {}
    return MAP_COORDINATES.get(map_name, {})


class MapLevelLoader:
    """Loads and provides map level information from map.json."""
    
    def __init__(self, map_file: str = "data/map.json"):
        self._map_file = map_file
        self._levels: Dict[str, str] = {}
        self._map_data: Dict[str, dict] = {}  # Store full data by map name
        self._boss_data: Dict[str, dict] = {}  # Store data by boss name
        # Removed automatic loading - use load_boss_reference() instead
    
    def load_boss_reference(self) -> None:
        """Load boss reference data from JSON file for lookup only."""
        try:
            if os.path.exists(self._map_file):
                with open(self._map_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for item in data:
                        boss = item.get("boss", "")
                        
                        # Only index by boss name for reference lookup
                        if boss:
                            self._boss_data[boss.lower()] = item
                            self._boss_data[boss] = item
                            
                print(f"[MapLevel] Loaded boss reference for {len(self._boss_data)} bosses from {self._map_file}")
            else:
                print(f"[MapLevel] Map file not found: {self._map_file}")
        except Exception as e:
            print(f"[MapLevel] Error loading boss reference: {e}")
    
    def get_level(self, map_name: str) -> str:
        """Get level for a map name (case-insensitive)."""
        if not map_name:
            return ""
        
        # Try exact match first
        if map_name in self._levels:
            return self._levels[map_name]
        
        # Try case-insensitive match
        return self._levels.get(map_name.lower(), "")
    
    def get_by_boss(self, boss_name: str) -> Tuple[str, str, str]:
        """Get (map, level, type) for a boss name (case-insensitive).
        
        Uses fuzzy matching to handle truncated or slightly different names.
        
        Returns:
            Tuple of (map_name, level, boss_type) or ("", "", "") if not found.
        """
        if not boss_name:
            return ("", "", "")
        
        # Try exact match first
        key = boss_name.lower()
        data = self._boss_data.get(key)
        
        if data:
            return (
                data.get("map", ""),
                data.get("lv", ""),
                data.get("type", "")
            )
        
        # Try fuzzy matching for truncated names
        # Remove common suffixes and try partial matching
        search_name = boss_name.lower().strip()
        
        # Try to find partial matches
        for stored_name, stored_data in self._boss_data.items():
            stored_lower = stored_name.lower()
            
            # Check if search name is contained in stored name (for truncated names)
            if search_name in stored_lower and len(search_name) >= len(stored_lower) * 0.6:
                print(f"[MapLevel] Fuzzy match: '{boss_name}' -> '{stored_name}'")
                return (
                    stored_data.get("map", ""),
                    stored_data.get("lv", ""),
                    stored_data.get("type", "")
                )
            
            # Check if stored name is contained in search name (for extra words)
            if stored_lower in search_name and len(stored_lower) >= len(search_name) * 0.6:
                print(f"[MapLevel] Fuzzy match: '{boss_name}' -> '{stored_name}'")
                return (
                    stored_data.get("map", ""),
                    stored_data.get("lv", ""),
                    stored_data.get("type", "")
                )
        
        return ("", "", "")


# Global instance
_map_loader: Optional[MapLevelLoader] = None


def get_map_level(map_name: str) -> str:
    """Get level for a map name (convenience function)."""
    global _map_loader
    if _map_loader is None:
        _map_loader = MapLevelLoader()
        _map_loader.load_boss_reference()  # Load boss reference only
    return _map_loader.get_level(map_name)


def get_boss_info(boss_name: str) -> Tuple[str, str, str]:
    """Get (map, level, type) for a boss name (convenience function).
    
    Returns:
        Tuple of (map_name, level, boss_type) or ("", "", "") if not found.
    """
    global _map_loader
    if _map_loader is None:
        _map_loader = MapLevelLoader()
        _map_loader.load_boss_reference()  # Load boss reference only
    return _map_loader.get_by_boss(boss_name)


def reload_map_data():
    """Reload boss reference data from file."""
    global _map_loader
    _map_loader = MapLevelLoader()
    _map_loader.load_boss_reference()  # Load boss reference only
