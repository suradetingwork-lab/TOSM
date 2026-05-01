# TOSM Boss Tracker

Python application สำหรับติดตามเวลาเกิดของ boss ในเกม Tree of Savior (TOSM) ด้วย OCR และ overlay UI

## วิธีติดตั้ง

```bash
pip install -r requirements.txt
```

## วิธีใช้งาน

1. เปิดเกม TOSM ก่อน
2. รัน `python main.py`
3. Overlay จะขึ้นมาบนหน้าจอ
4. **การย้าย overlay**: กดค้าง `Alt` + คลิกซ้ายค้าง + ลาก
5. **การปิด**: กด `Ctrl+C` หรือปิดหน้าต่าง overlay

## ฟีเจอร์

### ✅ ทำงานแล้ว
- **Window Capture**: จับภาพเกม TOSM TH ด้วย Windows API
- **OCR Recognition**: อ่านข้อความไทย+อังกฤษด้วย EasyOCR
- **Overlay UI**: หน้าต่างใส อยู่บนสุดเสมอ ทะลุผ่านได้
- **Boss Detection**: ตรวจจับชื่อ boss ภาษาอังกฤษ (Gaigalas, Gesti, etc.)
- **Channel Detection**: อ่านช่องเซิร์ฟเวอร์ (CH.1, CH.2)
- **Countdown Timer**: แสดงเวลาถอยหลังก่อนเกิด
- **Data Logging**: บันทึกข้อมูลเป็น JSON และ TXT
- **Session Summary**: แสดงสถิติ boss ที่เจอทั้งหมด
- **Data Persistence**: บันทึกข้อมูล boss แบบถาวรใน `boss_data.json`
  - เก็บประวัติการเกิดของแต่ละ boss
  - คำนวณเวลาเกิดจริง (absolute spawn time)
  - ติดตาม boss ตาม map และ channel
  - เก็บประวัติ 10 ครั้งล่าสุดต่อ location

### 🚧 ปัญหาปัจจุบัน

#### ปัญหาอื่นๆ
- **Capture Region**: อาจจะต้องปรับแต่งตามความละเอียดหน้าจออื่นๆ
- **Boss Names**: ยังต้องรวบรวมชื่อ boss ระดับล่างๆ เพิ่มเติม
- **Status Types**: การแยกแยะสถานะ "กำลังเกิด" กับ "ประทะ" อาจจะมี OCR หลุดบ้าง

## โครงสร้างไฟล์

```
TOSM/
├── main.py          # Main application orchestrator
├── capture.py       # Window capture with Windows API
├── vision.py        # OCR processing and boss parsing
├── ui.py            # PyQt6 overlay window
├── logger.py        # Session logging and report generation
├── data_manager.py  # Persistent boss data storage (JSON)
├── requirements.txt # Python dependencies
├── boss_data.json   # Persistent boss tracking data
└── data/logs/       # Session data and reports
```

## Dependencies

- **pygetwindow**: หา window handle
- **pywin32**: Windows API สำหรับ capture
- **opencv-python**: Image processing
- **easyocr**: Thai+English OCR
- **PyQt6**: Overlay UI
- **numpy**: Array operations
- **pillow**: Image handling

## ข้อมูลที่ตรวจจับได้

| ข้อมูล | ตัวอย่าง | ความหมาย |
|--------|----------|----------|
| **Boss Name** | Cowardly Gaigalas | ชื่อบอส |
| **Type** | Beast | ประเภทเผ่า |
| **Channel** | CH.1 | เซิร์ฟเวอร์ |
| **Map** | Laukyme Swamp | แมพปัจจุบัน |
| **Status** | กำลังรอ | สถานะการรอเวลา |
| **Countdown** | 00:47:40 | เวลาถอยหลัง |

## การแก้ไขปัญหา

### 1. ขยาย Capture Region
```python
# vision.py:32-36
panel_width = int(w * 0.45)  # เพิ่มจาก 0.35
panel_height = int(h * 0.7)  # เพิ่มจาก 0.6
```

### 2. ปรับ Parsing Logic
- รวมข้อมูลจากทุก OCR result ก่อน
- ใช้ channel แรกที่เจอสำหรับทุก boss
- จับคู่ boss กับ countdown ให้ถูกต้อง

### 3. เพิ่ม Boss Names
```python
boss_names = [
    'gaigalas', 'gesti', 'sparnas', 'naktis', 'zawra',
    'marnox', 'kepari', 'prisoner', 'demon'
]
```

## ถัดไป

1. **แก้ Capture Region**: ทดลองขยายขนาดและตำแหน่ง
2. **ทดสอบ Parsing**: ใช้ screenshot จริงเพื่อ debug
3. **เพิ่ม Boss Names**: รวบรวมชื่อ boss ทั้งหมด
4. **ปรับ UI**: แสดงข้อมูลที่ parse ได้ถูกต้อง
5. **ทดสอบสถานะ**: จับคู่ boss กับ status ต่างๆ

## บันทึกข้อมูล

### Session Logs (ชั่วคราว)
ทุกครั้งที่รันจะบันทึกใน `data/logs/`:
- **JSON**: `boss_session_YYYYMMDD_HHMMSS.json`
- **TXT Report**: `boss_report_YYYYMMDD_HHMMSS.txt`

ข้อมูลรวมถึง:
- เวลา detection ทุก frame
- ข้อมูล boss ที่ตรวจจับได้
- OCR raw text สำหรับ debug
- สถิติ session ทั้งหมด

### Persistent Data (ถาวร)
ไฟล์ `boss_data.json` เก็บข้อมูล boss แบบถาวร:

```json
{
  "cowardly gaigalas": {
    "name": "cowardly gaigalas",
    "first_seen": "2026-03-15T19:44:31.142893",
    "last_updated": "2026-03-15T19:50:15.523456",
    "spawn_count": 15,
    "locations": {
      "laukyme swamp_CH.1": {
        "map": "laukyme swamp",
        "channel": "CH.1",
        "spawn_history": [
          {
            "detected_at": "2026-03-15T19:44:31.142893",
            "time_left": "00:40:50",
            "spawn_time": "2026-03-15T20:25:21.142893"
          }
        ]
      }
    }
  }
}
```

**ฟีเจอร์:**
- คำนวณเวลาเกิดจริง (absolute spawn time) จาก countdown
- ติดตาม boss แยกตาม map และ channel
- เก็บประวัติ 10 ครั้งล่าสุดต่อ location
- บันทึกอัตโนมัติทุกครั้งที่ detect boss
- โหลดข้อมูลเก่าเมื่อเปิดโปรแกรมใหม่
