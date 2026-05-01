#!/usr/bin/env python3
"""Test script to demonstrate real-time JSON synchronization."""

import json
import time
from pathlib import Path

def test_json_sync():
    """Test real-time synchronization by modifying JSON file."""
    json_file = Path("boss_data.json")
    
    if not json_file.exists():
        print("boss_data.json not found!")
        return
    
    print("Testing real-time JSON synchronization...")
    print("Make sure the TOSM application is running!")
    print("Press Ctrl+C to stop testing\n")
    
    try:
        counter = 100
        while True:
            # Load current data
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Modify first boss entry
            if data:
                first_boss = list(data.keys())[0]
                data[first_boss]["spawn_count"] = counter
                data[first_boss]["last_updated"] = f"TEST-{counter}"
                
                # Save changes
                with open(json_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                print(f"Updated {first_boss} spawn_count to {counter}")
                
                counter += 1
            
            time.sleep(3)  # Wait 3 seconds between changes
            
    except KeyboardInterrupt:
        print("\nTest stopped by user")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_json_sync()
