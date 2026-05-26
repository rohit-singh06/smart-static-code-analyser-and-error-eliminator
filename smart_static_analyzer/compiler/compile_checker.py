"""
GCC syntax checking for C code using 'gcc -fsyntax-only'.
"""

import shutil
import subprocess
import tempfile
import os

class CompileCheckResult:
    def __init__(self, ok: bool, gcc_found: bool, return_code: int | None, stderr: str, stdout: str, command: list[str]):
        self.ok = ok
        self.gcc_found = gcc_found
        self.return_code = return_code
        self.stderr = stderr
        self.stdout = stdout
        self.command = command

    def to_dict(self) -> dict:
        return self.__dict__


def check_with_gcc(source_code: str, std: str = "c11") -> CompileCheckResult:
    """Check code validity by running GCC in syntax-only mode."""
    gcc = shutil.which("gcc")
    if not gcc:
        return CompileCheckResult(
            ok=False,
            gcc_found=False,
            return_code=None,
            stderr="gcc not found in PATH.",
            stdout="",
            command=["gcc", "-fsyntax-only"],
        )

    with tempfile.TemporaryDirectory() as td:
        c_path = os.path.join(td, "input.c")
        with open(c_path, "w", encoding="utf-8") as f:
            f.write(source_code)

        cmd = [gcc, "-x", "c", f"-std={std}", "-fsyntax-only", c_path]
        proc = subprocess.run(cmd, capture_output=True, text=True)

        return CompileCheckResult(
            ok=(proc.returncode == 0),
            gcc_found=True,
            return_code=proc.returncode,
            stderr=proc.stderr.strip(),
            stdout=proc.stdout.strip(),
            command=cmd,
        )
