"""Vision processing module using Gemini API for image analysis."""

import json
import cv2
import numpy as np
from datetime import datetime
from typing import List, Tuple, Dict, Any, Optional
from .map_level import get_boss_info
from .logger import BossDataLogger


class VisionProcessor:
    """Processes captured frames to extract boss information using Gemini API."""

    def __init__(self, gemini_api_key: str = None, ollama_config: dict = None, use_ollama: bool = False):
        # Global state for persistence
        self.last_channel = "--"
        self.last_map = "--"
        
        # Provider selection
        self.use_ollama = use_ollama
        self.active_provider = "ollama" if use_ollama else "gemini"
        
        # Initialize logger for API responses
        self.api_logger = BossDataLogger()
        
        # Token tracking for both providers
        self.gemini_tokens = {
            'total_prompt_tokens': 0,
            'total_candidates_tokens': 0,
            'total_api_calls': 0
        }
        self.ollama_stats = {
            'total_requests': 0,
            'successful_requests': 0
        }
        
        # Initialize AI clients
        self.gemini = GeminiClient(gemini_api_key, self.api_logger)
        self.ollama = OllamaClient(ollama_config, self.api_logger)
        
        # Initialize selected provider
        if use_ollama:
            if self.ollama.initialize():
                print("[Vision] Using Ollama as AI provider")
            else:
                print("[Vision] Ollama initialization failed, falling back to Gemini")
                self.use_ollama = False
                self.active_provider = "gemini"
                if gemini_api_key:
                    self.gemini.initialize()
                else:
                    print("[Vision] Warning: No Gemini API key provided")
        else:
            if gemini_api_key:
                self.gemini.initialize()
                print("[Vision] Using Gemini as AI provider")
            else:
                print("[Vision] Warning: No Gemini API key provided")

    def _get_boss_panel_region(self, frame: np.ndarray) -> Tuple[int, int, int, int]:
        """Extract the boss panel region from the right side of screen."""
        h, w = frame.shape[:2]
        # Map/Channel info is usually at top right corner
        # Boss panel is usually on the right side
        panel_width = int(w * 0.40)  # Reduce from 0.45 to save CPU
        panel_height = int(h * 0.70)  # Reduce from 0.8
        x1 = w - panel_width
        y1 = 0 # Start from very top to get Channel info
        return (x1, y1, panel_width, panel_height)

    def _extract_boss_panel(self, frame: np.ndarray) -> np.ndarray:
        """Crop the boss panel region from the frame."""
        x, y, w, h = self._get_boss_panel_region(frame)
        return frame[y:y+h, x:x+w]
    
    def _enhance_for_api(self, image: np.ndarray) -> np.ndarray:
        """Enhance image for better API analysis."""
        # Convert to RGB for API
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Resize to reasonable size for API (reduce bandwidth)
        h, w = rgb_image.shape[:2]
        max_dim = 1024
        if max(h, w) > max_dim:
            scale = max_dim / max(h, w)
            new_w = int(w * scale)
            new_h = int(h * scale)
            rgb_image = cv2.resize(rgb_image, (new_w, new_h), interpolation=cv2.INTER_AREA)
        
        return rgb_image

    def _update_token_stats(self, token_usage, provider: str = None):
        """Update cumulative token statistics for the appropriate provider."""
        provider = provider or self.active_provider
        
        if provider == "gemini" and token_usage:
            self.gemini_tokens['total_prompt_tokens'] += token_usage['prompt_tokens']
            self.gemini_tokens['total_candidates_tokens'] += token_usage['candidates_tokens']
            self.gemini_tokens['total_api_calls'] += 1
            
            print(f"[Vision] Gemini tokens - Input: {self.gemini_tokens['total_prompt_tokens']}, Output: {self.gemini_tokens['total_candidates_tokens']}, Calls: {self.gemini_tokens['total_api_calls']}")
        elif provider == "ollama":
            self.ollama_stats['total_requests'] += 1
            if token_usage is not None:  # token_usage is None for successful Ollama calls
                self.ollama_stats['successful_requests'] += 1
            print(f"[Vision] Ollama requests - Total: {self.ollama_stats['total_requests']}, Successful: {self.ollama_stats['successful_requests']}")

    def get_token_stats(self) -> Dict[str, Any]:
        """Get cumulative statistics for all providers."""
        gemini_total = self.gemini_tokens['total_prompt_tokens'] + self.gemini_tokens['total_candidates_tokens']
        
        return {
            'active_provider': self.active_provider,
            'gemini': {
                'total_prompt_tokens': self.gemini_tokens['total_prompt_tokens'],
                'total_candidates_tokens': self.gemini_tokens['total_candidates_tokens'],
                'total_api_calls': self.gemini_tokens['total_api_calls'],
                'total_tokens': gemini_total
            },
            'ollama': {
                'total_requests': self.ollama_stats['total_requests'],
                'successful_requests': self.ollama_stats['successful_requests']
            }
        }

    def switch_provider(self, use_ollama: bool = None):
        """Switch between AI providers."""
        if use_ollama is None:
            # Toggle current provider
            use_ollama = not self.use_ollama
        
        if use_ollama == self.use_ollama:
            print(f"[Vision] Already using {'Ollama' if use_ollama else 'Gemini'}")
            return
        
        # Try to switch
        if use_ollama and self.ollama._initialized:
            self.use_ollama = True
            self.active_provider = "ollama"
            print("[Vision] Switched to Ollama provider")
        elif not use_ollama and self.gemini._initialized:
            self.use_ollama = False
            self.active_provider = "gemini"
            print("[Vision] Switched to Gemini provider")
        else:
            target_provider = "Ollama" if use_ollama else "Gemini"
            print(f"[Vision] Cannot switch to {target_provider} - not initialized")

    def _parse_ai_response(self, response: str, provider: str = None) -> List[Dict[str, Any]]:
        """Parse AI response from either Gemini or Ollama to extract boss information."""
        provider = provider or self.active_provider
        print(f"[Vision] Parsing response from {provider}")
        
        bosses = []
        
        # Handle None or empty response
        if not response:
            print(f"[Vision] Empty response from {provider}")
            return bosses
        
        # Strip whitespace and check again
        response = response.strip()
        if not response:
            print(f"[Vision] Empty response after stripping from {provider}")
            return bosses
        
        # Log first 100 chars for debugging
        preview = response[:100].replace('\n', '\\n')
        print(f"[Vision] Response preview from {provider}: '{preview}...'")
        
        # Check if response is an error message
        if response.startswith(f"{provider.capitalize()} API error:") or "exceeded your current quota" in response or "quota exceeded" in response.lower():
            print(f"[Vision] API error response detected from {provider}")
            return bosses
            
        # Check for markdown code blocks and extract JSON
        if "```json" in response:
            try:
                start = response.find("```json") + 7
                end = response.find("```", start)
                if end > start:
                    response = response[start:end].strip()
                    print(f"[Vision] Extracted JSON from ```json block from {provider}")
            except:
                pass
        elif "```" in response:
            try:
                start = response.find("```") + 3
                end = response.find("```", start)
                if end > start:
                    response = response[start:end].strip()
                    print(f"[Vision] Extracted JSON from ``` block from {provider}")
            except:
                pass
        
        # Try to find JSON object in the response using regex
        if not response.startswith('{'):
            import re
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                extracted = json_match.group(0).strip()
                # Validate that extracted content looks like JSON
                if extracted and extracted.startswith('{') and len(extracted) > 10:
                    response = extracted
                    print(f"[Vision] Extracted JSON object using regex from {provider} ({len(response)} chars)")
                else:
                    print(f"[Vision] Regex match from {provider} is not valid JSON: '{extracted[:50]}...'")
                    return bosses
            else:
                print(f"[Vision] No JSON object found in response from {provider}")
                return bosses
        
        # Final validation before parsing
        if not response or len(response) < 2:
            print(f"[Vision] Response from {provider} too short to be valid JSON: '{response}'")
            return bosses
        
        if not response.startswith('{'):
            print(f"[Vision] Response from {provider} doesn't start with '{{': '{response[:50]}...'")
            return bosses
            
        try:
            # Try to parse as JSON directly
            print(f"[Vision] Attempting to parse JSON from {provider} ({len(response)} chars)...")
            data = json.loads(response)
            print(f"[Vision] JSON parsed successfully from {provider}")
            
            # Check if this is the new format (direct boss fields) or old format (bosses array)
            if "boss_name" in data:
                # New format: {boss_name, boss_type, channel, current_status, time_until_spawn, etc.}
                print(f"[Vision] Detected new format response with boss_name from {provider}")
                
                boss_name = data.get("boss_name", "")
                if boss_name:
                    # Lookup map, lv, type from map.json using boss name
                    lookup_map, lookup_lv, lookup_type = get_boss_info(boss_name)
                    
                    # Parse status from current_status
                    current_status = data.get("current_status", "")
                    status = "N"  # default
                    countdown = ""
                    
                    if current_status == "WAITING_FOR_SPAWN" or current_status == "BOSS_ACTIVE_VANISHING_SOON":
                        status = "N"
                        countdown = data.get("time", "")
                    elif current_status.startswith("LV_") or current_status.startswith("ACTIVITY_LEVEL_"):
                        # Extract level number
                        import re
                        level_match = re.search(r'(\d+)', current_status)
                        if level_match:
                            status = f"LV{level_match.group(1)}"
                        else:
                            status = "LV1"
                    elif current_status == "Active":
                        status = "Active"
                        countdown = data.get("time", "")
                    
                    # Use boss_type from API if available, otherwise use lookup
                    boss_type = data.get("boss_type", "")
                    if boss_type and "Type" in boss_type:
                        # Remove " Type" suffix if present (e.g., "Demon Type" -> "Demon")
                        boss_type = boss_type.replace(" Type", "").strip()
                    elif not boss_type:
                        boss_type = lookup_type
                    
                    boss_data = {
                        "name": boss_name,
                        "channel": data.get("channel", "--"),
                        "map": lookup_map,  # Use lookup map from JSON
                        "type": boss_type,
                        "status": status,
                        "countdown": countdown,
                        "phase": 0
                    }
                    bosses.append(boss_data)
                    print(f"[Vision] Parsed boss from new format from {provider}: {boss_name} @ {boss_data['channel']} [{status}]")
                    
            elif "bosses" in data:
                # Old format with bosses array
                print(f"[Vision] Detected old format with {len(data.get('bosses', []))} bosses from {provider}")
                
                # Get global channel and map from response
                global_channel = data.get("channel", "--")
                global_map = data.get("map", "--")
                
                # Update stored values
                if global_channel:
                    self.last_channel = global_channel
                if global_map:
                    self.last_map = global_map
                
                # Extract boss data - ensure channel is set for each boss
                for boss in data.get("bosses", []):
                    # Get boss map - use last_map only if key missing, preserve null if explicitly null
                    boss_map = boss.get("map")
                    if boss_map is None and "map" not in boss:
                        boss_map = self.last_map
                    
                    boss_data = {
                        "name": boss.get("name", ""),
                        "channel": boss.get("channel") if boss.get("channel") else self.last_channel,
                        "map": boss_map,
                        "type": boss.get("type", ""),
                        "status": boss.get("status", "N"),
                        "countdown": boss.get("countdown", ""),
                        "phase": boss.get("phase", 0)
                    }
                    if boss_data["name"]:
                        bosses.append(boss_data)
                    
        except json.JSONDecodeError as e:
            print(f"[Vision] Failed to parse {provider} response as JSON: {e}")
            print(f"[Vision] Response content from {provider} (first 500 chars): '{response[:500]}...'")
        except Exception as e:
            print(f"[Vision] Error parsing {provider} response: {e}")
        
        return bosses

    def _parse_gemini_response(self, response: str) -> List[Dict[str, Any]]:
        """Legacy method for backward compatibility - redirects to _parse_ai_response."""
        return self._parse_ai_response(response, "gemini")

    def process(self, frame: np.ndarray) -> Dict[str, Any]:
        """Process a frame using selected AI provider to extract boss information."""
        results = {
            "bosses": [],
            "raw_text": [],
            "timestamp": datetime.now().isoformat(),
            "ai_analysis": "",
            "provider": self.active_provider
        }
        
        # Check if the selected provider is initialized
        if self.active_provider == "gemini" and not self.gemini._initialized:
            return {"error": "Gemini API not initialized", "bosses": []}
        elif self.active_provider == "ollama" and not self.ollama._initialized:
            return {"error": "Ollama client not initialized", "bosses": []}

        try:
            # 1. Extract boss panel
            boss_panel = self._extract_boss_panel(frame)
            if boss_panel.size == 0:
                return results

            # 2. Enhance and prepare image for API
            api_image = self._enhance_for_api(boss_panel)
            
            # 3. Send to selected AI provider with structured prompt
            prompt = """
Extract MMORPG Field Boss data from the image and output ONLY raw JSON.

Extraction Rules:
- boss_name: string
- channel: string (e.g., "CH. 3")
- current_status: Determine strictly based on Thai text in the image:
  * If "กำลังรอ กิจกรรม Field" + timer -> "WAITING_FOR_SPAWN"
  * If "กิจกรรม Field ระดับ [X]" (no timer) -> "LV_[X]"
  * If "เปิดใช้งานกิจกรรม Field" or "กิจกรรม Field เปิดใช้งานแล้ว" + timer -> "BOSS_ACTIVE_VANISHING_SOON"
- time: Extract timer (e.g., "03:37") ONLY if status is WAITING_FOR_SPAWN or BOSS_ACTIVE_VANISHING_SOON. Omit otherwise.
- current_activity_level: Extract integer X (1-4) ONLY if status is LV_[X]. Omit otherwise.

Example JSON:
{
  "boss_name": "Indignant Nebulas",
  "channel": "CH. 3",
  "current_status": "WAITING_FOR_SPAWN",
  "time": "03:37"
}"""
            
            print(f"[Vision] Sending image to {self.active_provider} API...")
            
            # Send to selected provider
            if self.active_provider == "gemini":
                ai_response, token_usage = self.gemini.analyze_image(api_image, prompt)
            else:  # ollama
                ai_response, token_usage = self.ollama.analyze_image(api_image, prompt)
            
            results["ai_analysis"] = ai_response
            results["token_usage"] = token_usage  # Add token usage to results
            
            # 4. Parse the response
            bosses = self._parse_ai_response(ai_response, self.active_provider)
            results["bosses"] = bosses
            
            # Update token statistics
            self._update_token_stats(token_usage, self.active_provider)
            
            if bosses:
                print(f"[Vision] Detected {len(bosses)} boss(es) via {self.active_provider} API")
                for boss in bosses:
                    print(f"  - {boss['name']} @ {boss['channel']} [{boss['status']}]")

        except Exception as e:
            print(f"[Vision] Error processing frame: {e}")
            import traceback
            traceback.print_exc()

        return results


