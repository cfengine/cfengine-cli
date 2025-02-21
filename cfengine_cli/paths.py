import re
import os
from cfengine_cli.utils import UserError
from cf_remote.paths import path_append


def cfengine_dir(subdir=None):
    """
    Returns the directory used by the Python tools for temporary files,
    global config, downloads, etc.

    Defaults to ~/.cfengine/, but can be overridden via the CFENGINE_DIR
    environment variable.
    """
    override_dir = os.getenv("CFENGINE_DIR")

    if override_dir:
        override_dir = os.path.normpath(override_dir)
        parent = os.path.dirname(override_dir)

        if not os.path.exists(parent):
            raise UserError(
                "'{}' doesn't exist. Make sure this path is correct and exists.".format(
                    parent
                )
            )

        return path_append(override_dir, subdir)

    return path_append("~/.cfengine/", subdir)


def bin(component: str) -> str:
    """
    Get the path to a binary for use in a command.

    For example: "cf-agent" -> "/var/cfengine/bin/cf-agent"

    # Warning: Don't use this function with untrusted input.
    """
    # Stop things like semicolons, slashes, spaces, etc.
    # Only letters and dashes allowed currently.
    assert re.fullmatch(r"[-a-zA-Z]+", component)
    return f"/var/cfengine/bin/{component}"
