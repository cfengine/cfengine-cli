from pydantic import BaseModel, model_validator, Field
from typing import Union, Literal, Optional, List, Annotated

import cfengine_cli.validate as validate
from cfengine_cli.utils import UserError

from cf_remote import log
from cf_remote import commands
from cf_remote import utils
from cf_remote import paths
from cf_remote import aramid

import textwrap
import yaml

from collections import defaultdict


# Forces pydantic to throw validation error if config contains unknown keys
class NoExtra(BaseModel, extra="forbid"):
    pass


class Config(NoExtra):
    pass


class AWSConfig(Config):
    image: str
    size: Optional[Literal["micro", "xlarge"]] = None
    region: Optional[str] = None

    @model_validator(mode="after")
    def check_aws_config(self):
        validate.validate_aws_image(self.image)
        return self


class VagrantConfig(Config):
    box: str
    memory: int = 512
    cpus: int = 1
    sync_folder: Optional[str] = None
    provision: Optional[str] = None

    @model_validator(mode="after")
    def check_vagrant_config(self):
        if self.memory < 512:
            raise UserError("Cannot allocate less than 512MB to a Vagrant VM")
        if self.cpus < 1:
            raise UserError("Cannot use less than 1 cpu per Vagrant VM")

        validate.validate_vagrant_box(self.box)

        return self


class GCPConfig(Config):
    image: str  # There is no list of available GCP platforms to validate against yet
    network: Optional[str] = None
    public_ip: bool = True
    size: Optional[str] = None
    region: Optional[str] = None


class AWSProvider(Config):
    provider: Literal["aws"]
    aws: AWSConfig

    @model_validator(mode="after")
    def check_aws_provider(self):
        validate.validate_aws_credentials()
        return self


class GCPProvider(Config):
    provider: Literal["gcp"]
    gcp: GCPConfig

    @model_validator(mode="after")
    def check_gcp_provider(self):
        validate.validate_gcp_credentials()
        return self


class VagrantProvider(Config):
    provider: Literal["vagrant"]
    vagrant: VagrantConfig


class SaveMode(Config):
    mode: Literal["save"]
    hosts: List[str]


class SpawnMode(Config):
    mode: Literal["spawn"]
    # "Field" forces pydantic to report errors on the branch defined by the field "mode"
    spawn: Annotated[
        Union[VagrantProvider, AWSProvider, GCPProvider],
        Field(discriminator="provider"),
    ]
    count: int

    @model_validator(mode="after")
    def check_spawn_config(self):
        if self.count < 1:
            raise UserError("Cannot spawn less than 1 instance")
        return self


class CFEngineConfig(Config):
    version: Optional[str] = None
    bootstrap: Optional[str] = None
    edition: Literal["community", "enterprise"] = "enterprise"
    remote_download: bool = False
    hub_package: Optional[str] = None
    client_package: Optional[str] = None
    package: Optional[str] = None
    demo: bool = False
    insecure: bool = False
    call_collect: bool = False
    trust_keys: Optional[List[str]] = None

    @model_validator(mode="after")
    def check_cfengine_config(self):
        packages = [self.package, self.hub_package, self.client_package]
        for p in packages:
            validate.validate_package(p, self.remote_download)

        if self.version and any(packages):
            log.warning("Specifying package overrides cfengine version")

        validate.validate_version(self.version, self.edition)
        validate.validate_state_bootstrap(self.bootstrap)

        return self


class GroupConfig(Config):
    role: Literal["client", "hub"]
    # "Field" forces pydantic to report errors on the branch defined by the field "provider"
    source: Annotated[Union[SaveMode, SpawnMode], Field(discriminator="mode")]
    cfengine: Optional[CFEngineConfig] = None
    scripts: Optional[List[str]] = None

    @model_validator(mode="after")
    def check_group_config(self):
        if (
            self.role == "hub"
            and self.source.mode == "spawn"
            and self.source.count != 1
        ):
            raise UserError("A hub can only have one host")

        return self


