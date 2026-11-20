import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from urllib.parse import quote


class GitHub:
    def call(self, endpoint: str, method: str = "GET", payload: dict | None = None,
             missing_ok: bool = False):
        command = ["gh", "api", "--method", method, endpoint]
        if payload is not None:
            command += ["--input", "-"]
        result = subprocess.run(
            command, input=json.dumps(payload) if payload is not None else None,
            capture_output=True, text=True, encoding="utf-8",
        )
        if result.returncode:
            if missing_ok and "(HTTP 404)" in result.stderr:
                return None
            raise RuntimeError(f"{method} {endpoint}: {result.stderr.strip()}")
        return json.loads(result.stdout) if result.stdout.strip() else None


class Seeder:
    def __init__(self, github: GitHub, repository: str, config: dict, reset: bool):
        if repository != config["repository"]:
            raise ValueError("Scenario repository does not match the workflow caller")
        if config["version"] != 1:
            raise ValueError("Unsupported scenario format")
        self.github = github
        self.repository = repository
        self.prefix = f"repos/{repository}"
        self.config = config
        self.reset = reset
        self.commits = 0
        self.contents = {}
        self.trees = {}
        for path in config["baseline_files"]:
            self.validate_path(path)
        for scenario in config["pull_requests"]:
            if not re.fullmatch(r"demo/[a-z0-9-]+", scenario["branch"]):
                raise ValueError("Demo branches must use the reserved demo/ namespace")
            for path in scenario["files"]:
                self.validate_path(path)
                if path not in config["baseline_files"]:
                    raise ValueError("PR files must belong to the curated fixture allowlist")

    @staticmethod
    def validate_path(path: str) -> None:
        if "\\" in path or ".." in path.split("/") or not path.startswith(("src/", "services/")):
            raise ValueError(f"Not an allowed demo source path: {path}")

    def api(self, suffix: str, method: str = "GET", payload: dict | None = None,
            missing_ok: bool = False):
        return self.github.call(f"{self.prefix}/{suffix}", method, payload, missing_ok)

    def file(self, path: str, ref: str) -> str | None:
        key = (path, ref)
        if key in self.contents:
            return self.contents[key]
        data = self.api(f"contents/{quote(path, safe='/')}?ref={quote(ref, safe='')}",
                        missing_ok=True)
        content = base64.b64decode(data["content"]).decode("utf-8") if data else None
        self.contents[key] = content
        return content

    def commit_tree(self, sha: str) -> str:
        if sha not in self.trees:
            self.trees[sha] = self.api(f"git/commits/{sha}")["tree"]["sha"]
        return self.trees[sha]

    def paginated(self, suffix: str) -> list:
        items = []
        page = 1
        separator = "&" if "?" in suffix else "?"
        while True:
            batch = self.api(f"{suffix}{separator}per_page=100&page={page}")
            items.extend(batch)
            if len(batch) < 100:
                return items
            page += 1

    def secret_issue(self) -> dict:
        revision = os.environ.get("SECRET_REVISION", "1")
        password = hashlib.sha256(
            f"Nonfunctional ByteBrigadeAI fixture/{self.repository}/{revision}".encode()
        ).hexdigest()
        connection = "mongodb+srv://" + "bytebrigade_demo:" + password + \
            "@bytebrigade-demo.invalid/demo"
        digest = hashlib.sha256(
            f"Unissued AWS-shaped ByteBrigadeAI fixture/{self.repository}/{revision}".encode()
        ).digest()
        access_id = "AK" + "IA" + "Q" + base64.b32encode(digest).decode()[:15]
        access_secret = base64.b64encode(digest).decode()[:40]
        return {
            "key": "synthetic-secret-scanning",
            "title": "Remove the synthetic database credential from this issue",
            "labels": ["demo:security", "demo:agent"],
            "generated_fixture": True,
            "body": "## Secret scanning demonstration\n\n"
            "These are deliberately nonfunctional, generated scanner fixtures. "
            "The `.invalid` host has no database, and this value authenticates nowhere. "
            "The AWS-shaped pair was generated locally, never issued by AWS, and "
            "belongs to no account. No live credential was created or exposed. "
            "Do not attempt to use these values.\n\n"
            f"Demo fixture revision: `{revision}`.\n\n```text\n{connection}\n```\n\n"
            "```text\n" + "AWS_ACCESS_KEY_ID=" + access_id + "\n" +
            "AWS_SECRET_ACCESS_KEY=" + access_secret + "\n```\n\n"
            "## Acceptance criteria\n"
            "- Open the real detected test-pattern alert under Security > Secret scanning.\n"
            "- If generic scanning also recognizes the database string, inspect that alert too.\n"
            "- Explain issue-body detection, validity, and remediation.\n"
            "- Remove the synthetic value from the issue and resolve the demo alert.\n"
            "- Do not replace it with a real credential.\n\n"
            "The manual preparation workflow reuses this issue. Reuse the same revision "
            "for idempotent runs; choose a new `secret_revision` for a fresh alert "
            "after a previous demo alert has been resolved.",
        }

    def write_branch(self, branch: str, base_sha: str, files: dict[str, str],
                     title: str, is_default: bool = False) -> tuple[str, bool]:
        reference = self.api(f"git/ref/heads/{branch}", missing_ok=True)
        old_sha = reference["object"]["sha"] if reference else base_sha
        old_tree = self.commit_tree(old_sha)
        base_tree = self.commit_tree(base_sha)
        source_sha = base_sha if self.reset or is_default or not reference else old_sha
        changes = [
            {"path": path, "mode": "100644", "type": "blob", "content": content}
            for path, content in files.items() if self.file(path, source_sha) != content
        ]
        source_tree = self.commit_tree(source_sha)
        if changes:
            target_tree = self.api("git/trees", "POST", {
                "base_tree": source_tree, "tree": changes,
            })["sha"]
        else:
            target_tree = source_tree

        ahead = 0
        if reference and not is_default and old_sha != base_sha:
            ahead = self.api(f"compare/{base_sha}...{old_sha}")["ahead_by"]
        needs_new_pr_commit = not is_default and target_tree != base_tree and ahead == 0
        if reference and target_tree == old_tree and not needs_new_pr_commit:
            return old_sha, False
        if not reference and target_tree == base_tree:
            return base_sha, False
        parents = [base_sha] if not reference or ahead == 0 or is_default else list(
            dict.fromkeys([old_sha, base_sha])
        )
        commit = self.api("git/commits", "POST", {
            "message": title + "\n\nCo-authored-by: Copilot "
            "<223556219+Copilot@users.noreply.github.com>\n"
            "Copilot-Session: 0dc62600-42e2-4098-870f-53dcecf415d2",
            "tree": target_tree, "parents": parents,
        })
        if reference:
            self.api(f"git/refs/heads/{branch}", "PATCH", {"sha": commit["sha"], "force": False})
        else:
            self.api("git/refs", "POST", {"ref": f"refs/heads/{branch}", "sha": commit["sha"]})
        self.commits += 1
        return commit["sha"], True

    def prepare(self) -> dict:
        repository = self.github.call(self.prefix)
        branch = repository["default_branch"]
        base_sha = self.api(f"git/ref/heads/{branch}")["object"]["sha"]
        fixtures = self.config["baseline_files"]
        to_restore = fixtures if self.reset else {
            path: content for path, content in fixtures.items() if self.file(path, base_sha) is None
        }
        restored_security = any(
            path in to_restore and self.file(path, base_sha) != fixtures[path]
            for path in self.config["security_paths"]
        )
        base_sha, restored = self.write_branch(
            branch, base_sha, to_restore, "Restore curated demo fixtures", is_default=True
        )
        labels = {label["name"] for label in self.paginated("labels")}
        for name, description in self.config["labels"].items():
            if name not in labels:
                self.api("labels", "POST", {
                    "name": name, "color": "8250df", "description": description,
                })
        existing = [issue for issue in self.paginated("issues?state=all")
                    if "pull_request" not in issue]
        issues = {}
        created_issues = 0
        for scenario in self.config["issues"] + [self.secret_issue()]:
            marker = f"<!-- bytebrigade-demo:{scenario['key']} -->"
            matches = [issue for issue in existing if marker in (issue.get("body") or "")
                       or issue["title"] == scenario["title"]]
            if len(matches) > 1:
                raise RuntimeError(f"Ambiguous demo issue: {scenario['title']}")
            if matches:
                issue = matches[0]
                update = {}
                if marker not in (issue.get("body") or ""):
                    update["body"] = (issue.get("body") or "") + f"\n\n{marker}"
                if scenario.get("generated_fixture"):
                    desired_body = scenario["body"] + f"\n\n{marker}"
                    if issue.get("body") != desired_body:
                        update["body"] = desired_body
                if self.reset and issue["state"] == "closed":
                    update["state"] = "open"
                current_labels = {label["name"] for label in issue["labels"]}
                if not set(scenario["labels"]).issubset(current_labels):
                    update["labels"] = sorted(current_labels | set(scenario["labels"]))
                if update:
                    issue = self.api(f"issues/{issue['number']}", "PATCH", update)
            else:
                issue = self.api("issues", "POST", {
                    "title": scenario["title"], "body": scenario["body"] + f"\n\n{marker}",
                    "labels": scenario["labels"],
                })
                created_issues += 1
            issues[scenario["key"]] = issue

        open_prs = self.paginated("pulls?state=open")
        pull_requests = []
        created_prs = 0
        for scenario in self.config["pull_requests"]:
            desired = scenario["files"]
            if all(self.file(path, base_sha) == content for path, content in desired.items()):
                pull_requests.append({"title": scenario["title"], "state": "already implemented",
                                      "note": "Use restore_demo to repeat the fix scenario."})
                continue
            head_sha, _ = self.write_branch(
                scenario["branch"], base_sha, desired, scenario["title"]
            )
            if head_sha == base_sha:
                raise RuntimeError("The demo PR would have no source changes")
            matches = [pr for pr in open_prs if pr["head"]["ref"] == scenario["branch"]
                       and (pr["head"].get("repo") or {}).get("full_name") == self.repository]
            if len(matches) > 1:
                raise RuntimeError(f"Multiple open PRs for {scenario['branch']}")
            if matches:
                pr = matches[0]
            else:
                if os.environ.get("CREATE_PULL_REQUESTS", "false") != "true":
                    pull_requests.append({
                        "title": scenario["title"], "state": "manual creation required",
                        "url": f"https://github.com/{self.repository}/compare/"
                        f"{branch}...{scenario['branch']}?expand=1",
                        "note": "Organization policy currently blocks automatic PR creation. "
                        "Enable the org setting, then run with create_pull_requests=true.",
                    })
                    continue
                issue_number = issues[scenario["issue_key"]]["number"]
                pr = self.api("pulls", "POST", {
                    "title": scenario["title"], "head": scenario["branch"], "base": branch,
                    "body": scenario["body"] + f"\n\nCloses #{issue_number}.\n\n"
                    f"<!-- bytebrigade-demo:{scenario['key']} -->",
                })
                created_prs += 1
            if not any(label["name"] == "demo:review" for label in pr.get("labels", [])):
                self.api(f"issues/{pr['number']}/labels", "POST", {"labels": ["demo:review"]})
            pull_requests.append({"title": pr["title"], "url": pr["html_url"], "state": "open"})
        return {
            "repository": self.repository, "sha": base_sha, "default_branch": branch,
            "restored_files": restored, "created_issues": created_issues,
            "restored_security": restored_security,
            "created_pull_requests": created_prs, "created_commits": self.commits,
            "pending_pull_requests": sum(
                item["state"] == "manual creation required" for item in pull_requests
            ),
            "issues": [{"title": issue["title"], "url": issue["html_url"]}
                       for issue in issues.values()],
            "pull_requests": pull_requests, "languages": self.config["languages"],
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding="utf-8"))
    repository = os.environ["GITHUB_REPOSITORY"]
    reset = os.environ.get("RESTORE_DEMO", "false") == "true"
    result = Seeder(GitHub(), repository, config, reset).prepare()
    Path("demo-result.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if output := os.environ.get("GITHUB_OUTPUT"):
        with open(output, "a", encoding="utf-8") as stream:
            stream.write(f"sha={result['sha']}\n")
            stream.write(f"languages={json.dumps(result['languages'])}\n")
            stream.write(f"restored_files={str(result['restored_files']).lower()}\n")
            stream.write(f"restored_security={str(result['restored_security']).lower()}\n")
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as stream:
            status = "Demo assets staged; PR creation pending" if result["pending_pull_requests"] \
                else "Demo ready"
            stream.write(f"## {status}: {repository}\n\n")
            stream.write(f"Created {result['created_issues']} issues, "
                         f"{result['created_pull_requests']} PRs, and "
                         f"{result['created_commits']} commits. Existing assets are reused.\n\n")
            for item in result["issues"] + result["pull_requests"]:
                if "url" in item:
                    stream.write(f"- [{item['title']}]({item['url']})\n")
                    if item.get("state") == "manual creation required":
                        stream.write(f"  **PR not created:** {item['note']}\n")
                else:
                    stream.write(f"- {item['title']}: {item['state']}. {item['note']}\n")
            stream.write(f"\n[Real security alerts](https://github.com/{repository}/security/code-scanning)\n")
    print(json.dumps({key: result[key] for key in (
        "repository", "created_issues", "created_pull_requests", "pending_pull_requests",
        "created_commits", "sha"
    )}))


if __name__ == "__main__":
    main()
