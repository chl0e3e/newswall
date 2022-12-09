#!/bin/bash

# delete the Chrome crashpad handler

SCRIPT_FILE=$(realpath "${BASH_SOURCE[${#BASH_SOURCE[@]} - 1]}")
SCRIPT_PATH=`realpath $(dirname $SCRIPT_FILE)`

VARS_DIR="$SCRIPT_PATH/.vars"

cd $SCRIPT_PATH
CHROME_EXECUTABLE=$(cat $VARS_DIR/chrome)
CHROME_CRASHPAD_EXECUTABLE="$CHROME_EXECUTABLE""_crashpad_handler"
stat $CHROME_CRASHPAD_EXECUTABLE >/dev/null 2>&1
CHROME_CRASHPAD_DELETED=$?

if [[ "$CHROME_CRASHPAD_DELETED" -eq 0 ]]; then
    rm $CHROME_CRASHPAD_EXECUTABLE
    echo "Crashpad is now deleted"
else
    echo "Crashpad already deleted"
fi