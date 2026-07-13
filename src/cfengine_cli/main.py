import argparse
import os
import sys
import traceback
import pathlib
import subprocess

from cf_remote import log
from cfengine_cli.cfengine_wrapper import cfengine_commands
from cfengine_cli.version import cfengine_cli_version_string
from cfengine_cli import commands
from cfengine_cli.utils import UserError
from cf_remote.commands import spawn, list_boxes, list_platforms, init_cloud_config
from cf_remote.spawn import CFRUserError, Providers
from cfbs.utils import CFBSProgrammerError


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
    fmt = subp.add_parser("format", help="Autoformat .json and .cf files")
    fmt.add_argument("files", nargs="*", help="Files to format")
    fmt.add_argument("--line-length", default=80, type=int, help="Maximum line length")
    fmt.add_argument("--check", action="store_true")
    lnt = subp.add_parser(
        "lint",
        help="Look for syntax errors and other simple mistakes",
    )
    lnt.add_argument(
        "--strict",
        type=str,
        default="yes",
        help="Strict mode. Default=yes, checks for undefined promise types, bundles, bodies, functions",
    )
    lnt.add_argument(
        "--syntax-description",
        type=str,
        help="Lint based on a user given syntax description",
    )
    lnt.add_argument("files", nargs="*", help="Files to lint")
    report_parser = subp.add_parser(
        "report",
        help="Run the agent and hub commands necessary to get new reporting data",
    )
    report_parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Select which installation to use by name/IP (e.g. 'local' or '192.168.56.90'). "
        "If omitted and multiple installations of cf-agent+cf-hub are found, you'll be prompted.",
    )
    run_parser = subp.add_parser(
        "run", help="Run the CFEngine agent, fetching, evaluating, and enforcing policy"
    )
    run_parser.add_argument(
        "run_args",
        nargs="*",
        help="Command(s) to run with cf-agent",
    )
    run_parser.add_argument(
        "--host",
        type=str,
        default=None,
        help="Select which installation of cf-agent to use by name/IP (e.g. 'local' or '192.168.56.90'). "
        "If omitted and multiple installations are found, you'll be prompted.",
    )

    sp = subp.add_parser("spawn", help="Spawn hosts in the clouds")
    sp.add_argument(
        "--list-platforms", help="List supported platforms", action="store_true"
    )
    sp.add_argument(
        "--list-boxes", help="List installed vagrant boxes", action="store_true"
    )
    sp.add_argument(
        "--init-config",
        help="Initialize configuration file for spawn functionality",
        action="store_true",
    )
    sp.add_argument("--platform", help="Platform or vagrant box to use", type=str)
    sp.add_argument("--count", default=1, help="How many hosts to spawn", type=int)
    sp.add_argument(
        "--role", help="Role of the hosts", choices=["hub", "hubs", "client", "clients"]
    )
    sp.add_argument(
        "--name", help="Name of the group of hosts (can be used in other commands)"
    )
    sp.add_argument(
        "--append",
        help="Append the new VMs to a pre-existing group",
        action="store_true",
    )
    sp.add_argument(
        "--provider",
        help="VM provider",
        type=str,
        default="aws",
        choices=["aws", "gcp", "vagrant"],
    )
    sp.add_argument("--cpus", help="Number of CPUs of the vagrant instances", type=int)
    sp.add_argument(
        "--sync-folder",
        help="Root folder of synchronized folders of vagrant instance",
        type=str,
    )
    sp.add_argument(
        "--provision",
        help="full path to provision shell script for Vagrant VM",
        type=str,
    )
    sp.add_argument("--size", help="Size/type of the instances", type=str)
    sp.add_argument(
        "--network", help="network/subnet to assign the VMs to (GCP only)", type=str
    )
    sp.add_argument(
        "--no-public-ip",
        help="No public IP needed (GCP only; WARNING: The VMs will only be accessible"
        + " from some other VM in the same cloud/network!)",
        action="store_true",
    )

    dp = subp.add_parser("destroy", help="Destroy hosts spawned in the clouds")
    dp.add_argument(
        "--all", help="Destroy all hosts spawned in the clouds", action="store_true"
    )
    dp.add_argument("name", help="Name of the group of hosts to destroy", nargs="?")

    profile_parser = subp.add_parser(
        "profile", help="Parse CFEngine profiling output (cf-agent -Kp)"
    )
    profile_parser.add_argument(
        "profiling_input", help="Path to the profiling input file"
    )
    profile_parser.add_argument("--top", type=int, default=10)
    profile_parser.add_argument("--bundles", action="store_true")
    profile_parser.add_argument("--promises", action="store_true")
    profile_parser.add_argument("--functions", action="store_true")
    profile_parser.add_argument(
        "--flamegraph", type=str, help="Generate input file for ./flamegraph.pl"
    )

    dev_parser = subp.add_parser(
        "dev", help="Utilities intended for developers / maintainers of CFEngine"
    )
    dev_subparsers = dev_parser.add_subparsers(dest="dev_command")
    dev_subparsers.add_parser("update-dependency-tables")
    pdt = dev_subparsers.add_parser("print-dependency-tables")
    pdt.add_argument(
        "versions",
        nargs="+",
        help="Versions to compare (minimum 1 required)",
    )
    parser = dev_subparsers.add_parser("format-docs")
    parser.add_argument("files", nargs="*")
    parser = dev_subparsers.add_parser("lint-docs")
    parser.add_argument("files", nargs="*")
    parser = dev_subparsers.add_parser("syntax-tree")
    parser.add_argument("file", help="CFEngine policy file to print syntax tree for")
    parser = dev_subparsers.add_parser("generate-release-information")

    parser.add_argument(
        "--omit-download",
        help="Use existing masterfiles instead of downloading in 'cfengine dev generate-release-information'",
        action="store_true",
    )
    parser.add_argument(
        "--check-against-git",
        help="Check whether masterfiles from cfengine.com and github.com match in 'cfengine dev generate-release-information'",
        action="store_true",
    )
    parser.add_argument(
        "--from",
        help="Specify minimum version in 'cfengine dev generate-release-information'",
        dest="minimum_version",
    )

    up_parser = subp.add_parser(
        "up", help="Spawn and install with cf-remote from a yaml config"
    )
    up_parser.add_argument(
        "config", default="config.yaml", nargs="?", help="Path to yaml config"
    )
    up_parser.add_argument(
        "--validate", action="store_true", help="Validate the given config"
    )
    up_parser.add_argument(
        "--reset", action="store_true", help="Create a fresh new environment"
    )
    parser = dev_subparsers.add_parser(
        "generate-changelog",
        description="""Changelog generator for CFEngine repositories.

Auto-detects which repos to include based on the current working directory (core, masterfiles, enterprise)

Enterprise' changelog also reflects changes in mission-portal, nova and buildscripts (dependency-updates)
Core and Masterfiles only reflect themselves""",
        epilog="""Examples:
  - cfengine dev generate-changelog
    on 3.27.x this will check changelog for latest known (e.g. 3.27.1) and update the changelog for 3.27.1 -> 3.27.2

  - cfengine dev generate-changelog -o 3.26.0..3.27.0
    on any branch will print changelog from version 2.26.0 -> 3.27.0 to stdout""",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "-o",
        "--output",
        action="store_true",
        default=False,
        help="Write changelog to stdout instead of prepending to CHANGELOG.md",
    )
    parser.add_argument(
        "--show-version",
        action="store_true",
        dest="show_version",
        help="Print the version from .CFVERSION and exit",
    )
    parser.add_argument(
        "git_args",
        nargs="*",
        metavar="GIT_ARG",
        help="Commit range [other optional args], e.g. 3.27.0..origin/3.27.x",
    )
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
        return cfengine_commands.build()
    if args.command == "deploy":
        return cfengine_commands.deploy()
    if args.command == "format":
        return commands.format(args.files, args.line_length, args.check)
    if args.command == "lint":
        return commands.lint(
            args.files,
            (args.strict.lower() in ("y", "ye", "yes")),
            args.syntax_description,
        )
    if args.command == "report":
        return cfengine_commands.report(target=args.host)
    if args.command == "run":
        return cfengine_commands.run(*args.run_args, target=args.host)
    if args.command == "spawn":
        if args.list_platforms:
            return list_platforms()
        if args.list_boxes:
            return list_boxes()
        if args.init_config:
            return init_cloud_config()
        if args.name and "," in args.name:
            raise UserError("Group --name may not contain commas")
        if args.role and args.role.endswith("s"):
            # role should be singular
            args.role = args.role[:-1]
        if args.provider == "gcp":
            provider = Providers.GCP
        elif args.provider == "aws":
            provider = Providers.AWS
            if args.network:
                raise UserError("--network not supported for AWS")
            if args.no_public_ip:
                raise UserError("--no-public-ip not supported for AWS")
        else:
            assert args.provider == "vagrant"
            provider = Providers.VAGRANT

        if provider != Providers.VAGRANT:
            if args.cpus:
                raise UserError(f"--cpus not supported for {args.provider}")
            if args.sync_folder:
                raise UserError(f"--sync-folder not supported for {args.provider}")
            if args.provision:
                raise UserError(f"--provision not supported for {args.provider}")

        if args.network and (args.network.count("/") != 1):
            raise UserError(
                "Invalid network specified, needs to be in the network/subnet format"
            )

        return spawn(
            args.platform,
            args.count,
            args.role,
            args.name,
            provider=provider,
            size=args.size,
            network=args.network,
            public_ip=not args.no_public_ip,
            extend_group=args.append,
            vagrant_cpus=args.cpus,
            vagrant_sync_folder=args.sync_folder,
            vagrant_provision=args.provision,
        )
    if args.command == "destroy":
        return cfengine_commands.destroy(args.name, del_all=args.all)
    if args.command == "dev":
        return commands.dev(args.dev_command, args)
    if args.command == "profile":
        return commands.profile(args)
    if args.command == "up":
        return commands.up(args)
    raise UserError(f"Unknown command: '{args.command}'")


