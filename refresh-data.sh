#!/bin/bash -e

# This script operates in two modes. With a branch specified as an argument, it
# blats any existing branch by that name and refreshes the data relative to
# origin/master, which means it can be called multiple times until the data
# look right. Without a branch specified, it appends commits onto the current
# HEAD.
#
# In either mode, the git status must be clean before starting.

BRANCH=$1

if [ "$BRANCH" == "master" ]; then
  echo "Doing this to master would be a terrible idea"
  exit 1
fi

if [ "$(git status --porcelain)" ]; then
   echo "git status must be clean in $(pwd)"
   exit 1
fi

if ! command -v jq >/dev/null 2>&1
then
    echo "jq was not found on your PATH"
    exit 1
fi

if [ -d boundaries/build ]; then
  BOUNDARIES=boundaries/build
else
  BOUNDARIES=boundaries
fi

if [ "$BRANCH" ]; then
  git fetch origin
  git checkout --no-track -B "$BRANCH" origin/master
fi

HAS_BUNDLE_UPDATED=0

while true; do
  if [ "$HAS_BUNDLE_UPDATED" = "0" ]; then
    # Make sure the right versions of dependencies are installed for this
    # repository
    bundle install >/dev/null 2>&1
    PRE_POST_UPDATE=""
  else
    PRE_POST_UPDATE=" (post-\`bundle update\`)"
  fi

  if ! jq -e '.hand_maintained_files | contains(["executive/index.json"])' < config.json > /dev/null
  then
    bundle exec generate_executive_index > executive/index-warnings.txt
    git add executive/index-warnings.txt executive/index-query-used.rq
    if [ "$(git status executive/index* --porcelain)" ]; then
      git commit -a -m "Refresh executive index from Wikidata$PRE_POST_UPDATE"
    fi
  fi
  
  if ! jq -e '.hand_maintained_files | contains(["legislative/index.json"])' < config.json > /dev/null
  then
    bundle exec generate_legislative_index > legislative/index-warnings.txt
    git add legislative/index-warnings.txt legislative/index-query-used.rq legislative/index-terms-query-used.rq
    if [ "$(git status legislative/index* --porcelain)" ]; then
      git commit -a -m "Refresh legislative index from Wikidata$PRE_POST_UPDATE"
    fi
  fi
  
  # This isn't affected by commons-builder changes, so only needs running the
  # first time round
  if [ "$HAS_BUNDLE_UPDATED" = "0" ]; then
    ../boundary-data-merge.py
    if  [ "$(git status $BOUNDARIES --porcelain)" ]; then
      git commit -a -m "Update Wikidata IDs for merged items in boundary data"
    fi
  fi
  
  rm -f {legislative,executive}/*/*/{query-results.json,query-used.rq}
  bundle exec build update
  git add legislative/* executive/*
  if [ "$(git status legislative executive --porcelain | grep '^ D')" ]; then
    git rm $(git status legislative executive --porcelain | grep '^ D' | colrm 1 3)
  fi
  if [ -e $BOUNDARIES/position-data-query-used.rq ]; then
    git add $BOUNDARIES/position-data-query-*
  fi
  if [ "$(git status --porcelain)" ]; then
    git commit -a -m "Refresh data from Wikidata$PRE_POST_UPDATE"
  fi
  
  rm -f {legislative,executive}/*/*/popolo-m17n.json
  bundle exec build build > build_output.txt
  git add build_output.txt
  git add legislative/* executive/*
  if [ "$(git status legislative executive --porcelain | grep '^ D')" ]; then
    git rm $(git status legislative executive --porcelain | grep '^ D' | colrm 1 3)
  fi
  if [ -e $BOUNDARIES/position-data.json ]; then
    git add $BOUNDARIES/position-data.json
  fi
  if [ "$(git status --porcelain)" ]; then
    git commit -a -m "Rebuild using new Wikidata data$PRE_POST_UPDATE"
  fi
  
  bundle update >/dev/null 2>&1
  if [ "$(git status Gemfile.lock --porcelain)" ]; then
    git commit Gemfile.lock -m 'Update Gemfile.lock to most recent commons-builder'
    HAS_BUNDLE_UPDATED=1
  else
    break
  fi
done

if [ "$BRANCH" ]; then
  if git rev-parse --verify $BRANCH@{u} > /dev/null 2>&1; then
    git push origin $BRANCH --force-with-lease
  else
    git push -u origin $BRANCH
  fi
fi

