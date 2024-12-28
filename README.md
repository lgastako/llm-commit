# llm-commit

Use LLM to generate source control commit messages.

## Installation

Install this plugin in the same environment as [LLM](https://llm.datasette.io/).

```
llm install llm-commit
```

## Usage

Run `llm commit` like this:

```
% llm commit
> git commit -m 'Update command handling to properly quote messages' -a
[main 6a72485] Update command handling to properly quote messages
 1 file changed, 24 insertions(+), 3 deletions(-)
```

And it will generate the command to commit the changes with
and autogenerate message which you can accept, edit, or reject.

Run it with the -y flag to automatically commit the changes:

```
% llm commit -y
[main 98c22b3] Add force commit option to skip prompts and commit all changes
 1 file changed, 22 insertions(+), 7 deletions(-)
```

It will use your [default model](https://llm.datasette.io/en/stable/setup.html#setting-a-custom-default-model) to generate the corresponding commit message.

### Staged Changes

By default, if there are no staged changes it will assume that you
want to commit all changes. If there are staged changes, it will
use the staged changes to generate the commit message.

If you have staged changes and you want to commit all changes including
unstaged changes, you can use the -a flag:

```
% git status
On branch main
Your branch is up to date with 'origin/main'.

Changes to be committed:
  (use "git restore --staged <file>..." to unstage)
	modified:   README.md

Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
	modified:   llm_commit/plugin.py

% llm commit -a
[main 655c761] Update README and improve command registration logic in plugin.py
 2 files changed, 20 insertions(+), 5 deletions(-)
```

## SCM Support

# Currently Supported

- [Git](https://git-scm.com/)
- [Mercurial (Hg)](https://www.mercurial-scm.org/)
- [SVN](https://subversion.apache.org/)
- [CVS](https://www.nongnu.org/cvs/)
- [Darcs](https://www.darcs.net/)

If your favorite SCM system isn't on the list, please let me know.

## TODO

- [ ] Fix bug when -a isn't passed and there are no staged changes
- [ ] Prevent it from pulling in changes to lock files, etc.
