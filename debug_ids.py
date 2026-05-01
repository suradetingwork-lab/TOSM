"""Debug: Check actual content of boss_data.json map_id fields."""
import json

boss_data = json.load(open('boss_data.json', encoding='utf-8'))
map_data = json.load(open('data/map.json', encoding='utf-8'))

print("=== boss_data.json: first 5 entries with map_id ===")
count_with_id = 0
count_without_id = 0
for key, val in list(boss_data.items())[:10]:
    mid = val.get('map_id', 'MISSING')
    print(f"  {key}: name={val.get('name')!r}, map_id={mid!r}")
    if mid and mid != 'MISSING':
        count_with_id += 1
    else:
        count_without_id += 1

print(f"\nTotal entries: {len(boss_data)}")
print(f"  Has map_id: {sum(1 for v in boss_data.values() if v.get('map_id'))}")
print(f"  Missing map_id: {sum(1 for v in boss_data.values() if not v.get('map_id'))}")

print("\n=== map.json: first 5 entries with id ===")
for item in list(map_data)[:5]:
    print(f"  boss={item.get('boss')!r}, id={item.get('id')!r}")

print(f"\nmap.json entries with id: {sum(1 for i in map_data if i.get('id'))}/{len(map_data)}")

# Check specific: Strong Stone Whale
print("\n=== Checking 'Strong Stone Whale' ===")
map_entry = next((i for i in map_data if 'Stone Whale' in i.get('boss', '')), None)
if map_entry:
    print(f"  map.json id = {map_entry.get('id')!r}")

for key, val in boss_data.items():
    if 'stone whale' in val.get('name', '').lower():
        print(f"  boss_data.json key={key!r}, map_id={val.get('map_id')!r}")
