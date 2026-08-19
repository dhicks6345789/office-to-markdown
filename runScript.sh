#!/bin/bash

# Turn off Python's buffering of STDOUT/STDERR.
export PYTHONUNBUFFERED=1

if [ ! -d .venv ]; then
  python -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
else
  source .venv/bin/activate
fi

cp officeToMarkdownLib.py .venv/lib/python3.13/site-packages

python3 "$@"
