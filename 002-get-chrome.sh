#!/bin/bash

SCRIPT_FILE=$(realpath "${BASH_SOURCE[${#BASH_SOURCE[@]} - 1]}")
SCRIPT_PATH=`realpath $(dirname $SCRIPT_FILE)`
cd $SCRIPT_PATH

VARS_DIR="$SCRIPT_PATH/.vars"
mkdir -p "$VARS_DIR"

CHROME_PACKAGE="google-chrome-stable" # can be google-chrome-stable, google-chrome-unstable or google-chrome-beta

DISTRO_REPOSITORY_VERSION="stable"

CHROME_REPOSITORY_ROOT="https://dl.google.com/linux/chrome/deb"
CHROME_REPOSITORY_DIST_ROOT="$CHROME_REPOSITORY_ROOT/dists/$DISTRO_REPOSITORY_VERSION"

echo "repo version: $DISTRO_REPOSITORY_VERSION"
echo "root: $CHROME_REPOSITORY_ROOT"
echo "dist root $CHROME_REPOSITORY_DIST_ROOT"
echo ""

echo "downloading Release file"
CHROME_DPKG_RELEASE=$(mktemp)
wget -O $CHROME_DPKG_RELEASE -q --show-progress "$CHROME_REPOSITORY_DIST_ROOT/Release"

IS_SHA256_BLOCK=0

# bogo over the file line by line until it hits a SHA256 signature block
while IFS= read -r line
do
  if [[ "$IS_SHA256_BLOCK" -eq 1 ]]; then
    # we abort on the first line
    CHROME_DPKG_PACKAGES_THEIR_SHA256=$(echo -n $line | cut -f1 -d" ")
    CHROME_DPKG_PACKAGES_PATH=$(echo -n $line | cut -f3 -d" ")
    echo "packages path: $CHROME_DPKG_PACKAGES_PATH"
    echo "packages checksum: $CHROME_DPKG_PACKAGES_THEIR_SHA256"
    echo ""
    break
  fi

  if [[ "$line" == "SHA256:" ]]; then
    echo "file contains a SHA256 header"
    IS_SHA256_BLOCK=1
  fi
done < "$CHROME_DPKG_RELEASE"

echo "removing temp file $CHROME_DPKG_RELEASE"
rm $CHROME_DPKG_RELEASE

if [ -z ${CHROME_DPKG_PACKAGES_PATH} ]; then echo "error: could not find the path to the Packages file for the Chrome Debian repository"
  exit 1
fi

# we have a correct path to the Packages file
# append it to the repository root
CHROME_DPKG_PACKAGES=$(mktemp)
CHROME_DPKG_PACKAGES_URL="$CHROME_REPOSITORY_DIST_ROOT/$CHROME_DPKG_PACKAGES_PATH"
CHROME_DPKG_PACKAGES_URL_PATH=$(echo $CHROME_DPKG_PACKAGES_URL | sed 's/\/Packages//') # this is used later

echo "downloading Packages file"
echo "tmp: $CHROME_DPKG_PACKAGES"
echo "url: $CHROME_DPKG_PACKAGES_URL"
echo "";
wget -O $CHROME_DPKG_PACKAGES -q --show-progress "$CHROME_DPKG_PACKAGES_URL"

echo "performing integrity check on Packages"
# get the SHA256 sum of the file we just downloaded
CHROME_DPKG_PACKAGES_OUR_SHA256=$(sha256sum $CHROME_DPKG_PACKAGES | cut -f1 -d" ")

# verify it matches the one we got from the /Release file
if [[ "$CHROME_DPKG_PACKAGES_OUR_SHA256" == "$CHROME_DPKG_PACKAGES_THEIR_SHA256" ]]; then echo "repo integrity validated:"
  echo "$CHROME_DPKG_PACKAGES_OUR_SHA256 == $CHROME_DPKG_PACKAGES_THEIR_SHA256"
  echo ""
else echo "repo integrity check failed:"
  echo "$CHROME_DPKG_PACKAGES_OUR_SHA256 != $CHROME_DPKG_PACKAGES_THEIR_SHA256"
  exit 2
