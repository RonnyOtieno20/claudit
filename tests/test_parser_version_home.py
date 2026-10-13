"""PARSER_VERSION's home, disjoint from the pricing bot's write surface.

Issue #986: PARSER_VERSION shared backend/constants.py with
PRICING_VERSION, and the hourly pricing bot (refresh-pricing.yml's
cron) rewrites that file to bump PRICING_VERSION around the clock, so
every parser-version change textually conflicted with the bot's
commits and rebased on them first. The fix moved PARSER_VERSION to
backend/parser_version.py. These pins hold the split in place: the
bot's staged write surface never reaches the parser version's home,
constants holds no copy of the constant, every backend read stamps the
one value the module holds, and the SV-TEST-DATA guard flags a literal
patched onto the new module too.
"""
from __future__ import annotations

import ast
from pathlib import Path

import yaml

from backend import constants, parser_version
from tests.source_scan_cache import for_source, source
from tests.test_no_pinned_version_literals import check
from tests.version_literal_guard import detect

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "refresh-pricing.yml"
REFRESH_COMMON = ROOT / "scripts" / "ci" / "refresh_common.py"
HOME = "backend/parser_version.py"


def _run_blocks() -> list[str]:
    """Every `run:` block in the pricing bot's workflow."""
    doc = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return [step.get("run") or ""
            for job in doc["jobs"].values()
            for step in (job.get("steps") or [])]


def _staged_paths() -> set[str]:
    """The repository paths the bot's own script names as its files: the
    `cp` sources of the staged artifact, the `git add` arguments of the
    push, and the `git diff` paths that decide whether anything moved."""
    paths: set[str] = set()
    for run in _run_blocks():
        for line in run.splitlines():
            stripped = line.strip()
            if stripped.startswith("cp "):
                token = stripped.split()[1]
                if not token.startswith(('"', "$")):
                    paths.add(token)
            elif "git diff --quiet -- " in stripped:
                paths.update(stripped.split("-- ", 1)[1].split())
            elif "push-repo\" add " in stripped:
                paths.update(stripped.split(" add ", 1)[1].split())
    return paths


def test_the_pricing_bots_write_surface_excludes_the_parser_home():
    staged = _staged_paths()
    # Non-vacuous: the bot still stages the constants module it rewrites
    # for PRICING_VERSION — a workflow that stopped naming its own files
    # must not pass this pin by disappearance.
    assert "backend/constants.py" in staged
    home = Path(parser_version.__file__).resolve()
    assert home.relative_to(ROOT).as_posix() == HOME
    assert HOME not in staged, (
        "PARSER_VERSION's home is inside the pricing bot's write surface; "
        f"staged: {sorted(staged)}")


def test_the_bots_version_bump_never_names_the_parser_version():
    # The bump helper the bot drives rewrites PRICING_VERSION lines only;
    # a PARSER_VERSION reaching this file would put the parser version
    # back under the bot's regex.
    text = REFRESH_COMMON.read_text(encoding="utf-8")
    assert "PRICING_VERSION" in text
    assert "PARSER_VERSION" not in text


def test_constants_holds_no_parser_version():
    # No re-export, no stale copy: constants.py must not carry the
    # constant back into the file the bot rewrites hourly.
    assert not hasattr(constants, "PARSER_VERSION")


def test_every_backend_parser_version_read_goes_through_the_module():
    readers = set()
    offenders = []
    for path in sorted((ROOT / "backend").glob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        for node in ast.walk(for_source(source(path)).tree()):
            if (isinstance(node, ast.Attribute)
                    and node.attr == "PARSER_VERSION"):
                if (isinstance(node.value, ast.Name)
                        and node.value.id == "parser_version"):
                    readers.add(rel)
                else:
                    offenders.append(f"{rel}:{node.lineno}")
    assert not offenders, offenders
    # The two stampers — the ingest walk's version argument and the
    # scope fingerprint's "parser" key — read the same module, so one
    # bump reaches every stamp in the same commit.
    assert {"backend/ingest.py", "backend/ingest_scope.py"} <= readers


def test_a_literal_assignment_on_the_new_module_is_flagged():
    result = detect("parser_version.PARSER_VERSION = '82'\n")
    assert [(site.name, site.shape) for site in result] == [
        ("PARSER_VERSION", "assign")]


def test_a_setattr_literal_on_the_new_module_is_flagged():
    result = detect(
        "monkeypatch.setattr(parser_version, 'PARSER_VERSION', '2')\n")
    assert [(site.name, site.shape, site.value) for site in result] == [
        ("PARSER_VERSION", "setattr", "2")]


def test_a_derived_value_on_the_new_module_is_not_flagged():
    sample = ("monkeypatch.setattr(parser_version, 'PARSER_VERSION',\n"
              "    str(int(parser_version.PARSER_VERSION) + 1))\n")
    assert detect(sample) == []


def test_an_unmarked_literal_on_the_new_module_fails_check():
    problems = check("parser_version.PARSER_VERSION = '999'\n")
    assert len(problems) == 1
    assert "PARSER_VERSION" in problems[0]
