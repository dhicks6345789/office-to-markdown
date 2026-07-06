#!/bin/bash

if [ ! -d .venv ]; then
  python -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
else
  source .venv/bin/activate
fi

cp docsToMarkdownLib.py .venv/lib/python3.13/site-packages

python3 scanFolders.py "$@"
