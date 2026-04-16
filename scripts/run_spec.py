"""
Standalone entry point for spec-skill.
Run as: python run_spec.py [--root <project_dir>] <command> [options]
Commands: sync, check, init

--root lets callers pin the project directory explicitly so the script
never has to guess from cwd (useful when the script lives on a different
drive from the project, e.g. script in C:\ but project in D:\).
"""
import sys
import os

# Add this script's directory to sys.path so spec_cli package is importable
# without requiring `pip install -e .`
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import click
from spec_cli.cli import cli as _spec_cli


@click.group()
@click.option(
    "--root",
    default=None,
    type=click.Path(exists=True, file_okay=False),
    help="Project root directory (default: current working directory). "
         "Pass this when running the script from a different location than the project.",
    is_eager=True,
    expose_value=False,
    callback=lambda ctx, param, value: os.chdir(value) if value else None,
)
def cli():
    """spec-skill entry point — wraps spec sync / check / init."""


# Attach all sub-commands from the real cli
for cmd in _spec_cli.commands.values():
    cli.add_command(cmd)


if __name__ == "__main__":
    cli()
