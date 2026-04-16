"""GitHub API client: fetch tags, resolve semver ranges, download spec files."""
from __future__ import annotations

import base64
import os
import re
from typing import Dict, List, Optional, Tuple

import requests


class GitHubError(Exception):
    pass


class GitHubClient:
    BASE = "https://api.github.com"

    def __init__(self, token: Optional[str] = None):
        tok = token or os.getenv("GITHUB_TOKEN", "")
        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/vnd.github.v3+json",
            **({"Authorization": f"token {tok}"} if tok else {}),
        })

    def _get(self, url: str, **params) -> dict | list:
        r = self._session.get(url, params=params, timeout=30)
        if r.status_code == 404:
            raise GitHubError(f"Not found: {url}")
        if not r.ok:
            raise GitHubError(f"GitHub API error {r.status_code}: {r.text[:200]}")
        return r.json()

    # ── Tag resolution ────────────────────────────────────────────────────────

    def list_tags(self, repo: str) -> List[Tuple[str, str]]:
        """Return [(tag_name, commit_sha), ...] sorted newest first."""
        data = self._get(f"{self.BASE}/repos/{repo}/tags", per_page=100)
        return [(t["name"], t["commit"]["sha"]) for t in data]

    def resolve_version(self, repo: str, version_spec: str) -> Tuple[str, str]:
        """
        Given a version spec, return (tag_name, commit_sha).
        Supports: 'latest', exact '1.2.3', tilde '~1.2'.
        """
        tags = self.list_tags(repo)
        if not tags:
            raise GitHubError(f"No tags found in {repo}")

        versioned = [
            (name, sha) for name, sha in tags
            if re.match(r'^v?\d+\.\d+', name)
        ]
        if not versioned:
            raise GitHubError(f"No semver tags found in {repo}")

        if version_spec == "latest":
            return versioned[0]

        return _pick_tag(versioned, version_spec, repo)

    # ── File fetching ─────────────────────────────────────────────────────────

    def get_tree(self, repo: str, ref: str) -> List[str]:
        """Return all blob paths in the repo at the given ref."""
        commit_data = self._get(f"{self.BASE}/repos/{repo}/commits/{ref}")
        tree_sha = commit_data["commit"]["tree"]["sha"]
        tree_data = self._get(
            f"{self.BASE}/repos/{repo}/git/trees/{tree_sha}",
            recursive=1,
        )
        return [item["path"] for item in tree_data.get("tree", [])
                if item["type"] == "blob"]

    def get_file(self, repo: str, path: str, ref: str) -> str:
        """Return decoded text content of a file at ref."""
        data = self._get(
            f"{self.BASE}/repos/{repo}/contents/{path}",
            ref=ref,
        )
        if isinstance(data, list):
            raise GitHubError(f"{path} is a directory, not a file")
        return base64.b64decode(data["content"]).decode("utf-8")

    def get_spec_files(self, repo: str, base_path: str, ref: str) -> Dict[str, str]:
        """
        Return {capability: content} for all spec.md files under base_path.
        e.g. base_path='specs/company' → capability='api-security'
        """
        all_paths = self.get_tree(repo, ref)
        prefix = base_path.rstrip("/") + "/"
        result: Dict[str, str] = {}
        for p in all_paths:
            if p.startswith(prefix) and p.endswith("/spec.md"):
                # specs/company/api-security/spec.md → capability = api-security
                relative = p[len(prefix):]
                parts = relative.split("/")
                if len(parts) == 2 and parts[1] == "spec.md":
                    capability = parts[0]
                    result[capability] = self.get_file(repo, p, ref)
        return result


# ── Semver helpers ────────────────────────────────────────────────────────────

def _parse_version(tag: str) -> Tuple[int, int, int]:
    """Parse vX.Y.Z or X.Y.Z → (major, minor, patch)."""
    m = re.match(r'^v?(\d+)\.(\d+)(?:\.(\d+))?', tag)
    if not m:
        raise ValueError(f"Cannot parse version: {tag}")
    return int(m.group(1)), int(m.group(2)), int(m.group(3) or 0)


def _pick_tag(tags: List[Tuple[str, str]], spec: str, repo: str) -> Tuple[str, str]:
    """Match tilde range (~1.2 or ~1.2.3) or exact version."""
    tilde = re.match(r'^~(\d+)\.(\d+)(?:\.(\d+))?$', spec)
    if tilde:
        major = int(tilde.group(1))
        minor = int(tilde.group(2))
        candidates = []
        for name, sha in tags:
            try:
                v_maj, v_min, v_pat = _parse_version(name)
            except ValueError:
                continue
            if v_maj == major and v_min == minor:
                candidates.append(((v_maj, v_min, v_pat), name, sha))
        if not candidates:
            raise GitHubError(
                f"No tag matching {spec} found in {repo}. "
                f"Available: {[t[0] for t in tags[:5]]}"
            )
        candidates.sort(reverse=True)
        return candidates[0][1], candidates[0][2]

    # Exact version match
    target = spec.lstrip("v")
    for name, sha in tags:
        if name.lstrip("v") == target or name == spec:
            return name, sha
    raise GitHubError(f"Tag {spec} not found in {repo}")
