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
llm commit
TODO fill in output here
```

And it will generate the command to commit the changes with
and autogenerate message which you can accept, edit, or reject.

Run it with the -y flag to automatically commit the changes:

```
llm commit -y
TODO fill in output here
```

It will use your [default model](https://llm.datasette.io/en/stable/setup.html#setting-a-custom-default-model) to generate the corresponding commit message.

### Staged Changes

By default, if there are no staged changes it will assume that you
want to commit all changes. If there are staged changes, it will
use the staged changes to generate the commit message.

If you have staged changes and you want to commit all changes including
unstaged changes, you can use the -a flag:

```
llm commit -a
TODO fill in output here
```

## SCM Support

# Currently Supported

- [Git](https://git-scm.com/)

# Planned

- [Mercurial (Hg)](https://www.mercurial-scm.org/)
- [SVN](https://subversion.apache.org/)
- [CVS](https://www.nongnu.org/cvs/)
- [Darcs](https://www.darcs.net/)
- [Bazaar](https://www.bazaar.canonical.com/)

If your favorite SCM system isn't on the list, please let me know.

## TODO

- [ ] Prevent it from pulling in changes to lock files, etc.
- [ ] Add support for other SCM systems
