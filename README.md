## Usage

`fetcher.py -user USERNAME -repo REPOSITORY [-token TOKEN] [-maketargets MAKETARGET1 MAKETARGET2 ...]` to check the status of pull requests on a particular repository you have access to. Requires an elephant file with a github auth token in to be set (alternatively, this can be passed as an argument).

Intended to be fairly lightweight so it can be used in a low-RAM environment.

Should only be used on private repos where only trusted persons have access.

Lacks any sort of error checking, so is likely to break and not work much outside a closed environment.