def _resolve_templates(parent, templates):
    if not parent:
        return
    if isinstance(parent, dict):
        for key, value in parent.items():
            if isinstance(value, str) and value in templates:
                parent[key] = templates[value]
            else:
                _resolve_templates(value, templates)
    if isinstance(parent, list):
        for value in parent:
            _resolve_templates(value, templates)


def resolve_templates(content):
    if not content:
        raise UserError("Empty spawn config")

    if "groups" not in content:
        raise UserError("Missing 'groups' key in spawn config")

    groups = content["groups"]
    if groups is None:
        return {}

    templates = content.get("templates")
    if templates:
        _resolve_templates(groups, templates)

    return groups


def validate_config(groups):

    state = {}
    for k, v in groups.items():
        state[k] = GroupConfig(**v)

    return state


def generate_diff(old_state, new_state):
    spawn = []
    destroy = []
    install = []
    uninstall = []

    to_print = defaultdict(list)

    for key in old_state.keys() | new_state.keys():
        if key in old_state.keys() & new_state.keys():
            if old_state[key]["source"] != new_state[key]["source"]:
                destroy.append(key)
                spawn.append(key)

                old_text = textwrap.indent(
                    yaml.dump({"source": old_state[key]["source"]}), "- "
                )
                new_text = textwrap.indent(
                    yaml.dump({"source": new_state[key]["source"]}), "+ "
                )
                to_print[key].append(old_text + new_text)

            if old_state[key]["role"] != new_state[key]["role"]:
                if key not in destroy:
                    uninstall.append(key)
                install.append(key)

                old_text = textwrap.indent(
                    yaml.dump({"role": old_state[key]["role"]}), "- "
                )
                new_text = textwrap.indent(
                    yaml.dump({"role": new_state[key]["role"]}), "+ "
                )
                to_print[key].append(old_text + new_text)

            if old_state[key].get("cfengine", None) != new_state[key].get(
                "cfengine", None
            ):
                if key not in destroy:
                    uninstall.append(key)
                install.append(key)

                old_text = (
                    textwrap.indent(
                        yaml.dump({"cfengine": old_state[key]["cfengine"]}), "- "
                    )
                    if "cfengine" in old_state[key]
                    else ""
                )
                new_text = (
                    textwrap.indent(
                        yaml.dump({"cfengine": new_state[key]["cfengine"]}), "+ "
                    )
                    if "cfengine" in old_state
                    else ""
                )
                to_print[key].append(old_text + new_text)

        elif key not in old_state:
            spawn.append(key)
            if "cfengine" in new_state[key]:
                install.append(key)

            new_text = textwrap.indent(yaml.dump(new_state[key]), "+ ")
            to_print[key].append(new_text)
        elif key not in new_state:
            destroy.append(key)

            old_text = textwrap.indent(yaml.dump(old_state[key]), "- ")
            to_print[key].append(old_text)

    for group_name, changes in to_print.items():
        print(f"{group_name}:")
        for change in changes:
            print(change)

    return spawn, destroy, install, uninstall


def spawn_from_config(group_name, config):
    match config.source.mode:
        case "spawn":
            args = {
                "group_name": group_name,
                "count": config.source.count,
                "role": config.role,
            }

            match config.source.spawn.provider:
                case "vagrant":
                    args |= {
                        "provider": commands.Providers.VAGRANT,
                        "size": config.source.spawn.vagrant.memory,
                        "platform": config.source.spawn.vagrant.box,
                        "vagrant_cpus": config.source.spawn.vagrant.cpus,
                        "vagrant_sync_folder": config.source.spawn.vagrant.sync_folder,
                        "vagrant_provision": config.source.spawn.vagrant.provision,
                    }
                case "aws":
                    args |= {
                        "provider": commands.Providers.AWS,
                        "platform": config.source.spawn.aws.image,
                        "size": config.source.spawn.aws.size,
                        "region": config.source.spawn.aws.region,
                    }
                case "gcp":
                    args |= {
                        "provider": commands.Providers.GCP,
                        "platform": config.source.spawn.gcp.image,
                        "network": config.source.spawn.gcp.network,
                        "public_ip": config.source.spawn.gcp.public_ip,
                        "size": config.source.spawn.gcp.size,
                        "region": config.source.spawn.gcp.region,
                    }

            commands.spawn(**args)
        case "save":
            commands.save(name=group_name, hosts=config.source.hosts, role=config.role)


