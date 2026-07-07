"""
ToGMAL pipeline CLI.

    python3 -m togmal_pipeline run              # run stale stages only
    python3 -m togmal_pipeline run --force      # rebuild everything
    python3 -m togmal_pipeline run --only NAME  # run a single stage
    python3 -m togmal_pipeline status           # show freshness of each stage
    python3 -m togmal_pipeline grow             # git-pull new eval results, then run

`grow` is the scale-out entry point: TIGER-AI-Lab/MMLU-Pro accumulates new
model archives over time; pulling the sparse checkout and re-running lets
the content-hash cache rebuild only what the new data invalidates.
"""

import subprocess
import sys
from pathlib import Path

from .core import Pipeline
from .stages import build_stages, MMLU_EVAL_DIR


def grow():
    checkout = Path(MMLU_EVAL_DIR).parent
    if (checkout / ".git").exists():
        print(f"Pulling latest eval results into {checkout}...")
        r = subprocess.run(["git", "-C", str(checkout), "pull", "--depth", "1"],
                           capture_output=True, text=True)
        print(r.stdout.strip() or r.stderr.strip())
    else:
        print(f"No checkout at {checkout}; cloning sparse eval_results...")
        checkout.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--depth", "1", "--filter=blob:none", "--sparse",
             "https://github.com/TIGER-AI-Lab/MMLU-Pro.git", str(checkout)],
            check=True)
        subprocess.run(["git", "-C", str(checkout), "sparse-checkout",
                        "set", "eval_results"], check=True)


def main():
    args = sys.argv[1:]
    cmd = args[0] if args else "status"

    pipeline = Pipeline(build_stages())

    if cmd == "status":
        pipeline.status()
    elif cmd == "run":
        force = "--force" in args
        only = None
        if "--only" in args:
            only = args[args.index("--only") + 1]
        ok = pipeline.run(only=only, force=force)
        sys.exit(0 if ok else 1)
    elif cmd == "grow":
        grow()
        ok = pipeline.run()
        sys.exit(0 if ok else 1)
    else:
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
