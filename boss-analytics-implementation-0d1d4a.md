# Boss Analytics Implementation Plan

Implement three features: boss name filtering, spawn statistics visualization, and real-time time gap tracking for manual snapshot workflow.

---

## 🎯 Overview

เนื่องจาก user ใช้วิธี **manual snapshot** (ไปที่แผนที่ → view boss info → snapshot) ดังนั้น:
- ข้อมูล spawn time อาจไม่แม่นยำ 100%
- ต้องอิงจาก `last_updated` / `first_seen` ใน `boss_data.json`
- กราฟควรแสดง **pattern การ detect** มากกว่า **spawn time ที่แม่นยำ**

---

## 📋 Phase 1: Boss Name Filter (ง่าย ทำก่อน)

### Files to Modify
- `core/ui/overlay_window.py`

### Implementation
1. **Add search box** บน header (ระหว่าง title กับ opacity slider)
   - `QLineEdit` พร้อม placeholder "🔍 Filter bosses..."
   - Debounce 300ms เพื่อลดการ re-render บ่อย

2. **Filter logic** ใน `_update_display()`
   - **Fuzzy search**: พิมพ์ "bear" เจอ "Black Bear" (case-insensitive, partial match)
   - ทำงานร่วมกับ tab filter ที่มีอยู่ (AND condition)

3. **UI Style**
   - ดีไซน์คล้าย tab buttons ที่มีอยู่
   - แสดง "Showing X of Y bosses" ใต้ search box

### Time Estimate: 1-2 ชม.

---

## 📊 Phase 2: Spawn Statistics Charts

### New Files
- `core/ui/stats_chart_dialog.py` - Chart window ใหม่ (แยกจาก stats_window.py เดิม)

### Charts ที่จะ implement

#### 1. Detection Timeline (สำคัญที่สุด)
- **แกน X**: เวลา (last 24h / 7 days / 30 days)
- **แกน Y**: จำนวนการ detect
- **ชนิด**: Scatter plot หรือ heatmap (hour of day)
- **ข้อมูล**: ใช้ `first_seen` และ `last_updated` จาก `boss_data.json`

#### 2. Boss Activity Rank
- **แบบ**: Bar chart แนวนอน
- **ข้อมูล**: จำนวน detect ต่อ boss (รวมทุก channel)
- **Sort**: มาก → น้อย

#### 3. Channel Distribution (optional)
- **แบบ**: Pie chart หรือ bar chart
- **ข้อมูล**: การกระจายตาม channel

### Data Source
```python
# จาก BossDataManager ที่มีอยู่
data_manager.get_all_bosses()  # ดึงข้อมูลทั้งหมด
# วน loop อ่าน spawn_history ของแต่ละ boss
```

### UI Flow
1. กดปุ่ม 📊 (stats_btn) เปิด stats window
2. มี tab เลือก: "Detection Pattern" / "Boss Ranking" / "Channel Stats"
3. ใช้ `PyQt6.QtCharts` หรือ `matplotlib` (ถ้า charts ซับซ้อน)

### Time Estimate: 3-4 ชม.

---

## ⏱️ Phase 3: Real-Time Time Gap Display

### Concept
แสดง "ครั้งล่าสุดที่ detect ห่างจากตอนนี้เท่าไร" แบบ real-time

### Implementation

#### Implementation: Direct in BossRow
แก้ไข `BossRow.set_update_date()` ให้รับ `minutes_elapsed` และแสดง **โดยตรงใน row**:
- **Color-coded bar**: สีเปลี่ยนตามระยะเวลา (0-5m: green, 5-15m: yellow, 15m+: red)
- **Text**: "2m ago", "15m ago", "1h ago" ที่อัพเดททุกวินาที

### Files to Modify
- `core/ui/boss_row.py` - ปรับ `set_update_date()` และ `update_time_display()`
- `core/ui/overlay_window.py` - Timer สำหรับ update ทุกวินาที

### Data Calculation
```python
last_updated = datetime.fromisoformat(boss_data['last_updated'])
elapsed = datetime.now() - last_updated
minutes = elapsed.total_seconds() // 60
```

### Time Estimate: 2-3 ชม.

---

## 🔧 Technical Details

### บนฐาน Code ที่มีอยู่

**Current Structure:**
```
OverlayWindow
├── SummaryStatsBar (แสดงสถิติสรุป)
├── Headers (sortable)
├── ScrollArea
│   └── BossRow x72 (แสดงข้อมูลแต่ละตัว)
└── Tab bar (filter by level range)

BossDataManager
├── boss_data.json (persistent storage)
└── spawn_history (list of detections)
```

**New Components:**
```
OverlayWindow
├── SearchBox (NEW)
├── [existing components]
└── StatsChartDialog (NEW - opens on 📊 click)

BossRow
├── [existing labels]
└── TimeGapIndicator (NEW - color bar + text)
```

### Dependencies
- **`matplotlib`** (confirmed) - เพิ่มใน `requirements.txt`
- `PyQt6` widget embedding ผ่าน `FigureCanvasQTAgg`

### Performance Considerations
- กราฟขนาดใหญ่: โหลดครั้งเดียวตอนเปิด stats window
- Time gap: update ทุกวินาทีเฉพาะ boss ที่แสดงอยู่ (visible rows)
- Filter: debounce 300ms + ใช้ hidden widget แทน destroy/recreate

---

## 📅 Suggested Order

1. **Filter** → ทำง่าย ใช้งานทันที
2. **Time Gap** → เพิ่ม UX ให้ดีขึ้น
3. **Charts** → ใช้เวลานานสุด ทำทีหลัง

---

## ✅ Confirmed Choices

| Question | Answer |
|----------|--------|
| **Filter** | ✅ Fuzzy search ("bear" → "Black Bear") |
| **Charts Export** | ❌ No export needed |
| **Time Gap Display** | ✅ Directly in BossRow |
| **Chart Library** | ✅ matplotlib |

## 🚀 Ready to Implement

---

## ✅ Success Criteria

- [ ] พิมพ์ชื่อ boss ใน search box → รายการกรองทันที
- [ ] กด 📊 → เปิด window แสดงกราฟ spawn pattern
- [ ] ข้อมูลใน row แสดง "Xm ago" ที่อัพเดท real-time
- [ ] ทุก feature ทำงานได้บน Windows กับ PyQt6 ที่มีอยู่
