"""Unit tests for changelog_generator.py"""

import unittest
from unittest.mock import patch
import cfengine_cli.changelog as cg


def _lines(*texts):
    """Return list of byte-lines as fetch_git_output would."""
    return [t.encode() for t in texts]


# ===========================================================================
# collect_version_updates
# ===========================================================================
class TestCollectVersionUpdates(unittest.TestCase):

    def _run(self, subjects):
        lines = _lines(*subjects)
        with patch.object(cg, "fetch_git_output", return_value=lines):
            return cg.collect_version_updates(["../somerepo"], ["3.27.0..3.27.1"])

    def test_single_update(self):
        result = self._run(["Updated dependency 'openssl' from version 1.1.1 to 3.0.0"])
        self.assertEqual(
            result, ["Updated dependency 'openssl' from version 1.1.1 to 3.0.0"]
        )

    def test_revert_cancels_update(self):
        result = self._run(
            [
                "Updated dependency 'openssl' from version 1.1.1 to 3.0.0",
                "Revert \"Updated dependency 'openssl' from version 1.1.1 to 3.0.0\"",
            ]
        )
        self.assertEqual(result, [])

    def test_reapply_after_revert(self):
        result = self._run(
            [
                "Updated dependency 'openssl' from version 1.1.1 to 3.0.0",
                "Revert \"Updated dependency 'openssl' from version 1.1.1 to 3.0.0\"",
                "Reapply \"Updated dependency 'openssl' from version 1.1.1 to 3.0.0\"",
            ]
        )
        self.assertEqual(
            result, ["Updated dependency 'openssl' from version 1.1.1 to 3.0.0"]
        )

    def test_chain_collapses_to_first_from_last_to(self):
        result = self._run(
            [
                "Updated dependency 'zlib' from version 1.0 to 1.1",
                "Updated dependency 'zlib' from version 1.1 to 1.2",
            ]
        )
        self.assertEqual(result, ["Updated dependency 'zlib' from version 1.0 to 1.2"])

    def test_multiple_deps_sorted(self):
        result = self._run(
            [
                "Updated dependency 'zlib' from version 1.0 to 1.1",
                "Updated dependency 'openssl' from version 1.1.1 to 3.0.0",
            ]
        )
        self.assertEqual(result[0].split("'")[1], "openssl")
        self.assertEqual(result[1].split("'")[1], "zlib")

    def test_no_deps(self):
        result = self._run(["Fix some bug", "Add a feature"])
        self.assertEqual(result, [])


# ===========================================================================
# Main logic / git parsing tests
# ===========================================================================
class TestParseSha(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestParseSha, self).__init__(*args, **kwargs)
        self.repo = "enterprise"
        self.SHA = b"TEST"
        self.SHA_STR = "TEST"

    def _run(self, commit_text, entries=None, sha_to_tracker=None, linked_shas=None):
        entries = {} if entries is None else entries
        sha_to_tracker = {} if sha_to_tracker is None else sha_to_tracker
        linked_shas = {} if linked_shas is None else linked_shas

        lines = _lines(commit_text)
        with patch.object(cg, "fetch_git_output", return_value=lines):
            cg.parse_sha(self.SHA, entries, sha_to_tracker, linked_shas, self.repo)

        return entries, sha_to_tracker, linked_shas

    def test_body_keyword(self):
        commit = "fix: something\n\nThis is the body text.\nChangelog: Body"
        entries, *_ = self._run(commit)
        self.assertIn("This is the body text.", entries[self.SHA_STR])

    def test_commit_keyword(self):
        commit = "fix: something\n\nThis is the body text.\nChangelog: Commit"
        entries, *_ = self._run(commit)
        self.assertIn("This is the body text.", entries[self.SHA_STR])

    def test_changelog_none(self):
        lines = "fix: something\n\nA thing was fixed.\nChangelog: none\nSigned-off-by: someone"
        self.assertDictEqual(self._run(lines)[0], {})

    def test_custom_multiline(self):
        commit = "fix: something\n\nChangelog: Line one\n  line two continued\nSigned-off-by: x"
        entries, *_ = self._run(commit)
        entry_text = entries[self.SHA_STR][0]
        self.assertIn("Line one", entry_text)
        self.assertIn("line two continued", entry_text)

    def test_uses_title(self):
        commit = "feat: shiny new feature\n\nChangelog: Title"
        entries, *_ = self._run(commit)
        self.assertIn("feat: shiny new feature", entries[self.SHA_STR])

    def test_title_with_trailing_period(self):
        commit = "feat: shiny new feature\n\nChangelog: Title."
        entries, *_ = self._run(commit)
        self.assertIn("feat: shiny new feature", entries[self.SHA_STR])

    def test_cherry_pick_links_shas(self):
        other = "aabbccdd"
        commit = (
            f"fix: something\n\nChangelog: Title\n(cherry picked from commit {other})"
        )
        _, _, linked_shas = self._run(commit)
        self.assertIn(other, linked_shas.get(self.SHA_STR, []))
        self.assertIn(self.SHA_STR, linked_shas.get(other, []))

    def test_no_tracker_no_entry(self):
        commit = "fix: plain commit\n\nChangelog: Title"
        _, sha_to_tracker, _ = self._run(commit)
        self.assertNotIn(self.SHA_STR, sha_to_tracker)

    def test_jira_tracker_extracted(self):
        commit = "CFE-456 fix something\n\nChangelog: Title"
        _, sha_to_tracker, _ = self._run(commit)
        self.assertIn(self.SHA_STR, sha_to_tracker)
        self.assertTrue(
            any("CFE-456" in t for t in sha_to_tracker[self.SHA_STR]),
            f"Expected CFE-456 in tracker set, got: {sha_to_tracker}",
        )
