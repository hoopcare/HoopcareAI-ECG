"""Synthetic publication-guard tests; no real credentials or patient records."""

import importlib.util
import contextlib
import io
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch


GUARD = Path(__file__).resolve().parents[1] / "tools" / "check_public_tree.py"
SPEC = importlib.util.spec_from_file_location("public_tree_guard", GUARD)
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


class FileChecks(unittest.TestCase):
    def test_plain_source_and_docs_are_allowed(self):
        for path in ("LICENSE", "README.md", ".gitignore", ".github/CODEOWNERS",
                     "scripts/run.py", "demo/score.js", "CITATION.cff"):
            self.assertEqual(guard.inspect_file(path, b"ordinary public text\n"), [])

    def test_restricted_artifacts_are_rejected(self):
        for extension in ("csv", "tsv", "npz", "pt", "onnx", "zip", "pdf", "png", "xlsx"):
            self.assertTrue(guard.inspect_file("example." + extension, b"fixture"))

    def test_nojekyll_marker_must_be_empty(self):
        self.assertEqual(guard.inspect_file(".nojekyll", b""), [])
        self.assertTrue(guard.inspect_file(".nojekyll", b"unexpected payload"))

    def test_credential_filenames_are_rejected(self):
        for path in (".env", "nested/.env.production", "credentials.json", "id_rsa"):
            self.assertTrue(guard.inspect_file(path, b"fixture"))
        self.assertEqual(guard.inspect_file(".env.example", b"MODEL_DIRECTORY=\n"), [])

    def test_restricted_directory_is_rejected(self):
        self.assertTrue(guard.inspect_file("data/record.json", b"{}"))

    def test_binary_oversize_and_bad_utf8_are_rejected(self):
        for data in (b"text\x00more", b"\xff", b"x" * (guard.MAX_BYTES + 1)):
            self.assertTrue(guard.inspect_file("test.txt", data))

    def test_symlinks_and_submodules_are_rejected(self):
        for mode in ("120000", "160000"):
            self.assertTrue(guard.inspect_file("linked.md", b"target", mode))

    def test_secret_patterns_are_rejected_without_echoing_contents(self):
        secrets = ["gh" + "p_" + "A" * 36,
                   "github_" + "pat_" + "B" * 70,
                   "AK" + "IA" + "A" * 16,
                   "-----BEGIN " + "OPENSSH PRIVATE KEY-----",
                   "api_key = '" + "synthetic-secret-123456789" + "'"]
        for value in secrets:
            findings = guard.inspect_file("config.py", value.encode())
            self.assertTrue(findings)
            self.assertNotIn(value, " ".join(findings))

    def test_private_machine_paths_are_rejected(self):
        for parts in (("", "Users", "researcher", "private", "file"),
                      ("", "home", "researcher", "records"),
                      ("", "data", "workspaces", "researcher"),
                      ("", "data", "external-test-datasets", "dataset")):
            self.assertTrue(guard.inspect_file("run.py", "/".join(parts).encode()))

    def test_environment_variable_configuration_is_allowed(self):
        content = b'import os\nroot = os.environ["HOOPCARE_WORKSPACE"]\n'
        self.assertEqual(guard.inspect_file("run.py", content), [])

    def test_absolute_and_parent_paths_are_rejected(self):
        for path in ("/file.py", "../file.py"):
            self.assertTrue(guard.inspect_file(path, b"safe"))


class RepositoryChecks(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.git("init", "--quiet")

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args], check=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def stage(self, name, data=b"safe\n"):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        self.git("add", "--", name)

    def test_ignores_untracked_files_and_checks_tracked_ones(self):
        self.stage("README.md")
        (self.root / "local.csv").write_text("not tracked")
        self.assertEqual(guard.audit_repository(self.root), [])
        self.stage("published.csv")
        self.assertTrue(guard.audit_repository(self.root))

    def test_reads_staged_content_not_clean_worktree(self):
        secret = ("gh" + "p_" + "A" * 36).encode()
        self.stage("config.py", secret)
        (self.root / "config.py").write_text("safe replacement")
        findings = guard.audit_repository(self.root)
        self.assertTrue(findings)
        self.assertNotIn(secret.decode(), str(findings))

    def test_staged_symlink_is_rejected_without_following(self):
        (self.root / "link.md").symlink_to(self.root / "missing")
        self.git("add", "link.md")
        self.assertTrue(guard.audit_repository(self.root))

    def test_large_text_blob_is_rejected(self):
        self.stage("oversize.txt", b"x" * (guard.MAX_BYTES + 1))
        self.assertTrue(guard.audit_repository(self.root))

    def test_unmerged_index_fails_closed(self):
        output = [str(self.root.resolve()).encode(),
                  b"100644 " + b"0" * 40 + b" 1\tconflict.py\x00"]
        with patch.object(guard, "git_output", side_effect=output):
            self.assertEqual(guard.audit_repository(self.root),
                             [("conflict.py", "unmerged Git index entry")])

    def test_non_repository_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(guard.GuardError):
                guard.audit_repository(Path(directory))

    def test_nested_root_is_rejected(self):
        nested = self.root / "nested"
        nested.mkdir()
        with self.assertRaises(guard.GuardError):
            guard.audit_repository(nested)

    def test_empty_index_fails_closed(self):
        with self.assertRaises(guard.GuardError):
            guard.audit_repository(self.root)

    def test_cli_success_and_failure(self):
        self.stage("README.md")
        command = ["python3", str(GUARD), "--root", str(self.root)]
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0)
        self.assertIn("passed", result.stdout)
        self.stage("records.csv")
        result = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertIn("records.csv", result.stdout)

    def test_main_reports_success_and_failure(self):
        self.stage("README.md")
        with patch("sys.argv", [str(GUARD), "--root", str(self.root)]):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(guard.main(), 0)
            self.stage("records.csv")
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(guard.main(), 1)

    def test_main_reports_git_error(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch("sys.argv", [str(GUARD), "--root", directory]):
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(guard.main(), 2)


if __name__ == "__main__":
    unittest.main()
