from cfbs.commands import build_command
from cf_remote.commands import deploy as deploy_command
from cf_remote.commands import install as install_command
from cf_remote.commands import destroy as destroy_command

from cfengine_cli.cfengine_wrapper.cfengine_utils import (
    require_executable,
    require_installation,
)


def report(target: str | None = None) -> int:  # TODO? ENT-14122
    installation = require_installation(target)
    rc = installation.agent.run("-KIf update.cf", "-KI")
    if rc != 0:
        return rc
    return installation.hub.run(
        "--query rebase -H 127.0.0.1", "--query delta -H 127.0.0.1"
    )


def run(*args, target: str | None = None) -> int:
    agent = require_executable("cf-agent", target)
    if args:
        return agent.run(*args)
    return agent.run("-KIf update.cf", "-KI")


def install() -> int:  # TODO ENT-14117
    return install_command(None, None)


def destroy(groupname, del_all=False) -> int:
    if del_all:
        return destroy_command(None)
    return destroy_command(groupname)


def build() -> int:  # TODO ENT-14119
    return build_command()


def deploy() -> int:  # TODO ENT-14119
    return deploy_command(None, None)