class OllamaClient:
    """Client for sending images to local Ollama server for AI analysis."""
    
    def __init__(self, config: dict = None, api_logger = None):
        self.config = config or {
            "endpoint": "http://localhost:11434",
            "model": "gemma4:e2b",
            "timeout": 30
        }
        self.api_logger = api_logger
        self._initialized = True
        
    def initialize(self) -> bool:
        """Initialize the Ollama client by checking server availability."""
        try:
            import requests
            
            # Check if Ollama server is running
            response = requests.get(f"{self.config['endpoint']}/api/tags", timeout=5)
            if response.status_code == 200:
                # Check if the specified model is available
                models = response.json().get('models', [])
                model_available = any(self.config['model'] in model.get('name', '') for model in models)
                
                if not model_available:
                    print(f"[Ollama] Model '{self.config['model']}' not found. Available models: {[m.get('name') for m in models]}")
                    return False
                
                self._initialized = True
                print(f"[Ollama] Client initialized successfully with model '{self.config['model']}'")
                return True
            else:
                print(f"[Ollama] Server returned status {response.status_code}")
                return False
                
        except Exception as e:
            print(f"[Ollama] Failed to initialize: {e}")
            print("[Ollama] Make sure Ollama server is running with: ollama serve")
            return False
    
    def analyze_image(self, image: np.ndarray, prompt: str = None) -> str:
        """Send image to Ollama API for analysis."""
        if not self._initialized:
            return "Ollama client not initialized"
            
        try:
            import requests
            import base64
            from PIL import Image as PILImage
            import io
            
            # Prepare the request payload
            payload = {
                "model": self.config['model'],
                "prompt": prompt,
                "stream": False
            }
            
            # Add image if provided
            if image is not None:
                # Convert numpy array to PIL Image
                pil_image = PILImage.fromarray(image)
                
                # Convert image to base64
                buffer = io.BytesIO()
                pil_image.save(buffer, format='PNG')
                image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
                payload["images"] = [image_base64]
            
            # Default prompt for boss analysis (only if no prompt provided and no image)
            if not prompt and image is None:
                prompt = "What is 2+2? Just give the number."
                payload["prompt"] = prompt
            
            # Default prompt for boss analysis (if image provided but no prompt)
            elif not prompt and image is not None:
                prompt = """Analyze this game screenshot and identify any boss information.
                Look for:
                - Boss names
                - Channel numbers (CH.1, CH.2, etc.)
                - Status information (spawning, active, waiting)
                - Countdown timers
                - Phase numbers
                - Map names
                
                Return the information in a structured format with clear labels."""
                payload["prompt"] = prompt
            
            # Send request to Ollama API
            response = requests.post(
                f"{self.config['endpoint']}/api/generate",
                json=payload,
                timeout=self.config.get('timeout', 30)
            )
            
            if response.status_code == 200:
                result = response.json()
                analysis = result.get('response', '')
                
                if analysis:
                    print(f"[Ollama] Analysis completed: {len(analysis)} characters")
                    # Log API response
                    self.api_logger.log_api_response("ollama", analysis, None)
                    # Ollama doesn't provide token usage like Gemini, so return None
                    return analysis, None
                else:
                    error_msg = "Ollama API error: Empty response"
                    self.api_logger.log_api_response("ollama", "", None, error_msg)
                    return error_msg, None
            else:
                error_msg = f"Ollama API error: HTTP {response.status_code} - {response.text}"
                print(f"[Ollama] {error_msg}")
                self.api_logger.log_api_response("ollama", "", None, error_msg)
                return error_msg, None
            
        except Exception as e:
            error_msg = f"Ollama API error: {e}"
            print(f"[Ollama] {error_msg}")
            if self.api_logger:
                self.api_logger.log_api_response("ollama", "", None, error_msg)
            return error_msg, None


