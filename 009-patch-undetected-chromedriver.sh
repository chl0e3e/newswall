#!/bin/bash

# patches for xvfb use in undetected chromedriver

SCRIPT_FILE=$(realpath "${BASH_SOURCE[${#BASH_SOURCE[@]} - 1]}")
SCRIPT_PATH=`realpath $(dirname $SCRIPT_FILE)`
cd $SCRIPT_PATH

echo "Checking for UC patch"
grep chrome_env uc/__init__.py >/dev/null 2>/dev/null
UNDETECTED_CHROMEDRIVER_PATCHED=$?

if [[ "$UNDETECTED_CHROMEDRIVER_PATCHED" -eq 0 ]]; then
    echo "UC is already patched"
    exit 0
fi

sed -i "s/no_sandbox=True,/no_sandbox=True, display=None,/" uc/__init__.py
sed -i 's/browser = subprocess/chrome_env = os.environ.copy(); chrome_env["DISPLAY"] = display; browser = subprocess/' uc/__init__.py
sed -i 's/=IS_POSIX,/=IS_POSIX, env=chrome_env,/' uc/__init__.py

grep chrome_env uc/__init__.py >/dev/null 2>/dev/null
UNDETECTED_CHROMEDRIVER_PATCHED=$?

if [[ "$UNDETECTED_CHROMEDRIVER_PATCHED" -eq 0 ]]; then
    echo "UC is now patched"
    exit 0
else
    echo "Failed to patch UC"
fi