from enum import Enum, auto

import os
import subprocess
import click
import llm

from prompt_toolkit import PromptSession
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.patch_stdout import patch_stdout
from pygments.lexers.shell import BashLexer

from llm.plugins import hookimpl

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


@hookimpl
def register_commands(cli):
    @cli.command()
    @click.option("-m", "--model", default=None, help="Specify the model to use")
    @click.option("-s", "--system", help="Custom system prompt")
    @click.option("--key", help="API key to use")
    def commit(model, system, key):
        "Use an LLM to generate a commit message"
        from llm.cli import get_default_model

        changes = scm_changes()
        prompt = prompt_from_changes(changes)
        model = model or get_default_model()
        model_id = model or get_default_model()
        model_obj = llm.get_model(model_id)
        if model_obj.needs_key:
            model_obj.key = llm.get_key(key, model_obj.needs_key, model_obj.key_env_var)
        result = model_obj.prompt(prompt, system=system or SYSTEM_PROMPT)
        interactive_exec(str(result))

        click.echo("Hello world!")

    # def generate_commit_message(args):
    #     """Generate a commit message using a language model."""
    #     prompt = f"Write a concise Git commit message for: {args.changes}"
    #     response = llm.complete(prompt)
    #     print(response)

    # register_command(
    #     "commit",
    #     generate_commit_message,
    #     description="Generate a Git commit message using LLM",
    #     arguments=[
    #         {
    #             "name": "changes",
    #             "help": "Changes to generate a commit message for",
    #             "required": True,
    #         }
    #     ],
    # )


def detect_scm():
    if os.path.exists(".git"):
        return "git"
    return None


def scm_changes():
    scm_type = detect_scm()
    if scm_type != "git":
        raise click.ClickException(f"Unsupported SCM: {scm_type}")
    return git_scm_changes()


class StagedChangesStatus(Enum):
    NONE = auto()  # No changes are staged
    SOME = auto()  # Some changes are staged, some are not
    ALL = auto()  # All changes are staged


def staged_changes_status():
    match


def git_scm_changes():
    staged_changes = staged_changes_status()
    if staged_changes == StagedChangesStatus.NONE:
        stage_all_changes()
    changes = get_staged_changes()
    return changes


def interactive_exec(command):
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
