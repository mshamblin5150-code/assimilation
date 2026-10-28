# Prepare a reviewed source-update PR

The operator selected monthly reviewed update PRs and retained the MIT license. No update merges automatically. The initial public publication remains held for the before-publish review.

## Review the monthly proposal

The workflow runs on the first day of each month at 09:00 UTC, or by manual dispatch. It runs the offline suite, compares a committed `sources.lock.json` against upstream `main`, and saves two proposal files:

- `sources.update.json` freezes the installed and proposed SHA for each source.
- `PULL_REQUEST.md` contains source-diff links and the review checklist.

The workflow links its artifact from a review issue. It does not install upstream code or change `sources.lock.json`. A missing lock produces a setup-needed notice without an upstream request. A malformed or partial lock fails the workflow instead of becoming a baseline.

## Prepare the draft PR manually

Run this procedure only when repository publication and your branch/PR actions are authorized. Use a clean, isolated checkout of the base commit recorded by the workflow. Do not use an active project or a checkout with local skill changes.

1. Download the proposal artifact from the workflow run. Review the source-diff links, licenses, tool requirements, and changed executable files.
2. Copy `sources.update.json` into the checkout root. Keep `PULL_REQUEST.md` outside the staged changes until you use it as the PR body.
3. Create an update branch with a name you have not used before:

   ```sh
   git switch -c review/skill-update-YYYY-MM
   ```

4. Materialize the existing lock in the clean checkout. The command fetches the exact locked commits and does not run upstream scripts:

   ```sh
   python3 scripts/skills.py install --locked
   ```

   If this reports an existing or edited installation, stop. Use a fresh isolated checkout rather than adding approval flags to bypass the mismatch.

5. After reviewing the proposal, install its exact target commits:

   ```sh
   python3 scripts/skills.py install --approve-update --update-plan sources.update.json
   python3 -m unittest discover -s tests -v
   ```

   A stale proposal fails because each `from_sha` must match the current lock. The installer fetches each `to_sha`, not whatever `main` points to later. Confirm each resulting lock SHA equals its proposed `to_sha`.

6. Inspect the installed source trees and licenses. Record focused compatibility checks for the tools you use. The synthetic installer suite proves preservation behavior, not the safety or compatibility of new upstream instructions.
7. Stage only the lock and reviewed plan. Inspect the diff before committing:

   ```sh
   git add sources.lock.json sources.update.json
   git diff --cached
   git commit -m "Propose reviewed skill source updates"
   git push -u origin HEAD
   gh pr create --draft --title "Review skill source updates" --body-file /path/to/PULL_REQUEST.md
   ```

8. Obtain independent review, required check results for the exact PR commit, and operator acceptance. Approve requested workflow runs only after reviewing them. Merge remains a separate authorized action. Close the handoff issue after the accepted update lands.

To prepare a proposal without waiting for the schedule, run `python3 scripts/propose_update.py --output-dir review-update` in an installed checkout. The output directory must not already exist. Exit codes are `0` for current, `2` for a prepared proposal, `3` for missing initial installation, and `1` for an error.

## Automatic PR publication is held

The supplied workflow preserves `contents: read` and `issues: write`. Those permissions support comparison and the issue handoff, not branch pushes or PR creation. Artifact upload uses the Actions runtime; no extra `GITHUB_TOKEN` permission or secret is added.

Automated PR creation needs a separate reviewed workflow change with `contents: write` and `pull-requests: write`, plus the repository setting **Allow GitHub Actions to create and approve pull requests**, where organization policy permits it. The setting's name is not authorization for bot approval: the proposed workflow must never approve or merge its own PRs. Do not add a personal access token as a workaround. Review [GitHub token permissions](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token) and [repository Actions settings](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository) before activation.

The desired monthly PR behavior is therefore **partially implemented, not active**. Proposal preparation and the manual draft-PR route are available. Token expansion, repository settings, automated branch creation, live CI behavior, and publication are unverified and held.
