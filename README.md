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

To add a new country you can do:

    git submodule add git@github.com:everypolitician/proto-commons-[country].git [country]