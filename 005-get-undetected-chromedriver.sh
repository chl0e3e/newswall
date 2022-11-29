#!/bin/bash

SCRIPT_FILE=$(realpath "${BASH_SOURCE[${#BASH_SOURCE[@]} - 1]}")
SCRIPT_PATH=`realpath $(dirname $SCRIPT_FILE)`
cd $SCRIPT_PATH

VARS_DIR="$SCRIPT_PATH/.vars"

UNDETECTED_CHROMEDRIVER_REPO="git@github.com:ultrafunkamsterdam/undetected-chromedriver.git"

CHROMEDRIVERS_PATH="$SCRIPT_PATH/chromedriver"
UNDETECTED_CHROMEDRIVER_VERS_PATH="$SCRIPT_PATH/uc_versions"
UNDETECTED_CHROMEDRIVER_LINK_PATH="$SCRIPT_PATH/uc"

CHROMEDRIVER_VERSION=$(cat $VARS_DIR/chromedriver_version)
CHROMEDRIVER_VERSION_MAJOR=$(echo $CHROMEDRIVER_VERSION | sed 's/\..*//')

mkdir -p $UNDETECTED_CHROMEDRIVER_VERS_PATH

echo "attempting to get undetected-chromedriver"
echo ""

echo "getting latest commit"
UNDETECTED_CHROMEDRIVER_REPO_VER=$(git ls-remote "git@github.com:ultrafunkamsterdam/undetected-chromedriver.git" HEAD | cut -f1 -d$'\t')
echo "HEAD is at $UNDETECTED_CHROMEDRIVER_REPO_VER"

echo "cloning remote repo"
UNDETECTED_CHROMEDRIVER_REPO_VER_PATH="$UNDETECTED_CHROMEDRIVER_VERS_PATH/$UNDETECTED_CHROMEDRIVER_REPO_VER"
git clone "$UNDETECTED_CHROMEDRIVER_REPO" "$UNDETECTED_CHROMEDRIVER_REPO_VER_PATH"
UNDETECTED_CHROMEDRIVER_DOWNLOADED=$?

if [[ "$UNDETECTED_CHROMEDRIVER_DOWNLOADED" -eq 0 ]]; then
  echo -n $UNDETECTED_CHROMEDRIVER_REPO_VER_PATH > "$VARS_DIR/undetected-chromedriver"
  echo "downloaded undetected-chromedriver"
  echo "path: $UNDETECTED_CHROMEDRIVER_REPO_VER_PATH"

  UNDETECTED_CHROMEDRIVER_REPO_VER_PYPATH="$UNDETECTED_CHROMEDRIVER_REPO_VER_PATH/undetected_chromedriver"
  echo "setting up symlink $UNDETECTED_CHROMEDRIVER_REPO_VER_PYPATH -> $UNDETECTED_CHROMEDRIVER_LINK_PATH"
  rm $UNDETECTED_CHROMEDRIVER_LINK_PATH >/dev/null 2>&1
  ln -s $UNDETECTED_CHROMEDRIVER_REPO_VER_PYPATH $UNDETECTED_CHROMEDRIVER_LINK_PATH
  
  exit 0
else
  echo "failed to download undetected-chromedriver"
  exit 1
fi