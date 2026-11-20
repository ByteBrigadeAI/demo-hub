import unittest
import os
from unittest.mock import patch

from scripts.seed_demo import GitHub, Seeder


CONFIG = {
    "version": 1, "repository": "ByteBrigadeAI/example",
    "baseline_files": {"src/demo.ts": "original"},
    "pull_requests": [], "security_paths": [], "labels": {}, "issues": [],
    "languages": ["javascript-typescript"],
}


class BranchIdempotenceTests(unittest.TestCase):
    def setUp(self):
        self.seeder = Seeder(GitHub(), CONFIG["repository"], CONFIG, reset=False)

    def test_existing_demo_branch_is_not_recommitted(self):
        responses = {
            "git/ref/heads/demo/fix": {"object": {"sha": "existing"}},
            "git/commits/existing": {"tree": {"sha": "fixed-tree"}},
            "git/commits/base": {"tree": {"sha": "base-tree"}},
            "compare/base...existing": {"ahead_by": 1},
        }
        with patch.object(self.seeder, "api", side_effect=lambda path, *args, **kwargs: responses[path]) as api:
            with patch.object(self.seeder, "file", return_value="fixed"):
                sha, changed = self.seeder.write_branch(
                    "demo/fix", "base", {"src/demo.ts": "fixed"}, "Fix demo"
                )
        self.assertEqual((sha, changed, self.seeder.commits), ("existing", False, 0))
        self.assertFalse(any(call.args[0] == "git/commits" for call in api.call_args_list))

    def test_previously_merged_branch_gets_a_new_fix_commit_after_reset(self):
        self.seeder.reset = True
        responses = {
            "git/ref/heads/demo/fix": {"object": {"sha": "merged"}},
            "git/commits/merged": {"tree": {"sha": "fixed-tree"}},
            "git/commits/restored-base": {"tree": {"sha": "restored-tree"}},
            "git/trees": {"sha": "fixed-tree"},
            "compare/restored-base...merged": {"ahead_by": 0},
            "git/commits": {"sha": "new-fix"},
            "git/refs/heads/demo/fix": {},
        }
        with patch.object(self.seeder, "api", side_effect=lambda path, *args, **kwargs: responses[path]) as api:
            with patch.object(self.seeder, "file", return_value="original"):
                sha, changed = self.seeder.write_branch(
                    "demo/fix", "restored-base", {"src/demo.ts": "fixed"}, "Fix demo"
                )
        self.assertEqual((sha, changed, self.seeder.commits), ("new-fix", True, 1))
        commit = next(call for call in api.call_args_list if call.args[0] == "git/commits")
        self.assertEqual(commit.args[2]["parents"], ["restored-base"])
        update = next(call for call in api.call_args_list if call.args[0] == "git/refs/heads/demo/fix")
        self.assertFalse(update.args[2]["force"])

    def test_empty_default_restore_does_not_create_a_commit(self):
        responses = {
            "git/ref/heads/demo-baseline": {"object": {"sha": "base"}},
            "git/commits/base": {"tree": {"sha": "same-tree"}},
        }
        with patch.object(self.seeder, "api", side_effect=lambda path, *args, **kwargs: responses[path]):
            sha, changed = self.seeder.write_branch(
                "demo-baseline", "base", {}, "Restore demo", is_default=True
            )
        self.assertEqual((sha, changed, self.seeder.commits), ("base", False, 0))

    def test_secret_fixture_is_stable_for_the_same_revision(self):
        with patch.dict(os.environ, {"SECRET_REVISION": "1"}):
            first = self.seeder.secret_issue()
            second = self.seeder.secret_issue()
        self.assertEqual(first, second)
        self.assertIn("@bytebrigade-demo.invalid/demo", first["body"])

    def test_secret_revision_changes_the_fixture_not_the_issue_identity(self):
        with patch.dict(os.environ, {"SECRET_REVISION": "1"}):
            first = self.seeder.secret_issue()
        with patch.dict(os.environ, {"SECRET_REVISION": "2"}):
            second = self.seeder.secret_issue()
        self.assertEqual((first["key"], first["title"]), (second["key"], second["title"]))
        self.assertNotEqual(first["body"], second["body"])


class PullRequestPreparationTests(unittest.TestCase):
    def prepare(self, create_prs, existing=False):
        scenario = {
            "key": "fix", "issue_key": "task", "title": "Fix demo", "body": "Fix the fixture.",
            "branch": "demo/fix", "files": {"src/demo.ts": "fixed"},
        }
        config = {**CONFIG, "pull_requests": [scenario]}
        github = GitHub()
        seeder = Seeder(github, CONFIG["repository"], config, reset=False)
        issue = {
            "number": 1, "title": "Demo task", "body": "<!-- bytebrigade-demo:task -->",
            "state": "open", "labels": [], "html_url": "https://github.com/example/issues/1",
        }
        pr = {
            "number": 2, "title": "Fix demo", "html_url": "https://github.com/example/pull/2",
            "labels": [{"name": "demo:review"}],
            "head": {"ref": "demo/fix", "repo": {"full_name": CONFIG["repository"]}},
        }
        batches = {"labels": [], "issues?state=all": [issue],
                   "pulls?state=open": [pr] if existing else []}

        def api_response(path, method="GET", payload=None, **kwargs):
            if path == "git/ref/heads/demo-baseline":
                return {"object": {"sha": "base"}}
            if path == "pulls" and method == "POST":
                return pr
            raise AssertionError(f"Unexpected API call: {method} {path}")

        with patch.dict(os.environ, {"CREATE_PULL_REQUESTS": str(create_prs).lower()}), \
                patch.object(github, "call", return_value={"default_branch": "demo-baseline"}), \
                patch.object(seeder, "api", side_effect=api_response) as api, \
                patch.object(seeder, "file", return_value="original"), \
                patch.object(seeder, "write_branch", side_effect=[("base", False), ("fix", True)]), \
                patch.object(seeder, "paginated", side_effect=lambda path: batches[path]), \
                patch.object(seeder, "secret_issue", return_value={
                    "key": "task", "title": "Demo task", "labels": [], "body": "",
                }):
            result = seeder.prepare()
        return result, api.call_args_list

    def test_disabled_creation_reports_comparison_without_posting_a_pr(self):
        result, calls = self.prepare(create_prs=False)
        self.assertEqual(result["pending_pull_requests"], 1)
        self.assertEqual(result["created_pull_requests"], 0)
        self.assertIn("/compare/demo-baseline...demo/fix", result["pull_requests"][0]["url"])
        self.assertFalse(any(call.args[0] == "pulls" for call in calls))

    def test_enabled_creation_posts_a_linked_pr(self):
        result, calls = self.prepare(create_prs=True)
        self.assertEqual(result["pending_pull_requests"], 0)
        self.assertEqual(result["created_pull_requests"], 1)
        created = next(call for call in calls if call.args[0] == "pulls")
        self.assertIn("Closes #1.", created.args[2]["body"])

    def test_disabled_creation_still_reuses_an_existing_pr(self):
        result, calls = self.prepare(create_prs=False, existing=True)
        self.assertEqual(result["pending_pull_requests"], 0)
        self.assertEqual(result["created_pull_requests"], 0)
        self.assertEqual(result["pull_requests"][0]["state"], "open")
        self.assertFalse(any(call.args[0] == "pulls" for call in calls))


if __name__ == "__main__":
    unittest.main()
