from abc import ABC, abstractmethod
from enum import Enum, auto
from functools import cached_property

import os
import subprocess
import click
import llm

from prompt_toolkit import PromptSession
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.patch_stdout import patch_stdout
from pygments.lexers.shell import BashLexer

SYSTEM_PROMPT = """
Generate a concise and descriptive Git commit message following these rules:
- Start with a verb in imperative mood (e.g., "Add", "Fix", "Update")
- Keep the first line under 50 characters
- Focus on WHAT and WHY, not HOW
- Do not include any markdown, quotes, or other formatting
- Return only the commit message text, nothing else
- If there are 3 or less files touched, say something about each file

For example, if the changes are: Added user authentication with JWT
You return only: Add JWT-based user authentication system
""".strip()


class StagedChangesStatus(Enum):
    NONE = auto()  # There are stages, but none are staged for commit
    SOME = auto()  # Some changes are staged, some are not
    ALL = auto()  # All changes are staged
    NO_CHANGES = auto()  # No changes exist


class SCM(ABC):
    __scm_type__ = None

    @abstractmethod
    def detect_scm(self) -> str:
        pass

    @abstractmethod
    def get_changes(self) -> str:
        pass

    @abstractmethod
    def get_command(self, force_all: bool = False) -> str:
        pass


class GitSCM(SCM):
    __scm_type__ = "git"

    def detect_scm(self) -> str:
        repo_path = os.getcwd()
        if os.path.exists(os.path.join(repo_path, ".git")):
            return "git"
        return None

    def get_changes(self) -> str:
        command = ["git", "diff"]
        match self._staged_changes_status:
            case StagedChangesStatus.NONE:
                pass
            case StagedChangesStatus.SOME:
                command.append("--cached")
            case StagedChangesStatus.ALL:
                command.append("--cached")
            case StagedChangesStatus.NO_CHANGES:
                raise click.ClickException("No changes found")
        result = subprocess.run(command, capture_output=True, text=True)
        return result.stdout

    def get_command(self, force_all: bool = False) -> str:
        extra_args = []
        if self._staged_changes_status == StagedChangesStatus.NO_CHANGES:
            click.ClickException("No changes to commit")
        if force_all:
            extra_args.append("-a")
        elif self._staged_changes_status == StagedChangesStatus.NONE:
            extra_args.append("-a")
        return ["git", "commit", "-m", "{}", *extra_args]

    @cached_property
    def _staged_changes_status(self) -> StagedChangesStatus:
        result = subprocess.run(["git", "status"], capture_output=True, text=True)
        # print(f"git status result.stdout: {result.stdout}")
        if result.returncode != 0:
            raise click.ClickException("Failed to get staged changes")
        # print(result)
        to_be_committed = "to be committed:" in result.stdout
        not_staged_for_commit = "not staged for commit:" in result.stdout
        # print(f"to_be_committed: {to_be_committed}")
        # print(f"not_staged_for_commit: {not_staged_for_commit}")
        if to_be_committed:
            if not_staged_for_commit:
                return StagedChangesStatus.SOME
            else:
                return StagedChangesStatus.ALL
        elif not_staged_for_commit:
            return StagedChangesStatus.NONE
        return StagedChangesStatus.NO_CHANGES


class MercurialSCM(SCM):
    __scm_type__ = "hg"

    def detect_scm(self) -> str:
        repo_path = os.getcwd()
        if os.path.exists(os.path.join(repo_path, ".hg")):
            return "hg"
        return None

    def get_changes(self) -> str:
        command = ["hg", "diff"]
        match self._staged_changes_status:
            case StagedChangesStatus.NONE:
                pass
            case StagedChangesStatus.SOME:
                # Mercurial doesn't have staging area like Git
                # Show only changes that are added
                command.extend(["-w", "--change", "."])
            case StagedChangesStatus.ALL:
                command.extend(["-w", "--change", "."])
            case StagedChangesStatus.NO_CHANGES:
                raise click.ClickException("No changes found")
        result = subprocess.run(command, capture_output=True, text=True)
        return result.stdout

    def get_command(self, force_all: bool = False) -> str:
        if self._staged_changes_status == StagedChangesStatus.NO_CHANGES:
            click.ClickException("No changes to commit")
        # Mercurial automatically commits all changes, no need for -a flag
        return ["hg", "commit", "-m", "{}"]

    @cached_property
    def _staged_changes_status(self) -> StagedChangesStatus:
        result = subprocess.run(["hg", "status"], capture_output=True, text=True)
        if result.returncode != 0:
            raise click.ClickException("Failed to get status")

        if not result.stdout.strip():
            return StagedChangesStatus.NO_CHANGES

        # In Mercurial, all modified files are automatically "staged"
        # So we only have ALL or NO_CHANGES states
        return StagedChangesStatus.ALL


