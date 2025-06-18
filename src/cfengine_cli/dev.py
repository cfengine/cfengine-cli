from cfbs.commands import generate_release_information_command
from cfengine_cli.utils import UserError
from cfengine_cli.dependency_tables import update_dependency_tables
from cfengine_cli.docs_formatting import update_docs


def _continue_prompt() -> bool:
    answer = None
    while answer not in ("y", "n", "yes", "no"):
        print("Continue? (Y/n): ", end="")
        answer = input().strip().lower()
    return answer in ("y", "yes")


def _repo_notice(repo) -> bool:
    print(f"Note: This command is intended to be run in the {repo} repo")
    print(f"      https://github.com/cfengine/{repo}")
    answer = _continue_prompt()
    return answer


def dependency_tables() -> int:
    answer = _repo_notice("buildscripts")
    if answer:
        return update_dependency_tables()
    return 1


def docs_formatting() -> int:
    answer = _repo_notice("documentation")
    if answer:
        return update_docs()
    return 1


def release_information() -> int:
    answer = _repo_notice("release-information")
    if answer:
        generate_release_information_command()
        return 0
    return 1


def dispatch_dev_subcommand(subcommand) -> int:
    if subcommand == "dependency-tables":
        return dependency_tables()
    if subcommand == "docs-formatting":
        return docs_formatting()
    if subcommand == "release-information":
        return release_information()

    raise UserError("Invalid cfengine dev subcommand - " + subcommand)
