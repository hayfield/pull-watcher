## Usage

`fetcher.py -user [USERNAME] -repo [REPOSITORY]` to check the status of pull requests on a particular repository you have access to. Requires an elephant file with a github auto token in to be set.

Should only be used on private repos where only trusted persons have access.

### Repo setup

Watched repositories need a `Makefile` with the following options in: `install-deps`, `build-all`, `test-all`
