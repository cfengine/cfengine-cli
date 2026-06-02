from cf_remote.paths import CLOUD_CONFIG_FPATH, CLOUD_STATE_FPATH
from cf_remote.utils import read_json, is_package_url
from cf_remote.spawn import (
    Providers,
    get_cloud_driver,
    InvalidCredsError,
    AWSCredentials,
    GCPCredentials,
)
from cf_remote.cloud_data import aws_image_criteria
from cf_remote.remote import Releases

from cfengine_cli.utils import UserError

import os
import subprocess

cmd_cache = {}


def validate_state_bootstrap(bootstrap):
    state = read_json(CLOUD_STATE_FPATH)
    if state is None:
        return
    key = f"@{bootstrap}"

    # TODO: Change how to check this if cloud_state.json changes format
    if key in state and list(state[key].values())[1]["role"] != "hub":
        raise UserError("Cannot bootstrap to an existing host that is not a hub")


def validate_package(package, remote_download=False):
    if package is None:
        return

    if remote_download and not is_package_url(package):
        raise UserError(f"Package '{package}' is not a valid package URL")


def validate_version(version, edition):
    releases = Releases(edition)
    release = releases.default
    if version:
        release = releases.pick_version(version)
    if release is None:
        raise UserError(
            f"Could not find a release for version '{version}'. The supported versions are '{releases}'"
        )

    return release


def validate_vagrant_box(box):
    cmd = ("vagrant", "box", "list")
    if cmd in cmd_cache:
        cmd_output = cmd_cache[cmd]
    else:
        ret = subprocess.run(cmd, capture_output=True, text=True)
        cmd_output = ret.stdout
        cmd_cache[cmd] = cmd_output

    box_list = [
        line.split()[0] for line in cmd_output.split("\n") if len(line.split()) > 0
    ]

    if box not in box_list:
        raise UserError(f"Box '{box}' is not installed or doesn't exist")


def validate_aws_image(platform):
    platform_name = platform.split("-")[0]
    if platform_name not in aws_image_criteria:
        raise UserError(
            f"Platform '{platform}' is not in our set of image criteria. (Available platforms: {', '.join(aws_image_criteria.keys())})"
        )


def _get_aws_creds_from_env():
    if "AWS_ACCESS_KEY_ID" in os.environ and "AWS_SECRET_ACCESS_KEY" in os.environ:
        return AWSCredentials(
            os.environ["AWS_ACCESS_KEY_ID"],
            os.environ["AWS_SECRET_ACCESS_KEY"],
            os.environ.get("AWS_SESSION_TOKEN", ""),
        )
    return None


def validate_aws_credentials():
    creds_data = None
    if os.path.exists(CLOUD_CONFIG_FPATH):
        creds_data = read_json(CLOUD_CONFIG_FPATH)

    if not creds_data:
        raise UserError(f"Cloud configuration not found at '{CLOUD_CONFIG_FPATH}'")
    creds = None
    try:
        creds = _get_aws_creds_from_env() or AWSCredentials(
            creds_data["aws"]["key"],
            creds_data["aws"]["secret"],
            creds_data["aws"].get("token", ""),
        )
    except KeyError:
        raise UserError("Incomplete AWS credential info")  # TODO: report missing keys

    region = creds_data["aws"].get("region", "eu-west-1")
    sec_groups = creds_data["aws"]["security_groups"]
    key_pair = creds_data["aws"]["key_pair"]

    if creds:
        try:
            get_cloud_driver(Providers.AWS, creds, region)
        except InvalidCredsError as error:
            raise UserError(
                f"Invalid credentials, check cloud_config.json ({str(error)[1:-1]})"
            )
    return creds, region, sec_groups, key_pair


def validate_gcp_credentials():
    creds_data = None
    if os.path.exists(CLOUD_CONFIG_FPATH):
        creds_data = read_json(CLOUD_CONFIG_FPATH)

    if not creds_data:
        raise UserError(f"Cloud configuration not found at '{CLOUD_CONFIG_FPATH}'")
    try:
        creds = GCPCredentials(
            creds_data["gcp"]["project_id"],
            creds_data["gcp"]["service_account_id"],
            creds_data["gcp"]["key_path"],
        )
    except KeyError:
        raise UserError("Incomplete GCP credential info")  # TODO: report missing keys

    region = creds_data["gcp"].get("region", "europe-west1-b")

    return creds, region
