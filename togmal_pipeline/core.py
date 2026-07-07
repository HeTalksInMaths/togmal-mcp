"""
Pipeline core: stages, content-hash caching, DAG execution.

Design goals (deliberately minimal — no Airflow/Prefect dependency):
- A Stage is a name + command + declared input/output paths.
- A stage re-runs only when its fingerprint changes: the hash of its
  command plus the (name, size, mtime) of every input file. Directories
  as inputs are fingerprinted by walking their files.
- Execution order is topological: a stage whose inputs include another
  stage's outputs runs after it. Explicit `after=[...]` can force ordering
  where path overlap doesn't capture the dependency.
- State lives in .pipeline_state.json; delete it (or pass force=True)
  to rebuild everything.
"""

import hashlib
import json
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

STATE_FILE = Path(".pipeline_state.json")


@dataclass
class Stage:
    name: str
    command: List[str]              # subprocess argv
    inputs: List[str] = field(default_factory=list)    # files or dirs
    outputs: List[str] = field(default_factory=list)   # files or dirs
    after: List[str] = field(default_factory=list)     # explicit ordering
    optional: bool = False          # failure doesn't abort the pipeline

    def fingerprint(self) -> str:
        h = hashlib.sha256()
        h.update(' '.join(self.command).encode())
        for spec in sorted(self.inputs):
            p = Path(spec)
            files = sorted(p.rglob('*')) if p.is_dir() else [p]
            for f in files:
                if f.is_file():
                    st = f.stat()
                    h.update(f"{f}:{st.st_size}:{st.st_mtime_ns}".encode())
        return h.hexdigest()

    def outputs_exist(self) -> bool:
        return all(Path(o).exists() for o in self.outputs)


class Pipeline:
    def __init__(self, stages: List[Stage]):
        self.stages = self._topo_sort(stages)
        self.state = self._load_state()

    # ------------------------------------------------------------- ordering

    @staticmethod
    def _topo_sort(stages: List[Stage]) -> List[Stage]:
        by_name = {s.name: s for s in stages}
        producers = {}  # output path -> stage name
        for s in stages:
            for o in s.outputs:
                producers[str(Path(o))] = s.name

        def deps(s: Stage):
            found = set(s.after)
            for i in s.inputs:
                ip = str(Path(i))
                for out_path, producer in producers.items():
                    if producer == s.name:
                        continue
                    # dependency if input equals, contains, or is inside an output
                    if (ip == out_path or ip.startswith(out_path + '/')
                            or out_path.startswith(ip + '/')):
                        found.add(producer)
            return found

        ordered, seen, visiting = [], set(), set()

        def visit(name: str):
            if name in seen:
                return
            if name in visiting:
                raise ValueError(f"Cycle involving stage '{name}'")
            visiting.add(name)
            for d in sorted(deps(by_name[name])):
                if d in by_name:
                    visit(d)
            visiting.discard(name)
            seen.add(name)
            ordered.append(by_name[name])

        for s in stages:
            visit(s.name)
        return ordered

    # ---------------------------------------------------------------- state

    def _load_state(self) -> dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except json.JSONDecodeError:
                pass
        return {}

    def _save_state(self):
        STATE_FILE.write_text(json.dumps(self.state, indent=2))

    # ------------------------------------------------------------------ run

    def status(self):
        print(f"{'stage':30s} {'state':10s} last run")
        print("-" * 60)
        for s in self.stages:
            rec = self.state.get(s.name, {})
            if not rec:
                state = 'never-run'
            elif not s.outputs_exist():
                state = 'stale'
            elif rec.get('fingerprint') != s.fingerprint():
                state = 'outdated'
            else:
                state = 'fresh'
            print(f"{s.name:30s} {state:10s} {rec.get('completed_at', '—')}")

    def run(self, only: Optional[str] = None, force: bool = False) -> bool:
        ran, skipped, failed = [], [], []

        for s in self.stages:
            if only and s.name != only:
                continue

            fp = s.fingerprint()
            rec = self.state.get(s.name, {})
            if (not force and rec.get('fingerprint') == fp
                    and s.outputs_exist()):
                skipped.append(s.name)
                print(f"⏭  {s.name} (cached)")
                continue

            print(f"▶  {s.name}: {' '.join(s.command)}")
            t0 = time.time()
            proc = subprocess.run(s.command, capture_output=True, text=True)
            dt = time.time() - t0

            if proc.returncode != 0:
                print(f"❌ {s.name} failed ({dt:.0f}s)")
                print(proc.stderr[-2000:] or proc.stdout[-2000:])
                failed.append(s.name)
                if s.optional:
                    continue
                self._save_state()
                return False

            # fingerprint AFTER the run so output-mtime changes made by this
            # stage to downstream inputs are captured next time
            self.state[s.name] = {
                'fingerprint': s.fingerprint(),
                'completed_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'duration_s': round(dt, 1),
            }
            self._save_state()
            ran.append(s.name)
            print(f"✅ {s.name} ({dt:.0f}s)")

        print(f"\nDone: {len(ran)} ran, {len(skipped)} cached"
              + (f", {len(failed)} failed (optional)" if failed else ""))
        return True
