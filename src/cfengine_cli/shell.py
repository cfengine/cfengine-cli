import os


def user_command(cmd):
    """Run a command which was requested by the user.

    For example if the user typed cfengine run, we
    run the shell command `/var/cfengine/bin/cf-agent -KI`.

    Be transparent about the command, printing it first,
    so the user has visibility of what is happening and
    can learn the underlying tools over time.

    We might expand this in the future with more logging,
    confirmation prompts, etc.
    """

    print(f"Running command: '{cmd}'")
    os.system(cmd)


def silent_command(cmd):
    """Under-the-hood shell commands which the user does not
    need to know about.
    """

    os.system(cmd)