def poll_connection(public_ip):
    users = [
        "Administrator",
        "admin",
        "ubuntu",
        "ec2-user",
        "centos",
        "vagrant",
        "root",
    ]
    if utils.whoami() not in users:
        users = [utils.whoami()] + users

    i = 0

    while True:
        try:
            hosts = [aramid.Host(public_ip[0], user=users[i])]
            aramid.execute(
                hosts, "whoami", echo=False, echo_cmd=False, ignore_failed=False
            )
            return

        except aramid.AramidError:
            pass

        i = (i + 1) % len(users)


def install_from_config(key, public_ips, configs, private_ips):
    ip = public_ips[key]
    config = configs[key]
    bootstrap_key = config.cfengine.bootstrap

    if bootstrap_key is not None:
        if bootstrap_key not in private_ips:
            raise UserError(f"Group '{key}' doesn't have private ips")
        bootstrap = private_ips[bootstrap_key]
    else:
        bootstrap = None

    if not config.cfengine:
        return

    args = {
        "bootstrap": bootstrap,
        "package": config.cfengine.package,
        "hub_package": config.cfengine.hub_package,
        "client_package": config.cfengine.client_package,
        "version": config.cfengine.version,
        "demo": config.cfengine.demo,
        "call_collect": config.cfengine.call_collect,
        "edition": config.cfengine.edition,
        "remote_download": config.cfengine.remote_download,
        "insecure": config.cfengine.insecure,
        "trust_keys": config.cfengine.trust_keys,
        "hubs": None,
        "clients": None,
    }
    if config.role == "hub":
        args["hubs"] = ip
    else:
        args["clients"] = ip

    commands.install(**args)


def up_do(old_state, new_state, config):

    spawn, destroy, install, uninstall = generate_diff(old_state, new_state)

    data = utils.read_json(paths.CLOUD_STATE_FPATH)
    if data is None:
        data = {}

    for key in destroy:
        print("Destroying '%s'" % key)
        if f"@{key}" not in data:
            raise UserError("Cannot destroy %s: group doesn't exist" % key)
        commands.destroy(key)

    for key in spawn:
        print("Spawning '%s'" % key)
        spawn_from_config(key, config[key])

    data = utils.read_json(paths.CLOUD_STATE_FPATH)
    if data is None:
        data = {}

    public_ips = {}
    private_ips = {}
    for group, group_info in data.items():
        group = group[1:]
        for host, host_info in group_info.items():
            if host == "meta":
                continue

            if "public_ips" in host_info:
                public_ips[group] = [host_info["public_ips"][0]]

            if "private_ips" in host_info:
                private_ips[group] = [host_info["private_ips"][0]]

    for key in uninstall:
        print("Uninstalling CFEngine on '%s'" % key)
        if f"@{key}" not in data:
            raise UserError("Cannot uninstall %s: group doesn't exist" % key)
        commands.uninstall(public_ips, purge=True)

    install = sorted(install, key=lambda x: config[x].role)[::-1]
    for key in install:
        # We poll the VM to be sure it is up, otherwise the installation starts and fails
        poll_connection(public_ips[key])

        print("Installing CFEngine on '%s'" % key)
        install_from_config(key, public_ips, config, private_ips)

    return True
