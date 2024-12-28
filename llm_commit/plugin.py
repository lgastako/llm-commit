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
    def get_command(self) -> str:
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

    def get_command(self) -> str:
        extra_args = []
        if self._staged_changes_status == StagedChangesStatus.NO_CHANGES:
            click.ClickException("No changes to commit")
        if self._staged_changes_status == StagedChangesStatus.NONE:
            extra_args.append("-a")
        return ["git", "commit", "-m", "{}", *extra_args]

    @cached_property
    def _staged_changes_status(self) -> StagedChangesStatus:
        result = subprocess.run(["git", "status"], capture_output=True, text=True)
        if result.returncode != 0:
            raise click.ClickException("Failed to get staged changes")
        # print(result)
        to_be_committed = "to be commited:" in result.stdout
        not_staged_for_commit = "not staged for commit:" in result.stdout
        if to_be_committed:
            if not_staged_for_commit:
                return StagedChangesStatus.SOME
            else:
                return StagedChangesStatus.ALL
        elif not_staged_for_commit:
            return StagedChangesStatus.NONE
        return StagedChangesStatus.NO_CHANGES


@llm.hookimpl
def register_commands(cli):
    @cli.command(
        name="commit"
    )  # TODO once it's working see if I can remove the name and it'll default properly)
    @click.option("-m", "--model", default=None, help="Specify the model to use")
    @click.option("-s", "--system", help="Custom system prompt")
    @click.option("-p", "--path", help="Path to the repository")
    @click.option("--key", help="API key to use")
    def commit(model, system, key, path):
        "Use an LLM to generate a commit message"
        from llm.cli import get_default_model

        # TODO something with args?
        path = path or os.getcwd()

        scm = GitSCM()
        if scm.detect_scm() is None:
            raise click.ClickException("Unknown SCM")

        command = scm.get_command()
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
        interactive_exec(full_command_str)


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
    return command


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
