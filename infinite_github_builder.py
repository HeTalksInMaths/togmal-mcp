#!/usr/bin/env python3
"""
Infinite GitHub-Based Benchmark Builder
========================================

Continuously discovers and loads benchmarks from GitHub.
Works in restricted networks (no HuggingFace required).

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
    """Infinite benchmark builder using GitHub as data source."""

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
        self.state = self._load_state()

        logger.info("="*60)
        logger.info("Infinite GitHub Benchmark Builder")
        logger.info("="*60)
        logger.info(f"Data directory: {self.data_dir}")
        logger.info(f"Total questions: {self.state['total_questions']}")
        logger.info(f"Benchmarks processed: {len(self.state['processed_benchmarks'])}")

    def _load_state(self) -> Dict[str, Any]:
        """Load builder state."""
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                return json.load(f)

        return {
            'total_questions': 0,
            'processed_benchmarks': [],
            'last_check': None,
            'start_time': datetime.now().isoformat()
        }

    def _save_state(self):
        """Save builder state."""
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)

    def process_next_batch(self, batch_size: int = 3) -> int:
        """
        Process next batch of benchmarks.

        Returns:
            Number of benchmarks processed
        """
        logger.info("\n" + "="*60)
        logger.info(f"PROCESSING BATCH ({batch_size} repos max)")
        logger.info("="*60)

        # Discover benchmarks dynamically
        logger.info("🔍 Dynamically searching GitHub for benchmarks...")
        benchmarks = self.discovery.discover_benchmarks(min_stars=10, max_results=50)

        if not benchmarks:
            logger.warning("No benchmarks discovered!")
            return 0

        # Filter unprocessed
        new_benchmarks = [b for b in benchmarks
                         if b.repo_full_name not in self.state['processed_benchmarks']]

        if not new_benchmarks:
            logger.info("✓ All available benchmarks already processed!")
            return 0

        logger.info(f"Found {len(new_benchmarks)} unprocessed benchmarks")
        to_process = new_benchmarks[:batch_size]
        logger.info(f"Processing {len(to_process)} in this batch\n")

        processed_count = 0
        for i, benchmark in enumerate(to_process):
            logger.info(f"[{i+1}/{len(to_process)}] {benchmark.repo_full_name} ({benchmark.stars}⭐)")
            logger.info(f"  Desc: {benchmark.description[:70]}...")
            logger.info(f"  Files: {benchmark.num_files}, Schema: Q={benchmark.question_fields}, A={benchmark.answer_fields}")

            try:
                data = self.discovery.load_benchmark_data(benchmark, max_questions=10000)

                if data:
                    # Save
                    output_file = self.data_dir / f"{benchmark.repo_full_name.replace('/', '_')}.json"
                    with open(output_file, 'w') as f:
                        json.dump({
                            'benchmark': benchmark.repo_full_name,
                            'stars': benchmark.stars,
                            'description': benchmark.description,
                            'num_questions': len(data),
                            'questions': data
                        }, f, indent=2)

                    logger.info(f"  ✓ Saved {len(data):,} questions ({output_file.stat().st_size / 1024 / 1024:.1f}MB)")

                    # Update state
                    self.state['total_questions'] += len(data)
                    self.state['processed_benchmarks'].append(benchmark.repo_full_name)
                    self._save_state()
                    processed_count += 1
                else:
                    logger.warning(f"  ✗ No data extracted")

            except Exception as e:
                logger.error(f"  ✗ Error: {e}")

            logger.info("")

        logger.info("="*60)
        logger.info(f"BATCH COMPLETE: {processed_count} benchmarks added")
        logger.info(f"TOTAL: {self.state['total_questions']:,} questions, {len(self.state['processed_benchmarks'])} benchmarks")
        logger.info("="*60)

        return processed_count

    def run_continuous(self, batch_size: int = 3, interval_minutes: int = 60):
        """
        Run in continuous mode.

        Args:
            batch_size: Benchmarks per batch
            interval_minutes: Minutes between batches
        """
        logger.info("\n🚀 CONTINUOUS MODE ACTIVATED")
        logger.info(f"  Batch size: {batch_size} benchmarks")
        logger.info(f"  Check interval: {interval_minutes} minutes")
        logger.info(f"  Press Ctrl+C to stop\n")

        iteration = 0
        while True:
            iteration += 1
            logger.info(f"\n{'='*60}")
            logger.info(f"ITERATION #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info(f"{'='*60}")

            processed = self.process_next_batch(batch_size=batch_size)

            if processed == 0:
                logger.info("\n✓ No new benchmarks to process")

            self.state['last_check'] = datetime.now().isoformat()
            self._save_state()

            # Wait
            next_run = datetime.fromtimestamp(time.time() + interval_minutes * 60)
            logger.info(f"\n💤 Sleeping {interval_minutes} minutes...")
            logger.info(f"   Next run: {next_run.strftime('%Y-%m-%d %H:%M:%S')}")

            time.sleep(interval_minutes * 60)


def main():
    """Main entry point."""
    import sys

    builder = InfiniteGitHubBenchmarkBuilder()

    if len(sys.argv) > 1:
        mode = sys.argv[1]

        if mode == 'infinite':
            # Continuous mode
            batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 3
            interval = int(sys.argv[3]) if len(sys.argv) > 3 else 60

            logger.info(f"\nStarting INFINITE mode (batch={batch_size}, interval={interval}min)")
            builder.run_continuous(batch_size=batch_size, interval_minutes=interval)

        elif mode == 'batch':
            # Single batch
            batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 5
            logger.info(f"\nProcessing single batch ({batch_size} benchmarks)")
            builder.process_next_batch(batch_size=batch_size)

    else:
        # Quick test - just 1 benchmark
        logger.info("\nQUICK TEST mode (1 benchmark)")
        logger.info("Usage:")
        logger.info("  python infinite_github_builder.py batch 5          # Process 5 benchmarks once")
        logger.info("  python infinite_github_builder.py infinite 3 60   # Continuous: 3 benchmarks every 60min")
        logger.info("")
        builder.process_next_batch(batch_size=1)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\n⏹️  Stopped by user")
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}", exc_info=True)
