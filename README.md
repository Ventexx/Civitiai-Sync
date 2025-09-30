# Civitai Sync

A powerful command-line tool for syncing safetensor model metadata and preview images from Civitai.

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Getting Started](#getting-started)
   * [Prerequisites](#prerequisites)
   * [Installation](#installation)
   * [Uninstall](#uninstall)
4. [Command Line Options](#command-line-options)
5. [Usage](#usage)
   * [Basic Usage](#basic-usage)
   * [With API Key](#with-api-key)
   * [Save API Key](#save-api-key)
   * [Download Images](#download-images)
   * [List Not Found Files/Images](#list-not-found-filesimages)
   * [Rate Limiting](#rate-limiting)
6. [Contribution Guidelines](#contribution-guidelines)
7. [Contact](#contact)
8. [License](#license)


## Overview

Civitai Sync automatically detects `.safetensor(s)` files in your specified directory (including nested subdirectories), computes SHA256 hashes, fetches metadata from the Civitai API, and optionally downloads preview images. Metadata and previews are stored alongside each model file.

## Features

* 🔍 **Automatic Model Detection**: Recursively finds all `.safetensor` and `.safetensors` files.
* 🧮 **Hash Computation**: Computes SHA256 hashes for reliable model identification.
* 📊 **Metadata Sync**: Fetches detailed model information from Civitai.
* 🖼️ **Image Downloads**: Downloads preview images for your models.
* ⚡ **Smart Caching**: Skips re-processing files that haven't changed recently.
* 🔄 **Rate Limiting**: Built-in delay and exponential backoff to respect API limits.
* 🛡️ **Robust Error Handling**: Gracefully handles network errors and API failures.
* 🔧 **Configurable**: Customize rate limits, cache age, and more.

## Getting Started

### Prerequisites

* Python 3.8 or later
* `pip` package manager
* (Optional) A Civitai API key for enhanced features

### Installation

1. Clone this repository and navigate into it:

   ```
   git clone https://github.com/Ventexx/Civitiai-Sync.git
   cd civitai-sync
   ```

2. Standard Install (for end users):
   
    ```
    pip install .
    ```
    - Copies the package into your Python environment’s site-packages.
    - You can safely delete the repository afterward.
    - **API key location:**
        - Windows:
          
            ```
            C:\Users\<YourUsername>\.civitai-sync\config.json
            ```
        - macOS/Linux:
          
            ```
            ~/.civitai-sync/config.json
            ```

3. Development Install (for contributors):
   
    ```
    pip install -e .
    ```
    - Creates an editable link in site-packages pointing to your local code.
    - Changes in your working directory are reflected immediately.
    - Do not delete the repository when using editable mode.

### Uninstall
    ```
    pip uninstall civitai-sync
    ```

---

## Command Line Options

| Option | Description |
|--------|-------------|
| `folder_path` | Path to folder containing safetensor files |
| `--api-key` | Civitai API key for this session |
| `--save-api-key` | Save API key to local config |
| `--img, --images` | Download preview images |
| `--list, -l` | List all files that could not be found on Civitai |
| `--list-img, -li` | List all files that have no preview image |
| `--rate-limit` | Delay between API requests in seconds (default: 1.0) |
| `--verbose, -v` | Enable verbose logging |
| `--quiet, -q` | Suppress output except errors |


## Usage

### Basic Usage

Sync metadata for all safetensor files in a directory:

```
civitai-sync /path/to/your/models
```

### With API Key

For better rate limits and access to more features:

```
civitai-sync /path/to/your/models --api-key YOUR_API_KEY
```

### Save API Key

Save your API key for future use:

```
civitai-sync --save-api-key YOUR_API_KEY
```

### Download Images

Include preview images in the sync:

```
civitai-sync /path/to/your/models --images
```

### List Not Found Files/Images

Display all files that couldn't be found on Civitai and have no proper metadata:

```
civitai-sync /path/to/your/models --list
```


Display all files that don't have a corresponding preview image:

```
civitai-sync /path/to/your/models --list-img
```

These command works independently and cannot be combined with other processing options. They supports different output modes:

- **Standard output**: Clean list with relative paths and totals
- **Quiet mode** (`-q`): Only essential file paths for scripting
- **Verbose mode** (`-v`): File tree structure showing directory hierarchy

### Rate Limiting

Control the delay between API requests to respect Civitai's rate limits:

```
civitai-sync /path/to/your/models --rate-limit 2.0 
```

---

## Contribution Guidelines

Your contributions are welcome!

[Conventional Commits](https://www.conventionalcommits.org/)


## Contact

* **Maintainer**: Ventexx ([enquiry.kimventex@outlook.com](mailto:enquiry.kimventex@outlook.com))

## License

This work is licensed under a
[Creative Commons Attribution-NonCommercial 4.0 International License](LICENSE).

You may use, modify, and share this software for non-commercial purposes, provided that appropriate credit is given.

Disclaimer: This software is provided "as is", without warranty of any kind. The author is not liable for any damages or issues arising from its use.
