# CFEngine CLI

A simple CLI for interacting with various CFEngine tools, such as cf-agent, cf-remote, cf-hub, cf-remote, and cfbs.

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
