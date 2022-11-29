#!/bin/bash

SCRIPT_FILE=$(realpath "${BASH_SOURCE[${#BASH_SOURCE[@]} - 1]}")
SCRIPT_PATH=`realpath $(dirname $SCRIPT_FILE)`
cd $SCRIPT_PATH

VARS_DIR="$SCRIPT_PATH/.vars"

MONGODB_VERSION="6.0.3"
MONGODB_DEB_URL="https://repo.mongodb.org/apt/debian/dists/bullseye/mongodb-org/6.0/main/binary-amd64/mongodb-org-server_6.0.3_amd64.deb"
SHA256="e6242376dfec25cc100d271ed40a71fb78c558c14cc95d6772b782d6897fbfab"

echo "downloading MongoDB"
echo "url: $MONGODB_DEB_URL"
echo "sha256: $SHA256"
echo ""

MONGODB_DIR="$SCRIPT_PATH/mongodb"
echo "creating $MONGODB_DIR directory"
mkdir -p $MONGODB_DIR

echo ""
MONGODB_DEB_FILE=$(mktemp -t XXXXXXXXXX.deb)
echo "tmp: $MONGODB_DEB_FILE"
echo "url: $MONGODB_DEB_URL"
echo "downloading MongoDB deb package"
wget -O $MONGODB_DEB_FILE -q --show-progress $MONGODB_DEB_URL
MONGODB_DEB_DOWNLOADED=$?

if [[ "$MONGODB_DEB_DOWNLOADED" -ne 0 ]]; then
  echo "could not download MongoDB deb file"
  rm $MONGODB_DEB_FILE
  exit 1
fi

echo "performing integrity check on MongoDB package"
# get the SHA256 sum of the file we just downloaded
OUR_SHA256=$(sha256sum $MONGODB_DEB_FILE | cut -f1 -d" ")

# verify it matches the one we got from the /Release file
if [[ "$OUR_SHA256" == "$SHA256" ]]; then echo "package integrity validated:"
  echo "$OUR_SHA256 == $SHA256"
  echo ""
else echo "package integrity check failed:"
  echo "$OUR_SHA256 != $SHA256"
  exit 2
fi

echo "extracting MongoDB package"
MONGODB_DEB_EXTRACTED_FOLDER=$(mktemp -d)
echo "tmp: $MONGODB_DEB_EXTRACTED_FOLDER"
echo "pkg: $MONGODB_DEB_FILE"
ar x --output=$MONGODB_DEB_EXTRACTED_FOLDER $MONGODB_DEB_FILE
echo "cleaning up MongoDB package"
rm $MONGODB_DEB_FILE
echo ""

MONGODB_DEB_EXTRACTED_DATA="$MONGODB_DEB_EXTRACTED_FOLDER/data.tar.xz"
echo "extracting MongoDB package: $MONGODB_DEB_EXTRACTED_DATA"
tar -xvf "$MONGODB_DEB_EXTRACTED_DATA" -C "$MONGODB_DIR"
echo "cleaning up package folder"
rm -rf "$MONGODB_DEB_EXTRACTED_FOLDER"
echo ""

echo "checking for mongod"
MONGOD_BINARY="$MONGODB_DIR/usr/bin/mongod"
stat "$MONGOD_BINARY" >/dev/null 2>&1
MONGODB_DOWNLOADED=$?

if [[ "$MONGODB_DOWNLOADED" -eq 0 ]]; then
  echo "MongoDB downloaded successfully!"
  echo "$MONGOD_BINARY"

  echo -n $MONGODB_VERSION > "$VARS_DIR/mongodb_version"
  echo -n $MONGOD_BINARY > "$VARS_DIR/mongod"
  exit 0
else
  echo "Failed to download MongoDB"
  exit 3
fi