# TOSM Boss Tracker - Project Structure

## Overview
This project is organized into logical modules for better maintainability and scalability.

## Directory Structure

```
TOSM/
├── main.py                 # Application entry point
├── README.md              # Project documentation
├── core/                  # Core application modules
│   ├── __init__.py
│   ├── capture.py         # Screen capture functionality
│   ├── vision.py          # AI vision processing (Gemini API)
│   ├── ui.py              # User interface (PyQt6 overlay)
│   ├── data_manager.py    # Data persistence layer
│   ├── logger.py          # Session logging
│   └── map_level.py       # Map and boss metadata
├── utils/                 # Utility functions
│   ├── __init__.py
│   └── find_window.py     # Window detection utilities
├── tests/                 # Test files
│   ├── __init__.py
│   ├── test_data_manager.py
│   └── test_boss_data.json
├── config/                # Configuration files
│   ├── __init__.py
│   ├── gemini_api_key.txt
│   └── requirements.txt
└── data/                  # Runtime data
    ├── map.json           # Boss and map metadata
    ├── ui_state.json      # UI state persistence
    ├── boss_data.json     # Boss tracking data
    ├── logs/              # Session logs and reports
    └── pics/              # Debug screenshots
```

## Module Responsibilities

### Core Modules (`core/`)
- **capture.py**: Handles window capture and screen grabbing
- **vision.py**: Processes images using Gemini API for boss detection
- **ui.py**: Manages the PyQt6 overlay interface and user interactions
- **data_manager.py**: Provides persistent storage for boss tracking data
- **logger.py**: Handles session logging and report generation
- **map_level.py**: Loads and provides access to map/boss metadata

### Utilities (`utils/`)
- **find_window.py**: Helper functions for window detection and management

### Tests (`tests/`)
- **test_data_manager.py**: Unit tests for data management functionality
- **test_boss_data.json**: Test data for development and testing

### Configuration (`config/`)
- **gemini_api_key.txt**: API key for Gemini vision service
- **requirements.txt**: Python package dependencies

### Runtime Data (`data/`)
- **map.json**: Static boss and map information
- **ui_state.json**: Current UI state for session persistence
- **boss_data.json**: Historical boss tracking data
- **logs/**: Session logs and generated reports
- **pics/**: Debug screenshots captured during processing

## Import Structure

The project uses relative imports within packages:

```python
# In main.py
from core.capture import WindowCapture
from core.vision import VisionProcessor
from core.ui import OverlayWindow
# ...

# Within core modules
from .map_level import get_boss_info
```

## Benefits of This Structure

1. **Separation of Concerns**: Each module has a clear, single responsibility
2. **Maintainability**: Easy to locate and modify specific functionality
3. **Testability**: Isolated modules are easier to test
4. **Scalability**: New features can be added without affecting existing code
5. **Reusability**: Modules can be reused in other projects if needed

## Running the Application

```bash
python main.py
```

The application will automatically load all necessary modules and start the boss tracking overlay.
