# Experimental Democratic Commons super-repository

This is an experimental repository that contains submodules for each
[current prototype commons repository](https://github.com/everypolitician?utf8=%E2%9C%93&q=proto-).

## Cloning

The URLs in `.gitmodules` are scp-style Git URLs, so you need to
have your SSH key added to GitHub for updating the submodules to
work out-of-the-box.

You can either clone the repository with the `--recursive`
option, or if you've already cloned the repository, update all
the submodules with:

    git submodule update --init

## Adding new countries

To add a new country, make sure this country repository exists
under the
[everypolitician organization](https://github.com/everypolitician/)
with the topics `commons-data` and `country-code-XX` where XX is
the 2 leter ISO country code. Then run:

    ./add-repos-from-github.py

## Running commands for each country

You can run commands in each country using `git submodule
foreach`. For example, to run `bundle install` in each
repository:

    git submodule foreach 'bundle install'

To update each repository from Wikidata:

    git submodule foreach 'bundle exec build update'

To rebuild the fetched data in each repository:

    git submodule foreach 'bundle exec build build'
