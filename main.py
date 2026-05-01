#!/usr/bin/env python3
"""Game Tracker Overlay - Entry point for TOSM boss tracking application."""

import sys
import signal
import os
import threading
import ctypes
import json
from ctypes import wintypes
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QShortcut, QKeySequence
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QThread, QTimer

from core.capture import WindowCapture
from core.vision import VisionProcessor
from core.ui import OverlayWindow
from core.logger import BossDataLogger
from core.data_manager import BossDataManager, MapDataManager


# Windows API constants for global hotkey
WM_HOTKEY = 0x0312
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_ALT = 0x0001
VK_1 = 0x31


class SnapshotWorker(QObject):
    """Worker for async snapshot processing."""
    finished = pyqtSignal(dict)
    error = pyqtSignal(str)
    
    def __init__(self, capture, vision, frame_count):
        super().__init__()
        self.capture = capture
        self.vision = vision
        self.frame_count = frame_count
    
    def process(self):
        """Process snapshot asynchronously."""
        try:
            frame = self.capture.capture_frame()
            if frame is None:
                self.error.emit("Failed to capture frame - window not found or minimized")
                return
            
            results = self.vision.process(frame)
            self.finished.emit(results)
        except Exception as e:
            self.error.emit(str(e))


class GlobalHotkey(QObject):
    """Global hotkey handler using Windows API."""
    
    triggered = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = False
        self._thread = None
        self._hotkey_id = 1
        
    def start(self):
        """Start listening for global hotkey."""
        self._running = True
        self._thread = threading.Thread(target=self._listen, daemon=True)
        self._thread.start()
        print("[Hotkey] Global hotkey Ctrl+1 registered")
        
    def stop(self):
        """Stop listening for global hotkey."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)
        # Unregister hotkey
        try:
            ctypes.windll.user32.UnregisterHotKey(None, self._hotkey_id)
        except:
            pass
        
    def _listen(self):
        """Listen for hotkey events in background thread."""
        # Register hotkey: Alt + 1
        result = ctypes.windll.user32.RegisterHotKey(
            None, 
            self._hotkey_id, 
            MOD_ALT, 
            VK_1
        )
        if not result:
            print("[Hotkey] Failed to register global hotkey")
            return
            
        # Create message loop
        msg = wintypes.MSG()
        while self._running:
            # Peek for messages (non-blocking)
            if ctypes.windll.user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0x0001):
                if msg.message == WM_HOTKEY and msg.wParam == self._hotkey_id:
                    print("[Hotkey] Alt+1 pressed globally")
                    self.triggered.emit()
                ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
                ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))
            # Small sleep to prevent CPU spinning
            import time
            time.sleep(0.05)


def get_gemini_api_key() -> str:
    """Get Gemini API key from environment variables or config file."""
    # Try environment variable first
    api_key = os.getenv('GEMINI_API_KEY')
    if api_key:
        print("[App] Using Gemini API key from environment variable")
        return api_key
    
    # Try config file
    config_path = os.path.join("config", "gemini_api_key.txt")
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                api_key = f.read().strip()
                if api_key:
                    print(f"[App] Using Gemini API key from {config_path}")
                    return api_key
        except Exception as e:
            print(f"[App] Error reading API key from {config_path}: {e}")
    
    print("[App] No Gemini API key found - Gemini AI analysis disabled")
    print("[App] Set GEMINI_API_KEY environment variable or create gemini_api_key.txt")
    return None


def get_ollama_config() -> dict:
    """Get Ollama configuration from config file."""
    config_path = os.path.join("config", "ollama_config.txt")
    default_config = {
        "endpoint": "http://localhost:11434",
        "model": "gemma4:e2b",
        "timeout": 30
    }
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                print(f"[App] Using Ollama config from {config_path}")
                return {**default_config, **config}  # Merge with defaults
        except Exception as e:
            print(f"[App] Error reading Ollama config from {config_path}: {e}")
            print(f"[App] Using default Ollama config: {default_config}")
            return default_config
    else:
        print(f"[App] No Ollama config found at {config_path}")
        print(f"[App] Using default Ollama config: {default_config}")
        return default_config


def get_ai_provider_preference() -> bool:
    """Get AI provider preference from environment variable or default to Gemini."""
    # Check environment variable first
    use_ollama = os.getenv('USE_OLLAMA', '').lower() in ('true', '1', 'yes')
    
    if use_ollama:
        print("[App] Using Ollama as preferred AI provider (from environment)")
        return True
    else:
        # เปลี่ยนเป็น Ollama เป็นค่าเริ่มต้น
        print("[App] Using Ollama as preferred AI provider (default)")
        return True


class GameTrackerApp:
    """Main application orchestrating capture, vision, UI, and logging."""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        
        # Set dark theme for tooltips
        self.app.setStyleSheet("""
            QToolTip {
                background-color: rgba(30, 30, 35, 0.95);
                color: #F8FAFC;
                border: 1px solid rgba(139, 92, 246, 0.5);
                padding: 6px 10px;
                border-radius: 6px;
                font-size: 12px;
                font-weight: 500;
            }
        """)

        # Get AI configurations
        gemini_api_key = get_gemini_api_key()
        ollama_config = get_ollama_config()
        use_ollama = False #get_ai_provider_preference()

        self.capture = WindowCapture("TOSM TH")
        self.vision = VisionProcessor(gemini_api_key, ollama_config, use_ollama)
        self.overlay = OverlayWindow()
        self.logger = BossDataLogger()
        self.data_manager = BossDataManager()  # For boss data
        self.map_data_manager = MapDataManager()  # For map.json sync
        self._frame_count = 0
        self._shutdown_called = False
        
        # Async processing
        self.worker_thread = None
        self.worker = None
        self.pending_requests = []  # Queue for pending snapshot requests

        self.overlay.set_close_callback(self._on_overlay_closed)
        
        # Connect map data manager file watching signal to UI
        self.map_data_manager.data_changed.connect(self._on_map_file_changed)
        
        # Setup global hotkey for Ctrl+1 (works everywhere)
        self.global_hotkey = GlobalHotkey()
        self.global_hotkey.triggered.connect(self._manual_snapshot)
        
        # Keep local shortcut as fallback
        self.snapshot_shortcut = QShortcut(QKeySequence("Ctrl+1"), self.overlay)
        self.snapshot_shortcut.activated.connect(self._manual_snapshot)

        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully."""
        print("\n[App] Received interrupt signal, shutting down...")
        self.shutdown()

    def _manual_snapshot(self):
        """Manually capture and process a single frame asynchronously with queue support."""
        print("[App] Manual snapshot triggered (Alt+1)")
        
        # Show visual feedback immediately
        self.overlay.show_snapshot_feedback()
        
        # Add request to queue
        self.pending_requests.append(self._frame_count)
        
        # If no worker is running, start processing
        if not self.worker_thread or not self.worker_thread.isRunning():
            self._start_next_worker()
        else:
            print(f"[App] Request queued ({len(self.pending_requests)} pending)")

    def _start_next_worker(self):
        """Start processing the next request in queue."""
        if not self.pending_requests:
            return
        
        # Get next request
        frame_count = self.pending_requests.pop(0)
        
        # Create new worker and thread
        self.worker_thread = QThread()
        self.worker = SnapshotWorker(self.capture, self.vision, frame_count)
        self.worker.moveToThread(self.worker_thread)
        
        # Connect signals
        self.worker_thread.started.connect(self.worker.process)
        self.worker.finished.connect(self._on_snapshot_finished)
        self.worker.error.connect(self._on_snapshot_error)
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self._on_worker_finished)
        
        # Start async processing
        self.worker_thread.start()
        print(f"[App] Processing request (remaining: {len(self.pending_requests)})")

    def _on_worker_finished(self):
        """Called when worker finishes - start next if queue has items."""
        # Start next worker if there are pending requests
        QTimer.singleShot(0, self._start_next_worker)

    def _on_snapshot_finished(self, results):
        """Handle completed snapshot processing."""
        self._frame_count += 1
        
        # Log detection data
        self.logger.log_detection(
            self._frame_count,
            results.get("bosses", []),
            results.get("raw_text", [])
        )
        
        # Update persistent boss data
        bosses = results.get("bosses", [])
        for boss in bosses:
            boss_name = boss.get("name", "")
            map_name = boss.get("map", "--")
            channel = boss.get("channel", "--")
            countdown = boss.get("countdown", "")
            status = boss.get("status", "N")
            boss_type = boss.get("type", "--")
            
            if boss_name:
                self.data_manager.update_boss_record(
                    boss_name=boss_name,
                    map_name=map_name,
                    channel=channel,
                    time_left_str=countdown,
                    status=status,
                    boss_type=boss_type
                )
        
        # Update UI with logging info
        results["session"] = self.logger.get_session_summary()
        self.overlay.update_data(results)
        
        # Display AI analysis if available
        if "ai_analysis" in results and results["ai_analysis"]:
            provider_name = results.get("provider", "Unknown").upper()
            print("\n" + "="*50)
            print(f"{provider_name} AI ANALYSIS:")
            print("="*50)
            print(results["ai_analysis"])
            
            # Display token usage (only for Gemini)
            if "token_usage" in results and results["token_usage"] and results["provider"] == "gemini":
                tokens = results["token_usage"]
                print(f"Tokens - Input: {tokens['prompt_tokens']}, Output: {tokens['candidates_tokens']}, Total: {tokens['total_tokens']}")
            
            print("="*50 + "\n")
        
        # Update status
        if bosses:
            provider_name = results.get("provider", "ai").upper()
            ai_status = f" + {provider_name} analysis" if "ai_analysis" in results else ""
            
            # Display cumulative stats
            token_stats = self.vision.get_token_stats()
            active_provider = token_stats['active_provider'].upper()
            
            if active_provider == "GEMINI" and token_stats['gemini']['total_api_calls'] > 0:
                token_info = f" (Session: {token_stats['gemini']['total_tokens']} tokens, {token_stats['gemini']['total_api_calls']} calls)"
                self.overlay.update_status(f"Detected {len(bosses)} boss(es){ai_status}{token_info} - Press Alt+1 to scan again")
            elif active_provider == "OLLAMA" and token_stats['ollama']['total_requests'] > 0:
                ollama_info = f" (Session: {token_stats['ollama']['total_requests']} requests)"
                self.overlay.update_status(f"Detected {len(bosses)} boss(es){ai_status}{ollama_info} - Press Alt+1 to scan again")
            else:
                self.overlay.update_status(f"Detected {len(bosses)} boss(es){ai_status} - Press Alt+1 to scan again")
        else:
            self.overlay.update_status("No bosses detected - Press Alt+1 to scan again")

    def _on_snapshot_error(self, error_msg):
        """Handle snapshot processing error."""
        print(f"[App] Snapshot error: {error_msg}")
        self.overlay.update_status(f"Error: {error_msg}")

    def _on_overlay_closed(self):
        """Callback when overlay is closed."""
        self.shutdown()

    def _on_map_file_changed(self, map_data: list):
        """Handle external map.json file changes and update UI accordingly."""
        print("[App] External map.json file change detected, updating UI...")
        
        # Convert map data to UI format
        ui_data = {
            "bosses": [],
            "external_update": True  # Flag to indicate this is from external change
        }
        
        # Extract boss information from map data
        for map_entry in map_data:
            if map_entry.get("boss"):  # Only include entries with boss data
                ui_data["bosses"].append({
                    "name": map_entry.get("boss", ""),
                    "map": map_entry.get("map", "--"),
                    "channel": "--",  # Map data doesn't have channel info
                    "countdown": "",  # Map data doesn't have countdown
                    "status": "N",    # Default status
                    "type": map_entry.get("type", "--"),
                    "level": map_entry.get("lv", ""),
                    "note": map_entry.get("note", ""),
                    "from_map_update": True  # Mark this as coming from map update
                })
        
        # Update UI with the reloaded data
        self.overlay.update_data(ui_data)
        self.overlay.update_status(f"Map data refreshed from external edit - {len(ui_data['bosses'])} boss(es) loaded")

    def run(self):
        """Start the application."""
        print("[App] Starting Game Tracker Overlay for TOSM")
        print("[App] Looking for 'TOSM' window...")

        if not self.capture.initialize():
            print("[App] ERROR: Could not find 'TOSM' window. Is the game running?")
            return 1

        self.overlay.show()
        print("[App] Overlay displayed.")
        
        # Start global hotkey listener
        self.global_hotkey.start()
        
        print("[App] Press Alt+1 anywhere to capture and scan for bosses")
        print("[App] Press Ctrl+C or close overlay to exit.")
        print("[App] Data will be saved to data/logs/")

        return self.app.exec()

    def shutdown(self):
        """Gracefully shutdown the application."""
        if self._shutdown_called:
            return
        self._shutdown_called = True
        
        print("[App] Shutting down...")
        
        # Clear pending requests
        pending_count = len(self.pending_requests)
        if pending_count > 0:
            print(f"[App] Cancelling {pending_count} pending requests")
            self.pending_requests.clear()
        
        # Stop async worker
        if self.worker_thread and self.worker_thread.isRunning():
            self.worker_thread.quit()
            self.worker_thread.wait()
        
        # Stop global hotkey
        self.global_hotkey.stop()
        
        # Save session data
        # self.logger.save()
        # report_path = self.logger.export_txt()
        # print(f"[App] Report saved: {report_path}")
        
        self.app.quit()


def main():
    app = GameTrackerApp()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())
