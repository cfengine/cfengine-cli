from cfengine_cli.shell import user_command
from cfengine_cli.paths import bin
from cfengine_cli.version import cfengine_cli_version_string


def run() -> int:
    user_command(f"{bin('cf-agent')} -KIf update.cf && {bin('cf-agent')} -KI")
    return 0


def report() -> int:
    user_command(f"{bin('cf-agent')} -KIf update.cf && {bin('cf-agent')} -KI")
    user_command(f"{bin('cf-hub')} --query rebase -H 127.0.0.1")
    user_command(f"{bin('cf-hub')} --query delta -H 127.0.0.1")
    return 0


def help() -> int:
    print("Example usage:")
    print("cfengine run")
    return 0


def version() -> int:
    print(cfengine_cli_version_string())
    return 0
