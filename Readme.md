# stupidity
Stupid version control done for fun.  
Unlike git, this works on individual files instead of full repositories. Everything is assumed to not be in the repository until added. This is designed more for working on individual files that you want to treat separately instead of big projects. It is designed to be version control for things like gists.

## Commands
Run it as follows:
``` bash
[python3] stupidity.py <command> [options...] <args...> 
```
List of commands:
```
add <file...>: add a commit for file if there has been a change
update: update all files that are currently being tracked 
revert <file> <number>: revert file back number commits
```

## Other notes
Data is never deleted, even when reverted back. The structure of commits is stored in stpd.json, if you want to find the tree of revisions.

## Future plans
I am currently not working on this, but in the future I want this to connect to a remote repository and have a syncing feature, to hopefully make it something like a self-hosted google drive.