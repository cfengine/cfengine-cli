import os
import re
import json
import yaml
from cfengine_cli.profile import profile_cfengine, generate_callstack
from cfengine_cli.dev import dispatch_dev_subcommand
from cfengine_cli.lint import lint_args
from cfengine_cli.shell import user_command
from cfengine_cli.paths import bin
from cfengine_cli.version import cfengine_cli_version_string
from cfengine_cli.format import format_paths
from cfengine_cli.utils import UserError
from cfengine_cli.up import validate_config, up_do, resolve_templates
from cfbs.commands import build_command
from cf_remote.commands import deploy as deploy_command
from cf_remote.paths import cf_remote_dir
from pydantic import ValidationError


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


def format(names, line_length, check) -> int:
    return format_paths(names, line_length, check)


def _lint(files, strict, syntax_path) -> int:
    if not files:
        return lint_args(["."], strict, syntax_path)
    return lint_args(files, strict, syntax_path)


def lint(files, strict, syntax_path) -> int:
    errors = _lint(files, strict, syntax_path)
    if errors == 0:
        print("Success, no errors found.")
    elif errors == 1:
        print("Failure, 1 error in total.")
    else:
        print(f"Failure, {errors} errors in total.")
    return errors


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


def profile(args) -> int:
    data = None
    with open(args.profiling_input, "r") as f:
        m = re.search(r"\[[.\s\S]*\]", f.read())
        if m is not None:
            data = json.loads(m.group(0))

    if data is not None and any([args.bundles, args.functions, args.promises]):
        profile_cfengine(data, args)

    if args.flamegraph:
        generate_callstack(data, args.flamegraph)

    return 0


def up(args) -> int:
    content = None
    try:
        with open(args.config, "r") as f:
            content = yaml.safe_load(f)
    except yaml.YAMLError:
        raise UserError("'%s' is not valid yaml" % args.config)
    except FileNotFoundError:
        raise UserError("'%s' doesn't exist" % args.config)

    new_group = resolve_templates(content)
    try:
        new_config = validate_config(new_group)
    except ValidationError as v:
        msgs = []
        for err in v.errors():
            msgs.append(
                f"{err['msg']}. Input '{err['input']}' at location '{err['loc']}'"
            )
        raise UserError("\n".join(msgs))

    if args.validate:
        return 0

    old_group = {}
    try:
        if not args.reset:
            with open(os.path.join(cf_remote_dir(), "old_groups.yaml"), "r") as f:
                old_group = yaml.safe_load(f)
        else:
            os.remove(os.path.join(cf_remote_dir(), "old_groups.yaml"))
    except:
        pass
    if old_group != {}:
        try:
            validate_config(old_group)
        except ValidationError as v:
            msgs = []
            for err in v.errors():
                msgs.append(
                    f"{err['msg']}. Input '{err['input']}' at location '{err['loc']}'"
                )
            raise UserError("\n".join(msgs))

    is_ok = up_do(old_group, new_group, new_config)

    if is_ok:
        with open(os.path.join(cf_remote_dir(), "old_groups.yaml"), "w") as f:
            yaml.dump(new_group, f, default_flow_style=False, sort_keys=False)
    return 0
