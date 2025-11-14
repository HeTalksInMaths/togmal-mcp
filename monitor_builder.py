#!/usr/bin/env python3
"""
Monitor the infinite benchmark builder progress
"""
import json
import subprocess
from pathlib import Path
from datetime import datetime

print("="*70)
print("🔍 INFINITE BENCHMARK BUILDER - STATUS MONITOR")
print("="*70)

# Check state file
state_file = Path("data/github_builder_state.json")
if state_file.exists():
    with open(state_file) as f:
        state = json.load(f)

    print(f"\n📊 CURRENT STATS:")
    print(f"  Total questions: {state['total_questions']:,}")
    print(f"  Benchmarks processed: {len(state['processed_benchmarks'])}")
    print(f"  Last check: {state.get('last_check', 'Never')}")
    print(f"\n📋 Processed benchmarks:")
    for bm in state['processed_benchmarks']:
        print(f"    ✓ {bm}")
else:
    print("\n⚠️  No state file found")

# Check data files
data_dir = Path("data/github_benchmarks")
if data_dir.exists():
    files = list(data_dir.glob("*.json"))
    total_size = sum(f.stat().st_size for f in files)

    print(f"\n💾 DATASET FILES:")
    print(f"  Files: {len(files)}")
    print(f"  Total size: {total_size / 1024 / 1024:.1f} MB")

    for f in sorted(files):
        size_mb = f.stat().st_size / 1024 / 1024
        print(f"    📄 {f.name} ({size_mb:.1f}MB)")

# Check process
try:
    result = subprocess.run(
        ["ps", "aux"],
        capture_output=True,
        text=True
    )

    processes = [line for line in result.stdout.split('\n')
                 if 'python' in line and 'infinite_github' in line
                 and 'grep' not in line]

    print(f"\n🚀 PROCESS STATUS:")
    if processes:
        print(f"  ✓ Running ({len(processes)} process(es))")
        for proc in processes:
            parts = proc.split()
            print(f"    PID: {parts[1]}, CPU: {parts[2]}%, MEM: {parts[3]}%")
    else:
        print(f"  ✗ Not running")
except Exception as e:
    print(f"  ⚠️  Could not check process: {e}")

# Check GitHub rate limit
try:
    result = subprocess.run(
        ["curl", "-s", "https://api.github.com/rate_limit"],
        capture_output=True,
        text=True
    )

    data = json.loads(result.stdout)
    core = data['resources']['core']
    reset_time = datetime.fromtimestamp(core['reset'])
    now = datetime.now()
    minutes_left = int((reset_time - now).total_seconds() / 60)

    print(f"\n🌐 GITHUB API RATE LIMIT:")
    print(f"  Remaining: {core['remaining']}/{core['limit']}")
    print(f"  Resets at: {reset_time.strftime('%H:%M:%S')} ({minutes_left} min)")

    if core['remaining'] == 0:
        print(f"  ⚠️  Rate limited! Will resume at reset time")
except Exception as e:
    print(f"\n🌐 GITHUB API: Could not check ({e})")

print(f"\n{'='*70}")
print(f"Monitor run at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"{'='*70}")
