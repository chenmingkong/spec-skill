"""CLI entry point: spec sync | spec check | spec init"""
from __future__ import annotations

import io
import os
import sys

# Ensure UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import click

from .checker import print_results, run_check
from .config import find_config, load_sources, openspec_root
from .github import GitHubClient, GitHubError
from .merger import (
    LockEntry,
    merge,
    write_compliance_file,
    write_effective_spec,
    write_lock_file,
)
from .parser import parse_overrides, parse_requirements


@click.group()
def cli():
    """Multi-tier spec sync and compliance check."""


# ── spec sync ─────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--token", envvar="GITHUB_TOKEN", default="",
              help="GitHub personal access token (or set GITHUB_TOKEN env var)")
@click.option("--config", "config_path", default=None, type=click.Path(),
              help="Path to openspec/config.yaml (auto-detected if omitted)")
def sync(token: str, config_path: Optional[str]):
    """Pull upper-tier specs from GitHub, merge, and commit artifacts."""
    cfg_path = Path(config_path) if config_path else None
    try:
        sources = load_sources(cfg_path)
        root = openspec_root(cfg_path)
    except FileNotFoundError as e:
        click.echo(f"error: {e}", err=True)
        sys.exit(1)

    if not sources:
        click.echo("No spec_sources declared in config.yaml — nothing to sync.")
        return

    client = GitHubClient(token or None)
    tier_data = []
    lock_entries: list[LockEntry] = []

    for source in sources:
        click.echo(f"  → pulling {source.tier} from {source.repo} ({source.version})")
        try:
            tag, commit = client.resolve_version(source.repo, source.version)
        except GitHubError as e:
            click.echo(f"error: {e}", err=True)
            sys.exit(1)

        click.echo(f"    resolved {source.version} → {tag} ({commit[:8]})")
        try:
            spec_files = client.get_spec_files(source.repo, source.path, tag)
        except GitHubError as e:
            click.echo(f"error fetching specs: {e}", err=True)
            sys.exit(1)

        cap_map = {
            cap: parse_requirements(content, cap)
            for cap, content in spec_files.items()
        }
        tier_data.append((source.tier, tag, source.repo, cap_map))
        lock_entries.append(LockEntry(
            tier=source.tier,
            repo=source.repo,
            path=source.path,
            tag=tag,
            commit=commit,
            pulled_at=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        ))

    # Collect service-level overrides from openspec/specs/**/*.md
    service_overrides = _load_service_overrides(root / "openspec" / "specs")

    compliance, all_reqs = merge(tier_data, service_overrides)

    merged_dir = root / "openspec" / "merged"
    write_effective_spec(all_reqs, compliance, merged_dir / "effective-spec.md")
    write_lock_file(lock_entries, root / "openspec" / ".spec-lock.yaml")
    write_compliance_file(compliance, merged_dir / ".spec-compliance.yaml")

    click.echo(f"\n✓ Synced {len(all_reqs)} requirements from {len(sources)} tier(s).")
    must_count = sum(1 for c in compliance if c.level == "must")
    issues = sum(1 for c in compliance if c.status == "override_missing")
    click.echo(f"  {must_count} must requirement(s) — {issues} missing justification(s).")
    click.echo(f"\nFiles written:")
    click.echo(f"  openspec/merged/effective-spec.md")
    click.echo(f"  openspec/merged/.spec-compliance.yaml")
    click.echo(f"  openspec/.spec-lock.yaml")
    click.echo(f"\nCommit these files to your repo, then run `spec check` in CI.")


# ── spec check ────────────────────────────────────────────────────────────────

@cli.command()
@click.option("--json", "as_json", is_flag=True, help="Output results as JSON")
@click.option("--config", "config_path", default=None, type=click.Path())
def check(as_json: bool, config_path: Optional[str]):
    """Verify must-field compliance against committed effective spec."""
    cfg_path = Path(config_path) if config_path else None
    try:
        root = openspec_root(cfg_path)
    except FileNotFoundError as e:
        click.echo(f"error: {e}", err=True)
        sys.exit(1)

    compliance_path = root / "openspec" / "merged" / ".spec-compliance.yaml"
    result = run_check(compliance_path)
    exit_code = print_results(result, as_json=as_json)
    sys.exit(exit_code)


# ── spec init ─────────────────────────────────────────────────────────────────

@cli.command()
@click.argument("path", default=".", type=click.Path())
def init(path: str):
    """Scaffold openspec/ directory structure in PATH (default: current dir)."""
    root = Path(path).resolve()
    openspec = root / "openspec"

    if (openspec / "config.yaml").exists():
        click.echo("openspec/config.yaml already exists — nothing to do.")
        return

    (openspec / "specs").mkdir(parents=True, exist_ok=True)
    (openspec / "changes").mkdir(parents=True, exist_ok=True)
    (openspec / "merged").mkdir(parents=True, exist_ok=True)

    config_content = """\
schema: spec-driven

# Spec sources — upper-tier specs to inherit from.
# Run `spec sync` to pull and merge into openspec/merged/effective-spec.md
#
# spec_sources:
#   - tier: company
#     repo: github.com/your-org/company-specs
#     path: specs/company
#     version: "~1.0"      # ~1.0 | latest | 1.0.0
#   - tier: dept
#     repo: github.com/your-org/dept-specs
#     path: specs/backend
#     version: latest
"""
    (openspec / "config.yaml").write_text(config_content, encoding="utf-8")

    gitignore = openspec / ".gitignore"
    gitignore.write_text("# spec-compliance is machine-generated but should be committed\n")

    click.echo(f"✓ Initialised openspec/ in {root}")
    click.echo("  Edit openspec/config.yaml to declare spec_sources, then run `spec sync`.")


# ── Helpers ───────────────────────────────────────────────────────────────────

def _load_service_overrides(specs_dir: Path):
    from .parser import Override
    overrides = []
    if not specs_dir.exists():
        return overrides
    for spec_file in specs_dir.rglob("*.md"):
        content = spec_file.read_text(encoding="utf-8")
        overrides.extend(parse_overrides(content))
    return overrides
