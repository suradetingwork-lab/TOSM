"""Test script for BossDataManager functionality."""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.data_manager import BossDataManager
from datetime import datetime
import json

def test_data_manager():
    """Test the data persistence layer."""
    print("=" * 60)
    print("Testing BossDataManager")
    print("=" * 60)
    
    # Initialize manager
    dm = BossDataManager("test_boss_data.json")
    
    # Test 1: Add new boss (Initial state)
    print("\n[Test 1] Adding new boss (Initial state)...")
    result = dm.update_boss_record(
        boss_name="Indignant Nebulas",
        map_name="Laukyme Swamp",
        channel="CH.3",
        time_left_str="03:37",
        status="N",
        boss_type="Demon"
    )
    print(f"✓ Boss added: {result}")
    
    # Test 2: Update boss to Process state
    print("\n[Test 2] Updating boss to Process state...")
    result = dm.update_boss_record(
        boss_name="Indignant Nebulas",
        map_name="Laukyme Swamp",
        channel="CH.3",
        time_left_str="",
        status="LV2",
        boss_type="Demon"
    )
    print(f"✓ Boss updated to LV2: {result}")
    
    # Test 3: Update boss to Active state
    print("\n[Test 3] Updating boss to Active state...")
    result = dm.update_boss_record(
        boss_name="Indignant Nebulas",
        map_name="Laukyme Swamp",
        channel="CH.3",
        time_left_str="",
        status="Active",
        boss_type="Demon"
    )
    print(f"✓ Boss updated to Active: {result}")
    
    # Test 4: Add same boss in different channel
    print("\n[Test 4] Adding same boss in different channel...")
    result = dm.update_boss_record(
        boss_name="Indignant Nebulas",
        map_name="Laukyme Swamp",
        channel="CH.1",
        time_left_str="05:20",
        status="N",
        boss_type="Demon"
    )
    print(f"✓ Boss added to different channel: {result}")
    
    # Test 5: Get boss info
    print("\n[Test 5] Retrieving boss info...")
    info = dm.get_boss_info("Indignant Nebulas", "CH.3")
    if info:
        print(f"✓ Boss found:")
        print(f"  - Name: {info['name']}")
        print(f"  - Channel: {info['channel']}")
        print(f"  - Spawn count: {info['spawn_count']}")
        print(f"  - Locations: {len(info['locations'])}")
    
    # Test 6: Get upcoming spawns
    print("\n[Test 6] Getting upcoming spawns...")
    upcoming = dm.get_upcoming_spawns(within_minutes=120)
    print(f"✓ Found {len(upcoming)} upcoming spawns:")
    for spawn in upcoming:
        print(f"  - {spawn['boss']} @ {spawn['map']} {spawn['channel']}")
        print(f"    Spawns in: {spawn['time_until']}")
    
    # Test 7: Display full data structure
    print("\n[Test 7] Full data structure:")
    all_data = dm.get_all_bosses()
    print(json.dumps(all_data, indent=2, ensure_ascii=False))
    
    print("\n" + "=" * 60)
    print("All tests completed!")
    print("=" * 60)
    print(f"\nData saved to: test_boss_data.json")
    print("You can inspect the file to see the JSON structure.")

if __name__ == "__main__":
    test_data_manager()
