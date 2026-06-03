import os

from cfengine_cli.paths import cfengine_config_dir, cfengine_cache_dir, bin


def test_cfengine_cache_dir():
    a = os.path.abspath(os.path.expanduser(cfengine_cache_dir()))
    b = os.path.abspath(os.path.expanduser("~/.cache/cfengine"))

    assert a == b

    a = os.path.abspath(os.path.expanduser(cfengine_cache_dir("subdir")))
    b = os.path.abspath(os.path.expanduser("~/.cache/cfengine/subdir"))

    assert a == b


def test_cfengine_conf_dir():
    a = os.path.abspath(os.path.expanduser(cfengine_config_dir()))
    b = os.path.abspath(os.path.expanduser("~/.config/cfengine"))

    assert a == b

    a = os.path.abspath(os.path.expanduser(cfengine_config_dir("subdir")))
    b = os.path.abspath(os.path.expanduser("~/.config/cfengine/subdir"))

    assert a == b


def test_bin():
    assert bin("cf-agent") == "/var/cfengine/bin/cf-agent"
    assert bin("cf-hub") == "/var/cfengine/bin/cf-hub"
