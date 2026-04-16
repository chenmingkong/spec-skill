"""Parse openspec/config.yaml and extract spec_sources."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import yaml


@dataclass
class SpecSource:
    tier: str
    repo: str        # github.com/owner/repo
    path: str        # subdirectory within repo, e.g. specs/company
    version: str     # ~1.0 | latest | 1.0.0


def find_config(start: Optional[Path] = None) -> Path:
    """Walk up from start directory to find openspec/config.yaml."""
    current = start or Path.cwd()
    for directory in [current, *current.parents]:
        candidate = directory / "openspec" / "config.yaml"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "openspec/config.yaml not found. Run `spec init` to initialise."
    )


def load_sources(config_path: Optional[Path] = None) -> List[SpecSource]:
    """Return spec_sources from config.yaml, ordered by tier priority."""
    path = config_path or find_config()
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    raw_sources = data.get("spec_sources") or []
    sources: List[SpecSource] = []
    for entry in raw_sources:
        repo = entry.get("repo", "")
        # Normalise: strip leading "github.com/"
        repo = repo.removeprefix("https://").removeprefix("github.com/")
        sources.append(SpecSource(
            tier=entry.get("tier", "unknown"),
            repo=repo,
            path=entry.get("path", "specs").rstrip("/"),
            version=str(entry.get("version", "latest")),
        ))
    return sources


def openspec_root(config_path: Optional[Path] = None) -> Path:
    """Return the directory containing openspec/."""
    path = config_path or find_config()
    return path.parent.parent
