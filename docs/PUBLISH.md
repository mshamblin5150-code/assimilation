# Publishing Assimilation publicly on GitHub

**Publication remains held until the before-publish review is complete.** The following commands describe the later publication procedure; they are not permission to run it. The package is not a GitHub repository until an authorized owner publishes it. The starter includes no `.git` folder and no authentication token.

## GitHub CLI path

Run the following on **your own computer** after installing [Git](https://git-scm.com/) and [GitHub CLI](https://cli.github.com/) and extracting the ZIP into a folder called `assimilation`:

```sh
cd assimilation
gh auth login            # First use only; follow your browser's secure login flow
git init -b main
git add .
git commit -m "Initial public Assimilation doctrine"
gh repo create mshamblin5150-code/assimilation --public --source=. --remote=origin --push
```

The `gh repo create` command is a **public publication action**. Inspect the staged changes with `git status` and `git diff --cached` before running it. Keep `.assimilation-stage-*`, `.assimilation-install.lock`, `vendor/`, and `.agents/` out of the commit. Do not commit personal files, private project code, PHI, or credentials. If `git commit` requests an identity, configure your own `git config user.name` and `git config user.email` for that repository.

The repo should then be accessible at `https://github.com/mshamblin5150-code/assimilation`. This URL is a **planned address**, not confirmation the repository exists yet. Verify it opens publicly before sharing with Chad.

## Install the actual upstream skills

In a working copy with Git and Python 3.10+:

```sh
python3 scripts/skills.py install
python3 -m unittest discover -s tests -v
python3 scripts/skills.py check
```

On Windows, use `py -3` instead of `python3` if needed. The installer creates the **locally ignored** `vendor/` and `.agents/skills/` directories. This ensures the public repository stays small and upstream sources/credits remain intact. `sources.lock.json` records the actual installed commits and should be committed when you want monthly GitHub Actions checks to have an authoritative baseline:

```sh
git add sources.lock.json
git commit -m "Pin initial upstream skill revisions"
git push
```

Review the installed contents before letting an agent use executable upstream tools. The monthly workflow prepares a frozen update proposal and an issue handoff, not a published PR. Automatic PR publication is held for a separate token-permission decision. Follow [the reviewed update procedure](UPDATES.md) to prepare a draft PR without changing a reviewed SHA to the latest `main`. Keep automatic merge disabled.

## If GitHub CLI is unavailable

Create a public repository named `assimilation` under your own GitHub account, then upload the contents of the extracted ZIP while preserving the directory structure. This still requires signing into your GitHub account. Avoid uploading private or machine-generated `vendor/`, `.agents/`, or personal materials.
