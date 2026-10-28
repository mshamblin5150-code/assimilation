"""Synthetic gh API transport backed by a temporary local Git repository. No network."""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from urllib.parse import parse_qs, unquote, urlsplit

state_path = Path(os.environ["FIXTURE_STATE"])
state = json.loads(state_path.read_text())
args = sys.argv[1:]
method = args[args.index("--method") + 1]
endpoint = args[args.index("--method") + 2]
url = urlsplit(endpoint)
path = unquote(url.path)
query = parse_qs(url.query)
payload = json.load(sys.stdin) if "--input" in args else None
state["calls"].append({"method": method, "path": path})


def save():
    state_path.write_text(json.dumps(state))


def git(*args, data=None, env=None, check=True):
    proc = subprocess.run(["git", *args], cwd=state["repo"], env=env, input=data,
                          capture_output=True, text=True)
    if check and proc.returncode:
        raise RuntimeError(proc.stderr)
    return proc.stdout.strip()


def fail(message):
    state["last_error"] = message
    save()
    print(message, file=sys.stderr)
    sys.exit(1)


prefix = "/repos/fixture/assimilation"
result = None
try:
    if path == prefix and method == "GET":
        result = {"default_branch": "main", "full_name": "fixture/assimilation"}
    elif path.startswith(prefix + "/git/ref/heads/") and method == "GET":
        branch = path.split("/git/ref/heads/", 1)[1]
        state["base_reads"] = state.get("base_reads", 0) + 1
        if state.get("move_default_on_read") == state["base_reads"]:
            git("update-ref", "refs/heads/main", state["replacement_base"])
        result = {"ref": "refs/heads/" + branch,
                  "object": {"type": "commit", "sha": git("rev-parse", "refs/heads/" + branch)}}
    elif path.startswith(prefix + "/git/matching-refs/heads/") and method == "GET":
        branch = path.split("/git/matching-refs/heads/", 1)[1]
        refs = git("for-each-ref", "--format=%(refname) %(objectname)", "refs/heads/" + branch)
        result = [{"ref": line.split()[0], "object": {"type": "commit", "sha": line.split()[1]}}
                  for line in refs.splitlines() if line]
    elif path.startswith(prefix + "/contents/") and method == "GET":
        name = path.split("/contents/", 1)[1]
        content = subprocess.run(["git", "show", query["ref"][0] + ":" + name],
                                 cwd=state["repo"], capture_output=True, check=True).stdout
        if git("ls-tree", query["ref"][0], "--", name).split()[0] == "120000":
            # GitHub Contents returns the target bytes for an in-repository file link.
            content = subprocess.run(["git", "show", query["ref"][0] + ":" + content.decode()],
                                     cwd=state["repo"], capture_output=True, check=True).stdout
        result = {"type": "file", "encoding": "base64", "path": name,
                  "content": base64.b64encode(content).decode()}
    elif path.startswith(prefix + "/git/commits/") and method == "GET":
        sha = path.rsplit("/", 1)[1]
        result = {"sha": sha, "tree": {"sha": git("show", "-s", "--format=%T", sha)},
                  "message": git("show", "-s", "--format=%B", sha),
                  "parents": [{"sha": x} for x in git("show", "-s", "--format=%P", sha).split()]}
    elif path.startswith(prefix + "/git/trees/") and method == "GET":
        rows = git("ls-tree", path.rsplit("/", 1)[1]).splitlines()
        result = {"truncated": False, "tree": [{"mode": row.split()[0], "type": row.split()[1],
                            "sha": row.split()[2], "path": row.split("\t", 1)[1]} for row in rows]}
    elif path == prefix + "/git/blobs" and method == "POST":
        raw = base64.b64decode(payload["content"], validate=True) if payload["encoding"] == "base64" else payload["content"].encode()
        proc = subprocess.run(["git", "hash-object", "-w", "--stdin"], cwd=state["repo"], input=raw,
                              capture_output=True, check=True)
        result = {"sha": proc.stdout.decode().strip()}
    elif path == prefix + "/git/trees" and method == "POST":
        with tempfile.TemporaryDirectory() as temp:
            env = {**os.environ, "GIT_INDEX_FILE": str(Path(temp) / "index"), "GIT_WORK_TREE": temp}
            git("read-tree", payload["base_tree"], env=env) if "base_tree" in payload else git("read-tree", "--empty", env=env)
            for entry in payload["tree"]:
                if entry["type"] == "tree":
                    # Replacing a directory means replacing its complete contents, including deletions.
                    old = git("ls-files", "--", entry["path"], env=env).splitlines()
                    for filename in old:
                        git("update-index", "--force-remove", "--", filename, env=env)
                    git("read-tree", "--prefix=" + entry["path"] + "/", entry["sha"], env=env)
                elif "sha" in entry and entry["sha"] is None:
                    git("update-index", "--force-remove", "--", entry["path"], env=env)
                else:
                    blob = entry["sha"] if "sha" in entry else git("hash-object", "-w", "--stdin", data=entry["content"])
                    git("update-index", "--add", "--cacheinfo", entry["mode"] + "," + blob + "," + entry["path"], env=env)
            result = {"sha": git("write-tree", env=env)}
    elif path == prefix + "/git/commits" and method == "POST":
        result = {"sha": git("commit-tree", payload["tree"], "-p", payload["parents"][0], "-m", payload["message"])}
    elif path == prefix + "/git/refs" and method == "POST":
        git("update-ref", payload["ref"], payload["sha"], "0" * 40)
        result = {"ref": payload["ref"], "object": {"type": "commit", "sha": payload["sha"]}}
        if state.pop("fail_ref_after", False):
            fail("Injected lost create-ref response")
    elif path.startswith(prefix + "/compare/") and method == "GET":
        base, head = path.split("/compare/", 1)[1].split("...")
        ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", base, head], cwd=state["repo"]).returncode == 0
        files = git("diff", "--name-only", base, head).splitlines()
        result = {"total_commits": int(git("rev-list", "--count", base + ".." + head)),
                  "status": "identical" if base == head else ("ahead" if ancestor else "diverged"),
                  "files": [{"filename": x} for x in files]}
    elif path == prefix + "/pulls" and method == "GET":
        result = [p for p in state["pulls"] if p["head"]["label"] == query["head"][0]
                  and p["base"]["ref"] == query["base"][0]]
    elif path == prefix + "/pulls" and method == "POST":
        if state.pop("fail_pr_before", False):
            fail("Injected PR creation failure")
        number = len(state["pulls"]) + 1
        result = {"number": number, "html_url": f"https://github.com/fixture/assimilation/pull/{number}",
                  "state": "open", "draft": payload["draft"], "user": {"login": "github-actions[bot]"},
                  "head": {"ref": payload["head"], "label": "fixture:" + payload["head"],
                           "sha": git("rev-parse", "refs/heads/" + payload["head"]),
                           "repo": {"full_name": "fixture/assimilation"}},
                  "base": {"ref": payload["base"], "repo": {"full_name": "fixture/assimilation"}},
                  "title": payload["title"], "body": payload["body"]}
        state["pulls"].append(result)
        if state.pop("fail_pr_after", False):
            fail("Injected lost PR creation response")
    else:
        fail("Unsupported fixture API operation: " + method + " " + path)
except (RuntimeError, KeyError, ValueError, subprocess.CalledProcessError) as exc:
    fail(str(exc))
save()
print(json.dumps(result))
