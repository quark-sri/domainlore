"""install-skills.sh puts the skills where each agent reads them.

It never replaces a folder that it did not install.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "install-skills.sh"
SKILLS = sorted(p.name for p in (ROOT / "skills").iterdir() if (p / "SKILL.md").is_file())

pytestmark = pytest.mark.skipif(
    shutil.which("bash") is None or sys.platform == "win32",
    reason="needs bash and symbolic links",
)


def run(home: Path, *args: str, path: str | None = None) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "HOME": str(home)}
    if path is not None:
        env["PATH"] = path
    return subprocess.run(
        ["bash", str(SCRIPT), *args], capture_output=True, text=True, env=env, check=False
    )


def test_user_install_for_codex_links_each_skill_into_the_user_agents_folder(tmp_path):
    result = run(tmp_path, "--agent", "codex", "--user")
    assert result.returncode == 0, result.stderr
    target = tmp_path / ".agents" / "skills"
    assert sorted(p.name for p in target.iterdir()) == SKILLS
    for name in SKILLS:
        assert (target / name).is_symlink()
        assert (target / name).resolve() == (ROOT / "skills" / name).resolve()
    assert f"{target}: {len(SKILLS)} skills (link)" in result.stdout


def test_project_install_with_copy_writes_real_folders_with_a_marker(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    result = run(tmp_path, "--agent", "codex", "--project", str(repo), "--copy")
    assert result.returncode == 0, result.stderr
    skill = repo / ".agents" / "skills" / "lore-use"
    assert skill.is_dir() and not skill.is_symlink()
    source = (ROOT / "skills/lore-use/SKILL.md").read_text(encoding="utf-8")
    assert (skill / "SKILL.md").read_text(encoding="utf-8") == source
    assert (skill / ".domainlore-skill").is_file()


def test_a_second_install_replaces_its_own_copies_and_links(tmp_path):
    assert run(tmp_path, "--agent", "codex", "--user", "--copy").returncode == 0
    result = run(tmp_path, "--agent", "codex", "--user")
    assert result.returncode == 0, result.stderr
    assert "skip" not in result.stdout
    assert (tmp_path / ".agents/skills/lore-use").is_symlink()


def test_a_folder_that_domainlore_did_not_install_is_kept_and_the_run_fails(tmp_path):
    own = tmp_path / ".agents" / "skills" / "lore-use"
    own.mkdir(parents=True)
    (own / "SKILL.md").write_text("my own skill\n", encoding="utf-8")
    result = run(tmp_path, "--agent", "codex", "--user")
    assert result.returncode == 1
    assert "skip lore-use" in result.stdout
    assert "1 skill folders were skipped" in result.stderr
    assert (own / "SKILL.md").read_text(encoding="utf-8") == "my own skill\n"
    assert (tmp_path / ".agents/skills/lore-extract").is_symlink()


def test_other_skills_in_the_folder_are_not_touched(tmp_path):
    other = tmp_path / ".agents" / "skills" / "test-review-panel"
    other.mkdir(parents=True)
    (other / "SKILL.md").write_text("qestack\n", encoding="utf-8")
    assert run(tmp_path, "--agent", "codex", "--user").returncode == 0
    assert (other / "SKILL.md").read_text(encoding="utf-8") == "qestack\n"


def test_all_installs_each_shared_folder_once_and_leaves_out_claude(tmp_path):
    result = run(tmp_path, "--agent", "all", "--user")
    assert result.returncode == 0, result.stderr
    assert result.stdout.count(f"{tmp_path}/.agents/skills:") == 1
    assert (tmp_path / ".cline/skills/lore-use").is_symlink()
    assert (tmp_path / ".gemini/antigravity-cli/skills/lore-use").is_symlink()
    assert (tmp_path / ".gemini/config/skills/lore-use").is_symlink()
    assert not (tmp_path / ".claude").exists()


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (["--agent", "vim", "--user"], "unknown agent"),
        (["--agent", "codex"], "give --user"),
        (["--agent", "codex", "--project", "/no/such/folder"], "give --user"),
        (["--force"], "unknown option"),
    ],
)
def test_bad_arguments_stop_with_exit_code_2_and_install_nothing(tmp_path, args, message):
    result = run(tmp_path, *args)
    assert result.returncode == 2
    assert message in result.stderr
    assert not (tmp_path / ".agents").exists()


def test_help_lists_the_agents_and_how_to_install_the_lore_command(tmp_path):
    result = run(tmp_path, "--help")
    assert result.returncode == 0
    assert "codex" in result.stdout and "~/.agents/skills" in result.stdout
    assert "domainlore[docx,pdf] @ git+https://github.com/quark-sri/domainlore" in result.stdout


def test_a_link_to_a_folder_of_the_user_is_kept(tmp_path):
    mine = tmp_path / "my-skills" / "lore-use"
    mine.mkdir(parents=True)
    target = tmp_path / ".agents" / "skills"
    target.mkdir(parents=True)
    (target / "lore-use").symlink_to(mine)
    result = run(tmp_path, "--agent", "codex", "--user")
    assert result.returncode == 1
    assert (target / "lore-use").resolve() == mine.resolve()


def test_a_broken_link_is_replaced(tmp_path):
    target = tmp_path / ".agents" / "skills"
    target.mkdir(parents=True)
    (target / "lore-use").symlink_to(tmp_path / "moved-clone" / "skills" / "lore-use")
    assert run(tmp_path, "--agent", "codex", "--user").returncode == 0
    assert (target / "lore-use").resolve() == (ROOT / "skills" / "lore-use").resolve()


def test_a_project_path_with_spaces_works(tmp_path):
    repo = tmp_path / "my repo"
    repo.mkdir()
    result = run(tmp_path, "--agent", "codex", "--project", str(repo), "--copy")
    assert result.returncode == 0, result.stderr
    assert (repo / ".agents" / "skills" / "lore-use" / "SKILL.md").is_file()


def test_claude_installs_into_the_claude_folder_and_warns_about_the_plugin(tmp_path):
    result = run(tmp_path, "--agent", "claude", "--user")
    assert result.returncode == 0, result.stderr
    assert (tmp_path / ".claude" / "skills" / "lore-use").is_symlink()
    assert "shows each skill two times" in result.stdout


def test_without_the_lore_command_the_install_hint_names_the_word_and_pdf_extras(tmp_path):
    result = run(tmp_path, "--agent", "codex", "--user", path="/usr/bin:/bin")
    assert result.returncode == 0, result.stderr
    assert "not on your PATH" in result.stdout
    assert '"domainlore[docx,pdf] @ git+https://github.com/quark-sri/domainlore"' in result.stdout
