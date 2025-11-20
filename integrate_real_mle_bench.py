#!/usr/bin/env python3
"""
Integrate REAL MLE-Bench Data into ToGMAL
==========================================

Extracts metadata from the official OpenAI MLE-bench repository and
integrates it into the unified ToGMAL database with proper difficulty scores.

Based on: https://github.com/openai/mle-bench
"""

import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict


class MLEBenchIntegrator:
    """Extract and integrate real MLE-bench competitions"""

    def __init__(self, mle_bench_path: str = "/tmp/mle-bench"):
        self.mle_bench_path = Path(mle_bench_path)
        self.competitions_dir = self.mle_bench_path / "mlebench" / "competitions"
        self.splits_dir = self.mle_bench_path / "experiments" / "splits"

        # Load complexity splits
        self.complexity_map = self._load_complexity_splits()

        print(f"📊 MLE-bench Repository: {self.mle_bench_path}")
        print(f"   Competitions dir: {self.competitions_dir}")
        print(f"   Found {len(self.complexity_map)} competitions")

    def _load_complexity_splits(self) -> Dict[str, str]:
        """Load competition complexity from splits files"""
        complexity_map = {}

        # Load each complexity level
        for complexity in ["low", "medium", "high"]:
            split_file = self.splits_dir / f"{complexity}.txt"
            if split_file.exists():
                with open(split_file) as f:
                    comp_ids = f.read().strip().split('\n')
                    for comp_id in comp_ids:
                        complexity_map[comp_id] = complexity

        return complexity_map

    def _map_complexity_to_difficulty(self, complexity: str) -> float:
        """Map complexity level to difficulty score (0-1)"""
        mapping = {
            "low": 0.3,      # Easy
            "medium": 0.6,   # Medium
            "high": 0.85     # Hard
        }
        return mapping.get(complexity, 0.5)

    def _extract_domain_from_competition(self, comp_id: str, comp_name: str,
                                        description: str) -> tuple[str, str]:
        """Extract domain and subdomain from competition metadata"""

        # Common domain keywords
        domain_keywords = {
            "image": ("computer_vision", "image_classification"),
            "vision": ("computer_vision", "image_classification"),
            "photo": ("computer_vision", "image_classification"),
            "detection": ("computer_vision", "object_detection"),
            "segmentation": ("computer_vision", "segmentation"),
            "classification": ("machine_learning", "classification"),
            "text": ("nlp", "text_classification"),
            "language": ("nlp", "language_modeling"),
            "speech": ("audio", "speech_recognition"),
            "audio": ("audio", "audio_classification"),
            "tabular": ("machine_learning", "tabular"),
            "time": ("machine_learning", "time_series"),
            "regression": ("machine_learning", "regression"),
            "recommendation": ("machine_learning", "recommendation"),
            "nlp": ("nlp", "general"),
            "toxic": ("nlp", "text_classification"),
            "sentiment": ("nlp", "sentiment_analysis"),
            "question": ("nlp", "question_answering"),
        }

        # Check competition name and description
        text = f"{comp_id} {comp_name} {description[:200]}".lower()

        for keyword, (domain, subdomain) in domain_keywords.items():
            if keyword in text:
                return domain, subdomain

        # Default
        return "machine_learning", "general"

    def extract_competition_metadata(self, comp_id: str) -> Optional[Dict]:
        """Extract metadata for a single competition"""

        config_path = self.competitions_dir / comp_id / "config.yaml"

        if not config_path.exists():
            print(f"   ⚠️  No config found for {comp_id}")
            return None

        # Load config
        with open(config_path) as f:
            config = yaml.safe_load(f)

        # Load description
        description_path = self.mle_bench_path / config.get("description", "")
        description = ""
        if description_path.exists():
            with open(description_path) as f:
                description = f.read().strip()

        # Get complexity
        complexity = self.complexity_map.get(comp_id, "medium")
        difficulty_score = self._map_complexity_to_difficulty(complexity)

        # Extract domain
        domain, subdomain = self._extract_domain_from_competition(
            comp_id, config.get("name", ""), description
        )

        # Create unified question format
        question = {
            "question_id": f"mle_bench_{comp_id}",
            "question_text": self._format_competition_as_question(
                comp_id, config.get("name", ""), description
            ),
            "domain": domain,
            "subdomain": subdomain,
            "difficulty_score": difficulty_score,
            "source": "MLE-Bench (Real)",

            # MLE-bench specific metadata
            "competition_id": comp_id,
            "competition_name": config.get("name", comp_id),
            "competition_type": config.get("competition_type", "unknown"),
            "complexity": complexity,
            "awards_medals": config.get("awards_medals", False),
            "prizes": config.get("prizes"),

            # Evaluation
            "grader_name": config.get("grader", {}).get("name", "unknown"),

            # Dataset info (if available)
            "has_dataset": True,
            "dataset_path": config.get("dataset", {}),
        }

        return question

    def _format_competition_as_question(self, comp_id: str, name: str,
                                       description: str) -> str:
        """Format competition metadata as a question for ToGMAL"""

        # Truncate description if too long
        desc_preview = description[:500] + "..." if len(description) > 500 else description

        question_text = f"""**Kaggle Competition: {name}**

**Competition ID:** {comp_id}

**Description:**
{desc_preview}

**Task:** Build a machine learning solution to solve this competition task.
"""
        return question_text

    def extract_all_competitions(self) -> List[Dict]:
        """Extract metadata from all competitions"""

        print("\n" + "="*80)
        print("EXTRACTING MLE-BENCH COMPETITION METADATA")
        print("="*80)

        questions = []

        # Get all competition IDs from directories
        comp_dirs = [d for d in self.competitions_dir.iterdir()
                    if d.is_dir() and not d.name.startswith('__')]

        print(f"\nProcessing {len(comp_dirs)} competitions...")

        for comp_dir in sorted(comp_dirs):
            comp_id = comp_dir.name

            question = self.extract_competition_metadata(comp_id)
            if question:
                questions.append(question)
                complexity = question.get("complexity", "unknown")
                print(f"  ✅ {comp_id:<50} [{complexity:>6}]")

        print(f"\n✅ Extracted {len(questions)} competitions")

        # Statistics
        by_complexity = defaultdict(int)
        by_domain = defaultdict(int)

        for q in questions:
            by_complexity[q.get("complexity", "unknown")] += 1
            by_domain[q["domain"]] += 1

        print("\nBy complexity:")
        for complexity in ["low", "medium", "high"]:
            count = by_complexity[complexity]
            print(f"  {complexity:>6}: {count:>2} competitions")

        print("\nBy domain:")
        for domain, count in sorted(by_domain.items(), key=lambda x: -x[1]):
            print(f"  {domain:<25}: {count:>2} competitions")

        return questions

    def integrate_into_unified_db(self, mle_questions: List[Dict]):
        """Integrate MLE-bench questions into unified database"""

        print("\n" + "="*80)
        print("INTEGRATING INTO UNIFIED DATABASE")
        print("="*80)

        # Load existing unified database
        unified_db_path = Path("./data/unified_database_complete.json")

        if unified_db_path.exists():
            with open(unified_db_path) as f:
                unified_db = json.load(f)
        else:
            unified_db = {"questions": [], "metadata": {}}

        original_count = len(unified_db["questions"])
        print(f"\n📊 Current database: {original_count:,} questions")

        # Remove old MLE-bench synthetic data if it exists
        unified_db["questions"] = [
            q for q in unified_db["questions"]
            if not q.get("question_id", "").startswith("mle_")
        ]

        removed_count = original_count - len(unified_db["questions"])
        if removed_count > 0:
            print(f"   Removed {removed_count} old MLE-bench entries")

        # Add new real MLE-bench data
        unified_db["questions"].extend(mle_questions)

        # Update metadata
        unified_db["metadata"] = {
            "total_questions": len(unified_db["questions"]),
            "last_updated": datetime.now().isoformat(),
            "sources": list(set(q.get("source", "unknown") for q in unified_db["questions"])),
            "mle_bench_count": len(mle_questions),
            "mle_bench_version": "real_v1",
        }

        # Save updated database
        output_path = Path("./data/unified_database_with_real_mle.json")
        with open(output_path, 'w') as f:
            json.dump(unified_db, f, indent=2)

        print(f"\n✅ Saved to: {output_path}")
        print(f"   Total questions: {len(unified_db['questions']):,}")
        print(f"   MLE-bench (real): {len(mle_questions)}")

        return output_path

    def export_mle_bench_only(self, mle_questions: List[Dict]):
        """Export MLE-bench data as standalone file"""

        output_path = Path("./data/real_mle_bench_competitions.json")

        mle_db = {
            "competitions": mle_questions,
            "metadata": {
                "total_competitions": len(mle_questions),
                "source": "https://github.com/openai/mle-bench",
                "extracted": datetime.now().isoformat(),
                "complexity_breakdown": {
                    "low": len([q for q in mle_questions if q["complexity"] == "low"]),
                    "medium": len([q for q in mle_questions if q["complexity"] == "medium"]),
                    "high": len([q for q in mle_questions if q["complexity"] == "high"]),
                }
            }
        }

        with open(output_path, 'w') as f:
            json.dump(mle_db, f, indent=2)

        print(f"\n💾 Exported MLE-bench standalone: {output_path}")
        return output_path


def main():
    """Main integration workflow"""

    print("="*80)
    print("REAL MLE-BENCH INTEGRATION FOR TOGMAL")
    print("="*80)

    # Initialize integrator
    integrator = MLEBenchIntegrator()

    # Extract all competitions
    mle_questions = integrator.extract_all_competitions()

    # Integrate into unified database
    unified_path = integrator.integrate_into_unified_db(mle_questions)

    # Export standalone MLE-bench file
    standalone_path = integrator.export_mle_bench_only(mle_questions)

    print("\n" + "="*80)
    print("✅ INTEGRATION COMPLETE!")
    print("="*80)
    print(f"\nOutput files:")
    print(f"  1. {unified_path}")
    print(f"  2. {standalone_path}")

    print("\n⚠️  NEXT STEPS:")
    print("  1. ✅ Real MLE-bench data integrated")
    print("  2. ❌ Need to fetch/create LLM performance data")
    print("  3. ❌ Re-train failure rate predictor")
    print("  4. ❌ Re-benchmark Phase 1 + Phase 2 improvements")

    return unified_path


if __name__ == "__main__":
    main()
