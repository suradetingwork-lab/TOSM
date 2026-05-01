# TOSM Boss Tracker - Comprehensive Workflow Diagrams

This document contains detailed workflow diagrams for the TOSM Boss Tracker application using Mermaid.js syntax. Each diagram provides in-depth visualization of the application's architecture, data flows, and processes.

---

## Table of Contents

1. [Application Startup Flow](#1-application-startup-flow)
2. [Detailed Application Workflow](#2-detailed-application-workflow)
3. [Async Snapshot Processing](#3-async-snapshot-processing)
4. [AI Provider Selection & Initialization](#4-ai-provider-selection--initialization)
5. [Window Capture Process](#5-window-capture-process)
6. [Vision Processing Pipeline](#6-vision-processing-pipeline)
7. [AI Response Parsing](#7-ai-response-parsing)
8. [Data Manager Operations](#8-data-manager-operations)
9. [File Watching & Real-time Sync](#9-file-watching--real-time-sync)
10. [UI Component Architecture](#10-ui-component-architecture)
11. [UI State Management](#11-ui-state-management)
12. [User Interaction Flow](#12-user-interaction-flow)
13. [Global Hotkey Handling](#13-global-hotkey-handling)
14. [Session Logging](#14-session-logging)
15. [Error Handling Workflow](#15-error-handling-workflow)
16. [Graceful Shutdown Sequence](#16-graceful-shutdown-sequence)
17. [Module Interaction Diagram](#17-module-interaction-diagram)
18. [Data Persistence Architecture](#18-data-persistence-architecture)
19. [Configuration Management](#19-configuration-management)
20. [Complete System Architecture](#20-complete-system-architecture)

---

## 1. Application Startup Flow

```mermaid
flowchart TD
    START(["Application Entry<br/>python main.py"]) --> INIT_QT["Initialize QApplication<br/>• SetQuitOnLastWindowClosed(False)<br/>• Apply dark theme stylesheet<br/>• Configure tooltips"]
    
    INIT_QT --> LOAD_CONFIG["Load AI Configurations"]
    
    LOAD_CONFIG --> GET_GEMINI["get_gemini_api_key()<br/>• Check GEMINI_API_KEY env var<br/>• Read config/gemini_api_key.txt<br/>• Return API key or None"]
    
    LOAD_CONFIG --> GET_OLLAMA["get_ollama_config()<br/>• Load config/ollama_config.txt<br/>• Default: localhost:11434<br/>• Model: gemma4:e2b<br/>• Timeout: 30s"]
    
    GET_GEMINI --> INIT_MODULES["Initialize Core Modules"]
    GET_OLLAMA --> INIT_MODULES
    
    INIT_MODULES --> CAPTURE["WindowCapture('TOSM TH')<br/>• window_title: 'TOSM TH'<br/>• _window: None initially"]
    
    INIT_MODULES --> VISION["VisionProcessor()<br/>• gemini_api_key<br/>• ollama_config<br/>• use_ollama: False<br/>• Initialize AI clients"]
    
    INIT_MODULES --> OVERLAY["OverlayWindow()<br/>• PyQt6 QMainWindow<br/>• Always-on-top, transparent<br/>• Draggable with Alt+click"]
    
    INIT_MODULES --> LOGGER["BossDataLogger()<br/>• data_dir: 'data/logs'<br/>• Create timestamped session file<br/>• Initialize session data dict"]
    
    INIT_MODULES --> DATA_MGR["BossDataManager()<br/>• data_file: 'boss_data.json'<br/>• Load existing boss data<br/>• Setup file watching"]
    
    INIT_MODULES --> MAP_MGR["MapDataManager()<br/>• data_file: 'data/map.json'<br/>• Load map/boss metadata<br/>• Enable file watching"]
    
    CAPTURE --> SETUP_CALLBACKS["Setup Signal Connections"]
    VISION --> SETUP_CALLBACKS
    OVERLAY --> SETUP_CALLBACKS
    LOGGER --> SETUP_CALLBACKS
    DATA_MGR --> SETUP_CALLBACKS
    MAP_MGR --> SETUP_CALLBACKS
    
    SETUP_CALLBACKS --> CONNECT_SIGNALS["Connect PyQt Signals:<br/>• map_data_manager.data_changed → _on_map_file_changed<br/>• overlay.close_callback → shutdown<br/>• global_hotkey.triggered → _manual_snapshot"]
    
    CONNECT_SIGNALS --> SETUP_HOTKEY["Setup Hotkeys<br/>• Global: Alt+1 (Windows API)<br/>• Local: Ctrl+1 (QShortcut)<br/>• Both trigger _manual_snapshot"]
    
    SETUP_HOTKEY --> SIG_HANDLER["Setup Signal Handler<br/>• signal.signal(SIGINT, _signal_handler)<br/>• Handle Ctrl+C gracefully"]
    
    SIG_HANDLER --> RUN["Run Application<br/>app.run()"]
    
    RUN --> FIND_WINDOW["capture.initialize()<br/>find_window() via pygetwindow"]
    
    FIND_WINDOW --> WINDOW_FOUND{Window<br/>Found?}
    
    WINDOW_FOUND -->|No| ERROR_MSG["Print Error:<br/>'Could not find TOSM window.<br/>Is the game running?'"]
    
    WINDOW_FOUND -->|Yes| SHOW_OVERLAY["overlay.show()<br/>Display transparent overlay"]
    
    SHOW_OVERLAY --> START_HOTKEY["global_hotkey.start()<br/>Register Alt+1 hotkey<br/>Start message loop thread"]
    
    START_HOTKEY --> PRINT_INFO["Print Instructions:<br/>• Alt+1 to capture<br/>• Ctrl+C to exit<br/>• Data saved to data/logs/"]
    
    PRINT_INFO --> EXEC["app.exec()<br/>Start Qt Event Loop"]
    
    ERROR_MSG --> EXIT(["Exit with code 1"])
```

---

## 2. Detailed Application Workflow

```mermaid
flowchart TD
    subgraph "Initialization Phase"
        A["main.py: GameTrackerApp.__init__()"] --> B["Initialize QApplication"]
        B --> C["Load AI Configurations<br/>• Gemini API Key<br/>• Ollama Config"]
        C --> D["Initialize Core Modules"]
        D --> E["Setup Signal Connections"]
    end
    
    subgraph "Runtime Phase"
        E --> F["run() → capture.initialize()"]
        F --> G["Show Overlay Window"]
        G --> H["Start Global Hotkey Listener<br/>Alt+1"]
        H --> I["Qt Event Loop<br/>app.exec()"]
    end
    
    subgraph "User Triggered Snapshot (Async)"
        J["User Presses Alt+1"] --> K["_manual_snapshot()"]
        K --> L["Show Visual Feedback<br/>show_snapshot_feedback()"]
        L --> M["Add to Queue<br/>pending_requests.append()"]
        M --> N{Worker Running?}
        N -->|No| O["Start SnapshotWorker"]
        N -->|Yes| P["Request Queued<br/>Print queue length"]
        O --> Q["Worker Thread Processing"]
    end
    
    subgraph "Snapshot Processing Pipeline"
        Q --> R["SnapshotWorker.process()"]
        R --> S["capture.capture_frame()"]
        S --> T{Frame Captured?}
        T -->|No| U["Emit error signal<br/>'Window not found'"]
        T -->|Yes| V["vision.process(frame)"]
        V --> W["AI Analysis<br/>Gemini or Ollama"]
        W --> X["Parse AI Response"]
        X --> Y["Extract Boss Data"]
        Y --> Z["Emit finished signal"]
    end
    
    subgraph "Result Handling"
        Z --> AA["_on_snapshot_finished()"]
        U --> AB["_on_snapshot_error()"]
        AA --> AC["logger.log_detection()<br/>Save to session"]
        AA --> AD["data_manager.update_boss_record()<br/>Update persistent storage"]
        AA --> AE["overlay.update_data()<br/>Refresh UI"]
        AA --> AF["overlay.update_status()<br/>Show detection count"]
        AB --> AF
    end
    
    subgraph "External Map Update"
        AG["External edit to map.json"] --> AH["QFileSystemWatcher<br/>fileChanged signal"]
        AH --> AI["_on_map_file_changed()"]
        AI --> AJ["Reload map data"]
        AJ --> AK["Convert to UI format"]
        AK --> AL["overlay.update_data()<br/>Update UI with new data"]
    end
    
    subgraph "Shutdown Phase"
        AM["User closes overlay<br/>or Ctrl+C"] --> AN["shutdown()"]
        AN --> AO["Clear pending requests"]
        AO --> AP["Stop worker thread"]
        AP --> AQ["Stop global hotkey"]
        AQ --> AR["app.quit()"]
    end
    
    I --> J
    P --> Q
    AF --> I
    AL --> I
    AR --> EXIT(["Application Exit"])
```

---

## 3. Async Snapshot Processing

```mermaid
flowchart TD
    subgraph "Request Queue Management"
        A["User Presses Alt+1"] --> B["_manual_snapshot()<br/>Main Thread"]
        B --> C["show_snapshot_feedback()<br/>Visual feedback immediately"]
        C --> D["pending_requests.append(frame_count)<br/>Add to queue"]
        D --> E{Worker Thread<br/>Running?}
        E -->|No| F["_start_next_worker()<br/>Start processing"]
        E -->|Yes| G["Print: Request queued (N pending)"]
    end
    
    subgraph "Worker Thread Lifecycle"
        F --> H["Create QThread"]
        H --> I["Create SnapshotWorker<br/>• capture<br/>• vision<br/>• frame_count"]
        I --> J["worker.moveToThread(thread)"]
        J --> K["Connect signals:<br/>• started → process<br/>• finished → _on_snapshot_finished<br/>• error → _on_snapshot_error"]
        K --> L["thread.start()"]
        L --> M["Print: Processing request<br/>(remaining: N)"]
    end
    
    subgraph "Async Processing"
        M --> N["SnapshotWorker.process()<br/>Worker Thread"]
        N --> O["capture.capture_frame()"]
        O --> P{Frame Valid?}
        P -->|No| Q["error.emit('Failed to capture...')<br/>Return"]
        P -->|Yes| R["vision.process(frame)"]
        R --> S["AI Processing<br/>• Extract boss panel<br/>• Enhance image<br/>• Call AI API"]
        S --> T["Parse response<br/>_parse_ai_response()"]
        T --> U["finished.emit(results)<br/>Dict with bosses, ai_analysis, etc."]
    end
    
    subgraph "Completion & Chaining"
        U --> V["_on_worker_finished()"]
        Q --> V
        V --> W["QTimer.singleShot(0, _start_next_worker)<br/>Process next in queue"]
        W --> X{Queue Empty?}
        X -->|No| F
        X -->|Yes| Y["Worker thread<br/>terminates"]
    end
    
    subgraph "Main Thread Handling"
        U --> Z["_on_snapshot_finished(results)<br/>Main Thread"]
        Q --> AA["_on_snapshot_error(error_msg)<br/>Main Thread"]
        Z --> AB["Update frame count"]
        AB --> AC["logger.log_detection()"]
        AC --> AD["Update boss records<br/>Loop through detected bosses"]
        AD --> AE["overlay.update_data()<br/>Update UI"]
        AE --> AF["Print AI analysis<br/>if available"]
        AF --> AG["overlay.update_status()<br/>Show stats"]
    end
    
    G --> WAIT["Wait for<br/>current worker"]
    WAIT --> V
```

---

## 4. AI Provider Selection & Initialization

```mermaid
flowchart TD
    subgraph "Provider Configuration"
        A["VisionProcessor.__init__()"] --> B["Parameters:<br/>• gemini_api_key<br/>• ollama_config<br/>• use_ollama: False"]
        B --> C["Initialize state:<br/>• last_channel = '--'<br/>• last_map = '--'<br/>• active_provider"]
        C --> D["Initialize token tracking:<br/>• gemini_tokens dict<br/>• ollama_stats dict"]
    end
    
    subgraph "AI Client Initialization"
        D --> E["Create GeminiClient<br/>self.gemini = GeminiClient(api_key)"]
        E --> F["Create OllamaClient<br/>self.ollama = OllamaClient(config)"]
        F --> G{use_ollama?}
    end
    
    subgraph "Ollama Path"
        G -->|Yes| H["ollama.initialize()"]
        H --> I{Initialization<br/>Success?}
        I -->|Yes| J["Print: Using Ollama<br/>Set active_provider='ollama'"]
        I -->|No| K["Print: Ollama failed<br/>Falling back to Gemini"]
        K --> L{gemini_api_key?}
        L -->|Yes| M["gemini.initialize()<br/>Set use_ollama=False<br/>active_provider='gemini'"]
        L -->|No| N["Print: Warning<br/>No Gemini API key"]
    end
    
    subgraph "Gemini Path"
        G -->|No| O{gemini_api_key?}
        O -->|Yes| P["gemini.initialize()<br/>Print: Using Gemini"]
        O -->|No| Q["Print: Warning<br/>No Gemini API key<br/>Provider unavailable"]
    end
    
    subgraph "Provider Switching"
        R["switch_provider(use_ollama)"] --> S{Toggle or<br/>Specify?}
        S --> T["Toggle current<br/>use_ollama = not use_ollama"]
        T --> U{Requested ==<br/>Current?}
        U -->|Yes| V["Print: Already using<br/>requested provider"]
        U -->|No| W{Ollama<br/>Available?}
        W -->|Yes| X["Set use_ollama=True<br/>active_provider='ollama'"]
        W -->|No| Y{Gemini<br/>Available?}
        Y -->|Yes| Z["Set use_ollama=False<br/>active_provider='gemini'"]
        Y -->|No| AA["Print: Cannot switch<br/>Provider not initialized"]
    end
    
    subgraph "Token Statistics"
        AB["_update_token_stats()"] --> AC{Provider?}
        AC -->|Gemini| AD["Update:<br/>• total_prompt_tokens<br/>• total_candidates_tokens<br/>• total_api_calls++"]
        AC -->|Ollama| AE["Update:<br/>• total_requests++<br/>• successful_requests++"]
        AD --> AF["Print token stats"]
        AE --> AF
    end
    
    subgraph "Get Statistics"
        AG["get_token_stats()"] --> AH["Calculate totals:<br/>• gemini_total = prompt + candidates<br/>• Return dict with both providers"]
    end
    
    J --> END["Ready for processing"]
    M --> END
    N --> END
    P --> END
    Q --> END
    V --> END
    X --> END
    Z --> END
    AA --> END
```

---

## 5. Window Capture Process

```mermaid
flowchart TD
    subgraph "WindowCapture Initialization"
        A["WindowCapture.__init__()<br/>window_title: 'TOSM TH'"] --> B["self._window = None"]
    end
    
    subgraph "Finding Window"
        C["initialize() or<br/>find_window()"] --> D["gw.getWindowsWithTitle(window_title)"]
        D --> E{Windows<br/>Found?}
        E -->|Yes| F["self._window = windows[0]<br/>Return True"]
        E -->|No| G["Print error<br/>Return False"]
    end
    
    subgraph "Visibility Check"
        H["is_window_visible()"] --> I{self._window<br/>is None?}
        I -->|Yes| J["Return False"]
        I -->|No| K["Check window bounds:<br/>• left < -1000?<br/>• top < -1000?<br/>• width < 100?<br/>• height < 100?"]
        K --> L{Any condition<br/>True?}
        L -->|Yes| M["Minimized or hidden<br/>Return False"]
        L -->|No| N["Window is visible<br/>Return True"]
    end
    
    subgraph "Frame Capture"
        O["capture_frame()"] --> P{self._window<br/>is None?}
        P -->|Yes| Q["find_window()"]
        Q --> R{Found?}
        R -->|No| S["Return None"]
        R -->|Yes| T["Continue..."]
        P -->|No| T
        T --> U["is_window_visible()"]
        U --> V{Visible?}
        V -->|No| W["Return None"]
        V -->|Yes| X["Windows API Capture<br/>Begin..."]
    end
    
    subgraph "Windows API Capture Sequence"
        X --> Y["hwnd = self._window._hWnd<br/>Get window handle"]
        Y --> Z["hwndDC = GetWindowDC(hwnd)<br/>Get device context"]
        Z --> AA["mfcDC = CreateDCFromHandle(hwndDC)"]
        AA --> AB["saveDC = mfcDC.CreateCompatibleDC()<br/>Create memory DC"]
        AB --> AC["GetClientRect(hwnd)<br/>Get: left, top, right, bottom"]
        AC --> AD["width = right - left<br/>height = bottom - top"]
        AD --> AE["saveBitMap = CreateBitmap()<br/>CreateCompatibleBitmap"]
        AE --> AF["saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)"]
        AF --> AG["saveDC.SelectObject(saveBitMap)"]
        AG --> AH["PrintWindow(hwnd, saveDC, 3)<br/>SRCCOPY | CAPTUREBLT<br/>Copy to memory DC"]
    end
    
    subgraph "Convert to NumPy Array"
        AH --> AI["bmpinfo = saveBitMap.GetInfo()<br/>Get bitmap info"]
        AI --> AJ["bmpstr = saveBitMap.GetBitmapBits(True)<br/>Get raw bitmap data"]
        AJ --> AK["Cleanup:<br/>DeleteObject(saveBitMap)<br/>DeleteDC(saveDC)<br/>DeleteDC(mfcDC)<br/>ReleaseDC(hwndDC)"]
        AK --> AL["image = np.frombuffer(bmpstr, np.uint8)<br/>Reshape to (height, width, 4)<br/>BGRA format"]
        AL --> AM["Return image<br/>as NumPy array"]
    end
    
    subgraph "Error Handling"
        AN["Exception during capture"] --> AO["Print error message<br/>with exception details"]
        AO --> AP["Return None"]
    end
```

---

## 6. Vision Processing Pipeline

```mermaid
flowchart TD
    subgraph "VisionProcessor.process() Entry"
        A["process(frame)"] --> B["_get_boss_panel_region(frame)<br/>Calculate crop region"]
        B --> C["Calculate region:<br/>• panel_width = w * 0.40<br/>• panel_height = h * 0.70<br/>• x1 = w - panel_width<br/>• y1 = 0"]
    end
    
    subgraph "Panel Extraction"
        C --> D["_extract_boss_panel(frame)<br/>Crop region from frame"]
        D --> E["panel = frame[y:y+h, x:x+w]<br/>Returns cropped region"]
    end
    
    subgraph "Image Enhancement"
        E --> F["_enhance_for_api(panel)<br/>Prepare for AI analysis"]
        F --> G["Convert BGR to RGB:<br/>cv2.cvtColor(image, COLOR_BGR2RGB)"]
        G --> H{"max(h, w) > 1024?"}
        H -->|Yes| I["Calculate scale:<br/>scale = 1024 / max(h, w)"]
        I --> J["Resize image:<br/>new_w = w * scale<br/>new_h = h * scale<br/>INTER_AREA interpolation"]
        H -->|No| K["Skip resizing"]
        J --> L["Return enhanced_image"]
        K --> L
    end
    
    subgraph "AI Provider Selection"
        L --> M{self.use_ollama?}
        M -->|Yes| N["_process_with_ollama<br/>enhanced_image"]
        M -->|No| O["_process_with_gemini<br/>enhanced_image"]
    end
    
    subgraph "Ollama Processing"
        N --> P["ollama.process(image)<br/>Send to Ollama API"]
        P --> Q{Success?}
        Q -->|Yes| R["_update_token_stats<br/>provider='ollama'"]
        Q -->|No| S["Log error<br/>Return empty response"]
    end
    
    subgraph "Gemini Processing"
        O --> T["gemini.process(image)<br/>Send to Gemini API"]
        T --> U{Success?}
        U -->|Yes| V["_update_token_stats<br/>provider='gemini'<br/>with token usage"]
        U -->|No| W["Log error<br/>Return empty response"]
    end
    
    subgraph "Response Parsing"
        R --> X["_parse_ai_response()<br/>response_text"]
        V --> X
        S --> Y["Empty results<br/>Return {'bosses': []}"]
        W --> Y
        X --> Z["Parse JSON from<br/>AI response"]
    end
    
    subgraph "Build Results"
        Z --> AA["results = {<br/>• 'bosses': []<br/>• 'ai_analysis': ''<br/>• 'provider': ''<br/>• 'raw_text': []<br/>• 'token_usage': {}<br/>}"]
        AA --> AB["Return results dict"]
    end
```

---

## 7. AI Response Parsing

```mermaid
flowchart TD
    subgraph "Parse Entry"
        A["_parse_ai_response(response, provider)"] --> B{response is None<br/>or empty?}
        B -->|Yes| C["Print: Empty response<br/>Return []"]
        B -->|No| D["Strip whitespace<br/>response = response.strip()"]
        D --> E{Empty after strip?}
        E -->|Yes| F["Print: Empty after strip<br/>Return []"]
        E -->|No| G["Log preview:<br/>first 100 chars<br/>Preview: 'xxx...'"]
    end
    
    subgraph "Error Detection"
        G --> H{Response starts with<br/>'API error'?}
        H -->|Yes| I["Print: API error detected<br/>Return []"]
        H -->|No| J{"Contains<br/>'quota exceeded'?"}
        J -->|Yes| K["Print: Quota exceeded<br/>Return []"]
        J -->|No| L["Continue to<br/>content extraction"]
    end
    
    subgraph "Extract JSON from Markdown"
        L --> M{"Contains<br/>'```json'?"}
        M -->|Yes| N["Extract from<br/>```json block<br/>Find start/end<br/>Strip markdown"]
        M -->|No| O{"Contains<br/>'```'?"}
        O -->|Yes| P["Extract from<br/>generic code block"]
        O -->|No| Q["No markdown<br/>blocks found"]
        N --> R["Continue"]
        P --> R
        Q --> R
    end
    
    subgraph "Regex Extraction Fallback"
        R --> S{response starts<br/>with '{'?}
        S -->|Yes| T["Already JSON<br/>Continue to parse"]
        S -->|No| U["re.search(r'\{[\s\S]*\}', response)<br/>Find JSON with regex"]
        U --> V{Match found?}
        V -->|Yes| W{"Match is valid<br/>JSON (>10 chars,<br/>starts with '{')?"}
        W -->|Yes| X["response = match.group(0)<br/>Log extracted JSON"]
        W -->|No| Y["Print: Not valid JSON<br/>Return []"]
        V -->|No| Z["Print: No JSON found<br/>Return []"]
    end
    
    subgraph "Final Validation"
        X --> AA{"response length<br/>> 2?"}
        AA -->|No| AB["Print: Too short<br/>Return []"]
        AA -->|Yes| AC{"response starts<br/>with '{'?"}
        AC -->|No| AD["Print: Doesn't start with {<br/>Return []"]
        AC -->|Yes| AE["Continue to parsing"]
    end
    
    subgraph "JSON Parsing"
        AE --> AF["json.loads(response)<br/>Parse JSON"]
        AF --> AG{"Parse<br/>Success?"}
        AG -->|Yes| AH["Print: JSON parsed<br/>successfully"]
        AG -->|No| AI["Print: JSON parse error<br/>Return []"]
    end
    
    subgraph "Format Detection & Processing"
        AH --> AJ{"'boss_name'<br/>in data?"}
        AJ -->|Yes| AK["New format detected<br/>Process single boss object"]
        AJ -->|No| AL{"'bosses'<br/>in data?"}
        AL -->|Yes| AM["Old format detected<br/>Process bosses array"]
        AL -->|No| AN["Unknown format<br/>Return []"]
    end
    
    subgraph "New Format Processing"
        AK --> AO["Extract fields:<br/>• boss_name<br/>• boss_type<br/>• channel<br/>• current_status<br/>• time_until_spawn"]
        AO --> AP["get_boss_info(boss_name)<br/>Lookup map, lv, type"]
        AP --> AQ{"current_status<br/>== 'WAITING_FOR_SPAWN'?"}
        AQ -->|Yes| AR["status = 'N'<br/>countdown = time field"]
        AQ -->|No| AS{"current_status<br/>starts with 'LV_'?"}
        AS -->|Yes| AT["Extract level number<br/>status = 'LV{N}'"]
        AS -->|No| AU["Default status = 'N'"]
        AR --> AV["Build boss dict"]
        AT --> AV
        AU --> AV
    end
    
    subgraph "Build Boss Record"
        AV --> AW["boss = {<br/>• name<br/>• map (from lookup)<br/>• channel<br/>• countdown<br/>• status<br/>• type<br/>• level<br/>• note<br/>}"]
        AW --> AX["bosses.append(boss)"]
        AX --> AY["Return bosses list"]
    end
    
    C --> END(["Return []"])
    F --> END
    I --> END
    K --> END
    Y --> END
    Z --> END
    AB --> END
    AD --> END
    AI --> END
    AN --> END
    AY --> END
```

---

## 8. Data Manager Operations

```mermaid
flowchart TD
    subgraph "BossDataManager Initialization"
        A["BossDataManager.__init__()<br/>data_file='boss_data.json'"] --> B["Initialize:<br/>• boss_data: {}<br/>• _file_watcher<br/>• _watching_enabled=False"]
        B --> C["load_data()<br/>Load from JSON file"]
        C --> D["_setup_file_watching()<br/>Setup QFileSystemWatcher"]
    end
    
    subgraph "Load Data"
        D --> E{"data_file<br/>exists?"}
        E -->|No| F["Create new file<br/>boss_data = {}<br/>save_data()<br/>enable_file_watching()"]
        E -->|Yes| G["open(data_file, 'r')<br/>Read JSON"]
        G --> H["boss_data = json.load(f)"]
        H --> I["Print: Loaded N<br/>bosses from file"]
        H --> J["JSONDecodeError?"]
        J -->|Yes| K["Print: Error reading<br/>Create new file"]
        K --> L["boss_data = {}<br/>save_data()"]
    end
    
    subgraph "Update Boss Record"
        M["update_boss_record(<br/>boss_name, map_name,<br/>channel, time_left_str,<br/>status, boss_type)"] --> N{"boss_name in<br/>boss_data?"}
        N -->|No| O["Create new entry:<br/>boss_data[boss_name] = {<br/>• name<br/>• first_seen<br/>• last_updated<br/>• spawn_count: 0<br/>• locations: {}<br/>}"]
        N -->|Yes| P["Get existing entry"]
        O --> Q["Set first_seen = now()"]
        P --> R["Update last_updated = now()"]
        Q --> R
        R --> S{"location_key in<br/>locations?"}<br/>location_key = "{map}_{channel}"
        S -->|No| T["Create location:<br/>locations[loc_key] = {<br/>• map<br/>• channel<br/>• spawn_history: []<br/>}"]
        S -->|Yes| U["Get existing location"]
        T --> V["spawn_count += 1"]
        U --> V
    end
    
    subgraph "Spawn History Management"
        V --> W["Calculate spawn_time:<br/>now() + time_left_str"]
        W --> X["Create history entry:<br/>• detected_at<br/>• time_left<br/>• spawn_time"]
        X --> Y["Add to spawn_history<br/>at position 0 (newest)"]
        Y --> Z{"spawn_history<br/>length > 10?"}
        Z -->|Yes| AA["Remove oldest entry<br/>Keep only 10 records"]
        Z -->|No| AB["Keep as is"]
        AA --> AC["save_data()<br/>Persist to JSON"]
        AB --> AC
    end
    
    subgraph "Save Data (Atomic)"
        AC --> AD["save_data()"] --> AE{"data_file<br/>exists?"}
        AE -->|Yes| AF["Create backup:<br/>shutil.copy2(data_file,<br/>data_file.bak)"]
        AE -->|No| AG["Skip backup"]
        AF --> AH["Write to temp file:<br/>data_file.tmp"]
        AG --> AH
        AH --> AI["json.dump(boss_data, f,<br/>indent=2, ensure_ascii=False)"]
        AI --> AJ["Atomic replace:<br/>temp_file.replace(data_file)"]
        AJ --> AK{"Success?"}
        AK -->|Yes| AL["Return True"]
        AK -->|No| AM["Print error<br/>Return False"]
    end
    
    subgraph "File Watching"
        AN["_setup_file_watching()"] --> AO{"data_file<br/>exists?"}
        AO -->|Yes| AP["_file_watcher.addPath(data_file)"]
        AP --> AQ["Connect signal:<br/>fileChanged → _on_file_changed"]
        AQ --> AR["_watching_enabled = True"]
        AO -->|No| AS["Print: File not found<br/>Will watch when created"]
    end
    
    subgraph "External File Change"
        AT["External edit to file"] --> AU["QFileSystemWatcher<br/>fileChanged signal"]
        AU --> AV["_on_file_changed(path)"]
        AV --> AW{"_watching_enabled?"}
        AW -->|Yes| AX["QTimer.singleShot(100ms,<br/>_reload_and_notify)"]
        AW -->|No| AY["Ignore (disabled)"]
        AX --> AZ["_reload_and_notify()"]
        AZ --> BA["old_data = map_data.copy()"]
        BA --> BB["load_data()"]
        BB --> BC{"old_data !=<br/>map_data?"}
        BC -->|Yes| BD["data_changed.emit(map_data)<br/>Notify listeners"]
        BC -->|No| BE["No change detected"]
    end
```

---

## 9. File Watching & Real-time Sync

```mermaid
flowchart TD
    subgraph "MapDataManager File Watching"
        A["MapDataManager.__init__()"] --> B["data_file = 'data/map.json'"]
        B --> C["map_data: list = []"]
        C --> D["_file_watcher = QFileSystemWatcher()"]
        D --> E["_watching_enabled = False"]
        E --> F["load_data()"]
        F --> G["_setup_file_watching()"]
    end
    
    subgraph "Setup Watching"
        G --> H{"data_file.exists()?"}
        H -->|Yes| I["_file_watcher.addPath(str(data_file))"]
        I --> J["_file_watcher.fileChanged.connect(<br/>self._on_file_changed)"]
        J --> K["_watching_enabled = True"]
        K --> L["Print: File watching enabled"]
        H -->|No| M["Print: Will start watching<br/>when file created"]
    end
    
    subgraph "Enable/Disable Watching"
        N["enable_file_watching()"] --> O{"!_watching_enabled &&<br/>data_file.exists()?"}
        O -->|Yes| P["Call _setup_file_watching()"]
        O -->|No| Q["Already watching or<br/>file doesn't exist"]
        
        R["disable_file_watching()"] --> S{"_watching_enabled?"}
        S -->|Yes| T["_file_watcher.removePath(str(data_file))"]
        T --> U["_watching_enabled = False"]
        U --> V["Print: File watching disabled"]
    end
    
    subgraph "File Change Event"
        W["External application<br/>edits map.json"] --> X["OS file system<br/>detects change"]
        X --> Y["QFileSystemWatcher<br/>emits fileChanged signal"]
        Y --> Z["_on_file_changed(path)"]
        Z --> AA{"_watching_enabled?"}
        AA -->|Yes| AB["QTimer.singleShot(100, <br/>self._reload_and_notify)"]
        AB --> AC["Wait 100ms<br/>(ensure write complete)"]
        AA -->|No| AD["Return early<br/>(ignored)"]
    end
    
    subgraph "Reload & Notify"
        AC --> AE["_reload_and_notify()"]
        AE --> AF["old_data = map_data.copy()<br/>(shallow copy)"]
        AF --> AG["load_data()<br/>(re-read from disk)"]
        AG --> AH{"old_data !=<br/>map_data?"}
        AH -->|Yes| AI["Print: Data reloaded,<br/>N entries found"]
        AI --> AJ["data_changed.emit(<br/>map_data.copy())<br/>Notify all listeners"]
        AH -->|No| AK["No actual change<br/>Skip notification"]
    end
    
    subgraph "Main App Response"
        AL["_on_map_file_changed(map_data)"] --> AM["Print: External map.json<br/>change detected"]
        AM --> AN["Prepare ui_data:<br/>• 'bosses': []<br/>• 'external_update': True"]
        AN --> AO["for map_entry in map_data:"]
        AO --> AP{"map_entry.get('boss')?"}
        AP -->|Yes| AQ["Build boss dict:<br/>• name, map, type<br/>• from_map_update: True"]
        AP -->|No| AR["Skip entry"]
        AQ --> AS["ui_data['bosses'].append(boss)"]
        AS --> AT["Continue loop"]
        AT --> AU{"More entries?"}
        AU -->|Yes| AO
        AU -->|No| AV["overlay.update_data(ui_data)"]
        AV --> AW["overlay.update_status(<br/>'Map data refreshed...')"]
    end
```

---

## 10. UI Component Architecture

```mermaid
flowchart TD
    subgraph "OverlayWindow Hierarchy"
        A["OverlayWindow<br/>(QMainWindow)"] --> B["Central Widget<br/>QWidget"]
        
        B --> C["Main Layout<br/>QVBoxLayout<br/>setContentsMargins(12, 12, 12, 12)"]
        
        C --> D["Title Bar<br/>QHBoxLayout"]
        D --> D1["Title Label<br/>'🎮 TOSM Boss Tracker'"]
        D --> D2["Drag Handle<br/>'⋮⋮' (grip indicator)"]
        D --> D3["Control Buttons<br/>Minimize | Pin | Close"]
        
        C --> E["Filter Section<br/>QHBoxLayout"]
        E --> E1["Filter Input<br/>QLineEdit<br/>Placeholder: 'Filter by map...'"]
        E --> E2["Map Level Filter<br/>Dropdown"]
        E --> E3["Clear Filter<br/>QPushButton"]
        
        C --> F["Table Header<br/>QHBoxLayout"]
        F --> F1["SortableHeaderButton<br/>'BOSS' (210px)"]
        F --> F2["SortableHeaderButton<br/>'TYPE' (80px)"]
        F --> F3["SortableHeaderButton<br/>'MAP' (150px)"]
        F --> F4["SortableHeaderButton<br/>'CH' (50px)"]
        F --> F5["SortableHeaderButton<br/>'STATUS' (80px)"]
        F --> F6["SortableHeaderButton<br/>'TIME' (80px, right)"]
        F --> F7["SortableHeaderButton<br/>'LV' (50px, right)"]
        
        C --> G["Boss Data Container<br/>QVBoxLayout"]
        G --> G1["BossRow Widgets<br/>(Dynamic list)"]
        
        C --> H["Status Bar<br/>QHBoxLayout"]
        H --> H1["Status Label<br/>'Ready' | 'Detected N boss(es)'"]
        H --> H2["Size Grip<br/>QSizeGrip"]
    end
    
    subgraph "BossRow Component"
        I["BossRow<br/>(QFrame)"] --> J["Horizontal Layout"]
        
        J --> K["Boss Name<br/>QLabel (210px)"]
        K --> K1["Font: Segoe UI 11<br/>Color: #F8FAFC"]
        K --> K2["Map lookup tooltip<br/>on hover"]
        
        J --> L["Type Badge<br/>QLabel (80px)"]
        L --> L1["Background by type:<br/>• Demon: #EF4444<br/>• Beast: #A855F7<br/>• Plant: #22C55E<br/>• etc."]
        
        J --> M["Map Name<br/>QLabel (150px)"]
        M --> M1["Font: Segoe UI 10<br/>Color: #94A3B8"]
        
        J --> N["Channel<br/>QLabel (50px)"]
        N --> N1["'CH.1', 'CH.2', etc."]
        
        J --> O["Status Badge<br/>QFrame (80px)"]
        O --> O1["Styles:<br/>• N: Neutral<br/>• LV1-LV4: Activity levels<br/>Colors indicate urgency"]
        
        J --> P["Time Left<br/>QLabel (80px, right)"]
        P --> P1["Font: Segoe UI 10<br/>Color: #FBBF24 (gold)"]
        P --> P2["Format: HH:MM:SS"]
        
        J --> Q["Level Badge<br/>QLabel (50px, right)"]
        Q --> Q1["Format: '430+'"]
        Q --> Q2["Font: Segoe UI 9<br/>Bold weight"]
        
        I --> R["Hover Effects<br/>setStyleSheet on<br/>enter/leave events"]
        I --> S["Context Menu<br/>Right-click actions"]
    end
    
    subgraph "SortableHeaderButton"
        T["SortableHeaderButton<br/>(QPushButton)"] --> U["Properties:<br/>• _column: str<br/>• _sort_direction: None/'asc'/'desc'<br/>• _width: int<br/>• _align_right: bool"]
        
        U --> V["Signals:<br/>clicked.emit(str)<br/>Emits column name"]
        
        U --> W["Methods:<br/>• _update_style()<br/>• set_sort_direction()<br/>• reset_sort()"]
        
        W --> X["Style States:<br/>• Active sort: Purple gradient<br/>• Inactive: Transparent<br/>Arrow indicators: ▲ ▼"]
        
        T --> Y["Click Handler<br/>Connected from OverlayWindow<br/>Calls _on_header_clicked()"]
    end
    
    subgraph "Window Properties"
        Z["OverlayWindow<br/>Window Attributes"] --> AA["Window Flags:<br/>• Qt.WindowType.Window<br/>• Qt.WindowType.WindowStaysOnTopHint<br/>• Qt.WindowType.FramelessWindowHint<br/>• Qt.WindowType.WindowTransparentForInput (optional)"]
        
        AA --> AB["Attribute:<br/>Qt.WidgetAttribute.WA_TranslucentBackground"]
        
        AB --> AC["StyleSheet:<br/>• Background: rgba(15, 23, 42, 0.85)<br/>• Border-radius: 12px<br/>• Border: 1px solid rgba(139, 92, 246, 0.3)"]
        
        AC --> AD["Geometry:<br/>• Default size: 900x500<br/>• Restored from ui_state.json<br/>• Position: saved/loaded"]
    end
```

---

## 11. UI State Management

```mermaid
stateDiagram-v2
    [*] --> Initializing: Application Start
    
    Initializing --> Loading: Load UI State
    
    Loading --> Hidden: Position & Size<br/>Restored from JSON
    note right of Loading
        Load from ui_state.json:
        - window_position
        - window_size
        - column_sort
        - filter_text
        - column_widths
        - window_maximized
    end note
    
    Hidden --> Visible: show()
    note right of Hidden
        Window created but
        not yet displayed
    end note
    
    Visible --> Idle: No Activity
    note right of Idle
        Normal state waiting
        for user input or
        data updates
    end note
    
    Idle --> Dragging: Alt + MouseDown
    note right of Dragging
        User holds Alt and
        left-clicks on window
        to drag position
    end note
    
    Dragging --> Visible: MouseRelease
    Dragging --> Dragging: MouseMove<br/>Update Position
    
    Visible --> Updating: update_data()
    note right of Updating
        New boss data received
        from vision processing
    end note
    
    Updating --> Sorting: Apply Sort
    Sorting --> Filtering: Apply Filter
    Filtering --> Rendering: Rebuild Rows
    Rendering --> Visible: Update Complete
    
    Visible --> Resizing: Mouse on Edge
    Resizing --> Visible: Release
    
    Visible --> Minimized: Minimize Button
    Minimized --> Visible: Restore
    
    Visible --> Pinned: Pin Button
    Pinned --> Visible: Unpin
    note right of Pinned
        Pin window to stay
        on top of all
        other windows
    end note
    
    Visible --> ShowingFeedback: Snapshot Triggered
    note right of ShowingFeedback
        show_snapshot_feedback()
        - Flash overlay
        - Sound notification
        - Visual indicator
    end note
    
    ShowingFeedback --> Visible: Feedback Complete
    
    Visible --> Hidden: hide() / minimize
    Hidden --> Visible: show() / restore
    
    Visible --> Saving: _save_ui_state()
    note right of Saving
        Save to ui_state.json:
        - Current position
        - Current size
        - Sort settings
        - Filter settings
    end note
    
    Saving --> [*]: Close Event
    Visible --> [*]: closeEvent()
    Hidden --> [*]: Application Exit
```

---

## 12. User Interaction Flow

```mermaid
sequenceDiagram
    participant User
    participant Overlay as OverlayWindow
    participant DataMgr as BossDataManager
    participant MapMgr as MapDataManager
    participant File as JSON Files
    participant Logger as BossDataLogger
    
    rect rgb(40, 40, 50)
        Note over User,Logger: Initialization Phase
        User->>Overlay: Start Application
        Overlay->>DataMgr: Load boss_data.json
        Overlay->>MapMgr: Load map.json
        Overlay->>Overlay: Restore UI state<br/>position, size, filters
    end
    
    rect rgb(30, 50, 40)
        Note over User,Logger: Normal Operation - Snapshot
        User->>Overlay: Press Alt+1 (Global Hotkey)
        Overlay->>Overlay: show_snapshot_feedback()<br/>Visual feedback
        
        par Async Processing
            Overlay->>Overlay: Queue snapshot request
        and Worker Thread
            Overlay->>Overlay: Capture game window
            Overlay->>Overlay: AI vision processing
            Overlay->>Overlay: Parse boss data
        end
        
        Overlay->>DataMgr: update_boss_record()<br/>For each detected boss
        DataMgr->>DataMgr: Update spawn history
        DataMgr->>File: Save boss_data.json<br/>(atomic write with backup)
        DataMgr-->>Overlay: emit data_changed
        
        Overlay->>Logger: log_detection()<br/>Save to session file
        
        Overlay->>Overlay: update_data()<br/>Refresh UI
        Overlay->>User: Display updated boss list
    end
    
    rect rgb(50, 40, 30)
        Note over User,Logger: Dragging Window
        User->>Overlay: Hold Alt + MouseDown
        Overlay->>Overlay: Set _is_dragging = True
        Overlay->>Overlay: Store drag start position
        
        loop Mouse Movement
            User->>Overlay: MouseMove
            Overlay->>Overlay: Calculate delta<br/>Update window position
        end
        
        User->>Overlay: MouseRelease
        Overlay->>Overlay: _is_dragging = False
        Overlay->>Overlay: _save_ui_state()<br/>Persist new position
    end
    
    rect rgb(50, 50, 30)
        Note over User,Logger: External File Edit
        User->>File: Edit map.json<br/>(external editor)
        File->>MapMgr: QFileSystemWatcher<br/>fileChanged signal
        MapMgr->>MapMgr: _on_file_changed()
        MapMgr->>File: Reload map.json
        MapMgr-->>Overlay: emit data_changed(map_data)
        Overlay->>Overlay: _on_map_file_changed()
        Overlay->>Overlay: Convert map data to UI format
        Overlay->>Overlay: update_data()<br/>Refresh display
        Overlay->>User: Show 'Map data refreshed' status
    end
    
    rect rgb(50, 30, 30)
        Note over User,Logger: Sorting & Filtering
        User->>Overlay: Click column header
        Overlay->>Overlay: _on_header_clicked(column)
        Overlay->>Overlay: Toggle sort direction<br/>asc → desc → none
        Overlay->>Overlay: _sort_bosses()
        Overlay->>Overlay: Rebuild UI rows
        Overlay->>User: Display sorted data
        
        User->>Overlay: Type in filter box
        Overlay->>Overlay: _filter_text_changed(text)
        Overlay->>Overlay: _apply_filter()
        Overlay->>Overlay: Filter bosses by map/name
        Overlay->>Overlay: _rebuild_boss_list()
        Overlay->>User: Display filtered results
    end
    
    rect rgb(30, 30, 50)
        Note over User,Logger: Shutdown
        User->>Overlay: Close window or Ctrl+C
        Overlay->>Overlay: closeEvent()
        Overlay->>Overlay: _save_ui_state()
        Overlay->>File: Write ui_state.json
        Overlay->>DataMgr: Cleanup
        Overlay->>MapMgr: Disable file watching
        Overlay->>Logger: save()<br/>Export session report
        Overlay-->>User: Application exits
    end
```

---

## 13. Global Hotkey Handling

```mermaid
flowchart TD
    subgraph "GlobalHotkey Class"
        A["GlobalHotkey.__init__()"] --> B["Properties:<br/>• _running = False<br/>• _thread = None<br/>• _hotkey_id = 1"]
        B --> C["Signals:<br/>• triggered = pyqtSignal()"]
    end
    
    subgraph "Start Hotkey Listener"
        D["global_hotkey.start()"] --> E["_running = True"]
        E --> F["_thread = threading.Thread(<br/>target=_listen,<br/>daemon=True)"]
        F --> G["_thread.start()"]
        G --> H["Print: Global hotkey<br/>Ctrl+1 registered"]
    end
    
    subgraph "Windows API Registration"
        I["_listen()<br/>Background Thread"] --> J["RegisterHotKey(<br/>None,  // No window<br/>hotkey_id=1,<br/>MOD_ALT,  // Alt key<br/>VK_1     // '1' key<br/>)"]
        J --> K{Registration<br/>Success?}
        K -->|Yes| L["Continue to message loop"]
        K -->|No| M["Print: Failed to register<br/>Return"]
    end
    
    subgraph "Message Loop"
        L --> N["Create MSG struct"]
        N --> O{"_running<br/>is True?"}
        O -->|Yes| P["PeekMessageW(<br/>non-blocking check)"]
        P --> Q{Message<br/>Available?}
        Q -->|Yes| R{"msg.message ==<br/>WM_HOTKEY?"}
        Q -->|No| S["time.sleep(0.05)<br/>Prevent CPU spinning"]
        S --> O
        
        R -->|Yes| T{"msg.wParam ==<br/>hotkey_id?"}
        R -->|No| U["TranslateMessage()<br/>DispatchMessageW()"]
        U --> S
        
        T -->|Yes| V["Print: Alt+1 pressed<br/>globally"]
        V --> W["self.triggered.emit()<br/>Notify main thread"]
        W --> U
        T -->|No| U
    end
    
    subgraph "Stop Hotkey Listener"
        X["global_hotkey.stop()"] --> Y["_running = False"]
        Y --> Z["_thread.join(timeout=1)<br/>Wait for thread"]
        Z --> AA["UnregisterHotKey(<br/>None, hotkey_id)"]
        AA --> AB["Print: Hotkey stopped"]
    end
    
    subgraph "Main App Response"
        AC["triggered.connect(<br/>_manual_snapshot)"] --> AD["_manual_snapshot()<br/>Main Thread"]
        AD --> AE["Show visual feedback"]
        AE --> AF["Queue snapshot request"]
        AF --> AG["Start async processing"]
    end
    
    subgraph "Local Hotkey Fallback"
        AH["QShortcut setup"] --> AI["QShortcut(<br/>QKeySequence('Ctrl+1'),<br/>overlay)"]
        AI --> AJ["activated.connect(<br/>_manual_snapshot)"]
        AJ --> AK["Works when overlay<br/>has focus"]
    end
```

---

## 14. Session Logging

```mermaid
flowchart TD
    subgraph "Logger Initialization"
        A["BossDataLogger.__init__()<br/>data_dir='data/logs'"] --> B["self.data_dir.mkdir(<br/>parents=True,<br/>exist_ok=True)"]
        B --> C["_start_new_session()"]
    end
    
    subgraph "Start New Session"
        C --> D["timestamp = now().strftime(<br/>'%Y%m%d_%H%M%S')"]
        D --> E["current_session_file =<br/>boss_session_{timestamp}.json"]
        E --> F["Initialize session_data:<br/>• start_time: ISO format<br/>• boss_history: []<br/>• detections: []"]
        F --> G["Print: Started new session<br/>with filename"]
    end
    
    subgraph "Log Detection Event"
        H["log_detection(<br/>frame_count,<br/>bosses,<br/>raw_text)"] --> I["Create detection dict:<br/>• timestamp: now()<br/>• frame: frame_count<br/>• bosses_found: len(bosses)"]
        I --> J["Add boss_details:<br/>Full boss dicts"]
        J --> K["Add raw_text_sample:<br/>First 5 OCR results"]
        K --> L["Append to<br/>session_data['detections']"]
        L --> M["Loop through bosses"]
    end
    
    subgraph "Track Unique Bosses"
        M --> N{"boss_name in<br/>boss_history?"}
        N -->|No| O["Create entry:<br/>• name<br/>• first_seen<br/>• type<br/>• event_type"]
        O --> P["Append to<br/>boss_history"]
        N -->|Yes| Q["Skip (already tracked)"]
        P --> R["Continue loop"]
        Q --> R
    end
    
    subgraph "Save Session"
        S["save()"] --> T{"current_session_file?"}
        T -->|Yes| U["open(session_file, 'w')<br/>encoding='utf-8'"]
        U --> V["json.dump(<br/>session_data,<br/>ensure_ascii=False,<br/>indent=2)"]
        V --> W["Print: Saved session<br/>to {filepath}"]
        T -->|No| X["Skip (no session)"]
    end
    
    subgraph "Export TXT Report"
        Y["export_txt(filename=None)"] --> Z{"filename<br/>provided?"}
        Z -->|No| AA["Generate:<br/>boss_report_{timestamp}.txt"]
        Z -->|Yes| AB["Use provided name"]
        AA --> AC
        AB --> AC["Open txt file"]
    end
    
    subgraph "Write Report Content"
        AC --> AD["Write header:<br/>'=' * 50<br/>TOSM Boss Tracker Report<br/>'=' * 50"]
        AD --> AE["Write session info:<br/>• Start time<br/>• Total detections<br/>• Unique bosses"]
        AE --> AF{"boss_history<br/>not empty?"}
        AF -->|Yes| AG["Write boss list:<br/>For each boss:<br/>• Name<br/>• Type<br/>• Event type<br/>• First seen"]
        AF -->|No| AH["Skip boss section"]
        AG --> AI
        AH --> AI{"detections<br/>not empty?"}
        AI -->|Yes| AJ["Write recent detections:<br/>Last 10 entries<br/>• Timestamp<br/>• Frame number<br/>• Boss count<br/>• Boss names"]
        AI -->|No| AK["Skip detections"]
        AJ --> AL["Print: Exported report"]
        AK --> AL
        AL --> AM["Return filepath"]
    end
    
    subgraph "Get Session Summary"
        AN["get_session_summary()"] --> AO["Return dict:<br/>• start_time<br/>• total_detections<br/>• unique_bosses<br/>• recent_bosses"]
    end
```

---

## 15. Error Handling Workflow

```mermaid
flowchart TD
    subgraph "Error Classification"
        A["Exception Occurs"] --> B{Error Type}
        
        B -->|WindowCapture| C["Window Capture Errors:<br/>• Window not found<br/>• Window minimized<br/>• Windows API failure<br/>• Access denied"]
        
        B -->|VisionProcessing| D["Vision Processing Errors:<br/>• Gemini API error<br/>• Ollama connection failed<br/>• Rate limit exceeded<br/>• Quota exceeded<br/>• Invalid response format"]
        
        B -->|DataParsing| E["Data Parsing Errors:<br/>• JSON decode error<br/>• Missing required fields<br/>• Invalid boss name<br/>• Time format error"]
        
        B -->|FileIO| F["File I/O Errors:<br/>• Permission denied<br/>• Disk full<br/>• File locked<br/>• Corrupted JSON<br/>• Backup failure"]
        
        B -->|UI| G["UI Errors:<br/>• Qt widget error<br/>• StyleSheet parse error<br/>• Signal connection failed<br/>• Thread access violation"]
        
        B -->|Network| H["Network Errors:<br/>• Connection timeout<br/>• DNS resolution failed<br/>• SSL certificate error<br/>• Proxy error"]
    end
    
    subgraph "Window Capture Recovery"
        C --> C1["find_window()<br/>Retry detection"] --> C2{Window<br/>Found?}
        C2 -->|Yes| C3["Continue normally"]
        C2 -->|No| C4{"Retry count <<br/>max_retries?"}
        C4 -->|Yes| C5["Wait 2 seconds"] --> C1
        C4 -->|No| C6["Emit error signal:<br/>'Window not found'"] --> C7["Update status:<br/>'Check if game is running'"]
    end
    
    subgraph "AI Provider Recovery"
        D --> D1{Provider}
        D1 -->|Gemini| D2{"Error Type?"}
        D2 -->|Quota| D3["Print: 'Quota exceeded'"] --> D4["Try Ollama fallback<br/>if available"]
        D2 -->|Rate Limit| D5["Wait 5 seconds"] --> D6["Retry with backoff"]
        D2 -->|Auth| D7["Print: 'Invalid API key'"] --> D8["Disable Gemini<br/>Use Ollama only"]
        D2 -->|Network| D9["Retry 3 times"] --> D10{"Success?"}
        D10 -->|Yes| D11["Continue"]
        D10 -->|No| D4
        
        D1 -->|Ollama| D12{"Error Type?"}
        D12 -->|Connection| D13["Print: 'Ollama not running'"] --> D14["Check localhost:11434"]
        D12 -->|Timeout| D15["Increase timeout"] --> D16["Retry once"]
        D12 -->|Model| D17["Print: 'Model not found'"] --> D18["Suggest model pull"]
    end
    
    subgraph "Data Parsing Recovery"
        E --> E1{Error Type}
        E1 -->|JSON| E2["Print: 'Invalid JSON'"] --> E3["Try regex extraction"] --> E4{"Extracted<br/>valid JSON?"}
        E4 -->|Yes| E5["Continue with extracted"]
        E4 -->|No| E6["Log raw response<br/>for debugging"] --> E7["Return empty result"]
        
        E1 -->|Missing Fields| E8["Apply defaults:<br/>• name: 'Unknown'<br/>• map: '--'<br/>• status: 'N'"]
        E8 --> E9["Continue with defaults"]
        
        E1 -->|Time Format| E10["Try alternative parsers:<br/>• HH:MM:SS<br/>• HH:MM<br/>• Minutes only"]
        E10 --> E11{"Parse<br/>Success?"}
        E11 -->|Yes| E12["Use parsed value"]
        E11 -->|No| E13["Set countdown: ''<br/>status: 'N'"]
    end
    
    subgraph "File I/O Recovery"
        F --> F1{Error Type}
        F1 -->|Permission| F2["Try alternative path:<br/>• User home dir<br/>• Temp directory"]
        F2 --> F3{"Write<br/>Success?"}
        F3 -->|Yes| F4["Continue with new path"]
        F3 -->|No| F5["Print: 'Cannot write file'"] --> F6["Continue without saving"]
        
        F1 -->|Corrupted| F7["Load backup file:<br/>data_file.bak"]
        F7 --> F8{"Backup<br/>exists?"}
        F8 -->|Yes| F9["Restore from backup"]
        F8 -->|No| F10["Create new empty file"]
        
        F1 -->|Locked| F11["Wait 500ms"] --> F12["Retry write"] --> F13{"Success?"}
        F13 -->|Yes| F14["Continue"]
        F13 -->|No| F15["Skip this save<br/>Will retry next time"]
    end
    
    subgraph "Graceful Degradation"
        AllErrors["All Error Types"] --> RetryLogic{"Can<br/>Recover?"}
        RetryLogic -->|Yes| Recovery["Apply Recovery<br/>Action"]
        RetryLogic -->|No| Degrade["Graceful Degradation:<br/>• Disable feature<br/>• Use fallback<br/>• Inform user"]
        
        Recovery --> Monitor["Monitor for<br/>recurrence"]
        Degrade --> Monitor
        
        Monitor --> Log["Log error details:<br/>• Timestamp<br/>• Stack trace<br/>• Context<br/>• Recovery action"]
        
        Log --> Continue["Continue operation<br/>with reduced functionality<br/>if needed"]
    end
```

---

## 16. Graceful Shutdown Sequence

```mermaid
flowchart TD
    subgraph "Shutdown Triggers"
        A["Shutdown Initiated"] --> B{Trigger Source}
        B -->|User| C["Close button click<br/>on overlay window"]
        B -->|Signal| D["Ctrl+C pressed<br/>SIGINT received"]
        B -->|Error| E["Critical error<br/>requires restart"]
        B -->|System| F["Windows logout<br/>System shutdown"]
    end
    
    subgraph "Shutdown Entry"
        C --> G["_on_overlay_closed()"]
        D --> G
        E --> G
        F --> G
        G --> H["shutdown()<br/>Main method"]
    end
    
    subgraph "Shutdown Check"
        H --> I{"_shutdown_called?"}
        I -->|Yes| J["Already shutting down<br/>Return immediately"]
        I -->|No| K["_shutdown_called = True<br/>Prevent re-entry"]
    end
    
    subgraph "Phase 1: Stop Data Collection"
        K --> L["Print: 'Shutting down...'"]
        L --> M["Clear pending_requests<br/>Cancel queued snapshots"]
        M --> N{"Queue had<br/>items?"}
        N -->|Yes| O["Print: 'Cancelling N<br/>pending requests'"]
        N -->|No| P["Continue"]
    end
    
    subgraph "Phase 2: Stop Worker Thread"
        O --> Q
        P --> Q["Stop async worker:"]
        Q --> Q1["if worker_thread.isRunning():"]
        Q1 --> Q2["worker_thread.quit()<br/>Request termination"]
        Q2 --> Q3["worker_thread.wait()<br/>Wait for completion"]
    end
    
    subgraph "Phase 3: Stop Hotkey Listener"
        Q3 --> R["Stop global hotkey:<br/>global_hotkey.stop()"]
        R --> R1["Set _running = False"]
        R1 --> R2["UnregisterHotKey()<br/>Windows API"]
        R2 --> R3["Thread join with<br/>1 second timeout"]
    end
    
    subgraph "Phase 4: Disable File Watching"
        R3 --> S["Disable file watching:<br/>map_data_manager.disable_file_watching()"]
        S --> S1["Remove watcher paths"]
        S1 --> S2["_watching_enabled = False"]
    end
    
    subgraph "Phase 5: Save Final State"
        S2 --> T["UI State:<br/>overlay._save_ui_state()<br/>(if not already saved)"]
        
        T --> U{"Boss data<br/>changed?"}
        U -->|Yes| V["data_manager.save_data()<br/>Persist to JSON"]
        U -->|No| W["Skip boss data save"]
        
        V --> X["Session Logging:<br/>logger.save()"]
        W --> X
        
        X --> Y{"Session has<br/>detections?"}
        Y -->|Yes| Z["logger.export_txt()<br/>Generate human-readable report"]
        Y -->|No| AA["Skip report generation"]
        Z --> AB["Print: Report saved to<br/>{filepath}"]
    end
    
    subgraph "Phase 6: Resource Cleanup"
        AB --> AC
        AA --> AC["Resource cleanup:"]
        AC --> AC1["Release window handles"]
        AC1 --> AC2["Close file descriptors"]
        AC2 --> AC3["Free Qt resources"]
        AC3 --> AC4["Clear caches"]
    end
    
    subgraph "Phase 7: Exit Application"
        AC4 --> AD["app.quit()<br/>Exit Qt event loop"]
        AD --> AE["Print: 'Shutdown complete'"]
        AE --> AF(["Process Exit<br/>Return to OS"])
    end
    
    J --> AF
```

---

## 17. Module Interaction Diagram

```mermaid
graph TB
    subgraph "Entry Point"
        MAIN["main.py<br/>GameTrackerApp"]
    end
    
    subgraph "Core Processing Modules"
        CAPTURE["core/capture.py<br/>WindowCapture"]
        VISION["core/vision.py<br/>VisionProcessor"]
        AI_GEMINI["GeminiClient"]
        AI_OLLAMA["OllamaClient"]
    end
    
    subgraph "Data Management"
        DATA_MGR["core/data_manager.py<br/>BossDataManager"]
        MAP_MGR["core/data_manager.py<br/>MapDataManager"]
        LOGGER["core/logger.py<br/>BossDataLogger"]
        MAP_LEVEL["core/map_level.py<br/>Map/Boss Info"]
    end
    
    subgraph "User Interface"
        UI["core/ui.py<br/>OverlayWindow"]
        UI_COMP["UI Components:<br/>• BossRow<br/>• SortableHeaderButton<br/>• Filter Controls"]
    end
    
    subgraph "Utility"
        UTILS["utils/find_window.py<br/>Window Detection"]
    end
    
    subgraph "Data Files"
        BOSS_DATA[("boss_data.json<br/>Persistent boss records")]
        UI_STATE[("ui_state.json<br/>Window position,<br/>filters, sort")]
        MAP_JSON[("data/map.json<br/>Boss metadata")]
        SESSION_LOG[("data/logs/<br/>Session files")]
        CONFIG[("config/<br/>• gemini_api_key.txt<br/>• ollama_config.json")]
    end
    
    %% Main orchestration
    MAIN -->|initializes| CAPTURE
    MAIN -->|initializes| VISION
    MAIN -->|initializes| UI
    MAIN -->|initializes| DATA_MGR
    MAIN -->|initializes| MAP_MGR
    MAIN -->|initializes| LOGGER
    
    %% Vision processing
    MAIN -->|triggers| SNAPSHOT["SnapshotWorker<br/>(QThread)"]
    SNAPSHOT -->|calls| CAPTURE
    SNAPSHOT -->|calls| VISION
    CAPTURE -->|returns frame| VISION
    VISION -->|uses| AI_GEMINI
    VISION -->|uses| AI_OLLAMA
    VISION -->|looks up| MAP_LEVEL
    
    %% Data flow
    VISION -->|parsed results| MAIN
    MAIN -->|boss records| DATA_MGR
    MAIN -->|detection events| LOGGER
    MAIN -->|display data| UI
    
    %% Data manager operations
    DATA_MGR -->|reads/writes| BOSS_DATA
    MAP_MGR -->|reads/watches| MAP_JSON
    DATA_MGR -->|signals| MAIN
    MAP_MGR -->|signals| MAIN
    
    %% Logger
    LOGGER -->|writes| SESSION_LOG
    
    %% UI operations
    UI -->|loads/saves| UI_STATE
    UI -->|requests update| DATA_MGR
    UI -->|triggers| MAIN
    
    %% UI components
    UI -->|contains| UI_COMP
    UI_COMP -->|interacts| UI
    
    %% Map level
    MAP_LEVEL -->|reads| MAP_JSON
    VISION -->|queries| MAP_LEVEL
    
    %% Utilities
    CAPTURE -.->|uses| UTILS
    
    %% Configuration
    AI_GEMINI -.->|reads| CONFIG
    AI_OLLAMA -.->|reads| CONFIG
    
    %% File watching signals
    MAP_MGR -.->|data_changed| MAIN
    DATA_MGR -.->|data_changed| MAIN
    
    %% Hotkey
    MAIN -->|manages| HOTKEY["GlobalHotkey<br/>(Windows API)"]
    HOTKEY -->|signals| MAIN
    
    style MAIN fill:#4A5568,stroke:#F7FAFC,stroke-width:3px
    style UI fill:#2D3748,stroke:#63B3ED,stroke-width:2px
    style VISION fill:#2D3748,stroke:#9F7AEA,stroke-width:2px
    style DATA_MGR fill:#2D3748,stroke:#68D391,stroke-width:2px
```

---

## 18. Data Persistence Architecture

```mermaid
flowchart TD
    subgraph "Data Types"
        A["Application Data"] --> B["Boss Tracking Data<br/>Historical records"]
        A --> C["Session Data<br/>Temporary logs"]
        A --> D["UI State Data<br/>User preferences"]
        A --> E["Configuration Data<br/>API keys, settings"]
        A --> F["Map Metadata<br/>Boss information"]
    end
    
    subgraph "Storage Strategy"
        B --> B1["boss_data.json<br/>Persistent JSON storage"]
        B1 --> B2["Structure:<br/>• boss_name (key)<br/>• first_seen<br/>• last_updated<br/>• spawn_count<br/>• locations (dict)"]
        B2 --> B3["Location format:<br/>'{map}_{channel}'<br/>• map<br/>• channel<br/>• spawn_history[]"]
        B3 --> B4["History entry:<br/>• detected_at<br/>• time_left<br/>• spawn_time"]
        B4 --> B5["Max 10 records<br/>per location<br/>FIFO eviction"]
    end
    
    subgraph "Atomic Write Pattern"
        C1["Save Operation"] --> C2["1. Create backup:<br/>shutil.copy2(src, src.bak)"]
        C2 --> C3["2. Write to temp:<br/>file.json.tmp"]
        C3 --> C4["3. json.dump(data, f,<br/>indent=2,<br/>ensure_ascii=False)"]
        C4 --> C5["4. Atomic replace:<br/>temp.replace(original)"]
        C5 --> C6{"Success?"}
        C6 -->|Yes| C7["Return True"]
        C6 -->|No| C8["Return False<br/>Backup preserved"]
    end
    
    subgraph "Session Logging"
        D1["Session File:<br/>boss_session_YYYYMMDD_HHMMSS.json"] --> D2["Structure:<br/>• start_time<br/>• boss_history[]<br/>• detections[]"]
        D2 --> D3["Detection entry:<br/>• timestamp<br/>• frame<br/>• bosses_found<br/>• boss_details[]<br/>• raw_text_sample"]
        D3 --> D4["Auto-save on<br/>shutdown or<br/>periodic"]
    end
    
    subgraph "UI State Persistence"
        E1["ui_state.json"] --> E2["Saved on:<br/>• Window move<br/>• Window resize<br/>• Sort change<br/>• Filter change<br/>• Close"]
        E2 --> E3["Structure:<br/>• window_position [x, y]<br/>• window_size [w, h]<br/>• column_sort {col, dir}<br/>• filter_text<br/>• column_widths<br/>• window_maximized"]
    end
    
    subgraph "File Watching"
        F1["QFileSystemWatcher<br/>Setup"] --> F2["Watch:<br/>• data/map.json<br/>• boss_data.json"]
        F2 --> F3["Signals:<br/>fileChanged(path)"]
        F3 --> F4["Handler:<br/>_on_file_changed()"]
        F4 --> F5["Debounce:<br/>QTimer.singleShot(100ms)"]
        F5 --> F6["Compare old vs new<br/>Emit if changed"]
    end
    
    subgraph "Backup Strategy"
        G1["Automatic Backups"] --> G2["On every save:<br/>• .json → .json.bak"]
        G2 --> G3["Recovery:<br/>If .json corrupted,<br/>restore from .bak"]
        G3 --> G4["Graceful degradation:<br/>If both fail,<br/>create new empty"]
    end
```

---

## 19. Configuration Management

```mermaid
flowchart TD
    subgraph "Configuration Sources"
        A["Configuration Loading"] --> B["Priority Order:<br/>1. Environment Variables<br/>2. Config Files<br/>3. Default Values"]
        
        B --> C["Environment Variables:<br/>• GEMINI_API_KEY<br/>• USE_OLLAMA (true/false)"]
        
        B --> D["Config Files:<br/>• config/gemini_api_key.txt<br/>• config/ollama_config.json"]
        
        B --> E["Default Values:<br/>• Ollama: localhost:11434<br/>• Model: gemma4:e2b<br/>• Timeout: 30s"]
    end
    
    subgraph "Gemini API Key Loading"
        F["get_gemini_api_key()"] --> G{"GEMINI_API_KEY<br/>in environ?"}
        G -->|Yes| H["Return env value<br/>Print: 'Using from env'"]
        G -->|No| I["Check:<br/>config/gemini_api_key.txt"]
        I --> J{"File exists?"}
        J -->|Yes| K["Read file<br/>Strip whitespace"]
        K --> L{Content<br/>not empty?}
        L -->|Yes| M["Return key<br/>Print: 'Using from file'"]
        L -->|No| N["Print: 'No API key found'"]
        J -->|No| N
        N --> O["Return None<br/>Gemini disabled"]
    end
    
    subgraph "Ollama Config Loading"
        P["get_ollama_config()"] --> Q["default_config = {<br/>endpoint: 'http://localhost:11434',<br/>model: 'gemma4:e2b',<br/>timeout: 30}"]
        Q --> R{"config/ollama_config.json<br/>exists?"}
        R -->|Yes| S["json.load(config_file)"]
        S --> T["Merge with defaults:<br/>{**default, **loaded}"]
        T --> U["Print: 'Using config from file'"]
        R -->|No| V["Use defaults only<br/>Print: 'Using default config'"]
    end
    
    subgraph "Provider Preference"
        W["get_ai_provider_preference()"] --> X{"USE_OLLAMA<br/>in environ?"}
        X -->|Yes| Y{"Value in<br/>('true', '1', 'yes')?"}
        Y -->|Yes| Z["Return True<br/>Use Ollama"]
        Y -->|No| AA["Return False<br/>Use Gemini"]
        X -->|No| AB["Default: Ollama<br/>(current setting)"]
    end
    
    subgraph "Configuration Validation"
        AC["Validate Configurations"] --> AD{"Gemini API key<br/>valid?"}
        AD -->|Yes| AE["Initialize Gemini client"]
        AD -->|No| AF["Mark Gemini<br/>unavailable"]
        
        AE --> AG{"Ollama reachable?"}
        AF --> AG
        AG -->|Yes| AH["Initialize Ollama client"]
        AG -->|No| AI["Mark Ollama<br/>unavailable"]
        
        AH --> AJ{"At least one<br/>AI available?"}
        AI --> AJ
        AF --> AJ
        
        AJ -->|Yes| AK["Continue with<br/>available provider(s)"]
        AJ -->|No| AL["Show warning:<br/>'No AI provider available<br/>Vision processing disabled'"]
    end
```

---

## 20. Complete System Architecture

```mermaid
graph TB
    subgraph "User Layer"
        USER["👤 User<br/>• Game player<br/>• Alt+1 to scan<br/>• Drag to move<br/>• Close to exit"]
    end
    
    subgraph "Application Layer"
        APP["🎮 GameTrackerApp<br/>main.py"]
        HOTKEY["⌨️ GlobalHotkey<br/>Alt+1 handler"]
        WORKER["⚙️ SnapshotWorker<br/>QThread async"]
    end
    
    subgraph "Core Processing Layer"
        CAPTURE["📸 WindowCapture<br/>core/capture.py"]
        VISION["👁️ VisionProcessor<br/>core/vision.py"]
        
        subgraph "AI Providers"
            GEMINI["🤖 GeminiClient<br/>Google AI API"]
            OLLAMA["🦙 OllamaClient<br/>Local AI"]
        end
    end
    
    subgraph "Data Layer"
        BOSS_MGR["💾 BossDataManager<br/>Historical tracking"]
        MAP_MGR["🗺️ MapDataManager<br/>Real-time sync"]
        LOGGER["📝 BossDataLogger<br/>Session logging"]
        MAP_META["📋 MapLevel<br/>Metadata lookup"]
    end
    
    subgraph "UI Layer"
        OVERLAY["🪟 OverlayWindow<br/>core/ui.py"]
        
        subgraph "UI Components"
            HEADER["SortableHeaderButton<br/>Column sorting"]
            ROW["BossRow<br/>Individual entries"]
            FILTER["Filter Controls<br/>Search & filter"]
        end
    end
    
    subgraph "Persistence Layer"
        BOSS_DB[("boss_data.json<br/>Boss history<br/>Spawn tracking")]
        MAP_FILE[("data/map.json<br/>Boss metadata<br/>File watching")]
        UI_STATE[("ui_state.json<br/>Window settings<br/>User preferences")]
        LOG_DIR[("data/logs/<br/>Session files<br/>Reports")]
        CONFIG[("config/<br/>API keys<br/>Settings")]
    end
    
    subgraph "External Systems"
        GAME["🎲 TOSM Game Window<br/>Target for capture"]
        FILE_SYSTEM["💽 File System<br/>OS file watching"]
    end
    
    %% User interactions
    USER -->|Alt+1| HOTKEY
    USER -->|Close window| APP
    USER -->|Drag window| OVERLAY
    USER -->|Edit| MAP_FILE
    
    %% Application flow
    HOTKEY -->|triggered| APP
    APP -->|starts| WORKER
    APP -->|manages| OVERLAY
    
    %% Worker processing
    WORKER -->|capture| CAPTURE
    WORKER -->|analyze| VISION
    CAPTURE -->|frame| VISION
    CAPTURE -.->|find| GAME
    
    %% AI processing
    VISION -->|uses| GEMINI
    VISION -->|uses| OLLAMA
    VISION -->|lookup| MAP_META
    
    %% Data management
    APP -->|update| BOSS_MGR
    APP -->|sync| MAP_MGR
    APP -->|log| LOGGER
    VISION -.->|query| MAP_META
    
    %% File operations
    BOSS_MGR <-->|read/write| BOSS_DB
    MAP_MGR <-->|watch/read| MAP_FILE
    LOGGER -->|write| LOG_DIR
    OVERLAY <-->|load/save| UI_STATE
    
    %% File watching
    MAP_FILE -.->|change event| FILE_SYSTEM
    FILE_SYSTEM -.->|notify| MAP_MGR
    MAP_MGR -->|emit| APP
    
    %% UI updates
    APP -->|display| OVERLAY
    OVERLAY -->|contains| HEADER
    OVERLAY -->|contains| ROW
    OVERLAY -->|contains| FILTER
    
    %% Configuration
    GEMINI -.->|reads| CONFIG
    OLLAMA -.->|reads| CONFIG
    APP -.->|loads| CONFIG
    
    %% Style
    style USER fill:#4A5568,stroke:#F7FAFC,stroke-width:2px
    style APP fill:#2B6CB0,stroke:#90CDF4,stroke-width:2px
    style OVERLAY fill:#2C5282,stroke:#63B3ED,stroke-width:2px
    style VISION fill:#553C9A,stroke:#B794F4,stroke-width:2px
    style BOSS_MGR fill:#276749,stroke:#68D391,stroke-width:2px
    style BOSS_DB fill:#1A202C,stroke:#68D391,stroke-width:2px,color:#68D391
    style MAP_FILE fill:#1A202C,stroke:#63B3ED,stroke-width:2px,color:#63B3ED
    style GAME fill:#C53030,stroke:#FC8181,stroke-width:2px
```

---

## Summary

This comprehensive workflow documentation covers all major aspects of the TOSM Boss Tracker application:

### Key Architectural Decisions:

1. **Async Processing**: Snapshot processing runs in a separate QThread to prevent UI freezing during AI analysis
2. **Dual AI Provider Support**: Supports both Gemini (cloud) and Ollama (local) with automatic fallback
3. **Atomic File Writes**: All JSON writes use temp-file + atomic replace pattern for data integrity
4. **File System Watching**: Real-time synchronization with external edits to map.json
5. **Global Hotkeys**: Windows API integration allows hotkeys to work even when overlay doesn't have focus
6. **Graceful Degradation**: Application continues with reduced functionality if optional components fail

### Data Flow:

1. User triggers scan (Alt+1) → Global hotkey captures event
2. Async worker captures game screen and sends to AI
3. AI extracts boss information from image
4. Results parsed and validated
5. Data persisted to JSON with atomic writes
6. UI updated with new information
7. Session logged for review

### Error Handling Strategy:

- Retry with exponential backoff for transient failures
- Fallback to alternative providers when primary fails
- Graceful degradation rather than hard crashes
- Comprehensive logging for debugging
- User notification for actionable errors
