"""Read .spec-compliance.yaml and report must-field compliance."""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List

import yaml


@dataclass
class CheckResult:
    passed: List[dict]
    warnings: List[dict]   # override_justified
    errors: List[dict]     # override_missing


def run_check(compliance_path: Path) -> CheckResult:
    if not compliance_path.exists():
        print(
            "error: openspec/merged/.spec-compliance.yaml not found.\n"
            "       Run `spec sync` first.",
            file=sys.stderr,
        )
        sys.exit(1)

    with open(compliance_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    passed, warnings, errors = [], [], []
    for item in data.get("requirements", []):
        if item["level"] != "must":
            continue
        entry = {
            "tier": item["tier"],
            "capability": item["capability"],
            "requirement": item["requirement"],
            "justification": item.get("justification"),
        }
        status = item.get("status", "compliant")
        if status == "compliant":
            passed.append(entry)
        elif status == "override_justified":
            warnings.append(entry)
        else:
            errors.append(entry)

    return CheckResult(passed=passed, warnings=warnings, errors=errors)


def print_results(result: CheckResult, as_json: bool = False) -> int:
    """Print results. Returns exit code (0 = ok, 1 = errors found)."""
    if as_json:
        print(json.dumps({
            "passed": result.passed,
            "warnings": result.warnings,
            "errors": result.errors,
        }, ensure_ascii=False, indent=2))
        return 1 if result.errors else 0

    total = len(result.passed) + len(result.warnings) + len(result.errors)
    print(f"\nspec check — {total} must requirement(s) reviewed\n")

    for item in result.passed:
        print(f"  ✓ [{item['tier']}] {item['capability']} / {item['requirement']}")

    for item in result.warnings:
        print(f"  ⚠ [{item['tier']}] {item['capability']} / {item['requirement']}")
        print(f"      override: {item['justification']}")

    for item in result.errors:
        print(f"  ✗ [{item['tier']}] {item['capability']} / {item['requirement']}")
        print(f"      must override requires justification — add to ## Overrides")

    print()
    if result.errors:
        print(f"FAILED — {len(result.errors)} must field(s) have undeclared overrides.")
        return 1
    if result.warnings:
        print(f"PASSED (with {len(result.warnings)} declared override(s)).")
    else:
        print("PASSED — all must requirements satisfied.")
    return 0
