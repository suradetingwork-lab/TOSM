"""Find the correct window title for the game."""
import pygetwindow as gw

print("All windows:")
for win in gw.getAllWindows():
    if win.title and len(win.title.strip()) > 0:
        print(f"  - '{win.title}'")

print("\nWindows containing 'Tree':")
for win in gw.getAllWindows():
    if 'Tree' in win.title:
        print(f"  - '{win.title}'")

print("\nWindows containing 'Savior':")
for win in gw.getAllWindows():
    if 'Savior' in win.title:
        print(f"  - '{win.title}'")
