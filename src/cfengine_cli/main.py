import argparse
import os
import sys

from cf_remote import log
from cfengine_cli.version import cfengine_cli_version_string
from cfengine_cli import commands
from cfengine_cli.utils import UserError


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
        help="Print version number",
        action="version",
        version=f"{cfengine_cli_version_string()}",
    )

    command_help_hint = (
        "Commands (use %s COMMAND --help to get more info)"
        % os.path.basename(sys.argv[0])
    )
    subp = ap.add_subparsers(dest="command", title=command_help_hint)

    subp.add_parser("help", help="Print help information")
    subp.add_parser(
        "version",
        help="Print the version string",
    )
    subp.add_parser("build", help="Build a policy set from a CFEngine Build project")
    subp.add_parser("deploy", help="Deploy a built policy set")
    subp.add_parser("format", help="Autoformat .json and .cf files")
    subp.add_parser(
        "lint",
        help="Look for syntax errors and other simple mistakes",
    )
    subp.add_parser(
        "report",
        help="Run the agent and hub commands necessary to get new reporting data",
    )
    subp.add_parser(
        "run", help="Run the CFEngine agent, fetching, evaluating, and enforcing policy"
    )

    dev_parser = subp.add_parser(
        "dev", help="Utilities intended for developers / maintainers of CFEngine"
    )
    dev_subparsers = dev_parser.add_subparsers(dest="dev_command")
    dev_subparsers.add_parser("dependency-tables")
    dev_subparsers.add_parser("docs-format")
    dev_subparsers.add_parser("docs-check")
    dev_subparsers.add_parser("release-information")

    return ap


def get_args():
    ap = _get_arg_parser()
    args = ap.parse_args()
    return args


def run_command_with_args(args) -> int:
    if not args.command:
        raise UserError("No command specified - try 'cfengine help'")
    if args.command == "help":
        return commands.help()
    if args.command == "version":
        return commands.version()
    # The real commands:
    if args.command == "build":
        return commands.build()
    if args.command == "deploy":
        return commands.deploy()
    if args.command == "format":
        return commands.format()
    if args.command == "lint":
        return commands.lint()
    if args.command == "report":
        return commands.report()
    if args.command == "run":
        return commands.run()
    if args.command == "dev":
        return commands.dev(args.dev_command, args)
    raise UserError(f"Unknown command: '{args.command}'")


def validate_args(args):
    if args.command == "dev" and args.dev_command is None:
        raise UserError("Missing subcommand - cfengine dev <subcommand>")


def main():
    try:
        args = get_args()
        if args.log_level:
            log.set_level(args.log_level)
        validate_args(args)

        exit_code = run_command_with_args(args)
        assert type(exit_code) is int
        sys.exit(exit_code)
    except AssertionError as e:
        print(f"Error: {str(e)} (programmer error, please file a bug)")
        sys.exit(-1)
    except UserError as e:
        print(str(e))
        sys.exit(-1)


if __name__ == "__main__":
    main()
