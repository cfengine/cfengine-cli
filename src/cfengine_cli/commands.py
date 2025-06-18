import os
from cfengine_cli.lint import lint_cfbs_json, lint_json, lint_policy_file
from cfengine_cli.shell import user_command
from cfengine_cli.paths import bin
from cfengine_cli.version import cfengine_cli_version_string
from cfengine_cli.format import format_policy_file, format_json_file
from cfbs.utils import find, user_error


def require_cfagent():
    if not os.path.exists(bin("cf-agent")):
        user_error(f"cf-agent not found at {bin('cf-agent')}")


def require_cfhub():
    if not os.path.exists(bin("cf-hub")):
        user_error(f"cf-hub not found at {bin('cf-hub')}")


def format() -> int:
    for filename in find(".", extension=".json"):
        if filename.startswith("./."):
            continue
        format_json_file(filename)
    for policy_file in find(".", extension=".cf"):
        if policy_file.startswith("./."):
            continue
        format_policy_file(policy_file)
    return 0


def lint() -> int:
    errors = 0
    for filename in find(".", extension=".json"):
        if filename.startswith("./."):
            continue
        if filename.endswith("/cfbs.json"):
            lint_cfbs_json(filename)
            continue
        errors += lint_json(filename)

    for filename in find(".", extension=".cf"):
        if filename.startswith("./."):
            continue
        errors += lint_policy_file(filename)

    if errors == 0:
        return 0
    return 1


def report() -> int:
    require_cfhub()
    require_cfagent()
    user_command(f"{bin('cf-agent')} -KIf update.cf && {bin('cf-agent')} -KI")
    user_command(f"{bin('cf-hub')} --query rebase -H 127.0.0.1")
    user_command(f"{bin('cf-hub')} --query delta -H 127.0.0.1")
    return 0


def run() -> int:
    require_cfagent()
    user_command(f"{bin('cf-agent')} -KIf update.cf && {bin('cf-agent')} -KI")
    return 0


def help() -> int:
    print("Example usage:")
    print("cfengine run")
    return 0


def version() -> int:
    print(cfengine_cli_version_string())
    return 0
