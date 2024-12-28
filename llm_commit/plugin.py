import llm


def generate_commit_message(args):
    """Generate a commit message using a language model."""
    prompt = f"Write a concise Git commit message for: {args.description}"
    response = llm.complete(prompt)
    print(response)


def register_llm_plugin(plugin):
    plugin.register_command(
        "commit-msg",
        generate_commit_message,
        description="Generate a Git commit message using LLM",
        arguments=[
            {
                "name": "description",
                "help": "Description of the change to generate a commit message for",
                "required": True,
            }
        ],
    )
