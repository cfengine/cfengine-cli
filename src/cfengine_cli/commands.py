import sys
import os
from cfengine_cli.dev import dispatch_dev_subcommand
from cfengine_cli.lint import lint_cfbs_json, lint_json, lint_policy_file
from cfengine_cli.shell import user_command
from cfengine_cli.paths import bin
from cfengine_cli.version import cfengine_cli_version_string
from cfengine_cli.format import (
    format_policy_file,
    format_json_file,
    format_policy_fin_fout,
)
from cfengine_cli.utils import UserError
from cfbs.utils import find
from cfbs.commands import build_command
from cf_remote.commands import deploy as deploy_command


def _require_cfagent():
    if not os.path.exists(bin("cf-agent")):
        raise UserError(f"cf-agent not found at {bin('cf-agent')}")


def _require_cfhub():
    if not os.path.exists(bin("cf-hub")):
        raise UserError(f"cf-hub not found at {bin('cf-hub')}")


def help() -> int:
    print("Example usage:")
    print("cfengine run")
    return 0


def version() -> int:
    print(cfengine_cli_version_string())
    return 0


def build() -> int:
    r = build_command()
    return r


def deploy() -> int:
    r = deploy_command(None, None)
    return r


def _format_filename(filename):
    if filename.startswith("./."):
        return
    if filename.endswith(".json"):
        format_json_file(filename)
        return
    if filename.endswith(".cf"):
        format_policy_file(filename)
        return
    raise UserError(f"Unrecognized file format: {filename}")


def _format_dirname(directory):
    for filename in find(directory, extension=".json"):
        _format_filename(filename)
    for filename in find(directory, extension=".cf"):
        _format_filename(filename)


def format(args) -> int:
    if not args:
        _format_dirname(".")
        return 0
    if len(args) == 1 and args[0] == "-":
        # Special case, format policy file from stdin to stdout
        format_policy_fin_fout(sys.stdin, sys.stdout)
        return 0

    for arg in args:
        if arg == "-":
            raise UserError(
                "The - argument has a special meaning and cannot be combined with other paths"
            )
        if not os.path.exists(arg):
            raise UserError(f"{arg} does not exist")
        if os.path.isfile(arg):
            _format_filename(arg)
            continue
        if os.path.isdir(arg):
            _format_dirname(arg)
            continue
    return 0


def lint() -> int:
    errors = 0
    for filename in find(".", extension=".json"):
        if filename.startswith(("./.", "./out/")):
            continue
        if filename.endswith("/cfbs.json"):
            lint_cfbs_json(filename)
            continue
        errors += lint_json(filename)

    for filename in find(".", extension=".cf"):
        if filename.startswith(("./.", "./out/")):
            continue
        errors += lint_policy_file(filename)

    if errors == 0:
        return 0
    return 1


def report() -> int:
    _require_cfhub()
    _require_cfagent()
    user_command(f"{bin('cf-agent')} -KIf update.cf && {bin('cf-agent')} -KI")
    user_command(f"{bin('cf-hub')} --query rebase -H 127.0.0.1")
    user_command(f"{bin('cf-hub')} --query delta -H 127.0.0.1")
    return 0


def run() -> int:
    _require_cfagent()
    user_command(f"{bin('cf-agent')} -KIf update.cf && {bin('cf-agent')} -KI")
    return 0


def dev(subcommand, args) -> int:
    return dispatch_dev_subcommand(subcommand, args)
