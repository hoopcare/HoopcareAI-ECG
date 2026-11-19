#!/usr/bin/env python3
"""Check staged Git blobs for material that must not enter this public repo.

This is a release guard, not proof that files contain no patient information.
Human review remains necessary, especially for prose and tabular JSON.
No file contents are printed, including when a potential secret is detected.
"""

import argparse
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys


MAX_BYTES = 512 * 1024
TEXT_SUFFIXES = {
    ".md", ".py", ".html", ".css", ".js", ".cjs", ".mjs", ".json",
    ".yml", ".yaml", ".cff", ".txt", ".toml", ".ini", ".sh", ".cfg",
}
TEXT_NAMES = {"LICENSE", "NOTICE", "CODEOWNERS", ".gitignore", ".gitattributes",
              ".env.example", ".nojekyll", "Makefile"}
RESTRICTED_DIRS = {"data", "datasets", "results", "outputs", "models", "weights",
                   "private", "private-audit"}
SECRET_PATTERNS = (
    re.compile(r"gh[pousr]_[A-Za-z0-9]{30,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{40,}"),
    re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    re.compile(r"-----BEGIN (?:[A-Z0-9]+ )?PRIVATE KEY-----"),
    re.compile(r"\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|password)"
               r"\s*[:=]\s*['\"][^'\"\s]{16,}['\"]", re.IGNORECASE),
)
PRIVATE_PATHS = re.compile(
    r"/(?:data/(?:workspaces|external-test-datasets)/|"
    r"Users/[^/\s'\"]+/|home/[^/\s'\"]+/)"
)


class GuardError(RuntimeError):
    """The guard cannot establish what would be published."""


def inspect_file(name, data, mode="100644"):
    """Return reasons to reject one staged blob, without displaying its data."""
    path = PurePosixPath(name)
    if mode not in {"100644", "100755"}:
        return ["symlinks, submodules and special file modes are not allowed"]
    if path.is_absolute() or ".." in path.parts:
        return ["invalid repository path"]
    if any(part.lower() in RESTRICTED_DIRS for part in path.parts[:-1]):
        return ["restricted data, model or output directory"]
    credential_name = path.name.lower()
    if ((credential_name.startswith(".env") and path.name != ".env.example")
            or credential_name.startswith(("credentials", "secrets"))
            or credential_name in {"id_rsa", "id_ed25519", "id_dsa"}):
        return ["credential file name"]
    if path.name not in TEXT_NAMES and path.suffix.lower() not in TEXT_SUFFIXES:
        return ["file type is not approved for this code-only release"]
    if path.name == ".nojekyll" and data:
        return ["the Pages marker must be empty"]
    if len(data) > MAX_BYTES:
        return ["file exceeds the public-source size limit"]
    try:
        content = data.decode("utf-8")
    except UnicodeDecodeError:
        return ["non-UTF-8 or binary content"]
    if "\x00" in content:
        return ["binary content"]
    findings = []
    if any(pattern.search(content) for pattern in SECRET_PATTERNS):
        findings.append("possible embedded credential or private key")
    if PRIVATE_PATHS.search(content):
        findings.append("hard-coded private workstation or VM path")
    return findings


def git_output(root, *args):
    try:
        return subprocess.run(
            ["git", "-C", str(root), *args], check=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as error:
        raise GuardError("Git inspection failed; no publication approval inferred") from error


def audit_repository(root):
    """Audit the exact staged blobs, ignoring all untracked local material."""
    root = Path(root).resolve()
    top = git_output(root, "rev-parse", "--show-toplevel").decode().strip()
    if Path(top).resolve() != root:
        raise GuardError("Use the repository root, not a subdirectory")
    entries = git_output(root, "ls-files", "--stage", "-z").split(b"\0")
    entries = [entry for entry in entries if entry]
    if not entries:
        raise GuardError("The index is empty; stage the intended public files first")
    findings = []
    for entry in entries:
        metadata, encoded_name = entry.split(b"\t", 1)
        mode, object_id, stage = metadata.decode().split()
        name = encoded_name.decode("utf-8")
        if stage != "0":
            findings.append((name, "unmerged Git index entry"))
            continue
        reasons = inspect_file(name, b"", mode)
        if not reasons:
            size = int(git_output(root, "cat-file", "-s", object_id))
            if size > MAX_BYTES:
                reasons = ["file exceeds the public-source size limit"]
            else:
                data = git_output(root, "cat-file", "blob", object_id)
                reasons = inspect_file(name, data, mode)
        findings.extend((name, reason) for reason in reasons)
    return findings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    try:
        findings = audit_repository(args.root)
    except (GuardError, UnicodeDecodeError, ValueError) as error:
        print(f"Publication check failed: {error}", file=sys.stderr)
        return 2
    for name, reason in findings:
        print(f"{name}: {reason}")
    if findings:
        print("Publication check failed. Review and remove the flagged material.")
        return 1
    print("Publication check passed for staged files. Human data/privacy review is still required.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
