#!/usr/bin/env python3
"""
Build MCP Data Store
====================

Creates simple JSON-based data store for MCP server.
Architecture: MCP fetches data, Skills analyze data.

Data Store Structure:
- questions_by_id.json: Quick lookup by question ID
- questions_by_benchmark.json: Grouped by benchmark
- questions_by_difficulty.json: Grouped by difficulty
- questions_with_errors.json: Only questions with error patterns
- error_patterns_catalog.json: All 32 error patterns
- statistics.json: Summary statistics
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from collections import defaultdict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MCPDataStoreBuilder:
    """Builds MCP-optimized data store from unified database"""

    def __init__(
        self,
        data_dir: Path = Path("./data"),
        output_dir: Path = Path("./mcp_datastore")
    ):
        self.data_dir = data_dir
        self.output_dir = output_dir
        self.output_dir.mkdir(exist_ok=True)

    def load_unified_database(self) -> List[Dict[str, Any]]:
        """Load unified database"""
        db_path = self.data_dir / "unified_database_complete.json"
        logger.info(f"Loading unified database from {db_path}...")

        with open(db_path, 'r') as f:
            data = json.load(f)

        questions = data['questions']
        logger.info(f"✅ Loaded {len(questions):,} questions")
        return questions

    def build_datastore(self):
        """Build all data store files"""
        logger.info("="*80)
        logger.info("Building MCP Data Store")
        logger.info("="*80)

        # Load questions
        questions = self.load_unified_database()

        # 1. Questions by ID (fast lookup)
        logger.info("\n1. Building questions_by_id.json...")
        questions_by_id = {q['question_id']: q for q in questions}
        self._save_json('questions_by_id.json', questions_by_id)
        logger.info(f"   ✅ {len(questions_by_id):,} questions indexed by ID")

        # 2. Questions by benchmark
        logger.info("\n2. Building questions_by_benchmark.json...")
        by_benchmark = defaultdict(list)
        for q in questions:
            by_benchmark[q['benchmark']].append(q)
        self._save_json('questions_by_benchmark.json', dict(by_benchmark))
        logger.info(f"   ✅ {len(by_benchmark)} benchmarks")
        for bench, qs in by_benchmark.items():
            logger.info(f"      {bench}: {len(qs):,} questions")

        # 3. Questions by difficulty
        logger.info("\n3. Building questions_by_difficulty.json...")
        by_difficulty = defaultdict(list)
        for q in questions:
            by_difficulty[q['difficulty_label']].append(q)
        self._save_json('questions_by_difficulty.json', dict(by_difficulty))
        logger.info(f"   ✅ {len(by_difficulty)} difficulty levels")
        for diff, qs in sorted(by_difficulty.items(), key=lambda x: len(x[1]), reverse=True):
            logger.info(f"      {diff}: {len(qs):,} questions")

        # 4. Questions with error analysis
        logger.info("\n4. Building questions_with_errors.json...")
        with_errors = [q for q in questions if len(q['error_patterns']) > 0]
        self._save_json('questions_with_errors.json', with_errors)
        logger.info(f"   ✅ {len(with_errors):,} questions with error patterns")

        # 5. Universal failures
        logger.info("\n5. Building universal_failures.json...")
        universal = [q for q in questions if q.get('is_universal_failure', False)]
        self._save_json('universal_failures.json', universal)
        logger.info(f"   ✅ {len(universal):,} universal failures")

        # 6. Error patterns catalog
        logger.info("\n6. Building error_patterns_catalog.json...")
        all_patterns = []
        pattern_frequencies = defaultdict(int)

        for q in questions:
            for pattern in q['error_patterns']:
                all_patterns.append(pattern)
                pattern_key = f"{pattern['source']}:{pattern['pattern']}"
                pattern_frequencies[pattern_key] += 1

        # Unique patterns
        unique_patterns = {}
        for pattern in all_patterns:
            pattern_key = f"{pattern['source']}:{pattern['pattern']}"
            if pattern_key not in unique_patterns:
                pattern['frequency_in_dataset'] = pattern_frequencies[pattern_key]
                unique_patterns[pattern_key] = pattern

        catalog = {
            'total_pattern_instances': len(all_patterns),
            'unique_patterns': len(unique_patterns),
            'patterns': list(unique_patterns.values())
        }

        self._save_json('error_patterns_catalog.json', catalog)
        logger.info(f"   ✅ {len(unique_patterns)} unique patterns ({len(all_patterns):,} instances)")

        # 7. Statistics
        logger.info("\n7. Building statistics.json...")
        stats = self._compute_statistics(questions)
        self._save_json('statistics.json', stats)
        logger.info(f"   ✅ Statistics computed")

        # 8. Domain index
        logger.info("\n8. Building questions_by_domain.json...")
        by_domain = defaultdict(list)
        for q in questions:
            by_domain[q['domain']].append(q)
        self._save_json('questions_by_domain.json', dict(by_domain))
        logger.info(f"   ✅ {len(by_domain)} domains indexed")

        logger.info("\n" + "="*80)
        logger.info("✅ MCP Data Store Built Successfully!")
        logger.info("="*80)
        logger.info(f"\nLocation: {self.output_dir}")
        logger.info(f"Files created: 8")
        logger.info(f"\nData Store Files:")
        for file in sorted(self.output_dir.glob('*.json')):
            size_mb = file.stat().st_size / (1024 * 1024)
            logger.info(f"  {file.name}: {size_mb:.1f} MB")

        return stats

    def _save_json(self, filename: str, data: Any):
        """Save JSON file"""
        path = self.output_dir / filename
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def _compute_statistics(self, questions: List[Dict]) -> Dict:
        """Compute summary statistics"""
        total = len(questions)

        # By benchmark
        by_benchmark = defaultdict(int)
        for q in questions:
            by_benchmark[q['benchmark']] += 1

        # By difficulty
        by_difficulty = defaultdict(int)
        for q in questions:
            by_difficulty[q['difficulty_label']] += 1

        # Error analysis coverage
        with_errors = sum(1 for q in questions if len(q['error_patterns']) > 0)
        universal_failures = sum(1 for q in questions if q.get('is_universal_failure', False))
        cot_failures = sum(1 for q in questions if q.get('cot_failure_mode'))

        # Success rate stats
        success_rates = [q['success_rate'] for q in questions]
        avg_success = sum(success_rates) / len(success_rates)

        # Domain distribution
        by_domain = defaultdict(int)
        for q in questions:
            by_domain[q['domain']] += 1

        # Error pattern stats
        all_patterns = []
        for q in questions:
            all_patterns.extend(q['error_patterns'])

        by_source = defaultdict(int)
        by_severity = defaultdict(int)
        for p in all_patterns:
            by_source[p['source']] += 1
            by_severity[p['severity']] += 1

        return {
            'total_questions': total,
            'by_benchmark': dict(by_benchmark),
            'by_difficulty': dict(by_difficulty),
            'by_domain': dict(sorted(by_domain.items(), key=lambda x: x[1], reverse=True)),
            'error_analysis': {
                'questions_with_patterns': with_errors,
                'percentage_with_patterns': f"{with_errors/total*100:.1f}%",
                'universal_failures': universal_failures,
                'cot_failures': cot_failures,
                'total_pattern_instances': len(all_patterns),
                'patterns_by_source': dict(by_source),
                'patterns_by_severity': dict(by_severity)
            },
            'success_rates': {
                'average': f"{avg_success:.1%}",
                'min': f"{min(success_rates):.1%}",
                'max': f"{max(success_rates):.1%}"
            }
        }

def main():
    """Build the MCP data store"""
    builder = MCPDataStoreBuilder()
    stats = builder.build_datastore()

    logger.info("\n" + "="*80)
    logger.info("Summary Statistics")
    logger.info("="*80)
    logger.info(json.dumps(stats, indent=2))

    logger.info("\n" + "="*80)
    logger.info("Next Steps")
    logger.info("="*80)
    logger.info("1. Refactor MCP to query this data store")
    logger.info("2. MCP tools: fetch_question, query_by_difficulty, get_error_patterns")
    logger.info("3. Create ToGMAL Skill with analysis procedures")
    logger.info("4. Test Skills + MCP integration")

if __name__ == "__main__":
    main()
