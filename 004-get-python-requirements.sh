#!/bin/bash

echo "Attempting to install Python 3 requirements"
echo ""

pip3 install -r requirements.txt
PIP_REQUIREMENTS_DOWNLOADED=$?

if [[ "$PIP_REQUIREMENTS_DOWNLOADED" -eq 0 ]]; then
  echo "Requirements downloaded successfully"
  exit 0
else
  echo "Failed to download requirements"
  exit 1
fi