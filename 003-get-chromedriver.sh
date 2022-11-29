#!/bin/bash

SCRIPT_FILE=$(realpath "${BASH_SOURCE[${#BASH_SOURCE[@]} - 1]}")
SCRIPT_PATH=`realpath $(dirname $SCRIPT_FILE)`
cd $SCRIPT_PATH

VARS_DIR="$SCRIPT_PATH/.vars"

CHROMEDRIVERS_PATH="$SCRIPT_PATH/chromedriver"

CHROMEDRIVER_ABI="linux64"

CHROME_VERSION=$(cat $VARS_DIR/chrome_version)
CHROME_VERSION_MAJOR=$(echo $CHROME_VERSION | sed 's/\..*//')

CHROMEDRIVER_STORAGE_URL="https://chromedriver.storage.googleapis.com"

echo "downloading chromedriver repo index"
CHROMEDRIVER_INDEX=$(mktemp)
echo "tmp: $CHROMEDRIVER_INDEX"
wget -O $CHROMEDRIVER_INDEX -q --show-progress "$CHROMEDRIVER_STORAGE_URL"
CHROMEDRIVER_INDEX_SUCCESS=$?
if [[ "$CHROMEDRIVER_INDEX_SUCCESS" -ne 0 ]]; then echo "failed to get chromedriver version listings"
  exit 1
fi

CHROMEDRIVER_INDEX_CONTENTS=$(cat $CHROMEDRIVER_INDEX)
CHROMEDRIVER_CHOICES=$(mktemp)
IFS="<>" 
for line in $CHROMEDRIVER_INDEX_CONTENTS; do
  if [[ $line == *".zip"* ]]; then
    if [[ $line == "$CHROME_VERSION_MAJOR"* ]]; then
      if [[ $line == *"$CHROMEDRIVER_ABI"* ]]; then
        echo $line >> $CHROMEDRIVER_CHOICES
      fi
    fi
  fi
done

CHROMEDRIVER_BINARY_URL_PATH=$(tail -1 $CHROMEDRIVER_CHOICES)
if [[ $(echo $CHROMEDRIVER_BINARY_URL_PATH | wc -l) -eq 0 ]]; then echo "could not find a chromedriver for $CHROME_VERSION_MAJOR"
  exit 2
fi
CHROMEDRIVER_VERSION=$(echo $CHROMEDRIVER_BINARY_URL_PATH | sed 's/\/.*//')
echo "using chromedriver $CHROMEDRIVER_VERSION for chrome $CHROME_VERSION"

echo "cleaning up repo index"
rm $CHROMEDRIVER_CHOICES

CHROMEDRIVER_BINARY_ZIP=$(mktemp)
CHROMEDRIVER_BINARY_URL="$CHROMEDRIVER_STORAGE_URL/$CHROMEDRIVER_BINARY_URL_PATH"

echo "downloading chromedriver binary"
echo "tmp: $CHROMEDRIVER_BINARY_ZIP"
echo "url: $CHROMEDRIVER_BINARY_URL"
wget -O $CHROMEDRIVER_BINARY_ZIP -q --show-progress "$CHROMEDRIVER_BINARY_URL"
CHROMEDRIVER_DOWNLOAD_SUCCESS=$?
if [[ "$CHROMEDRIVER_DOWNLOAD_SUCCESS" -ne 0 ]]; then echo "failed to get chromedriver version from url"
  exit 3
fi

CHROMEDRIVER_EXTRACTED_PATH="$CHROMEDRIVERS_PATH/$CHROMEDRIVER_VERSION"
echo "creating folder for chromedriver: $CHROMEDRIVER_EXTRACTED_PATH"
mkdir -p $CHROMEDRIVER_EXTRACTED_PATH
echo "extracting chromedriver to $CHROMEDRIVER_EXTRACTED_PATH"
unzip -d "$CHROMEDRIVER_EXTRACTED_PATH" "$CHROMEDRIVER_BINARY_ZIP"
echo "cleaning up chromedriver archive"
rm $CHROMEDRIVER_BINARY_ZIP

CHROMEDRIVER_BINARY="$CHROMEDRIVER_EXTRACTED_PATH/chromedriver"
stat "$CHROMEDRIVER_BINARY" >/dev/null 2>&1
CHROMEDRIVER_DOWNLOADED=$?

if [[ "$CHROMEDRIVER_DOWNLOADED" -eq 0 ]]; then
  echo "chromedriver downloaded successfully!"
  echo "$CHROMEDRIVER_BINARY"

  echo -n $CHROMEDRIVER_BINARY > "$VARS_DIR/chromedriver"
  echo -n $CHROMEDRIVER_VERSION > "$VARS_DIR/chromedriver_version"
  exit 0
else
  echo "failed to get chromedriver"
  exit 4
fi