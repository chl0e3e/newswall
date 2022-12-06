#!/bin/bash

APT_DEPENDENCIES="binutils wget python3 python3-pip git xvfb xdotool"

echo "Attempting to install $APT_DEPENDENCIES"
echo ""
apt-get install -y $APT_DEPENDENCIES
DEP_DOWNLOADED=$?

if [[ "$DEP_DOWNLOADED" -eq 0 ]]; then
  echo "Dependencies downloaded successfully"
  exit 0
else
  echo "Failed to download DPKG dependencies"
  exit 1
fi