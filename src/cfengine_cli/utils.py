import subprocess
import re


class UserError(Exception):
    """Exception raised when a user has most likely made a mistake"""

    def __init__(self, message):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return f"Error: {self.message}"


def get_upstream_remote(repo_name, repo_owner, repo_path):
    upstream = r"github\.com[:/]{}/{}(\.git)?/?$".format(
        re.escape(repo_owner), re.escape(repo_name)
    )
    remotes = subprocess.check_output(
        ["git", "-C", repo_path, "remote", "-v"], text=True
    )
    for line in remotes.splitlines():
        parts = line.split()
        # GitHub owner and repository names are case-insensitive
        if len(parts) >= 2 and re.search(upstream, parts[1], re.IGNORECASE):
            return parts[0]
    return None
