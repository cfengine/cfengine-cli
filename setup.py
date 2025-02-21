import setuptools
import subprocess
import os

cfengine_cli_version = (
    subprocess.run(["git", "describe", "--tags"], stdout=subprocess.PIPE)
    .stdout.decode("utf-8")
    .strip()
)

if "-" in cfengine_cli_version:
    # when not on tag, git describe outputs: "1.3.3-22-gdf81228"
    # pip has gotten strict with version numbers
    # so change it to: "1.3.3+22.git.gdf81228"
    # See: https://peps.python.org/pep-0440/#local-version-segments
    v, i, s = cfengine_cli_version.split("-")
    cfengine_cli_version = v + "+" + i + ".git." + s

assert "-" not in cfengine_cli_version
assert "." in cfengine_cli_version

assert os.path.isfile("cfengine_cli/version.py")
with open("cfengine_cli/VERSION", "w", encoding="utf-8") as fh:
    fh.write("%s\n" % cfengine_cli_version)

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="cfengine",
    version=cfengine_cli_version,
    author="Northern.tech, Inc.",
    author_email="contact@northern.tech",
    description="Human-oriented CLI for interacting with CFEngine tools",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cfengine/cfengine-cli",
    packages=setuptools.find_packages(),
    package_data={"cfengine_cli": ["VERSION"]},
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.9",
    entry_points={"console_scripts": ["cfengine = cfengine_cli.main:main"]},
    install_requires=[
        "cfbs >= 4.3.1",
        "cf-remote >= 0.6.2",
    ],
)