class GeminiClient:
    """Client for sending images to Google Gemini API for AI analysis."""
    
    def __init__(self, api_key: str = None, api_logger = None):
        self.api_key = api_key
        self.api_logger = api_logger
        self._model = None
        self._initialized = False
        
    def initialize(self) -> bool:
        """Initialize the Gemini API client."""
        if not self.api_key:
            print("[Gemini] No API key provided - Gemini integration disabled")
            return False
            
        try:
            import google.generativeai as genai
            genai.configure(api_key=self.api_key)
            self._model = genai.GenerativeModel('gemini-2.5-flash-lite')
            # self._model = genai.GenerativeModel('gemma-4-e2b-it')
            self._initialized = True
            print("[Gemini] API client initialized successfully")
            return True
        except Exception as e:
            print(f"[Gemini] Failed to initialize: {e}")
            return False
    
    def analyze_image(self, image: np.ndarray, prompt: str = None) -> str:
        """Send image to Gemini API for analysis."""
        if not self._initialized or not self._model:
            return "Gemini API not initialized"
            
        try:
            from PIL import Image as PILImage
            
            # Image is already RGB from _enhance_for_api
            pil_image = PILImage.fromarray(image)
            
            # Default prompt for boss analysis
            if not prompt:
                prompt = """Analyze this game screenshot and identify any boss information.
                Look for:
                - Boss names
                - Channel numbers (CH.1, CH.2, etc.)
                - Status information (spawning, active, waiting)
                - Countdown timers
                - Phase numbers
                - Map names
                
                Return the information in a structured format with clear labels."""
            
            # Send to Gemini API
            response = self._model.generate_content([prompt, pil_image])
            
            # Handle cases where response or response.text is None/empty
            if response is None:
                error_msg = "Gemini API error: Empty response from API"
                if self.api_logger:
                    self.api_logger.log_api_response("gemini", "", None, error_msg)
                return error_msg, None
            
            result = response.text
            if result is None or result.strip() == "":
                error_msg = "Gemini API error: Empty response text from API"
                if self.api_logger:
                    self.api_logger.log_api_response("gemini", "", None, error_msg)
                return error_msg, None
            
            # Extract token usage metadata
            token_usage = None
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                token_usage = {
                    'prompt_tokens': response.usage_metadata.prompt_token_count,
                    'candidates_tokens': response.usage_metadata.candidates_token_count,
                    'total_tokens': response.usage_metadata.total_token_count
                }
                print(f"[Gemini] Token usage - Input: {token_usage['prompt_tokens']}, Output: {token_usage['candidates_tokens']}, Total: {token_usage['total_tokens']}")
            
            print(f"[Gemini] Analysis completed: {len(result)} characters")
            
            # Log API response
            if self.api_logger:
                self.api_logger.log_api_response("gemini", result, token_usage)
            
            return result, token_usage
            
        except Exception as e:
            error_msg = f"Gemini API error: {e}"
            print(f"[Gemini] {error_msg}")
            if self.api_logger:
                self.api_logger.log_api_response("gemini", "", None, error_msg)
            return error_msg, None
