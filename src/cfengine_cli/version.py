from importlib.metadata import version


def cfengine_cli_version_number():
    try:
        return version("cfengine")
    except:
        pass
    return "unknown (git checkout)"


def cfengine_cli_version_string():
    return f"CFEngine CLI {cfengine_cli_version_number()}"