@llm.hookimpl
def register_commands(cli):
    @cli.command()
    @click.option("-m", "--model", default=None, help="Specify the model to use")
    @click.option("-s", "--system", help="Custom system prompt")
    @click.option("-p", "--path", help="Path to the repository")
    @click.option(
        "-y",
        "--yes",
        is_flag=True,
        help="Automatically commit the changes, do not prompt for edits",
    )
    @click.option(
        "-a", "--all", is_flag=True, help="Commit all changes, staged or unstaged."
    )
    @click.option("--key", help="API key to use")
    def commit(model, system, key, path, yes, all):
        "Use an LLM to generate a commit message"
        from llm.cli import get_default_model

        path = path or os.getcwd()

        # Try Git first, then Mercurial
        scm = None
        scm_classes = [GitSCM, MercurialSCM]
        for scm_class in scm_classes:
            scm = scm_class()
            if scm.detect_scm() is not None:
                break

        if scm is None:
            supported_scms = ", ".join([scm.__scm_type__ for scm in scm_classes])
            raise click.ClickException(
                f"No supported SCM found (supported scms: {supported_scms}"
            )

        command = scm.get_command(force_all=all)
        changes = scm.get_changes()
        prompt = changes

        model = model or get_default_model()
        model_id = model or get_default_model()
        model_obj = llm.get_model(model_id)
        if model_obj.needs_key:
            model_obj.key = llm.get_key(key, model_obj.needs_key, model_obj.key_env_var)
        result = model_obj.prompt(prompt, system=system or SYSTEM_PROMPT)
        reply = result.text()
        if not isinstance(reply, str):
            raise Exception("reply Expected a string, got: " + str(type(reply)))
        full_command_str = insert_message(command, reply)
        # print(f"full_command_str: {full_command_str}")
        if not yes:
            interactive_exec(full_command_str)
        else:
            # print(f"Running: {full_command_str}")
            subprocess.run(full_command_str, shell=True)


def escape(s):
    return s.replace("'", "'\"'\"")


def quote(s):
    # If there are no single quotes in the string, then we want to wrap it in single quotes
    # If there are single quotes but no double quotes, then we want to wrap it in double quotes
    # If there are both then we want to escape the single quotes and wrap it in single quotes
    if "'" not in s:
        return f"'{s}'"
    if '"' not in s:
        return f'"{s}"'
    return escape(s)


def insert_message(command, message):
    command = command.copy()
    for index, segment in enumerate(command):
        if segment == "{}":
            command[index] = quote(message)
    return " ".join(command)


def interactive_exec(command):
    if isinstance(command, list):
        command = " ".join(command)
    # print(f"interactive_exec: {command}")
    session = PromptSession(lexer=PygmentsLexer(BashLexer))
    with patch_stdout():
        if "\n" in command:
            print("Multiline command - Meta-Enter or Esc Enter to execute")
            edited_command = session.prompt("> ", default=command, multiline=True)
        else:
            edited_command = session.prompt("> ", default=command)
    try:
        output = subprocess.check_output(
            edited_command, shell=True, stderr=subprocess.STDOUT
        )
        print(output.decode())
    except subprocess.CalledProcessError as e:
        print(
            f"Command failed with error (exit status {e.returncode}): {e.output.decode()}"
        )
