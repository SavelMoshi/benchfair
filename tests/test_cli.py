"""Exercise the real module entry point and expected file/argument failures."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from benchfair.cli import load_roster

ROOT = Path(__file__).resolve().parents[1]


class CliTests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, "-m", "benchfair", *map(str, args)],
                              cwd=ROOT, capture_output=True, text=True, encoding="utf-8")

    def test_default_markdown(self):
        result = self.run_cli("examples/players.json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        self.assertTrue(result.stdout.startswith("# BenchFair schedule"))
        self.assertIn("Courts: 1 · Rounds: 6 · Seed: 42", result.stdout)

    def test_documented_json_command(self):
        result = self.run_cli("examples/players.json", "--courts", "2", "--rounds", "8",
                              "--seed", "42", "--format", "json")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, "")
        data = json.loads(result.stdout)
        self.assertEqual(len(data["rounds"]), 8)
        self.assertEqual(data["session"]["courts"], 2)

    def test_help(self):
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0)
        for phrase in ("Examples:", "gaming station", "--seed", "--format", "default: 42"):
            self.assertIn(phrase, result.stdout)

    def test_argument_errors(self):
        cases = [(), ("missing.json",), ("examples/players.json", "--courts", "3"),
                 ("examples/players.json", "--courts", "0"),
                 ("examples/players.json", "--rounds", "101"),
                 ("examples/players.json", "--seed", "nope"),
                 ("examples/players.json", "--format", "html")]
        for args in cases:
            with self.subTest(args=args):
                result = self.run_cli(*args)
                self.assertEqual(result.returncode, 2)
                self.assertEqual(result.stdout, "")
                self.assertIn("error:", result.stderr)
                self.assertNotIn("Traceback", result.stderr)

    def test_malformed_files(self):
        cases = [b"{broken", b"\xff", b"null", b"[]", b"{}", b'{"players":"ABCD"}',
                 b'{"players":["A","B","C",1]}', b'{"players":["A","B","C"," a "]}',
                 b'{"players":["A","B","C","D\\n"]}']
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "roster.json"
            for content in cases:
                with self.subTest(content=content):
                    path.write_bytes(content)
                    result = self.run_cli(path)
                    self.assertEqual(result.returncode, 2)
                    self.assertEqual(result.stdout, "")
                    self.assertNotIn("Traceback", result.stderr)
            result = self.run_cli(directory)
            self.assertEqual(result.returncode, 2)

    def test_unreadable_file(self):
        # Permission bits alone do not simulate unreadable files when run as root.
        with patch.object(Path, "read_text", side_effect=PermissionError("permission denied")):
            with self.assertRaisesRegex(ValueError, "cannot read roster"):
                load_roster(Path("roster.json"))


if __name__ == "__main__":
    unittest.main()
