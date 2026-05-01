"""Data persistence layer for boss tracking using local JSON storage."""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path
from PyQt6.QtCore import QObject, pyqtSignal, QFileSystemWatcher


class MapDataManager(QObject):
    """Manages map.json file watching with real-time synchronization."""
    
    data_changed = pyqtSignal(list)  # Signal emitted when data changes
    
    def __init__(self, data_file: str = "data/map.json"):
        super().__init__()
        self.data_file = Path(data_file)
        self.map_data: list = []  # Map data is an array
        self._file_watcher = QFileSystemWatcher()
        self._watching_enabled = False
        self.load_data()
        self._setup_file_watching()
    
    def load_data(self) -> list:
        """
        Load map data from JSON file.
        Creates empty file if it doesn't exist.
        
        Returns:
            List containing map data
        """
        if not self.data_file.exists():
            print(f"[MapDataManager] Creating new data file: {self.data_file}")
            self.map_data = []
            self.save_data()
            # Enable file watching after creating the file
            self.enable_file_watching()
            return self.map_data
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                self.map_data = json.load(f)
            print(f"[MapDataManager] Loaded {len(self.map_data)} map entries from {self.data_file}")
            return self.map_data
        except json.JSONDecodeError as e:
            print(f"[MapDataManager] Error reading JSON file: {e}")
            print(f"[MapDataManager] Creating new data file")
            self.map_data = []
            self.save_data()
            return self.map_data
        except Exception as e:
            print(f"[MapDataManager] Unexpected error loading data: {e}")
            self.map_data = []
            return self.map_data
    
    def save_data(self) -> bool:
        """
        Save map data to JSON file safely.
        
        Returns:
            True if save successful, False otherwise
        """
        try:
            # Create backup if file exists
            if self.data_file.exists():
                backup_file = self.data_file.with_suffix('.json.bak')
                try:
                    import shutil
                    shutil.copy2(self.data_file, backup_file)
                except Exception as e:
                    print(f"[MapDataManager] Warning: Could not create backup: {e}")
            
            # Write to temporary file first
            temp_file = self.data_file.with_suffix('.json.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.map_data, f, indent=2, ensure_ascii=False)
            
            # Atomic replace
            temp_file.replace(self.data_file)
            
            return True
        except Exception as e:
            print(f"[MapDataManager] Error saving data: {e}")
            return False
    
    def _setup_file_watching(self):
        """Setup file system watcher for real-time JSON changes."""
        try:
            if self.data_file.exists():
                self._file_watcher.addPath(str(self.data_file))
                self._file_watcher.fileChanged.connect(self._on_file_changed)
                self._watching_enabled = True
                print(f"[MapDataManager] File watching enabled for: {self.data_file}")
            else:
                print(f"[MapDataManager] File not found, will start watching when created: {self.data_file}")
        except Exception as e:
            print(f"[MapDataManager] Error setting up file watcher: {e}")
    
    def _on_file_changed(self, path):
        """Handle file change events - reload data and emit signal."""
        if not self._watching_enabled:
            return
            
        print(f"[MapDataManager] File changed: {path}")
        
        # Small delay to ensure file write is complete
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, self._reload_and_notify)
    
    def _reload_and_notify(self):
        """Reload data from file and emit change signal."""
        old_data = self.map_data.copy()
        self.load_data()
        
        # Only emit if data actually changed
        if old_data != self.map_data:
            print(f"[MapDataManager] Data reloaded, {len(self.map_data)} map entries found")
            self.data_changed.emit(self.map_data.copy())
    
    def enable_file_watching(self):
        """Enable file watching (call this after creating new files)."""
        if not self._watching_enabled and self.data_file.exists():
            self._setup_file_watching()
    
    def disable_file_watching(self):
        """Disable file watching (useful during bulk operations)."""
        if self._watching_enabled:
            self._file_watcher.removePath(str(self.data_file))
            self._watching_enabled = False
            print("[MapDataManager] File watching disabled")


