from typing import Optional
import numpy as np
import cv2
import pygetwindow as gw
from PIL import Image
import win32gui
import win32ui
import win32con
from ctypes import windll


class WindowCapture:
    """Captures frames from a specific window on-demand."""

    def __init__(self, window_title: str):
        self.window_title = window_title
        self._window: Optional[gw.Win32Window] = None


    def find_window(self) -> bool:
        """Find the target window by title."""
        try:
            windows = gw.getWindowsWithTitle(self.window_title)
            if windows:
                self._window = windows[0]
                return True
        except Exception as e:
            print(f"[Capture] Error finding window: {e}")
        return False

    def is_window_visible(self) -> bool:
        """Check if window is visible and not minimized."""
        if self._window is None:
            return False
        try:
            # Check for minimized window (negative coordinates or very small size)
            if self._window.left < -1000 or self._window.top < -1000:
                return False
            if self._window.width < 100 or self._window.height < 100:
                return False
            return True
        except Exception:
            return False

    def get_window_bbox(self) -> Optional[tuple]:
        """Get the current window bounding box (left, top, right, bottom)."""
        if self._window is None or not self.is_window_visible():
            return None
        try:
            return (
                self._window.left,
                self._window.top,
                self._window.right,
                self._window.bottom,
            )
        except Exception:
            return None

    def capture_frame(self) -> Optional[np.ndarray]:
        """Capture a single frame from the target window using Windows API."""
        if self._window is None:
            if not self.find_window():
                return None

        if not self.is_window_visible():
            return None

        try:
            # Get window handle
            hwnd = self._window._hWnd
            
            # Bring window to foreground to ensure it's visible
            # Don't activate it, just make sure content is rendered
            
            # Get window DC
            hwndDC = win32gui.GetWindowDC(hwnd)
            mfcDC = win32ui.CreateDCFromHandle(hwndDC)
            saveDC = mfcDC.CreateCompatibleDC()
            
            # Get client area (excluding borders)
            left, top, right, bottom = win32gui.GetClientRect(hwnd)
            width = right - left
            height = bottom - top
            
            # Create bitmap
            saveBitMap = win32ui.CreateBitmap()
            saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
            saveDC.SelectObject(saveBitMap)
            
            # Copy from window DC to memory DC
            # Use SRCCOPY | CAPTUREBLT to capture layered windows
            result = windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 3)
            
            # Convert to numpy array
            bmpinfo = saveBitMap.GetInfo()
            bmpstr = saveBitMap.GetBitmapBits(True)
            
            # Clean up
            win32gui.DeleteObject(saveBitMap.GetHandle())
            saveDC.DeleteDC()
            mfcDC.DeleteDC()
            win32gui.ReleaseDC(hwnd, hwndDC)
            
            if result == 0:
                return None
            
            # Create image from bitmap data
            im = Image.frombuffer(
                'RGB',
                (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
                bmpstr, 'raw', 'BGRX', 0, 1
            )
            
            # Crop left portion - keep only right side with boss info
            # Remove left 40% of the image
            width, height = im.size
            left_crop = int(width * 0.4)
            bottom_crop = int(height * 0.5)
            im = im.crop((left_crop, 0, width, bottom_crop))
            
            frame = np.array(im)
            frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
            return frame
            
        except Exception as e:
            print(f"[Capture] Error capturing frame: {e}")
            return None


    def initialize(self) -> bool:
        """Initialize by finding the target window."""
        if not self.find_window():
            print(f"[Capture] Could not find window '{self.window_title}'")
            return False
        print(f"[Capture] Window found: {self.window_title}")
        return True


if __name__ == "__main__":
    capture = WindowCapture("TOSM TH")
    if capture.initialize():
        frame = capture.capture_frame()
        if frame is not None:
            print(f"[Test] Captured frame: {frame.shape}")
        else:
            print("[Test] Failed to capture frame")
    else:
        print("[Test] Failed to find window")
