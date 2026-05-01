#!/usr/bin/env python3
"""Test script for Ollama integration."""

import sys
import os
import json

# Add the project root to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.vision import OllamaClient

def test_ollama_connection():
    """Test basic Ollama connection and model availability."""
    print("Testing Ollama integration...")
    
    # Load Ollama config
    config_path = os.path.join("config", "ollama_config.txt")
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            config = json.load(f)
        print(f"Loaded config: {config}")
    else:
        print("No config found, using defaults")
        config = {
            "endpoint": "http://localhost:11434",
            "model": "gemma4:e2b",
            "timeout": 30
        }
    
    # Initialize Ollama client
    client = OllamaClient(config)
    
    # Test initialization
    if client.initialize():
        print("✓ Ollama client initialized successfully")
        
        # Test a simple text prompt (no image)
        try:
            response, token_usage = client.analyze_image(None, "What is 2+2? Just give the number.")
            if response and "4" in response:
                print("✓ Basic text test passed")
                print(f"Response: {response[:100]}...")
            else:
                print("✗ Basic text test failed")
                print(f"Response: {response}")
        except Exception as e:
            print(f"✗ Text test error: {e}")
    else:
        print("✗ Failed to initialize Ollama client")
        print("Make sure Ollama server is running with: ollama serve")
        print("And the model is available: ollama pull gemma4:e2b")

if __name__ == "__main__":
    test_ollama_connection()
