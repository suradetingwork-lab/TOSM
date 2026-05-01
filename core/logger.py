"""Data logger for saving boss tracking information."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any


class BossDataLogger:
    """Logs boss detection data to files."""

    def __init__(self, data_dir: str = "data/logs"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.current_session_file = None
        self._start_new_session()

    def _start_new_session(self) -> None:
        """Start a new logging session with timestamped file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.current_session_file = self.data_dir / f"boss_session_{timestamp}.json"
        self._session_data = {
            "start_time": datetime.now().isoformat(),
            "boss_history": [],
            "detections": []
        }
        print(f"[Logger] Started new session: {self.current_session_file}")

    def log_detection(self, frame_count: int, bosses: List[Dict[str, Any]], raw_text: List[Dict[str, Any]]) -> None:
        """Log a detection event."""
        detection = {
            "timestamp": datetime.now().isoformat(),
            "frame": frame_count,
            "bosses_found": len(bosses),
            "boss_details": bosses,
            "raw_text_sample": [t["text"] for t in raw_text[:5]]
        }
        self._session_data["detections"].append(detection)

        # Track unique bosses
        for boss in bosses:
            boss_name = boss.get("name", "Unknown")
            if not any(b.get("name") == boss_name for b in self._session_data["boss_history"]):
                self._session_data["boss_history"].append({
                    "name": boss_name,
                    "first_seen": detection["timestamp"],
                    "type": boss.get("type", ""),
                    "event_type": boss.get("event_type", "")
                })

    def save(self) -> None:
        """Save current session to file."""
        if self.current_session_file:
            with open(self.current_session_file, "w", encoding="utf-8") as f:
                json.dump(self._session_data, f, ensure_ascii=False, indent=2)
            print(f"[Logger] Saved session to {self.current_session_file}")

    def export_txt(self, filename: str = None) -> str:
        """Export session to readable text file."""
        if filename is None:
            filename = f"boss_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        txt_path = self.data_dir / filename
        
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write("=" * 50 + "\n")
            f.write("TOSM Boss Tracker Report\n")
            f.write("=" * 50 + "\n\n")
            
            f.write(f"Session Start: {self._session_data['start_time']}\n")
            f.write(f"Total Detections: {len(self._session_data['detections'])}\n")
            f.write(f"Unique Bosses Found: {len(self._session_data['boss_history'])}\n\n")
            
            if self._session_data["boss_history"]:
                f.write("-" * 50 + "\n")
                f.write("Boss History:\n")
                f.write("-" * 50 + "\n")
                for boss in self._session_data["boss_history"]:
                    f.write(f"• {boss['name']}\n")
                    if boss.get("type"):
                        f.write(f"  Type: {boss['type']}\n")
                    if boss.get("event_type"):
                        f.write(f"  Event: {boss['event_type']}\n")
                    f.write(f"  First Seen: {boss['first_seen']}\n\n")
            
            if self._session_data["detections"]:
                f.write("-" * 50 + "\n")
                f.write("Recent Detections:\n")
                f.write("-" * 50 + "\n")
                for det in self._session_data["detections"][-10:]:  # Last 10
                    f.write(f"[{det['timestamp']}] Frame {det['frame']}: {det['bosses_found']} bosses\n")
                    for boss in det['boss_details']:
                        f.write(f"  - {boss.get('name', 'Unknown')}\n")
                    f.write("\n")
        
        print(f"[Logger] Exported report to {txt_path}")
        return str(txt_path)

    def log_api_response(self, provider: str, response: str, token_usage: Dict = None, error: str = None) -> None:
        """Log API response for analysis."""
        timestamp = datetime.now()
        log_date = timestamp.strftime("%Y%m%d")
        log_file = self.data_dir / f"api-response-{log_date}.log"
        
        log_entry = {
            "timestamp": timestamp.isoformat(),
            "provider": provider,
            "response_length": len(response) if response else 0,
            "response_preview": response[:200] + "..." if response and len(response) > 200 else response,
            "token_usage": token_usage,
            "error": error,
            "full_response": response
        }
        
        # Append to daily log file
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        
        print(f"[Logger] API response logged to {log_file}")

    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session."""
        return {
            "file": str(self.current_session_file),
            "start_time": self._session_data["start_time"],
            "total_detections": len(self._session_data["detections"]),
            "unique_bosses": len(self._session_data["boss_history"]),
            "boss_names": [b["name"] for b in self._session_data["boss_history"]]
        }
