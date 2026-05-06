"""YAML file validation.

Checks that a YAML file parses successfully (per the PyYAML safe loader)
and is not empty. Null documents (e.g. a bare `---`) are accepted.
"""

import yaml


def check_yml_file(filename: str) -> str | None:
    """Check a YAML file: parses, and is not empty.

    Null documents (a bare document marker with no content) are accepted;
    only files where PyYAML produces no documents at all are rejected.

    Returns None if valid, otherwise a short description of the problem.
    """
    try:
        with open(filename, "r") as f:
            documents = list(yaml.safe_load_all(f))
    except (OSError, yaml.YAMLError) as e:
        return str(e)
    if not documents:
        return "empty file"
    return None
