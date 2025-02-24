import os


def cfengine_cli_version_number():
    try:
        with open(os.path.dirname(__file__) + "/VERSION", "r", encoding="utf-8") as fh:
            version = fh.read().strip()
            if version:
                return version
    except:
        pass
    return "unknown (git checkout)"


def cfengine_cli_version_string():
    return f"CFEngine CLI {cfengine_cli_version_number()}"