def validate_args(args):
    if args.command == "dev" and args.dev_command is None:
        raise UserError("Missing subcommand - cfengine dev <subcommand>")
    if (
        args.command == "spawn"
        and not args.list_platforms
        and not args.init_config
        and not args.list_boxes
    ):
        # The above options don't require any other options/arguments (TODO:
        # --provider), but otherwise all have to be given
        if not args.platform:
            raise UserError("--platform needs to be specified")
        if not args.count:
            raise UserError("--count needs to be specified")
        if not args.role:
            raise UserError("--role needs to be specified")
        if not args.name:
            raise UserError("--name needs to be specified")

    if args.command == "destroy":
        if not args.all and not args.name:
            raise UserError("Either '--all' or 'NAME' must be specified for destroy")
        if args.all and args.name:
            raise UserError(
                "Only one of '--all' or 'NAME' may be specified for destruction"
            )


def _main():
    args = get_args()
    if args.log_level:
        log.set_level(args.log_level)
    validate_args(args)
    return run_command_with_args(args)


def main():
    if os.getenv("CFBACKTRACE") == "1":
        r = _main()
        return r
    try:
        exit_code = _main()
        assert type(exit_code) is int
        sys.exit(exit_code)
    except (UserError, CFRUserError) as e:
        print(str(e))
        sys.exit(-1)
    # Exceptions below are not expected, print extra info:
    except subprocess.CalledProcessError as e:
        print(f"subprocess command failed: {' '.join(e.cmd)}")
    except AssertionError as e:
        tb = traceback.extract_tb(e.__traceback__)
        frame = tb[-1]
        this_file = pathlib.Path(__file__)
        cfbs_prefix = os.path.abspath(this_file.parent.parent.resolve())
        filename = os.path.abspath(frame.filename)
        # Opportunistically cut off beginning of path if possible:
        if filename.startswith(cfbs_prefix):
            filename = filename[len(cfbs_prefix) :]
            if filename.startswith("/"):
                filename = filename[1:]
        line = frame.lineno
        # Avoid using frame.colno - it was not available in python 3.5,
        # and even in the latest version, it is not declared in the
        # docstring, so you will get linting warnings;
        # https://github.com/python/cpython/blob/v3.13.5/Lib/traceback.py#L276-L288
        # column = frame.colno
        assertion = frame.line
        explanation = str(e)
        message = "Assertion failed - %s%s (%s:%s)" % (
            assertion,
            (" - " + explanation) if explanation else "",
            filename,
            line,
        )
        print("Error: " + message)
    except CFBSProgrammerError as e:
        print("Error: " + str(e))
    print(
        "       This is an unexpected error indicating a bug, please create a ticket at:"
    )
    print("       https://northerntech.atlassian.net/")
    print(
        "       (Rerun with CFBACKTRACE=1 in front of your command to show the full backtrace)"
    )

    # TODO: Handle other exceptions
    return 1


if __name__ == "__main__":
    main()
