# Civitai Sync

A powerful command-line tool for syncing safetensor model metadata and preview images from Civitai.

## Features

- 🔍 **Automatic Model Detection**: Finds all safetensor files in your directory
- 🧮 **Hash Computation**: Computes SHA256 hashes for model identification
- 📊 **Metadata Sync**: Fetches detailed model information from Civitai
- 🖼️ **Image Downloads**: Downloads preview images for your models
- ⚡ **Smart Caching**: Avoids re-processing files that haven't changed
- 🔄 **Rate Limiting**: Built-in rate limiting with exponential backoff
- 🛡️ **Robust Error Handling**: Handles network issues and API failures gracefully
- 🔧 **Configurable**: Flexible configuration options

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd civitai-sync
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Make the script executable (optional):
```bash
chmod +x main.py
```

## Usage

### Basic Usage

Sync metadata for all safetensor files in a directory:
```bash
python main.py /path/to/your/models
```

### With API Key

For better rate limits and access to more features, use your Civitai API key:
```bash
python main.py /path/to/your/models --api-key YOUR_API_KEY
```

### Save API Key

Save your API key for future use:
```bash
python main.py --save-api-key YOUR_API_KEY
```

### Download Images

Download preview images along with metadata:
```bash
python main.py /path/to/your/models --img
```

### Advanced Options

```bash
python main.py /path/to/your/models \
  --api-key YOUR_API_KEY \
  --img \
  --rate-limit 2.0 \
  --refresh-metadata \
  --max-age 7 \
  --verbose
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `folder_path` | Path to folder containing safetensor files |
| `--api-key` | Civitai API key for this session |
| `--save-api-key` | Save API key to local config |
| `--img, --images` | Download preview images |
| `--rate-limit` | Delay between API requests in seconds (default: 1.0) |
| `--refresh-metadata` | Refresh metadata even if recent |
| `--max-age` | Max age of metadata in days before refresh (default: 30) |
| `--verbose, -v` | Enable verbose logging |
| `--quiet, -q` | Suppress output except errors |

## File Structure

The tool creates the following files alongside your safetensor files:

- `model.safetensors` - Your original model file
- `model.json` - Metadata including hash and Civitai information
- `model.preview.png` - Preview image (if `--img` is used)

## Configuration

The tool stores configuration in `~/.civitai-sync/config.json`, including:
- Saved API key
- User preferences
- Cache settings

