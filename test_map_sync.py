#!/usr/bin/env python3
"""Test script to demonstrate real-time map.json synchronization."""

import json
import time
from pathlib import Path

def test_map_json_sync():
    """Test real-time synchronization by modifying map.json file."""
    json_file = Path("data/map.json")
    
    if not json_file.exists():
        print("data/map.json not found!")
        return
    
    print("Testing real-time map.json synchronization...")
    print("Make sure the TOSM application is running!")
    print("Press Ctrl+C to stop testing\n")
    
    try:
        # Load current data
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Find first entry with boss to modify
        test_entry = None
        for i, entry in enumerate(data):
            if entry.get("boss"):
                test_entry = i
                break
        
        if test_entry is None:
            print("No entries with boss data found!")
            return
        
        counter = 1
        while True:
            # Modify note field to test real-time updates
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Update the note field
            data[test_entry]["note"] = f"TEST-{counter}"
            
            # Save changes
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            print(f"Updated note for {data[test_entry]['map']} to 'TEST-{counter}'")
            
            counter += 1
            
            time.sleep(3)  # Wait 3 seconds between changes
            
    except KeyboardInterrupt:
        print("\nTest stopped by user")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_map_json_sync()
