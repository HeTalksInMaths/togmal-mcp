#!/usr/bin/env python3
"""
Infinite Benchmark Builder
==========================

Combines:
1. Massive initial build (10+ benchmarks)
2. Dynamic discovery of new benchmarks
3. Intelligent auto-expansion based on gaps
4. No hardcoded limits - grows indefinitely!

This script can run continuously, periodically discovering and adding
new benchmarks as they become available.

Author: ToGMAL Project
"""

import json
import logging
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('infinite_build.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Import both systems
from massive_vector_db_builder import MassiveVectorDBBuilder
from dynamic_benchmark_discovery import (
    CoverageAnalyzer,
    BenchmarkDiscovery,
    DynamicBenchmarkIntegrator
)


class InfiniteBenchmarkBuilder:
    """
    Builds and continuously expands vector database without limits.
    
    Three phases:
    1. Foundation: Build initial set of major benchmarks
    2. Expansion: Discover and add new benchmarks
    3. Maintenance: Periodically check for new data and expand
    """
    
    def __init__(
        self,
        detailed_db_path: Path = Path("./data/vector_db_detailed"),
        topline_db_path: Path = Path("./data/vector_db_topline"),
        state_file: Path = Path("./data/builder_state.json")
    ):
        """Initialize infinite builder."""
        
        self.detailed_db_path = detailed_db_path
        self.topline_db_path = topline_db_path
        self.state_file = state_file
        
        # Initialize sub-systems
        self.massive_builder = MassiveVectorDBBuilder(
            detailed_db_path=detailed_db_path,
            topline_db_path=topline_db_path
        )
        
        self.analyzer = CoverageAnalyzer(topline_db_path)
        self.discovery = BenchmarkDiscovery()
        self.integrator = DynamicBenchmarkIntegrator(topline_db_path)
        
        # Load or initialize state
        self.state = self._load_state()
    
    def _load_state(self) -> Dict[str, Any]:
        """Load builder state (what's been built, when, etc.)."""
        
        if self.state_file.exists():
            with open(self.state_file) as f:
                return json.load(f)
        
        return {
            'phase': 'not_started',
            'foundation_complete': False,
            'expansion_rounds': 0,
            'last_discovery': None,
            'benchmarks_added': [],
            'total_questions': 0,
            'history': []
        }
    
    def _save_state(self):
        """Save current state."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(self.state, f, indent=2)
    
    def phase1_foundation(self, top_k_models: int = 5):
        """
        Phase 1: Build foundation with major benchmarks.
        
        This gives you a solid baseline to work from.
        """
        
        logger.info("\n" + "="*80)
        logger.info("PHASE 1: FOUNDATION BUILD")
        logger.info("="*80)
        logger.info("Building initial database with major benchmarks...")
        
        if self.state['foundation_complete']:
            logger.info("Foundation already built. Skipping to expansion.")
            return
        
        # Use massive builder for foundation
        self.massive_builder.build_all(
            top_k_models=top_k_models,
            verify_every_n=3
        )
        
        # Update state
        self.state['phase'] = 'expansion'
        self.state['foundation_complete'] = True
        self.state['history'].append({
            'timestamp': datetime.now().isoformat(),
            'action': 'foundation_complete',
            'benchmarks': self.massive_builder.stats['benchmarks_completed']
        })
        
        self._save_state()
        
        logger.info("\n✓ Foundation build complete!")
    
    def phase2_expansion(
        self,
        rounds: int = 3,
        benchmarks_per_round: int = 5
    ):
        """
        Phase 2: Intelligent expansion based on gaps.
        
        Args:
            rounds: Number of expansion rounds
            benchmarks_per_round: How many to add per round
        """
        
        logger.info("\n" + "="*80)
        logger.info("PHASE 2: INTELLIGENT EXPANSION")
        logger.info("="*80)
        
        if not self.state['foundation_complete']:
            logger.warning("Foundation not built yet. Run phase1_foundation() first.")
            return
        
        for round_num in range(1, rounds + 1):
            logger.info(f"\n{'#'*80}")
            logger.info(f"EXPANSION ROUND {round_num}/{rounds}")
            logger.info('#'*80)
            
            # Analyze current coverage
            logger.info("\nAnalyzing coverage gaps...")
            coverage = self.analyzer.analyze_coverage()
            
            logger.info(f"Current total: {coverage['total_questions']:,} questions")
            logger.info(f"Sources: {len(coverage['sources'])}")
            logger.info(f"Gaps identified: {len(coverage['coverage_gaps'])}")
            
            for gap in coverage['coverage_gaps'][:3]:
                logger.info(f"  • {gap}")
            
            # Discover new benchmarks
            logger.info("\nDiscovering new benchmarks...")
            suggestions = self.integrator.suggest_next_benchmarks(
                max_suggestions=benchmarks_per_round * 2
            )
            
            if not suggestions:
                logger.info("No new benchmarks found. Expansion complete.")
                break
            
            logger.info(f"Found {len(suggestions)} candidates")
            
            # Add top benchmarks
            logger.info(f"\nAdding top {benchmarks_per_round} benchmarks...")
            added = self.integrator.auto_expand(
                max_benchmarks=benchmarks_per_round,
                dry_run=False
            )
            
            if added:
                logger.info(f"✓ Added {len(added)} benchmarks: {', '.join(added)}")
                
                # Update state
                self.state['expansion_rounds'] += 1
                self.state['benchmarks_added'].extend(added)
                self.state['history'].append({
                    'timestamp': datetime.now().isoformat(),
                    'action': f'expansion_round_{round_num}',
                    'added': added
                })
                self._save_state()
            else:
                logger.info("No benchmarks added this round")
            
            # Brief pause between rounds
            if round_num < rounds:
                logger.info("\nPausing before next round...")
                time.sleep(5)
        
        logger.info("\n✓ Expansion phase complete!")
    
    def phase3_continuous(
        self,
        interval_hours: int = 24,
        max_iterations: int = None
    ):
        """
        Phase 3: Continuous discovery and expansion.
        
        Runs indefinitely, periodically checking for new benchmarks.
        
        Args:
            interval_hours: Hours between discovery attempts
            max_iterations: Maximum iterations (None = infinite)
        """
        
        logger.info("\n" + "="*80)
        logger.info("PHASE 3: CONTINUOUS EXPANSION")
        logger.info("="*80)
        logger.info(f"Will check for new benchmarks every {interval_hours} hours")
        
        iteration = 0
        
        while max_iterations is None or iteration < max_iterations:
            iteration += 1
            
            logger.info(f"\n{'='*80}")
            logger.info(f"CONTINUOUS EXPANSION - ITERATION {iteration}")
            logger.info('='*80)
            
            # Check coverage
            coverage = self.analyzer.analyze_coverage()
            logger.info(f"Current size: {coverage['total_questions']:,} questions")
            
            # Discover new
            logger.info("Checking for new benchmarks...")
            suggestions = self.integrator.suggest_next_benchmarks(max_suggestions=10)
            
            if suggestions:
                logger.info(f"Found {len(suggestions)} new candidates")
                
                # Add best 2-3 per iteration
                added = self.integrator.auto_expand(max_benchmarks=3, dry_run=False)
                
                if added:
                    logger.info(f"✓ Added: {', '.join(added)}")
                    
                    self.state['history'].append({
                        'timestamp': datetime.now().isoformat(),
                        'action': f'continuous_iteration_{iteration}',
                        'added': added
                    })
                    self._save_state()
            else:
                logger.info("No new benchmarks found")
            
            # Wait until next iteration
            if max_iterations is None or iteration < max_iterations:
                logger.info(f"\nSleeping for {interval_hours} hours...")
                time.sleep(interval_hours * 3600)
    
    def run_full_build(
        self,
        foundation_top_k: int = 5,
        expansion_rounds: int = 3,
        continuous: bool = False
    ):
        """
        Run complete build pipeline.
        
        Args:
            foundation_top_k: Number of models for foundation
            expansion_rounds: Number of expansion rounds
            continuous: If True, enter continuous mode after expansion
        """
        
        logger.info("\n" + "="*80)
        logger.info("INFINITE BENCHMARK BUILDER - FULL PIPELINE")
        logger.info("="*80)
        
        start_time = datetime.now()
        
        # Phase 1: Foundation
        self.phase1_foundation(top_k_models=foundation_top_k)
        
        # Phase 2: Expansion
        self.phase2_expansion(rounds=expansion_rounds, benchmarks_per_round=5)
        
        # Phase 3: Continuous (optional)
        if continuous:
            logger.info("\nEntering continuous expansion mode...")
            logger.info("Press Ctrl+C to stop")
            try:
                self.phase3_continuous(interval_hours=24)
            except KeyboardInterrupt:
                logger.info("\nStopped by user")
        
        elapsed = datetime.now() - start_time
        
        # Final stats
        coverage = self.analyzer.analyze_coverage()
        
        logger.info("\n" + "="*80)
        logger.info("BUILD COMPLETE!")
        logger.info("="*80)
        logger.info(f"Total time: {elapsed}")
        logger.info(f"Total questions: {coverage['total_questions']:,}")
        logger.info(f"Sources: {len(coverage['sources'])}")
        logger.info(f"Expansion rounds: {self.state['expansion_rounds']}")
        logger.info(f"Benchmarks added: {len(self.state['benchmarks_added'])}")
        logger.info("="*80)
    
    def status_report(self) -> Dict[str, Any]:
        """Get current status report."""
        
        coverage = self.analyzer.analyze_coverage()
        
        return {
            'state': self.state,
            'coverage': coverage,
            'summary': {
                'total_questions': coverage['total_questions'],
                'num_sources': len(coverage['sources']),
                'phase': self.state['phase'],
                'expansion_rounds': self.state['expansion_rounds'],
                'benchmarks_added': len(self.state['benchmarks_added'])
            }
        }


def main():
    """Main entry point with CLI-like interface."""
    
    import sys
    
    builder = InfiniteBenchmarkBuilder()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'foundation':
            builder.phase1_foundation()
        
        elif command == 'expand':
            rounds = int(sys.argv[2]) if len(sys.argv) > 2 else 3
            builder.phase2_expansion(rounds=rounds)
        
        elif command == 'continuous':
            builder.phase3_continuous()
        
        elif command == 'full':
            builder.run_full_build(
                foundation_top_k=5,
                expansion_rounds=3,
                continuous=False
            )
        
        elif command == 'infinite':
            builder.run_full_build(
                foundation_top_k=5,
                expansion_rounds=3,
                continuous=True  # Never stops!
            )
        
        elif command == 'status':
            status = builder.status_report()
            print(json.dumps(status, indent=2))
        
        else:
            print(f"Unknown command: {command}")
            print("\nUsage:")
            print("  python infinite_benchmark_builder.py foundation")
            print("  python infinite_benchmark_builder.py expand [rounds]")
            print("  python infinite_benchmark_builder.py continuous")
            print("  python infinite_benchmark_builder.py full")
            print("  python infinite_benchmark_builder.py infinite")
            print("  python infinite_benchmark_builder.py status")
    
    else:
        # Default: run full build
        builder.run_full_build(
            foundation_top_k=5,
            expansion_rounds=3,
            continuous=False
        )


if __name__ == "__main__":
    main()
