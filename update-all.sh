#!/bin/bash

BRANCH=$1

git fetch origin
git reset --hard
git checkout origin/master
git reset --hard
git branch -D $BRANCH
git checkout -b $BRANCH

bundle update
git commit Gemfile.lock -m 'Update Gemfile.lock to most recent commons-builder'

bundle exec generate_executive_index > executive/index-warnings.txt
git add executive/index-warnings.txt
git commit -a -m "Refresh executive index from Wikidata"

bundle exec generate_legislative_index > legislative/index-warnings.txt
git add legislative/index-warnings.txt
git commit -a -m "Refresh legislative index from Wikidata"

bundle exec build update
git commit -a -m "Refresh data from Wikidata"

bundle exec build build > build_output.txt
git add build_output.txt
git commit -a -m "Rebuild using new Wikidata data"

git push -u origin $BRANCH --force-with-lease

