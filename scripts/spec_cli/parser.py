"""Parse spec.md files to extract requirements and override declarations."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Requirement:
    name: str
    level: str          # must | should | may
    content: str        # full markdown block (header + body + scenarios)
    capability: str
    tier: str = ""
    version: str = ""


@dataclass
class Override:
    display_name: str
    requirement_ref: str    # tier/capability/requirement-name
    justification: str      # empty → missing


def parse_requirements(content: str, capability: str) -> List[Requirement]:
    """Extract Requirement objects from a spec.md file."""
    requirements: List[Requirement] = []
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        # Match "### Requirement: <name>"
        m = re.match(r'^###\s+Requirement:\s+(.+)$', line)
        if m:
            name = m.group(1).strip()
            level = "should"
            block_lines = [line]
            i += 1
            # Next line may be "level: must"
            if i < len(lines):
                lm = re.match(r'^level:\s*(must|should|may)\s*$', lines[i])
                if lm:
                    level = lm.group(1)
                    i += 1
            # Collect until next H3 or end
            while i < len(lines):
                next_line = lines[i]
                if re.match(r'^###\s+', next_line) and not re.match(r'^####', next_line):
                    break
                block_lines.append(next_line)
                i += 1
            requirements.append(Requirement(
                name=name,
                level=level,
                content="\n".join(block_lines),
                capability=capability,
            ))
        else:
            i += 1
    return requirements


def parse_overrides(content: str) -> List[Override]:
    """Extract Override declarations from ## Overrides sections."""
    overrides: List[Override] = []
    lines = content.splitlines()
    in_overrides = False
    i = 0
    while i < len(lines):
        line = lines[i]
        if re.match(r'^##\s+Overrides', line):
            in_overrides = True
            i += 1
            continue
        if in_overrides and re.match(r'^##\s+', line):
            in_overrides = False
        if in_overrides:
            m = re.match(r'^###\s+(.+)$', line)
            if m:
                display_name = m.group(1).strip()
                ref = ""
                justification = ""
                i += 1
                while i < len(lines) and not re.match(r'^###\s+', lines[i]):
                    rm = re.match(r'^override:\s*(.+)$', lines[i])
                    jm = re.match(r'^justification:\s*(.*)$', lines[i])
                    if rm:
                        ref = rm.group(1).strip()
                    if jm:
                        justification = jm.group(1).strip()
                    i += 1
                overrides.append(Override(
                    display_name=display_name,
                    requirement_ref=ref,
                    justification=justification,
                ))
                continue
        i += 1
    return overrides
