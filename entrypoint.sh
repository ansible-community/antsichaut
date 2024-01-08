#!/bin/sh

ARG_TO_VERSION=""
if [ ! -z "$INPUT_TO_VERSION" ]; then
  ARG_TO_VERSION="--to_version $INPUT_TO_VERSION"
fi

ARG_SINCE_VERSION=""
if [ ! -z "$INPUT_SINCE_VERSION" ]; then
  ARG_SINCE_VERSION="--since_version $INPUT_SINCE_VERSION"
fi

echo "antsichaut --github_token $INPUT_GITHUB_TOKEN $ARG_SINCE_VERSION $ARG_TO_VERSION"
antsichaut --github_token $INPUT_GITHUB_TOKEN $ARG_SINCE_VERSION $ARG_TO_VERSION
