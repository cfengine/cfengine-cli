import argparse
import os
import sys

from cfengine_cli import log
from cfengine_cli import version
from cfengine_cli import commands
from cf_remote.utils import (
    user_error,
)
from cf_remote.utils import cache


def print_version_info():
    print("CFEngine CLI version %s" % version.string())


@cache
def _get_arg_parser():
    ap = argparse.ArgumentParser(
        description="Human-oriented CLI for interacting with CFEngine tools",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    ap.add_argument(
        "--log-level",
        help="Specify level of logging: DEBUG, INFO, WARNING, ERROR, or CRITICAL",
        type=str,
        default="WARNING",
    )
    ap.add_argument(
        "--version",
        "-V",
        help="Print or specify version",
        nargs="?",
        type=str,
        const=True,
    )

    command_help_hint = (
        "Commands (use %s COMMAND --help to get more info)"
        % os.path.basename(sys.argv[0])
    )
    subp = ap.add_subparsers(dest="command", title=command_help_hint)

    subp.add_parser("help", help="Print help information")

    subp.add_parser(
        "run", help="Run the CFEngine agent, evaluating and enforcing policy"
    )

    subp.add_parser(
        "update", help="Update the policy, downloading it from the policy server"
    )

    return ap


def get_args():
    ap = _get_arg_parser()
    args = ap.parse_args()
    return args


def run_command_with_args(command, _):
    if command == "info":
        return commands.info()
    if command == "run":
        return commands.run()
    if command == "update":
        return commands.update()
    user_error("Unknown command: '{}'".format(command))


def validate_command(_command, _args):
    pass


def main():
    args = get_args()
    if args.log_level:
        log.set_level(args.log_level)
    validate_command(args.command, args)

    exit_code = run_command_with_args(args.command, args)
    assert type(exit_code) is int
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
