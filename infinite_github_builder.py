#!/usr/bin/env python3
"""
Infinite GitHub-Based Benchmark Builder
========================================

Simplified version that works in restricted networks.
Uses GitHub as data source instead of HuggingFace.

Author: ToGMAL Project
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any
import time
from datetime import datetime

from github_benchmark_discovery import GitHubBenchmarkDiscovery

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('github_infinite_build.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class InfiniteGitHubBenchmarkBuilder:
    """
    Infinite benchmark builder using GitHub as data source.
    Continuously discovers and integrates benchmarks.
    """

    def __init__(
        self,
        data_dir: Path = Path("./data/github_benchmarks"),
        state_file: Path = Path("./data/github_builder_state.json")
    ):
        """Initialize the infinite builder."""
        self.data_dir = data_dir
        self.state_file = state_file
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.discovery = GitHubBenchmarkDiscovery()

        # Load state
        self.state = self._load_state()

        logger.info("="*60)
        logger.info("Infinite GitHub Benchmark Builder")
        logger.info("="*60)
        logger.info(f"Data directory: {self.data_dir}")
        logger.info(f"Total questions collected: {self.state['total_questions']}")
        logger.info(f"Benchmarks processed: {len(self.state['processed_benchmarks'])}")

    def _load_state(self) -> Dict[str, Any]:
        """Load builder state."""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)

        return {
            'total_questions': 0,
            'processed_benchmarks': [],
            'last_discovery': None,
            'start_time': datetime.now().isoformat()
        }

    def _save_state(self):
        """Save builder state."""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def phase1_foundation(self, max_benchmarks: int = 3):
        """
        Phase 1: Build foundation with known benchmarks.

        Args:
            max_benchmarks: Maximum benchmarks to load
        """
        logger.info("\n" + "="*60)
        logger.info("PHASE 1: FOUNDATION BUILD")
        logger.info("="*60)

        # Discover known benchmarks
        benchmarks = self.discovery.load_known_benchmarks()

        if not benchmarks:
            logger.warning("No benchmarks discovered!")
            return

        logger.info(f"\nDiscovered {len(benchmarks)} benchmarks")
        logger.info(f"Will process first {max_benchmarks} for foundation")

        for i, benchmark in enumerate(benchmarks[:max_benchmarks]):
            if benchmark.repo_full_name in self.state['processed_benchmarks']:
                logger.info(f"\n[{i+1}/{max_benchmarks}] {benchmark.repo_full_name} - Already processed, skipping")
                continue

            logger.info(f"\n[{i+1}/{max_benchmarks}] {benchmark.repo_full_name} ({benchmark.stars}⭐)")
            logger.info(f"  Description: {benchmark.description[:100]}...")
            logger.info(f"  Data files: {benchmark.num_files}")
            logger.info(f"  Schema: Q={benchmark.question_fields}, A={benchmark.answer_fields}")

            # Load data
            try:
                data = self.discovery.load_benchmark_data(benchmark, max_questions=10000)

                if data:
                    # Save to file
                    output_file = self.data_dir / f"{benchmark.repo_full_name.replace('/', '_')}.json"
                    with open(output_file, 'w') as f:
                        json.dump({
                            'benchmark': benchmark.repo_full_name,
                            'stars': benchmark.stars,
                            'description': benchmark.description,
                            'num_questions': len(data),
                            'questions': data
                        }, f, indent=2)

                    logger.info(f"  ✓ Saved {len(data)} questions to {output_file.name}")

                    # Update state
                    self.state['total_questions'] += len(data)
                    self.state['processed_benchmarks'].append(benchmark.repo_full_name)
                    self._save_state()
                else:
                    logger.warning(f"  ✗ No data loaded from {benchmark.repo_full_name}")

            except Exception as e:
                logger.error(f"  ✗ Error loading {benchmark.repo_full_name}: {e}")

        logger.info("\n" + "="*60)
        logger.info(f"PHASE 1 COMPLETE!")
        logger.info(f"Total questions: {self.state['total_questions']}")
        logger.info(f"Benchmarks processed: {len(self.state['processed_benchmarks'])}")
        logger.info("="*60)

    def phase2_continuous(self, check_interval_hours: int = 24):
        """
        Phase 2: Continuous discovery mode.

        Args:
            check_interval_hours: Hours between discovery checks
        """
        logger.info("\n" + "="*60)
        logger.info("PHASE 2: CONTINUOUS DISCOVERY MODE")
        logger.info("="*60)
        logger.info(f"Will check for new benchmarks every {check_interval_hours} hours")
        logger.info("(Press Ctrl+C to stop)")

        iteration = 0
        while True:
            iteration += 1
            logger.info(f"\n--- Discovery Iteration #{iteration} ---")
            logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # Check for new benchmarks
            benchmarks = self.discovery.load_known_benchmarks()
            new_benchmarks = [b for b in benchmarks if b.repo_full_name not in self.state['processed_benchmarks']]

            if new_benchmarks:
                logger.info(f"Found {len(new_benchmarks)} new benchmarks!")

                for benchmark in new_benchmarks:
                    logger.info(f"\nProcessing: {benchmark.repo_full_name}")

                    try:
                        data = self.discovery.load_benchmark_data(benchmark, max_questions=10000)

                        if data:
                            output_file = self.data_dir / f"{benchmark.repo_full_name.replace('/', '_')}.json"
                            with open(output_file, 'w') as f:
                                json.dump({
                                    'benchmark': benchmark.repo_full_name,
                                    'stars': benchmark.stars,
                                    'description': benchmark.description,
                                    'num_questions': len(data),
                                    'questions': data
                                }, f, indent=2)

                            logger.info(f"  ✓ Saved {len(data)} questions")

                            self.state['total_questions'] += len(data)
                            self.state['processed_benchmarks'].append(benchmark.repo_full_name)
                            self._save_state()

                    except Exception as e:
                        logger.error(f"  ✗ Error: {e}")
            else:
                logger.info("No new benchmarks found")

            self.state['last_discovery'] = datetime.now().isoformat()
            self._save_state()

            logger.info(f"\nCurrent stats:")
            logger.info(f"  Total questions: {self.state['total_questions']}")
            logger.info(f"  Benchmarks: {len(self.state['processed_benchmarks'])}")

            logger.info(f"\nSleeping for {check_interval_hours} hours...")
            logger.info(f"Next check: {datetime.fromtimestamp(time.time() + check_interval_hours * 3600).strftime('%Y-%m-%d %H:%M:%S')}")

            time.sleep(check_interval_hours * 3600)


def main():
    """Main entry point."""
    import sys

    builder = InfiniteGitHubBenchmarkBuilder()

    if len(sys.argv) > 1 and sys.argv[1] == 'infinite':
        # Full infinite mode
        logger.info("\nStarting INFINITE mode...")
        logger.info("Phase 1: Building foundation")
        builder.phase1_foundation(max_benchmarks=3)

        logger.info("\nPhase 2: Starting continuous discovery")
        builder.phase2_continuous(check_interval_hours=24)
    else:
        # Quick test mode
        logger.info("\nRunning in TEST mode (use 'infinite' argument for full mode)")
        builder.phase1_foundation(max_benchmarks=2)

        logger.info("\n" + "="*60)
        logger.info("Test complete! Run with 'infinite' argument for continuous mode:")
        logger.info("  python infinite_github_builder.py infinite")
        logger.info("="*60)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\nStopped by user")
    except Exception as e:
        logger.error(f"\nFatal error: {e}", exc_info=True)
