#!/usr/bin/env python3
"""
Continuous Autonomous Growth
=============================

Runs the autonomous benchmark grower on a schedule.
Can be run as a daemon or cron job.

Author: ToGMAL Project
"""

import time
import logging
import argparse
from datetime import datetime
from pathlib import Path
import subprocess
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('continuous_growth.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def run_growth_cycle(max_questions: int = 5000):
    """Run one growth cycle."""
    logger.info("="*70)
    logger.info(f"🚀 Starting growth cycle (max {max_questions:,} questions)")
    logger.info("="*70)

    try:
        result = subprocess.run(
            [sys.executable, "autonomous_benchmark_grower.py", str(max_questions)],
            capture_output=True,
            text=True,
            timeout=600  # 10 minute timeout
        )

        if result.returncode == 0:
            logger.info("✅ Growth cycle completed successfully")
            logger.info("\nOutput:")
            for line in result.stdout.split('\n')[-30:]:  # Last 30 lines
                if line.strip():
                    logger.info(f"  {line}")
            return True
        else:
            logger.error(f"❌ Growth cycle failed with code {result.returncode}")
            logger.error(f"Error: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        logger.error("❌ Growth cycle timed out after 10 minutes")
        return False
    except Exception as e:
        logger.error(f"❌ Error running growth cycle: {e}")
        return False


def run_continuous(
    interval_hours: float = 24,
    max_questions: int = 5000,
    max_iterations: int = None
):
    """
    Run growth cycles continuously.

    Args:
        interval_hours: Hours between growth cycles
        max_questions: Max questions per cycle
        max_iterations: Max number of cycles (None = infinite)
    """
    logger.info("\n" + "="*70)
    logger.info("CONTINUOUS AUTONOMOUS GROWTH")
    logger.info("="*70)
    logger.info(f"Interval: Every {interval_hours} hours")
    logger.info(f"Max questions per cycle: {max_questions:,}")
    logger.info(f"Max iterations: {max_iterations or 'Infinite'}")
    logger.info("\nPress Ctrl+C to stop\n")

    iteration = 0

    try:
        while True:
            iteration += 1

            logger.info(f"\n{'='*70}")
            logger.info(f"ITERATION {iteration}")
            if max_iterations:
                logger.info(f"({iteration}/{max_iterations})")
            logger.info(f"{'='*70}\n")

            success = run_growth_cycle(max_questions=max_questions)

            if not success:
                logger.warning("Growth cycle failed, will retry next cycle")

            if max_iterations and iteration >= max_iterations:
                logger.info(f"\n✅ Completed {max_iterations} iterations")
                break

            # Wait for next cycle
            logger.info(f"\n⏳ Waiting {interval_hours} hours until next cycle...")
            logger.info(f"Next cycle at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            time.sleep(interval_hours * 3600)

    except KeyboardInterrupt:
        logger.info("\n\n⏹️  Stopped by user")
    except Exception as e:
        logger.error(f"\n❌ Fatal error: {e}", exc_info=True)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Continuous autonomous benchmark dataset growth",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run once
  python run_continuous_growth.py --once

  # Run every 6 hours
  python run_continuous_growth.py --interval 6

  # Run 5 times, every hour, with 10k questions
  python run_continuous_growth.py --interval 1 --iterations 5 --questions 10000

  # Continuous mode (24 hour intervals)
  python run_continuous_growth.py
        """
    )

    parser.add_argument(
        '--interval',
        type=float,
        default=24,
        help='Hours between growth cycles (default: 24)'
    )

    parser.add_argument(
        '--questions',
        type=int,
        default=5000,
        help='Max questions per cycle (default: 5000)'
    )

    parser.add_argument(
        '--iterations',
        type=int,
        default=None,
        help='Max iterations (default: infinite)'
    )

    parser.add_argument(
        '--once',
        action='store_true',
        help='Run once and exit'
    )

    args = parser.parse_args()

    if args.once:
        run_growth_cycle(max_questions=args.questions)
    else:
        run_continuous(
            interval_hours=args.interval,
            max_questions=args.questions,
            max_iterations=args.iterations
        )


if __name__ == '__main__':
    main()
