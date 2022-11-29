#!/bin/bash

SCRIPT_FILE=$(realpath "${BASH_SOURCE[${#BASH_SOURCE[@]} - 1]}")
SCRIPT_PATH=`realpath $(dirname $SCRIPT_FILE)`
cd $SCRIPT_PATH

VARS_DIR="$SCRIPT_PATH/.vars"
MONGOD_BINARY=$(cat $VARS_DIR/mongod)

mkdir -p ./db/

echo "Starting mongod: $MONGOD_BINARY"
$MONGOD_BINARY -f db.conf