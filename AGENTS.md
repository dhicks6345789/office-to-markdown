# Repository Guidelines for AI Agents

## Overview
This repository contains a Python-based document transforms pipeline. The core script (`scanFolders.py`) recursively scans a directory tree, matches target sub-folders by specific (Python) Regular Expression (RE) strings, and delegates processing to modular transformation sub-scripts.

The directory tree to be scanned should look and act like a standard filesystem directory. However, it is assumed that this project will be used extensively with cloud-based filesystems (Google Drive, Microsoft OneDrive, Dropbox, etc), with folders from those filesystems mounted as part of the local directory structure. In particular, on Linux systems cloud-based filesystems might be mounted using the rclone utility. This might affect performance (file read/write times) and the filesystem features that can be supported.

## Architecture Pattern
1. **Core Orchestrator (`scanFolders.py`)**: Walks the filesystem recursively, evaluates folder paths against match strings, and invokes the appropriate transformer script.
2. **Transformers (various scripts / folders in the repository root)**: Modular sub-scripts responsible for converting specific document types into web pages (e.g., Markdown, HTML).

## How Sub-Scripts Work (The Plugin Pattern)
Every transformer sub-script must adhere to a strict interface contract so the main scanner can invoke it via CLI subprocesses. Sub-scripts do not have to be written in Python, they can be in any language.



### Sub-Script Contract Rules
If you are creating a new transformation sub-script:
- **Trigger Pattern**: Define the folder naming or path-matching pattern the sub-script handles (e.g., folders containing `[type-pdf]` or matching a specific naming convention).
- **Entry Point**: The script must accept a `--folder-path` parameter (or standard CLI arguments: `python script.py <folder_path>`).
- **Input/Output**:
  - Input: A path to the target folder containing raw source documents.
  - Output: Generated web-ready files (e.g., `.md`, `.html`) saved into the target output directory.
- **Idempotency**: Sub-scripts must overwrite existing outputs safely or skip unchanged source files.
- **Exit Codes**: Return exit code `0` on success and non-zero on error. Print clear errors to `stderr`.

## Instructions for AI Agents Creating New Sub-Scripts
When asked to create a new document transformer:
1. Create a new module inside `src/transformers/` named `transform_<format>.py`.
2. Implement the standard transformer signature (see `src/transformers/base.py` or `transform_docx.py` as an example).
3. Register the trigger rule in `config.py` (or ensure the script exposes its own `MATCH_PATTERN` string).
4. Add a unit test in `tests/test_transformers.py` verifying document conversion on a sample file.
