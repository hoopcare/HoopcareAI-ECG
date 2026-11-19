"""Portable paths for the analysis release; no clinical configuration is changed."""

import os
from pathlib import Path


SCRIPT_ROOT = Path(__file__).resolve().parent
REPOSITORY_ROOT = SCRIPT_ROOT.parents[2]


def required_dir(variable):
    """Return an explicitly configured, existing directory."""
    value = os.environ.get(variable, "").strip()
    if not value:
        raise ValueError(f"Set {variable} to an existing authorized local directory.")
    directory = Path(value).expanduser().resolve()
    if not directory.is_dir():
        raise ValueError(f"{variable} must point to an existing directory.")
    return directory


def workspace_dir():
    """Keep generated patient-level files outside the publication repository."""
    return external_dir("HOOPCARE_WORKSPACE")


def required_file(variable):
    """Return an explicitly configured existing file, without reading its contents."""
    value = os.environ.get(variable, "").strip()
    if not value:
        raise ValueError(f"Set {variable} to an existing authorized local file.")
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise ValueError(f"{variable} must point to an existing file.")
    return path


def _outside_repository(path, variable):
    if path == REPOSITORY_ROOT or REPOSITORY_ROOT in path.parents:
        raise ValueError(f"{variable} must be outside the publication repository.")
    return path


def external_file(variable):
    return _outside_repository(required_file(variable), variable)


def external_dir(variable):
    return _outside_repository(required_dir(variable), variable)


def script_path(name):
    """Resolve trusted packaged helper scripts independently of working directory."""
    if not isinstance(name, str) or Path(name).name != name or not name.endswith(".py"):
        raise ValueError("Expected a packaged Python script filename.")
    script = SCRIPT_ROOT / name
    if not script.is_file():
        raise ValueError("Packaged helper script not found.")
    return str(script)
