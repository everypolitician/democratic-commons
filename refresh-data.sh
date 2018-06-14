#!/bin/bash -e

BRANCH=$1

if [ "$BRANCH" == "" ]; then
  echo "Specify a branch name as an argument"
  exit 1
fi

if [ "$BRANCH" == "master" ]; then
  echo "Doing this to master would be a terrible idea"
  exit 1
fi

git fetch origin
git reset --hard
git checkout origin/master
git reset --hard
if git rev-parse --verify $BRANCH ; then
    git branch -D $BRANCH
fi
git checkout -b $BRANCH

bundle update
if [ "$(git status Gemfile.lock --porcelain)" ]; then
  git commit Gemfile.lock -m 'Update Gemfile.lock to most recent commons-builder'
fi

bundle exec generate_executive_index > executive/index-warnings.txt
git add executive/index-warnings.txt
if [ "$(git status executive/index* --porcelain)" ]; then
  git commit -a -m "Refresh executive index from Wikidata"
fi

bundle exec generate_legislative_index > legislative/index-warnings.txt
git add legislative/index-warnings.txt
if [ "$(git status legislative/index* --porcelain)" ]; then
  git commit -a -m "Refresh legislative index from Wikidata"
fi

rm -f {legislative,executive}/*/*/{query-results.json,query-used.rq}
bundle exec build update
git add legislative/* executive/*
if [ "$(git status legislative executive --porcelain | grep '^ D')" ]; then
  git rm $(git status legislative executive --porcelain | grep '^ D' | colrm 1 3)
fi
if [ "$(git status legislative executive --porcelain)" ]; then
  git commit -a -m "Refresh data from Wikidata"
fi

rm -f {legislative,executive}/*/*/popolo-m17n.json
bundle exec build build > build_output.txt
git add build_output.txt
git add legislative/* executive/*
if [ "$(git status legislative executive --porcelain | grep '^ D')" ]; then
  git rm $(git status legislative executive --porcelain | grep '^ D' | colrm 1 3)
fi
if [ "$(git status legislative executive build_output.txt --porcelain)" ]; then
  git commit -a -m "Rebuild using new Wikidata data"
fi

#git push -u origin $BRANCH --force-with-lease
