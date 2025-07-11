import os
from cfbs.commands import generate_release_information_command
from cfengine_cli.utils import UserError
from cfengine_cli.deptool import (
    update_dependency_tables,
    print_release_dependency_tables,
)
from cfengine_cli.docs import update_docs, check_docs


def _continue_prompt() -> bool:
    answer = None
    while answer not in ("y", "n", "yes", "no"):
        print("Continue? (Y/n): ", end="")
        answer = input().strip().lower()
    return answer in ("y", "yes")


def _expect_repo(repo) -> bool:
    cwd = os.getcwd()
    if cwd.endswith(repo):
        return True
    print(f"Note: This command is intended to be run in the {repo} repo")
    print(f"      https://github.com/cfengine/{repo}")
    answer = _continue_prompt()
    return answer


def deps_readme() -> int:
    answer = _expect_repo("buildscripts")
    if answer:
        return update_dependency_tables()
    return 1


def deps_release(args) -> int:
    answer = _expect_repo("buildscripts")
    if answer:
        return print_release_dependency_tables(args)
    return 1


def docs_format() -> int:
    answer = _expect_repo("documentation")
    if answer:
        return update_docs()
    return 1


def docs_check() -> int:
    answer = _expect_repo("documentation")
    if answer:
        return check_docs()
    return 1


def release_information() -> int:
    answer = _expect_repo("release-information")
    if answer:
        generate_release_information_command()
        return 0
    return 1


def dispatch_dev_subcommand(subcommand, args) -> int:
    if subcommand == "deps-readme":
        return deps_readme()
    if subcommand == "deps-release":
        return deps_release(args)
    if subcommand == "docs-format":
        return docs_format()
    if subcommand == "docs-check":
        return docs_check()
    if subcommand == "release-information":
        return release_information()

    raise UserError("Invalid cfengine dev subcommand - " + subcommand)
