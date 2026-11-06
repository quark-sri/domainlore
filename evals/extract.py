"""Agent extraction test: can an agent find the planted Spec Conflict in the demo documents?

    uv run python evals/extract.py <empty dir>          # set up one copy, print the agent command
    uv run python evals/extract.py <empty dir> --run    # run Claude Code once and score
    uv run python evals/extract.py <copy> --score <transcript.jsonl>  # score a finished run

Each copy is the demo without the threshold Spec Conflict page, with a neutral threshold page and
only the lore-extract and lore-use skills, in a new git repository. The agent gets one prompt.
The checks read the copy's git and file state; only the tool checks read the transcript, which
is Claude Code stream-json.
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
MODEL = "claude-opus-5-5"
BUDGET_USD = 3  # a session that loops stops here
TIMEOUT_S = 1800  # a session that hangs stops here
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
TOOLS = [  # writes only in the Proposal folder; the checks below also detect other writes
    *("Read", "Grep", "Glob", "Skill", "Bash(lore:*)", "Bash(uv run lore:*)"),
    *(f"{tool}(./.lore/proposals/**)" for tool in ("Write", "Edit")),
    *(f"Bash({c}:*)" for c in ("git status", "git log", "git diff", "ls", "mkdir")),
    "Bash(git branch --show-current)",
]
# A heuristic for a shell write into knowledge/ (a redirect, tee or sed -i); the allowed tools
# and the git-state check are the real guards.
SHELL_WRITE = re.compile(r"(>>?|\btee(\s+-a)?|\bsed\s+-i\S*)\s*[^\s|;&]*knowledge/")


def lore_bin() -> str:
    """The `lore` next to this Python (a `uv run` environment), else the one on PATH."""
    found = shutil.which("lore", path=str(Path(sys.executable).parent)) or shutil.which("lore")
    if not found:
        sys.exit("`lore` not found; run with `uv run python evals/extract.py`")
    return found


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
    sh(root, lore_bin(), "build")
    if subprocess.run([lore_bin(), "check"], cwd=root, capture_output=True).returncode:
        sys.exit("lore check fails on the set-up copy")
    sh(root, "git", "init", "-q", "-b", "main")
    sh(root, "git", "config", "user.name", "demo")
    sh(root, "git", "config", "user.email", "demo@example.com")
    sh(root, "git", "add", "-A")
    sh(root, "git", "commit", "-q", "-m", "Demo Knowledge Base")


def command(model: str = MODEL) -> list[str]:
    return [
        *("claude", "-p", PROMPT, "--model", model, "--max-budget-usd", str(BUDGET_USD)),
        *("--setting-sources", "project,local", "--output-format", "stream-json", "--verbose"),
        *("--allowedTools", *TOOLS),
        *("--disallowedTools", "WebFetch", "WebSearch", "Agent", "Bash(gh:*)"),
    ]


def run(root: Path, transcript: Path, model: str = MODEL) -> None:
    env = {**os.environ, "PATH": f"{Path(lore_bin()).parent}{os.pathsep}{os.environ['PATH']}"}
    with transcript.open("w") as out:
        try:
            subprocess.run(
                command(model),
                cwd=root,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=out,
                timeout=TIMEOUT_S,
            )
        except subprocess.TimeoutExpired:
            print(f"session stopped after {TIMEOUT_S} s; scoring what it left")


def frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    return yaml.safe_load(text.split("\n---", 1)[0][4:]) or {} if text.startswith("---") else {}


def plain(text: str) -> str:
    return re.sub(r"[*`]|__", "", text)


def span_ok(root: Path, page: Path, source: dict) -> bool:
    """The span's text matches the footnote quote and the version is the file's hash."""
    try:
        doc, span = str(source["resource"]).removeprefix("../").split("#char=")
        start, end = map(int, span.split(","))
        cache = json.loads((root / ".lore/cache" / f"{doc}.json").read_text())
        sha = hashlib.sha256((root / doc).read_bytes()).hexdigest()
    except (OSError, ValueError, KeyError):
        return False
    quoted = plain(" ".join(cache["text"][start:end].split()))
    note = re.search(
        rf"^\[\^{re.escape(str(source.get('id')))}\]:.*\"(.*)\"$", page.read_text(), re.MULTILINE
    )
    return source.get("version") == f"sha256:{sha}" and bool(note) and plain(note[1]) == quoted


def spans(root: Path) -> list[tuple[str, str, bool]]:
    """(page, source id, ok) for every document Source in the Knowledge Base."""
    return [
        (page.relative_to(root).as_posix(), str(source.get("id")), span_ok(root, page, source))
        for page in sorted((root / "knowledge").rglob("*.md"))
        for source in frontmatter(page).get("sources") or []
        if "#char=" in str(source.get("resource", ""))
    ]


def tool_uses(transcript: Path) -> tuple[list[dict], dict]:
    events = [json.loads(line) for line in transcript.read_text().splitlines() if line.strip()]
    uses = [
        c
        for e in events
        if e.get("type") == "assistant"
        for c in e["message"]["content"]
        if c.get("type") == "tool_use"
    ]
    return uses, next((e for e in events if e.get("type") == "result"), {})


def checks(root: Path, transcript: Path) -> tuple[list[tuple[str, bool]], list[str]]:
    """The scored rows and the details to print for failures."""
    uses, _ = tool_uses(transcript)
    proposals = root / ".lore" / "proposals"
    stray = [  # files written outside the Proposal folder, by a tool or a shell redirect
        u["input"].get("file_path", "")
        for u in uses
        if u["name"] in ("Edit", "Write")
        and not (root / u["input"].get("file_path", ""))
        .resolve()
        .is_relative_to(proposals.resolve())
    ] + [
        u["input"].get("command", "")
        for u in uses
        if u["name"] == "Bash" and SHELL_WRITE.search(u["input"].get("command", ""))
    ]
    branch = sh(root, "git", "branch", "--show-current").strip()
    commits = sh(root, "git", "log", "--format=%s", "main..HEAD").splitlines()
    uncommitted = sh(root, "git", "status", "--porcelain", "--", "knowledge").splitlines()
    changed = sh(root, "git", "diff", "--name-only", "main..HEAD").split()
    planted = [
        p
        for p in changed
        if p.startswith("knowledge/")
        and (root / p).is_file()
        and frontmatter(root / p).get("type") == "Spec Conflict"
        and {"5 000", "10 000"} <= set(re.findall(r"\d+ 000", (root / p).read_text()))
        and "approval-rules.pdf" in str(frontmatter(root / p).get("sources"))
    ]
    before = sh(root, "git", "ls-tree", "-r", "--name-only", "main", "--", "knowledge").split()
    reviewed = [  # pages a person had reviewed that lost their review, or were deleted or moved
        p
        for p in before
        if p.endswith(".md")
        and frontmatter_at(root, p).get("verified")
        and not ((root / p).is_file() and frontmatter(root / p).get("verified"))
    ]
    checked = spans(root)
    good = sum(ok for *_, ok in checked)
    check = subprocess.run([lore_bin(), "check"], cwd=root, capture_output=True)
    rows = [
        (
            "used the lore-extract skill",
            any(
                u["name"] == "Skill" and str(u["input"].get("skill", "")).endswith("lore-extract")
                for u in uses
            ),
        ),
        ("wrote only in .lore/proposals/", not stray),
        (
            "knowledge/ changed only by Proposal commits on a lore/ branch",
            branch.startswith("lore/")
            and bool(commits)
            and all(c.startswith("Proposal: ") for c in commits)
            and not uncommitted,
        ),
        ("planted Spec Conflict found (5 000 vs 10 000, cites the PDF)", bool(planted)),
        (
            f"document spans verified ({good}/{len(checked)})",
            bool(checked) and good == len(checked),
        ),
        ("no review removed", not reviewed),
        ("lore check: 0 errors", check.returncode == 0),
    ]
    details = [f"bad span: {page} [{sid}]" for page, sid, ok in checked if not ok]
    details += [f"written: {s}" for s in stray] + [f"review removed: {p}" for p in reviewed]
    details += [f"commit: {c}" for c in commits if not c.startswith("Proposal: ")]
    details += [f"uncommitted: {line}" for line in uncommitted]
    return rows, details


def frontmatter_at(root: Path, path: str, ref: str = "main") -> dict:
    text = sh(root, "git", "show", f"{ref}:{path}")
    return yaml.safe_load(text.split("\n---", 1)[0][4:]) or {} if text.startswith("---") else {}


def score(root: Path, transcript: Path) -> bool:
    rows, details = checks(root, transcript)
    _, result = tool_uses(transcript)
    skill = root / ".claude" / "skills" / "lore-extract" / "SKILL.md"
    commit = sh(REPO, "git", "rev-parse", "--short", "HEAD").strip()
    events = [json.loads(line) for line in transcript.read_text().splitlines() if line.strip()]
    model = next((e.get("model") for e in events if e.get("type") == "system"), None) or "unknown"
    status = ("status", "--porcelain", "--untracked-files=no", "--", "skills", "src", "evals")
    dirty = " (uncommitted changes)" if sh(REPO, "git", *status) else ""
    for name, ok in rows:
        print(f"{'PASS' if ok else 'FAIL'}  {name}")
    for line in details:
        print(f"      {line}")
    changed = sh(root, "git", "diff", "--name-only", "main..HEAD", "--", "knowledge").split()
    print(
        f"scored at repo {commit}{dirty}; lore-extract sha256:"
        f"{hashlib.sha256(skill.read_bytes()).hexdigest()[:12]}, model {model}, "
        f"pages changed {len(changed)}, cost ${result.get('total_cost_usd', 0):.2f}, "
        f"turns {result.get('num_turns')}"
    )
    return all(ok for _, ok in rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("dir", type=Path)
    parser.add_argument("--run", action="store_true", help="run Claude Code headless and score")
    parser.add_argument("--runs", type=int, default=1, help="sessions with --run (default 1)")
    parser.add_argument("--model", default=MODEL, help=f"agent model (default {MODEL})")
    parser.add_argument("--score", type=Path, metavar="TRANSCRIPT", help="score a finished run")
    args = parser.parse_args()
    if args.runs < 1:
        parser.error("--runs must be 1 or more")
    base = args.dir.resolve()
    if args.score:
        sys.exit(0 if score(base, args.score) else 1)
    if not args.run:
        setup(base)
        transcript = base.with_name(base.name + ".jsonl")
        print(f"Set up {base}. With {Path(lore_bin()).parent} on PATH, run:")
        agent = shlex.join(command(args.model))
        print(f"  cd {shlex.quote(str(base))} && {agent} < /dev/null > {transcript}")
        print(f"Then: uv run python evals/extract.py {base} --score {transcript}")
        return
    print(f"{args.runs} session(s), at most {args.runs * BUDGET_USD} USD")
    passed = 0
    for i in range(1, args.runs + 1):
        root, transcript = base / f"run-{i}", base / f"run-{i}.jsonl"
        setup(root)
        run(root, transcript, args.model)
        print(f"\n## run {i}: {root}")
        passed += score(root, transcript)
    print(f"\n{passed}/{args.runs} runs passed all checks")
    sys.exit(0 if 3 * passed >= 2 * args.runs else 1)  # 1 of 1, 2 of 3


if __name__ == "__main__":
    main()