fi

echo "parsing Packages"
SECTIONS=()
BUFFER=""
LAST_WAS_LINE=0
while IFS= read -r line
do
  if [[ "${#line}" -eq 0 ]]; then
    SECTIONS[${#SECTIONS[@]}]=$BUFFER
    BUFFER=""
    continue
  fi

  BUFFER+="$line"$'\n'
done < $CHROME_DPKG_PACKAGES
echo "removing temp file $CHROME_DPKG_PACKAGES"

RELEASE_COUNT=${#SECTIONS[@]}
echo "$RELEASE_COUNT releases found"
echo ""
if [[ "$RELEASE_COUNT" -eq 0 ]]; then echo "error: no releases parsed"
  exit 3
fi

# broken parsing of the Packages file
# lines are missed because the basic parser cannot handle multi-line descriptions
for section in "${SECTIONS[@]}"; do
  IFS=$'\n'
  for line in $section; do
    if [[ $line == "Package: "* ]] ; then PACKAGE=$(echo $line | sed 's/^.*: //'); fi
    if [[ $line == "Version: "* ]] ; then VERSION=$(echo $line | sed 's/^.*: //'); fi
    if [[ $line == "Architecture: "* ]] ; then ARCHITECTURE=$(echo $line | sed 's/^.*: //'); fi
    if [[ $line == "Maintainer: "* ]] ; then MAINTAINER=$(echo $line | sed 's/^.*: //'); fi
    if [[ $line == "Installed-Size: "* ]] ; then INSTALLED_SIZE=$(echo $line | sed 's/^.*: //'); fi
    if [[ $line == "Pre-Depends: "* ]] ; then PREDEPENDS=$(echo $line | sed 's/^.*: //'); fi
    if [[ $line == "Depends: "* ]] ; then DEPENDS=$(echo $line | sed 's/^.*: //'); fi
    if [[ $line == "Provides: "* ]] ; then PROVIDES=$(echo $line | sed 's/^.*: //'); fi
    if [[ $line == "Section: "* ]] ; then SECTION=$(echo $line | sed 's/^.*: //'); fi
    if [[ $line == "Filename: "* ]] ; then FILENAME=$(echo $line | sed 's/^.*: //'); fi
    if [[ $line == "Size: "* ]] ; then SIZE=$(echo $line | sed 's/^.*: //'); fi
    if [[ $line == "SHA256: "* ]] ; then SHA256=$(echo $line | sed 's/^.*: //'); fi
  done

  if [[ "$CHROME_PACKAGE" == "$PACKAGE" ]]; then
    echo "package found"
    echo "name: $PACKAGE"
    echo "version: $VERSION"
    echo "filename: $FILENAME"
    echo "depends: $DEPENDS"
    echo "sha256: $SHA256"
    echo ""
    break
  fi
done

if [ -z ${PACKAGE} ]; then echo "no valid packages found"
  exit 4
fi

regex_open_bracket="\("
regex_close_bracket="\)"
regex_tab=$'\t'

echo "checking dependencies are met"
echo ""
dependencies_met=1
IFS=','
for line in $DEPENDS; do
  line=$(echo $line | sed 's/^ //')
  dependency_choice=0
  dependency_met=0

  if [[ $line == *"|"* ]]; then
    dependency_choice=1
  fi
  
  IFS='|'
  for dependency in $line; do
    dependency=$(echo $dependency | sed 's/^ //' | sed 's/ $//')
    
    if [[ $dependency == *">= "* ]]; then
      dependency_version=$(echo $dependency | sed -E 's/^.*'$regex_open_bracket'>= //' | sed -E 's/'$regex_close_bracket'//')
      dependency_name=$(echo $dependency | cut -f1 -d" ")
    else
      dependency_version="any"
      dependency_name=$dependency
    fi

    host_package_info=$(dpkg-query -W $dependency_name 2>/dev/null)

    if [[ "$host_package_info" != *$'\t\n'* ]] && [[ "$host_package_info" != "" ]]; then dependency_met=1; fi

    if [[ "$host_package_info" != "" ]]; then
      if [[ "$dependency_version" != "any" ]]; then
        host_package_version=$(echo $host_package_info | head -1 | cut -f2 -d$regex_tab)
        if dpkg --compare-versions $host_package_version ge-nl $dependency_version; then
          dependency_met=1
          break
        fi
      fi
    fi
  done

  if [[ "$dependency_met" -eq 0 ]]; then
    dependencies_met=0

    if [[ "$dependency_choice" -eq 0 ]]; then echo ""
      echo "$dependency is required to use Google Chrome"
      echo "Please install the dependency using the following command as root:"
      echo ""
      dependency_name=$(echo $dependency | cut -f1 -d" ")
      echo "apt-get install $dependency_name"
    else echo ""
      echo "One of the following dependencies is required to use Google Chrome"
      echo "$dependency"
      echo "Please install one of them using one of the following commands as root:"
      echo ""
      for dependency in $line; do
        dependency=$(echo $dependency | sed 's/^ //' | sed 's/ $//')
        dependency_name=$(echo $dependency | cut -f1 -d" ")
        echo "apt-get install $dependency_name"
      done
    fi
  fi

  IFS=','
done
  
if [[ "$dependencies_met" -eq 0 ]]; then echo ""
  exit 5
fi
echo "dependencies are met"

echo ""
CHROME_DEB_FILE=$(mktemp -t XXXXXXXXXX.deb)
CHROME_DEB_URL="$CHROME_REPOSITORY_ROOT/$FILENAME"
echo "tmp: $CHROME_DEB_FILE"
echo "url: $CHROME_DEB_URL"
echo "downloading chrome deb package"
wget -O $CHROME_DEB_FILE -q --show-progress $CHROME_DEB_URL

echo "performing integrity check on Google Chrome package"
# get the SHA256 sum of the file we just downloaded
OUR_SHA256=$(sha256sum $CHROME_DEB_FILE | cut -f1 -d" ")

# verify it matches the one we got from the /Release file
if [[ "$OUR_SHA256" == "$SHA256" ]]; then echo "package integrity validated:"
  echo "$OUR_SHA256 == $SHA256"
  echo ""
else echo "package integrity check failed:"
  echo "$OUR_SHA256 != $SHA256"
  rm $CHROME_DEB_FILE
  exit 6
fi

echo "extracting Chrome package"
CHROME_DEB_EXTRACTED_FOLDER=$(mktemp -d)
echo "tmp: $CHROME_DEB_EXTRACTED_FOLDER"
echo "pkg: $CHROME_DEB_FILE"
ar x --output=$CHROME_DEB_EXTRACTED_FOLDER $CHROME_DEB_FILE
echo "cleaning up Chrome package"
rm $CHROME_DEB_FILE
echo ""

CHROME_DIR="$SCRIPT_PATH/chrome"
echo "creating $CHROME_DIR directory"
mkdir -p $CHROME_DIR

CHROME_VER_DIR="$SCRIPT_PATH/chrome/$VERSION"
echo "creating $CHROME_VER_DIR directory"
mkdir -p $CHROME_VER_DIR

CHROME_DEB_EXTRACTED_DATA="$CHROME_DEB_EXTRACTED_FOLDER/data.tar.xz"
echo "extracting Chrome package: $CHROME_DEB_EXTRACTED_DATA"
tar -xvf "$CHROME_DEB_EXTRACTED_DATA" -C "$CHROME_VER_DIR"
echo "cleaning up package folder"
rm -rf "$CHROME_DEB_EXTRACTED_FOLDER"
echo ""

echo "checking for Chrome"
CHROME_BINARY="$CHROME_VER_DIR/opt/google/chrome/chrome"
stat "$CHROME_BINARY" >/dev/null 2>&1
CHROME_DOWNLOADED=$?

if [[ "$CHROME_DOWNLOADED" -eq 0 ]]; then
  echo "Google Chrome downloaded successfully!"
  echo "$CHROME_BINARY"

  echo -n $CHROME_BINARY > "$VARS_DIR/chrome"
  echo -n $VERSION > "$VARS_DIR/chrome_version"
  exit 0
else
  echo "Failed to download Chrome"
  exit 7
fi