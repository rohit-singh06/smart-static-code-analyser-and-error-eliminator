"""
GCC syntax/semantic checking for real C code.

Runs:
    gcc -fsyntax-only <tempfile.c>

If GCC accepts the code, it is valid C for the installed GCC version.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
import shutil
import subprocess
import tempfile
import os


@dataclass
class CompileCheckResult:
    ok: bool
    gcc_found: bool
    return_code: Optional[int]
    stderr: str
    stdout: str
    command: list[str]

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "gcc_found": self.gcc_found,
            "return_code": self.return_code,
            "stderr": self.stderr,
            "stdout": self.stdout,
            "command": self.command,
        }


def check_with_gcc(source_code: str, *, std: str = "c11") -> CompileCheckResult:
    """
    Check if GCC accepts the given C source code.
    Uses -fsyntax-only so no binary is produced.
    """
    gcc = shutil.which("gcc")
    if not gcc:
        return CompileCheckResult(
            ok=False,
            gcc_found=False,
            return_code=None,
            stderr="gcc not found in PATH. Install GCC (e.g., MinGW-w64) or add it to PATH.",
            stdout="",
            command=["gcc", "-fsyntax-only"],
        )

    with tempfile.TemporaryDirectory() as td:
        c_path = os.path.join(td, "input.c")
        with open(c_path, "w", encoding="utf-8") as f:
            f.write(source_code)

        cmd = [gcc, "-x", "c", f"-std={std}", "-fsyntax-only", c_path]
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        return CompileCheckResult(
            ok=(proc.returncode == 0),
            gcc_found=True,
            return_code=proc.returncode,
            stderr=proc.stderr.strip(),
            stdout=proc.stdout.strip(),
            command=cmd,
        )

