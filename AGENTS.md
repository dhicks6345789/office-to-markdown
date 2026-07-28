# Repository Guidelines for AI Agents

## Overview
This repository contains a Python-based document transforms pipeline. The core script (`scanFolders.py`) recursively scans a directory tree, matches target sub-folders by specific (Python) Regular Expression (RE) strings, and delegates processing to modular transformation sub-scripts.

The directory tree to be scanned should look and act like a standard filesystem directory. However, it is assumed that this project will be used extensively with cloud-based filesystems (Google Drive, Microsoft OneDrive, Dropbox, etc), with folders from those filesystems mounted as part of the local directory structure. In particular, on Linux systems cloud-based filesystems might be mounted using the rclone utility. This might affect performance (file read/write times) and the filesystem features that can be supported.

Output is designed to be used by the Hugo static-site generation tool, so output is typically Markdown file and associated assets placed in the "content" folder of a "Hugo" root output folder. Scripts that generate self-contained HTML should probably output to Hugo's "static" folder instead.

## Architecture Pattern
1. **Core Orchestrator (`scanFolders.py`)**: Walks the filesystem recursively, evaluates folder paths against match strings, and invokes the appropriate transformer script.
2. **officeToMarkdownLib.py**: Provides a central library of functions and value definitions.
3. **matches.csv**: Holds the regular expression match strings that describe which input file / folder patterns are handled by which sub-script.
4. **Transformers (various scripts / folders in the repository root)**: Modular sub-scripts responsible for converting specific document types into web pages (e.g., Markdown, HTML).

## How Sub-Scripts Work (The Plugin Pattern)
Every transformer sub-script must adhere to a strict interface contract so the main scanner can invoke it via CLI subprocesses. Sub-scripts do not have to be written in Python, they can be in any language.

### Sub-Script Contract Rules
Sub-scripts (which do not have to be written in Python) should accept standard CLI arguments as defined by the Python `argparse.ArgumentParser` library:
- **--input**: Input file or folder. An absolute path.
- **--outputRoot**: The root output folder, an absolute path, typically a 'Hugo' folder ready to be processed by the Hugo static site utility.
- **--output**: The output folder, relative to the outputRoot.
- **--scriptRoot**: The root of the script folder, where the executable scripts are stored. Defaults to the current working directory.
- **--dataRoot**: The root of the data folder, where file update data can be stored. Defaults to the current working directory.
- **--verbose**: Turn on verbose output.

Subscripts, when run, are passed a set of file update tuples (as simple comma-separated strings, e.g. filename,lastModifiedTimestamp, with a newline at the end) via stdin that give the set of last-seen input files.
On successful exit, scripts should write out (to stdout) a list of any used input files, again as filename,lastModifiedTimestamp tuples, followed by "---", followed by a simple list (separated by newlines) of any output files generated.

This data being passed is to allow for idempotency, so that the same operation being called on the same input files can be spotted and unnecessary work be avoided. This is particularly important as some cloud-based mounted filesystems can be slow and some input files (images, videos) quite large and time-consuming to process. The list of input files will include the last-updated timestamp of the script itself and any associated files, if any of these files have been updated the operation should be re-run regardless of other input files being changed or not.

Any other output (including error messages) from the sub-script should be to stderr so that the central calling script can separate that from data being passed. Return exit code `0` on success and non-zero on error.

## Instructions for AI Agents Creating New Sub-Scripts
When asked to create a new document transformer:
1. Unless a different language is specified, create a new Python script inside a folder in the main project root.
2. Implement the standard transformer signature (simply using the `setArgsForSubScript` function from `officeToMarkdownLib.py` to set the command-line options for a `argparse.ArgumentParser` object)
3. Register the RE match string in `matches.csv`.
4. Add a unit test in `tests/test_transformers.py` verifying document conversion on a sample file.
