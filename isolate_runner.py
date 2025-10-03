import subprocess
import json
from pathlib import Path
from typing import Dict
from dataclasses import dataclass, asdict
from enum import Enum
import uuid


class Language(Enum):
    PYTHON = "python"
    CPP = "cpp"
    C = "c"
    GO = "go"


class Status(Enum):
    OK = "OK"
    RE = "Runtime Error"
    TLE = "Time Limit Exceeded"
    MLE = "Memory Limit Exceeded"
    CE = "Compilation Error"
    IE = "Internal Error"


@dataclass
class RunResult:
    status: Status
    time: float = 0.0
    memory: int = 0
    exit_code: int = 0
    stdout: str = ""
    stderr: str = ""
    message: str = ""

    def to_dict(self) -> Dict:
        result = asdict(self)
        result['status'] = self.status.value
        return result

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


class IsolateRunner:
    def __init__(self, box_id=0):
        self.box_id = box_id
        self.box_path = Path(f"/var/local/lib/isolate/{box_id}/box")
        self.init_box()

    def init_box(self):
        """Sandbox init"""
        subprocess.run(
            ["isolate", f"--box-id={self.box_id}", "--init"],
            check=True
        )

    def cleanup(self):
        """Sandbox cleanup"""
        subprocess.run(
            ["isolate", f"--box-id={self.box_id}", "--cleanup"],
            check=False
        )

    def run(self, source_code, language: Language, input_data: str = "", time_limit: float = 1.0, memory_limit: int = 262144):

        self.init_box()
        uid = uuid.uuid4().hex[:8]

        src_file = self.box_path / f"main_{uid}"
        bin_file = self.box_path / f"prog_{uid}"

        compile_cmd = None
        run_cmd = None

        try:
            # ==== Source yozish ====
            if language == Language.PYTHON:
                src_file = src_file.with_suffix(".py")
                src_file.write_text(source_code)
                run_cmd = ["/usr/bin/python3", src_file.name]

            elif language == Language.CPP:
                src_file = src_file.with_suffix(".cpp")
                src_file.write_text(source_code)
                bin_file = bin_file.with_suffix(".out")
                compile_cmd = ["g++", "-O2", "-std=c++17", src_file.name, "-o", bin_file.name]
                run_cmd = [f"./{bin_file.name}"]

            elif language == Language.C:
                src_file = src_file.with_suffix(".c")
                src_file.write_text(source_code)
                bin_file = bin_file.with_suffix(".out")
                compile_cmd = ["gcc", src_file.name, "-o", bin_file.name]
                run_cmd = [f"./{bin_file.name}"]

            elif language == Language.GO:
                src_file = src_file.with_suffix(".go")
                src_file.write_text(source_code)
                bin_file = bin_file.with_suffix(".out")
                compile_cmd = ["go", "build", "-o", bin_file.name, src_file.name]
                run_cmd = [f"./{bin_file.name}"]

            else:
                return RunResult(status=Status.IE, message="Noma'lum til")

            # ==== Kompilyatsiya ====
            if compile_cmd:
                comp = subprocess.run(
                    compile_cmd,
                    cwd=self.box_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                if comp.returncode != 0:
                    return RunResult(
                        status=Status.CE,
                        message="Kompilyatsiya xatosi",
                        stderr=comp.stderr.decode()
                    )

            # ==== Input yozish ====
            (self.box_path / "input.txt").write_text(input_data)

            # ==== Isolate bilan bajarish ====
            meta_file = self.box_path / "meta.txt"
            cmd = [
                "isolate",
                f"--box-id={self.box_id}",
                "--run",
                f"--time={time_limit}",
                f"--mem={memory_limit}",
                "--stdin=input.txt",
                "--stdout=stdout.txt",
                "--stderr=stderr.txt",
                "--meta", str(meta_file),
                "--",
            ] + run_cmd

            proc = subprocess.run(
                cmd,
                cwd=self.box_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            # ==== Natija ====
            stdout = (self.box_path / "stdout.txt").read_text() if (self.box_path / "stdout.txt").exists() else ""
            stderr = (self.box_path / "stderr.txt").read_text() if (self.box_path / "stderr.txt").exists() else ""

            # Meta fayldan vaqt/xotira
            time_used, mem_used = 0.0, 0
            status = Status.OK
            if meta_file.exists():
                for line in meta_file.read_text().splitlines():
                    if line.startswith("time:"):
                        _, val = line.split(":", 1)
                        time_used = float(val.strip())
                    elif line.startswith("max-rss:"):
                        _, val = line.split(":", 1)
                        mem_used = int(val.strip())
                    elif line.startswith("status:"):
                        _, val = line.split(":", 1)
                        st = val.strip()
                        if st == "RE":
                            status = Status.RE
                        elif st == "TO":
                            status = Status.TLE
                        elif st == "SG":
                            status = Status.RE
                        elif st == "XX":
                            status = Status.IE

            return RunResult(
                status=status,
                time=time_used,
                memory=mem_used,
                exit_code=proc.returncode,
                stdout=stdout.strip(),
                stderr=stderr.strip(),
                message="Tugadi"
            )

        except Exception as e:
            return RunResult(
                status=Status.IE,
                message=f"Ichki xato: {e}"
            )
        finally:
            self.cleanup()
