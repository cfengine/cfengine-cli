# CFEngine command line interface (CLI)

A CLI for humans to interact with CFEngine, enabling downloading and installing packages, building policy sets, deploying, and enforcing policy.
It is practically a wrapper around our other tools, like `cf-agent`, `cf-hub`, `cf-remote` and `cfbs`.

**Warning:** This is an early version.
Things might be missing or changed.
Proceed with caution and excitement.

## Installation

Install using pip:

```
pip install cfengine
```

## Usage

To perform an agent run:

```
cfengine run
```

To get additional help:

```
cfengine help
```

## Supported platforms and versions

This tool will only support a limited number of platforms, it is not int.
Currently we are targeting:

- Officially supported versions of macOS, Ubuntu, and Fedora.
- Officially supported versions of Python.

It is not intended to be installed on all hosts in your infrastructure.
CFEngine itself supports a wide range of platforms, but this tool is intended to run on your laptop, your workstation, or the hub in your infrastructure, not all the other hosts.

## Backwards compatibility

This CLI is entirely intended for humans.
If you put it into scripts and automation, expect it to break in the future.
In order to make the user experience better, we might add, change, or remove commands.
We will also be experimenting with different types of interactive prompts and input.

## Development, maintenance, contributions, and releases

Looking for more information related to contributing code, releasing new versions or otherwise maintaining the CFEngine CLI?
Please see the [HACKING.md](./HACKING.md) file.
