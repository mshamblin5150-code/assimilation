# Review monthly source-update PRs

Monthly automation proposes exact upstream commits in a draft PR. It does not install sources, execute upstream code, change `sources.lock.json`, approve a PR, or merge one.

## What the workflow publishes

The workflow runs on the first day of each month at 09:00 UTC, or by manual dispatch. Both the job and publisher accept only scheduled or manual runs on the repository's default branch. Before publication, the publisher checks that the checkout commit and baseline lock still match the remote default branch. The lock must also be an unchanged regular Git blob committed in that checkout; a dirty regular-file copy cannot hide a committed symlink.

The read-only generator compares the committed lock against upstream `main`. It writes `sources.update.json` and a draft PR body to a temporary artifact directory. Each source entry has an exact `from_sha` and `to_sha`. The generator passes a SHA-256 digest of the original plan bytes to the publisher through a workflow step output. Modified artifact bytes fail validation. This binds steps within the same trusted job; it is not a signature or verification scheme for arbitrary downloaded artifacts.

The publisher creates a deterministic `automation/skill-update-<plan-hash>` branch. Its commit changes only `sources.update.json`. It constructs that commit from the remote base tree, not the local working directory, and never updates or force-pushes an existing branch. Unrelated local files and artifact files cannot enter the commit. The baseline lock stays unchanged for human review.

A missing lock reports setup needed without an upstream request, branch, or PR. An invalid lock, stale plan, changed default branch, or modified artifact fails closed. An unchanged source pair produces no PR.

## Review and adopt a proposal

1. Open the draft PR and inspect the exact source-diff links, licenses, changed executable files, and tool requirements. Confirm that the bot commit changes only `sources.update.json`.
2. Use a fresh isolated checkout of the proposal branch. Do not use an active project or a checkout with local skill changes.
3. Materialize the unchanged baseline lock:

   ```sh
   python3 scripts/skills.py install --locked
   ```

   If this reports an existing or edited installation, stop and use a fresh checkout. Do not add approval flags to bypass that mismatch.

4. After reviewing the proposal, apply its exact target commits:

   ```sh
   python3 scripts/skills.py install --approve-update --update-plan sources.update.json
   python3 -m unittest discover -s tests -v
   ```

   Each `from_sha` must still match the lock. Each resulting lock SHA must equal its proposed `to_sha`, even if upstream `main` has moved.

5. Inspect the installed trees and licenses. Record focused compatibility checks for the tools you use. Synthetic installer tests do not establish the safety or compatibility of new upstream instructions.
6. With authority to update the PR, commit the reviewed `sources.lock.json` to that branch. Preserve the plan as review evidence and inspect the staged diff before pushing. Generated `vendor/` and `.agents/` trees stay local.
7. Obtain independent review, required checks for the exact PR commit, and operator acceptance. Approve requested workflow runs only after reviewing them. Merge remains a separate authorized action; the bot cannot approve or merge its proposal.

The workflow stops reusing a branch after a human changes it. That is expected once reviewed adoption adds the lock commit. Finish that PR through the normal human review process.

## Retry without overwriting work

The plan hash identifies the same source pair across retries. An existing branch is reused only when its commit message, sole parent, plan blob, and complete root-tree entries prove the original one-file proposal. Every unchanged subtree SHA must match the parent, and that parent must remain on the current default branch with the same baseline lock. This is content verification, not proof of who originally created the branch.

The publisher searches a bounded PR list for the exact head and base. It reuses only an open draft owned by `github-actions[bot]` with the expected head commit. Human-owned, closed, promoted, duplicate, or modified PRs require manual review. It never reopens a rejected proposal or edits an existing PR's body.

If branch creation succeeds but its response is lost, or PR creation fails after the branch commit, a rerun inspects and reuses the retained branch. If a PR response is lost, a rerun finds the existing draft rather than opening a duplicate. No retry deletes or resets a branch. An uncertain API result may fail the current run; rerun the workflow only after inspecting its reported state.

GitHub cannot atomically lease the default branch across PR creation. The publisher checks the default branch and proposal branch again before reporting success. A detected race leaves any created draft intact and reports failure for a fresh run or human review. This does not prevent a human from changing a branch after the last check.

## Activate and verify repository settings

The operator approved workflow authority to write update branches and open draft PRs. The publication job requests only `contents: write` and `pull-requests: write`; other jobs default to read-only contents. It uses the runner's `GITHUB_TOKEN`, never a new personal access token. The former issue handoff and its issues permission are removed.

The repository setting **Allow GitHub Actions to create and approve pull requests** must also permit PR creation, subject to organization policy. GitHub bundles creation and approval in that setting's name. This workflow never calls an approval or merge operation. Enabling the setting is a separate administrative action; the code and offline tests do not establish that it is enabled.

Bot-created PR workflow runs may require a writer to approve their execution. Do not treat an open draft as proof that CI ran. Verify the exact run and PR checks in GitHub. See [GitHub token permissions](https://docs.github.com/en/actions/tutorials/authenticate-with-github_token), [repository Actions settings](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/enabling-features-for-your-repository/managing-github-actions-settings-for-a-repository), and [workflow trigger behavior](https://docs.github.com/en/actions/how-tos/write-workflows/choose-when-workflows-run/trigger-a-workflow).

## Prepare a proposal without publishing

Run `python3 scripts/propose_update.py --output-dir review-update` in a locked checkout. The output directory must not already exist. Exit codes are `0` for current, `2` for a prepared proposal, `3` for a missing baseline, and `1` for an error. The publisher is an Actions-only entry point, not a general artifact uploader.
