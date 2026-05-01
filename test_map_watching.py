#!/usr/bin/env python3
"""Simple test for map.json file watching."""

import sys
import json
import time
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from core.data_manager import MapDataManager

def test_file_watching():
    """Test file watching functionality."""
    app = QApplication(sys.argv)
    
    # Create map data manager
    map_manager = MapDataManager()
    
    def on_data_changed(data):
        print(f"File changed! Loaded {len(data)} entries")
        # Find the test entry
        for entry in data:
            if entry.get("map") == "Siauliai Miners Village":
                print(f"  -> Note field: {entry.get('note')}")
                break
    
    # Connect signal
    map_manager.data_changed.connect(on_data_changed)
    
    print("Map file watching test started...")
    print("Modify data/map.json to see real-time updates")
    print("Test will run for 30 seconds...")
    
    # Auto-quit after 30 seconds
    QTimer.singleShot(30000, app.quit)
    
    sys.exit(app.exec())

if __name__ == "__main__":
    test_file_watching()
