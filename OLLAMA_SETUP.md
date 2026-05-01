# Ollama Integration Setup

This document explains how to set up and use Ollama as a local AI provider for the TOSM Boss Tracker.

## What is Ollama?

Ollama is a local AI server that allows you to run AI models on your own machine. This provides:
- **Privacy**: Your images never leave your computer
- **Cost savings**: No API calls to paid services
- **Offline capability**: Works without internet connection
- **Speed**: Faster processing on local hardware

## Prerequisites

1. **Install Ollama**:
   ```bash
   # Download and install from https://ollama.ai/
   # Or use package manager:
   # Windows: Download installer from ollama.ai
   # Linux/Mac: curl -fsSL https://ollama.ai/install.sh | sh
   ```

2. **Pull the required model**:
   ```bash
   ollama pull gemma4:e2b
   ```

3. **Start Ollama server**:
   ```bash
   ollama serve
   ```
   The server will run on `http://localhost:11434` by default.

## Configuration

The Ollama configuration is stored in `config/ollama_config.txt`:

```json
{
  "endpoint": "http://localhost:11434",
  "model": "gemma4:e2b",
  "timeout": 30
}
```

- `endpoint`: Ollama server URL (usually localhost:11434)
- `model`: AI model to use (gemma4:e2b recommended)
- `timeout`: Request timeout in seconds

## Usage

### Method 1: Environment Variable (Recommended)
Set the environment variable before running the application:
```bash
# Windows
set USE_OLLAMA=true
python main.py

# Linux/Mac
export USE_OLLAMA=true
python main.py
```

### Method 2: Modify Configuration
Edit `get_ai_provider_preference()` in `main.py` to return `True` for Ollama.

## Features

### Dual Provider Support
- **Gemini**: Cloud-based AI (requires API key)
- **Ollama**: Local AI (requires Ollama server)

### Provider Switching
The application supports switching between providers at runtime:
```python
# In code
vision_processor.switch_provider(use_ollama=True)  # Switch to Ollama
vision_processor.switch_provider(use_ollama=False) # Switch to Gemini
```

### Statistics Tracking
Both providers track usage separately:
- **Gemini**: Token counts, API calls
- **Ollama**: Request counts, success rates

## Troubleshooting

### Common Issues

1. **"Ollama client not initialized"**
   - Make sure Ollama server is running: `ollama serve`
   - Check if server is accessible: `curl http://localhost:11434/api/tags`

2. **"Model not found"**
   - Pull the required model: `ollama pull gemma4:e2b`
   - Check available models: `ollama list`

3. **Connection timeout**
   - Increase timeout in `config/ollama_config.txt`
   - Check if Ollama server is responsive

4. **Memory issues**
   - Ollama requires sufficient RAM for the model
   - gemma4:e2b requires at least 8GB RAM recommended

### Testing

Run the test scripts to verify setup:
```bash
# Test Ollama connection
python test_ollama_integration.py

# Test dual provider functionality
python test_dual_ai_providers.py
```

## Performance Tips

1. **Hardware**: Use a machine with adequate RAM (8GB+ recommended)
2. **Model**: gemma4:e2b provides good balance of speed and accuracy
3. **Server**: Keep Ollama server running for faster subsequent requests

## Comparison: Ollama vs Gemini

| Feature | Ollama (Local) | Gemini (Cloud) |
|---------|-----------------|----------------|
| Privacy | ✅ 100% private | ❌ Data sent to Google |
| Cost | ✅ Free after setup | ❌ Pay per API call |
| Speed | ⚡ Fast (local) | 🌐 Depends on internet |
| Quality | 🎯 Good | 🎯 Excellent |
| Setup | 🔧 Requires setup | ✅ Just API key |
| Offline | ✅ Works offline | ❌ Requires internet |

## Next Steps

1. Install Ollama and pull the model
2. Test with the provided test scripts
3. Set USE_OLLAMA=true environment variable
4. Run the main application
5. Enjoy local AI processing!