class BossDataManager(QObject):
    """Manages persistent boss data storage in JSON format with real-time file watching."""
    
    data_changed = pyqtSignal(dict)  # Signal emitted when data changes
    
    def __init__(self, data_file: str = "boss_data.json"):
        super().__init__()
        self.data_file = Path(data_file)
        self.boss_data: Dict[str, Any] = {}
        self._file_watcher = QFileSystemWatcher()
        self._watching_enabled = False
        self._map_id_lookup: Dict[str, str] = {}  # boss_name_lower -> map_id
        self._load_map_id_lookup()
        self.load_data()
        self._setup_file_watching()

    def _load_map_id_lookup(self) -> None:
        """Build a lookup table: lowercase boss name -> map id from data/map.json."""
        map_path = Path(self.data_file).parent / 'data' / 'map.json'
        if not map_path.exists():
            # Try relative to cwd
            map_path = Path('data') / 'map.json'
        try:
            with open(map_path, 'r', encoding='utf-8') as f:
                map_data = json.load(f)
            for entry in map_data:
                boss_name = entry.get('boss', '').strip()
                map_id = entry.get('id', '').strip()
                if boss_name and map_id:
                    self._map_id_lookup[boss_name.lower()] = map_id
            print(f"[DataManager] Loaded {len(self._map_id_lookup)} boss id mappings from map.json")
        except Exception as e:
            print(f"[DataManager] Warning: Could not load map id lookup: {e}")
    
    def load_data(self) -> Dict[str, Any]:
        """
        Load boss data from JSON file.
        Creates empty file if it doesn't exist.
        
        Returns:
            Dictionary containing boss data
        """
        if not self.data_file.exists():
            print(f"[DataManager] Creating new data file: {self.data_file}")
            self.boss_data = {}
            self.save_data()
            # Enable file watching after creating the file
            self.enable_file_watching()
            return self.boss_data
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                self.boss_data = json.load(f)
            print(f"[DataManager] Loaded {len(self.boss_data)} boss records from {self.data_file}")
            return self.boss_data
        except json.JSONDecodeError as e:
            print(f"[DataManager] Error reading JSON file: {e}")
            print(f"[DataManager] Creating new data file")
            self.boss_data = {}
            self.save_data()
            return self.boss_data
        except Exception as e:
            print(f"[DataManager] Unexpected error loading data: {e}")
            self.boss_data = {}
            return self.boss_data
    
    def parse_time_left(self, time_str: str) -> Optional[timedelta]:
        """
        Parse time string into timedelta.
        
        Supports formats:
        - MM:SS (e.g., '45:30')
        - HH:MM:SS (e.g., '01:45:30')
        
        Args:
            time_str: Time string to parse
            
        Returns:
            timedelta object or None if parsing fails
        """
        if not time_str:
            return None
        
        try:
            parts = time_str.strip().split(':')
            
            if len(parts) == 2:
                # MM:SS format
                minutes, seconds = map(int, parts)
                return timedelta(minutes=minutes, seconds=seconds)
            elif len(parts) == 3:
                # HH:MM:SS format
                hours, minutes, seconds = map(int, parts)
                return timedelta(hours=hours, minutes=minutes, seconds=seconds)
            else:
                print(f"[DataManager] Invalid time format: {time_str}")
                return None
        except ValueError as e:
            print(f"[DataManager] Error parsing time '{time_str}': {e}")
            return None
    
    def update_boss_record(
        self, 
        boss_name: str, 
        map_name: str = "--", 
        channel: str = "--", 
        time_left_str: str = "",
        status: str = "N",
        boss_type: str = "--"
    ) -> bool:
        """
        Update or create boss record with latest information.
        
        Args:
            boss_name: Name of the boss
            map_name: Map where boss spawns
            channel: Channel/server number
            time_left_str: Time until spawn (e.g., '60:00' or '01:00:00')
            status: Boss status - 'N' (Initial), 'LV2' (Process), 'Active'
            boss_type: Boss type (Demon, Beast, etc.)
            
        Returns:
            True if update successful, False otherwise
        """
        if not boss_name:
            return False
        
        # Normalize boss name and channel (lowercase for consistency)
        normalized_name = boss_name.lower().strip()
        normalized_channel = channel.strip() if channel else "Unknown"
        
        # Create composite key: boss_name + channel
        boss_key = f"{normalized_name}_{normalized_channel}"
        
        # Calculate absolute spawn time if time_left provided
        absolute_spawn_time = None
        time_delta = None
        
        if time_left_str:
            time_delta = self.parse_time_left(time_left_str)
            if time_delta:
                absolute_spawn_time = datetime.now() + time_delta
        
        # Check if boss exists in data
        is_new = boss_key not in self.boss_data
        
        # Create or update record
        # Resolve map_id from lookup table
        map_id = self._map_id_lookup.get(normalized_name, "")

        if is_new:
            self.boss_data[boss_key] = {
                "name": boss_name,
                "map_id": map_id,
                "channel": channel,
                "type": boss_type,
                "status": status,
                "first_seen": datetime.now().isoformat(),
                "last_updated": datetime.now().isoformat(),
                "spawn_count": 1,
                "locations": {}
            }
            print(f"[DataManager] New boss added: {boss_name} (id={map_id!r}) @ {channel} [{status}]")
        else:
            self.boss_data[boss_key]["last_updated"] = datetime.now().isoformat()
            self.boss_data[boss_key]["spawn_count"] = self.boss_data[boss_key].get("spawn_count", 0) + 1
            self.boss_data[boss_key]["status"] = status
            self.boss_data[boss_key]["type"] = boss_type
            # Backfill map_id if missing (older records)
            if map_id and not self.boss_data[boss_key].get("map_id"):
                self.boss_data[boss_key]["map_id"] = map_id
        
        # Update location-specific data (map only, since channel is already in the main key)
        location_key = map_name
        if location_key not in self.boss_data[boss_key]["locations"]:
            self.boss_data[boss_key]["locations"][location_key] = {
                "map": map_name,
                "spawn_history": []
            }
        
        # Add spawn record with status
        spawn_record = {
            "detected_at": datetime.now().isoformat(),
            "time_left": time_left_str,
            "spawn_time": absolute_spawn_time.isoformat() if absolute_spawn_time else None,
            "status": status
        }
        
        self.boss_data[boss_key]["locations"][location_key]["spawn_history"].append(spawn_record)
        
        # Keep only last 10 spawn records per location
        history = self.boss_data[boss_key]["locations"][location_key]["spawn_history"]
        if len(history) > 10:
            self.boss_data[boss_key]["locations"][location_key]["spawn_history"] = history[-10:]
        
        # Save immediately
        self.save_data()
        
        return True
    
    def save_data(self) -> bool:
        """
        Save boss data to JSON file safely.
        
        Returns:
            True if save successful, False otherwise
        """
        try:
            # Create backup if file exists
            if self.data_file.exists():
                backup_file = self.data_file.with_suffix('.json.bak')
                try:
                    import shutil
                    shutil.copy2(self.data_file, backup_file)
                except Exception as e:
                    print(f"[DataManager] Warning: Could not create backup: {e}")
            
            # Write to temporary file first
            temp_file = self.data_file.with_suffix('.json.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(self.boss_data, f, indent=2, ensure_ascii=False)
            
            # Atomic replace
            temp_file.replace(self.data_file)
            
            return True
        except Exception as e:
            print(f"[DataManager] Error saving data: {e}")
            return False
    
    def get_boss_info(self, boss_name: str, channel: str = "--") -> Optional[Dict[str, Any]]:
        """
        Get stored information for a specific boss.
        
        Args:
            boss_name: Name of the boss
            channel: Channel/server number
            
        Returns:
            Boss data dictionary or None if not found
        """
        normalized_name = boss_name.lower().strip()
        normalized_channel = channel.strip() if channel else "Unknown"
        boss_key = f"{normalized_name}_{normalized_channel}"
        return self.boss_data.get(boss_key)
    
    def get_all_bosses(self) -> Dict[str, Any]:
        """
        Get all stored boss data.
        
        Returns:
            Complete boss data dictionary
        """
        return self.boss_data
    
    def get_upcoming_spawns(self, within_minutes: int = 60) -> list:
        """
        Get list of bosses spawning within specified time window.
        
        Args:
            within_minutes: Time window in minutes
            
        Returns:
            List of boss spawn information
        """
        upcoming = []
        now = datetime.now()
        cutoff = now + timedelta(minutes=within_minutes)
        
        for boss_key, boss_data in self.boss_data.items():
            for loc_key, loc_data in boss_data.get("locations", {}).items():
                history = loc_data.get("spawn_history", [])
                if history:
                    latest = history[-1]
                    spawn_time_str = latest.get("spawn_time")
                    if spawn_time_str:
                        try:
                            spawn_time = datetime.fromisoformat(spawn_time_str)
                            if now <= spawn_time <= cutoff:
                                upcoming.append({
                                    "boss": boss_data.get("name"),
                                    "map": loc_data.get("map"),
                                    "channel": boss_data.get("channel"),
                                    "spawn_time": spawn_time_str,
                                    "time_until": str(spawn_time - now).split('.')[0]
                                })
                        except ValueError:
                            continue
        
        # Sort by spawn time
        upcoming.sort(key=lambda x: x["spawn_time"])
        return upcoming
    
    def _setup_file_watching(self):
        """Setup file system watcher for real-time JSON changes."""
        try:
            if self.data_file.exists():
                self._file_watcher.addPath(str(self.data_file))
                self._file_watcher.fileChanged.connect(self._on_file_changed)
                self._watching_enabled = True
                print(f"[DataManager] File watching enabled for: {self.data_file}")
            else:
                print(f"[DataManager] File not found, will start watching when created: {self.data_file}")
        except Exception as e:
            print(f"[DataManager] Error setting up file watcher: {e}")
    
    def _on_file_changed(self, path):
        """Handle file change events - reload data and emit signal."""
        if not self._watching_enabled:
            return
            
        print(f"[DataManager] File changed: {path}")
        
        # Small delay to ensure file write is complete
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, self._reload_and_notify)
    
    def _reload_and_notify(self):
        """Reload data from file and emit change signal."""
        old_data = self.boss_data.copy()
        self.load_data()
        
        # Only emit if data actually changed
        if old_data != self.boss_data:
            print(f"[DataManager] Data reloaded, {len(self.boss_data)} boss records found")
            self.data_changed.emit(self.boss_data.copy())
    
    def enable_file_watching(self):
        """Enable file watching (call this after creating new files)."""
        if not self._watching_enabled and self.data_file.exists():
            self._setup_file_watching()
    
    def disable_file_watching(self):
        """Disable file watching (useful during bulk operations)."""
        if self._watching_enabled:
            self._file_watcher.removePath(str(self.data_file))
            self._watching_enabled = False
            print("[DataManager] File watching disabled")
