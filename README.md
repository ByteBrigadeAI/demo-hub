# ByteBrigadeAI demo hub

Reusable GitHub and GitHub Copilot demonstrations with fictional applications,
real GitHub issues and PRs, and genuine scanner findings.

## Applications

| Repository | Application | Best demonstrations |
| --- | --- | --- |
| [assettrack](https://github.com/ByteBrigadeAI/assettrack) | Asset management across .NET, Java, Python, Astro, and React | Multi-service comprehension, issue-to-PR agents, SQL injection, modernization, tests |
| [gamehub](https://github.com/ByteBrigadeAI/gamehub) | Tailspin Toys game crowdfunding catalog with Astro, TypeScript, and SQLite | Small feature work, code review, DOM XSS, accessibility, quality findings |

Each application has eight curated issue scenarios, a reusable fix PR, and
synthetic security and quality fixtures. The default branch is `demo-baseline`.
The upstream MIT licenses and authorship are preserved.

## Prepare a demo

1. Open either application repository and select **Actions > Prepare demo assets**.
2. Select **Run workflow**, using **demo-baseline**.
3. Leave the defaults for a low-cost refresh of issues and existing PRs.
   Existing seeded PRs are reused. Creating a new PR from Actions requires the
   organization permission below and **create_pull_requests** selected.
4. To repeat a completed demo, select **restore_demo**. This restores only the
   source files explicitly listed in `.github/demo/scenarios.json`, reopens
   curated issues, and prepares a new fix branch if the previous PR was merged.
   With the permission prerequisite satisfied and **create_pull_requests**
   selected, it also creates the replacement PR.
5. Select **scan_security** for a fresh security scan, or **scan_quality** to
   include CodeQL reliability and maintainability findings in the same scan.
6. Keep **secret_revision** unchanged for idempotent runs. If a prior secret
   alert was resolved and you want a new alert, enter a new revision such as `2`.
   This updates the same issue with a new nonfunctional scanner fixture.
7. Open the completed run summary for links to the issues, PRs, and Security tab.

Repeated runs reuse existing issues, open PRs, branches, and unchanged commits.
New source commits are made only when curated files actually change. The
`demo/` branch namespace is reserved for these seeded PRs; unrelated PRs and
files are not changed. No secret values are committed to source code: scanner
patterns are constructed at runtime and posted only to a labeled demo issue.

The shared implementation lives in `scripts/seed_demo.py` and
`.github/workflows/prepare-demo.yml` here. Each application owns its scenario
definitions. The caller's `GITHUB_TOKEN` is used; no personal token is stored.
GitHub's **Allow GitHub Actions to create and approve pull requests** setting
must be allowed by the organization and enabled for each application. The
workflow requests only the permissions needed by its seed and scan jobs.

**Current permission prerequisite:** ByteBrigadeAI currently blocks Actions
from creating PRs. The current CLI token cannot change that organization
policy, and no approval to change it was available. Initial review PRs are
created through the owner's normal CLI authorization. Preparation reuses them
without error. If a PR is missing, the default workflow prepares its branch and
reports a comparison link plus **PR not created** instead of attempting a
forbidden API request. After an owner enables the organization setting and
the per-repository setting, select **create_pull_requests** to automate this.

## Verified starter assets

| Application | Review PR | Code scanning | Secret scanning issue | Quality finding |
| --- | --- | --- | --- | --- |
| AssetTrack | [Badge colors #9](https://github.com/ByteBrigadeAI/assettrack/pull/9) | [SQL injection #2](https://github.com/ByteBrigadeAI/assettrack/security/code-scanning/2) and [#3](https://github.com/ByteBrigadeAI/assettrack/security/code-scanning/3) | [Issue #7](https://github.com/ByteBrigadeAI/assettrack/issues/7), detected AWS-shaped ID and secret | [Unreachable statement #8](https://github.com/ByteBrigadeAI/assettrack/security/code-scanning/8) |
| GameHub | [Malformed ratings #10](https://github.com/ByteBrigadeAI/gamehub/pull/10) | [DOM XSS #1](https://github.com/ByteBrigadeAI/gamehub/security/code-scanning/1) | [Issue #8](https://github.com/ByteBrigadeAI/gamehub/issues/8), detected AWS-shaped ID and secret | [Overwritten assignment #2](https://github.com/ByteBrigadeAI/gamehub/security/code-scanning/2) |

These are actual GitHub findings, not uploaded mock alerts. The secret alert
locations point to the listed issue bodies; the generated values were never
issued by AWS. Both applications' manual preparation and quality runs passed.
A second unchanged preparation run created zero issues, PRs, or commits and
skipped scanning. Use the latest run summary for current PR links after resets.

## A simple 15-minute walkthrough

1. **Show the application and repository.** Start with GameHub. Explain the
   static site and seeded SQLite catalog. Show the README, custom Copilot
   instructions, tests, and scoped instructions before opening the app.
2. **Delegate one issue.** Open the game-search issue labeled `demo:agent`.
   Show its acceptance criteria, then start Copilot from the issue when the
   organization permits cloud agents. Do not assign all issues at once.
   Prompt: "Implement this issue without changing unrelated demo scenarios.
   Follow the repository instructions and add focused regression tests."
3. **Review an existing PR.** Open a PR labeled `demo:review`. Show the small
   diff and linked issue. Request a Copilot review during the demo, not
   automatically. Keep it unmerged if you want the scenario to remain ready.
4. **Show genuine code scanning.** Open **Security > Code scanning**. In
   AssetTrack, inspect Java SQL injection and its data-flow path. In GameHub,
   inspect DOM XSS in the isolated preview. Use Autofix where GitHub offers it,
   or give the linked remediation issue to Copilot. Verify the targeted
   finding is gone on the fix branch rather than merely dismissing the alert.
5. **Show issue-body secret detection.** Open the labeled synthetic-credential
   issue, then its real **Security > Secret scanning** alert. Explain that
   the AWS-shaped values were generated locally and never issued by AWS.
   Inspect actual validity metadata; do not present a dummy value as active.
   Remove the fixture text and resolve the alert to demonstrate remediation.
6. **Show code quality.** Open the verified quality finding above and inspect
   CodeQL's reliability/maintainability findings in Code scanning. The isolated
   quality tasks include an overwritten funding label and unreachable Python
   code. Have Copilot explain the defect and add regression tests. Run preparation
   with **scan_quality** before the presentation when a fresh scan is needed.
7. **Show validation only when needed.** Use **Actions > Run tests** in
   GameHub or **Application checks** in AssetTrack and select the PR branch.
   These checks do not run automatically. Review the run before merging.

Copilot cloud agents, code review, and Autofix availability depend on plan,
organization policy, and the finding. Preparing assets does not start agents,
request Copilot reviews, or generate Autofix PRs automatically.

## Code quality and cost boundaries

The quality demo uses the standard CodeQL `security-and-quality` query suite
and manual application checks. It does **not** enable the separately billed
**GitHub Code Quality** product. That feature has its own dashboard, AI
analysis, and recurring scans, so it remains off under this organization's
no-recurring-automation policy.

The GameHub quality fixture is intentionally excluded from normal ESLint
checks, because it is not used by the catalog and is deliberately flawed.
The manual CodeQL quality scan still analyzes it. Normal app checks should
remain green while the demo scanner reports real seeded findings.

There are no cron schedules, automatic push/PR workflows, recurring Dependabot
updates, deployments, or automatic paid agent runs. CodeQL default setup is
disabled to prevent overlapping or implicit scheduled scans. Preparation scans
only when requested or when security fixtures are restored; an unchanged
default preparation run does not rescan. Artifacts expire after seven days.

Manual runs can still produce notifications according to the presenter's
personal settings. For complete Actions notification silence, use GitHub
**Settings > Notifications > System > Actions > Don't notify**. That is an
account-wide preference; these repositories do not change it automatically.

## Source selection

| Source | Decision |
| --- | --- |
| [github-samples/contoso-inventory](https://github.com/github-samples/contoso-inventory) | Reused for AssetTrack: small polyglot services and existing atomic exercises; MIT |
| [github-samples/tailspin-toys](https://github.com/github-samples/tailspin-toys) | Reused for GameHub: realistic, focused app with unit/E2E tests; MIT |
| [github-samples/copilot-workshops](https://github.com/github-samples/copilot-workshops) | Reference for scenario flow and future workshop expansion |
| [github-samples/copilot-in-a-box](https://github.com/github-samples/copilot-in-a-box) | Reference inventory for future demonstrations |
| [adeyosemanputra/pygoat](https://github.com/adeyosemanputra/pygoat) | Candidate for a later dedicated Django security lab; not imported |
| [microsoft/GitHubCopilot_Customized](https://github.com/microsoft/GitHubCopilot_Customized) | Researched, not copied: no repository license was detected during inspection |

Source snapshots: AssetTrack `4f9d1eb4bfa168372540fff53b8f510fec8b0b01`;
GameHub `9cd9a450f923c7a084bd47d661877d82ff710826`.
Upstream issues and PRs do not transfer with source code; the preparation
workflow supplies the demo assets independently.

## Official feature references

- [Start Copilot from an issue or task](https://docs.github.com/copilot/how-tos/copilot-on-github/use-copilot-agents/kick-off-a-task)
- [Request a Copilot code review](https://docs.github.com/copilot/how-tos/use-copilot-agents/request-a-code-review/use-code-review)
- [CodeQL query suites](https://docs.github.com/en/code-security/concepts/code-scanning/codeql/codeql-query-suites)
- [Autofix for code scanning](https://docs.github.com/en/code-security/concepts/code-scanning/autofix-for-code-scanning)
- [Secret scanning and issue-body scope](https://docs.github.com/en/code-security/concepts/secret-security/secret-scanning)
- [Supported secret-scanning patterns](https://docs.github.com/en/code-security/reference/secret-security/supported-secret-scanning-patterns)
- [GitHub Code Quality and billing](https://docs.github.com/code-security/code-quality)
- [Code Quality scan frequency](https://docs.github.com/en/code-security/how-tos/maintain-quality-code/enable-code-quality)
- [Actions notification settings](https://docs.github.com/en/subscriptions-and-notifications/how-tos/managing-github-actions-notifications)

Use isolated environments and synthetic data for the intentionally vulnerable
apps. Do not expose their labs as public running services.
