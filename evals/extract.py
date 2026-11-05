"""Agent extraction test: can an agent find the planted Spec Conflict in the demo documents?

    uv run python evals/extract.py <empty dir>         # set up the copy, print the agent command
    uv run python evals/extract.py <empty dir> --run   # also run Claude Code headless and score
    uv run python evals/extract.py <dir> --score <transcript.jsonl>  # score a finished run

The copy is the demo without the threshold Spec Conflict page, with a neutral threshold page and
only the lore-extract and lore-use skills, in a new git repository. The agent gets one prompt.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
DEMO = REPO / "examples" / "order-approval"
LORE = REPO / ".venv" / "bin"
PROMPT = "Extract the domain facts from the documents in docs/ into the knowledge base."
CONFLICT = "knowledge/conflicts/approval-threshold-amount.md"
THRESHOLD = "knowledge/approvals/rules/approval-threshold.md"
NEUTRAL = [  # (old, new) in the threshold page: no amount, no link to the removed conflict
    (
        "Confluence sets the threshold at **10 000 EUR**.[^wiki-approvals] The BRD sets it at "
        "**5 000 EUR**.[^policy]\nSee the open "
        "[Spec Conflict](/conflicts/approval-threshold-amount.md).\n\n"
        "[^wiki-approvals]: Approval rules (Confluence)\n",
        "Orders above a total amount need approval before they are processed.[^policy]\n\n",
    ),
    (
        "  - id: wiki-approvals\n    resource: https://wiki.example.com/display/APR/Approval+rules\n"
        '    title: Approval rules (Confluence)\n    version: "12"\n'
        "    last_modified: 2026-06-01T00:00:00Z\n",
        "",
    ),
]
TOOLS = [
    *("Read", "Grep", "Glob", "Write", "Edit", "Skill", "Bash(lore:*)", "Bash(uv run lore:*)"),
    *(f"Bash({c}:*)" for c in ("git status", "git log", "git branch", "git diff", "ls", "cat")),
    "Bash(mkdir:*)",
]


def sh(cwd: Path, *args: str) -> str:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True, check=True).stdout


def setup(root: Path) -> None:
    if root.exists() and any(root.iterdir()):
        sys.exit(f"{root} is not empty")
    shutil.copytree(DEMO, root, ignore=shutil.ignore_patterns(".lore", "proposals"))
    (root / CONFLICT).unlink()
    page = root / THRESHOLD
    text = page.read_text()
    for old, new in NEUTRAL:
        if old not in text:
            sys.exit(f"the demo threshold page changed; update NEUTRAL in {__file__}")
        text = text.replace(old, new)
    page.write_text(text)
    for skill in ("lore-extract", "lore-use"):
        shutil.copytree(REPO / "skills" / skill, root / ".claude" / "skills" / skill)
    lore = str(LORE / "lore")
    sh(root, lore, "build")
    if subprocess.run([lore, "check"], cwd=root, capture_output=True).returncode:
        sys.exit("lore check fails on the set-up copy")
    sh(root, "git", "init", "-q", "-b", "main")
    sh(root, "git", "config", "user.name", "demo")
    sh(root, "git", "config", "user.email", "demo@example.com")
    sh(root, "git", "add", "-A")
    sh(root, "git", "commit", "-q", "-m", "Demo Knowledge Base")


def command() -> list[str]:
    return [
        *("claude", "-p", PROMPT, "--setting-sources", "project,local"),
        *("--output-format", "stream-json", "--verbose", "--allowedTools", *TOOLS),
        *("--disallowedTools", "WebFetch", "WebSearch", "Agent", "Bash(gh:*)"),
    ]


def run(root: Path, transcript: Path) -> None:
    env = {**os.environ, "PATH": f"{LORE}{os.pathsep}{os.environ['PATH']}"}
    with transcript.open("w") as out:
        subprocess.run(command(), cwd=root, env=env, stdin=subprocess.DEVNULL, stdout=out)


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(text.split("\n---", 1)[0][4:]) or {} if text.startswith("---") else {}


def plain(text: str) -> str:
    return re.sub(r"[*`]|__", "", text)


def spans(root: Path) -> list[tuple[str, str, bool]]:
    """(page, source id, ok) for every document Source: span text, hash and footnote agree."""
    found = []
    for page in sorted((root / "knowledge").rglob("*.md")):
        for source in frontmatter(page).get("sources") or []:
            resource = str(source.get("resource", ""))
            if "#char=" not in resource:
                continue
            doc, span = resource.removeprefix("../").split("#char=")
            start, end = map(int, span.split(","))
            cache = json.loads((root / ".lore/cache" / f"{doc}.json").read_text())
            sha = hashlib.sha256((root / doc).read_bytes()).hexdigest()
            quoted = plain(" ".join(cache["text"][start:end].split()))
            note = re.search(
                rf"^\[\^{re.escape(source['id'])}\]:.*\"(.*)\"$", page.read_text(), re.MULTILINE
            )
            ok = (
                source.get("version") == f"sha256:{sha}" and bool(note) and plain(note[1]) == quoted
            )
            found.append((page.relative_to(root).as_posix(), source["id"], ok))
    return found


def score(root: Path, transcript: Path) -> bool:
    events = [json.loads(line) for line in transcript.read_text().splitlines() if line.strip()]
    uses = [
        c
        for e in events
        if e.get("type") == "assistant"
        for c in e["message"]["content"]
        if c.get("type") == "tool_use"
    ]
    result = next((e for e in events if e.get("type") == "result"), {})
    direct = [
        u["input"]["file_path"]
        for u in uses
        if u["name"] in ("Edit", "Write") and "/knowledge/" in u["input"].get("file_path", "")
    ]
    branch = sh(root, "git", "branch", "--show-current").strip()
    commits = sh(root, "git", "log", "--format=%s", "main..HEAD").splitlines()
    changed = sh(root, "git", "diff", "--name-only", "main..HEAD").split()
    conflicts = [
        p
        for p in changed
        if p.startswith("knowledge/") and frontmatter(root / p).get("type") == "Spec Conflict"
    ]
    planted = [
        p
        for p in conflicts
        if {"5 000", "10 000"} <= set(re.findall(r"\d+ 000", (root / p).read_text()))
        and "approval-rules.pdf" in str(frontmatter(root / p).get("sources"))
    ]
    modified = sh(root, "git", "diff", "--name-only", "--diff-filter=M", "main..HEAD").split()
    reviewed = [  # pages a person had reviewed that lost their review
        p
        for p in modified
        if p.startswith("knowledge/")
        and "\nverified:" in sh(root, "git", "show", f"main:{p}")
        and not frontmatter(root / p).get("verified")
    ]
    checked = spans(root)
    check = subprocess.run([str(LORE / "lore"), "check"], cwd=root, capture_output=True)
    rows = [
        ("used lore-extract", any(u["name"] == "Skill" for u in uses)),
        ("no direct edits to knowledge/", not direct),
        ("committed on a lore/ branch", branch.startswith("lore/") and bool(commits)),
        ("planted Spec Conflict found (5 000 vs 10 000, cites the PDF)", bool(planted)),
        (
            f"document spans verified ({sum(ok for *_, ok in checked)}/{len(checked)})",
            bool(checked) and all(ok for *_, ok in checked),
        ),
        ("no review removed", not reviewed),
        ("lore check: 0 errors", check.returncode == 0),
    ]
    for name, ok in rows:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    for page, sid, ok in checked:
        if not ok:
            print(f"      bad span: {page} [{sid}]")
    for path in direct + reviewed:
        print(f"      {path}")
    print(
        f"pages changed: {len([p for p in changed if p.startswith('knowledge/')])}, "
        f"cost ${result.get('total_cost_usd', 0):.2f}, turns {result.get('num_turns')}"
    )
    return all(ok for _, ok in rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dir", type=Path)
    parser.add_argument("--run", action="store_true", help="run Claude Code headless and score")
    parser.add_argument("--score", type=Path, metavar="TRANSCRIPT", help="score a finished run")
    args = parser.parse_args()
    root = args.dir.resolve()
    if args.score:
        sys.exit(0 if score(root, args.score) else 1)
    setup(root)
    transcript = root.with_name(root.name + ".jsonl")
    if not args.run:
        run_it = (
            f"cd {shlex.quote(str(root))} && {shlex.join(command())} < /dev/null > {transcript}"
        )
        print(f"Set up {root}. With {LORE} on PATH, run:\n  {run_it}")
        print(f"Then: uv run python evals/extract.py {root} --score {transcript}")
        return
    run(root, transcript)
    sys.exit(0 if score(root, transcript) else 1)


if __name__ == "__main__":
    main()
