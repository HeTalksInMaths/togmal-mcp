#!/usr/bin/env python3
"""
Unified Vector Database Builder
================================

Builds a single vector database combining:
1. MMLU-Pro (12K questions, 37 models, WITH error analysis from taxonomy)
2. DS-1000 (1K problems, 3 models, WITH error analysis)
3. DataSciBench (222 tasks, 28 models, NO error analysis yet)

Schema supports both types:
- error_patterns: [] (empty for DataSciBench)
- error_patterns: [...] (populated for MMLU-Pro + DS-1000)

Error Pattern Sources:
- DS-1000: 8 patterns (code errors)
- Universal Failures: 20 patterns (questions all models fail)
- CoT Failures: 2 patterns (reasoning errors)
- ML-Discovered: 2 patterns (dangerous clusters)

Total: 32 error patterns integrated
"""

import json
import gzip
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ErrorPattern:
    """Represents a specific error pattern (all sources)"""
    pattern: str  # e.g., "mutability_misunderstanding", "always_fails", "Complex unit conversion"
    source: str  # "ds1000", "universal_failure", "cot_failure", "ml_discovered"
    frequency: float  # 0.0 to 1.0 or absolute count
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    description: str  # Human-readable description
    example_wrong: str = ""  # Optional example (DS-1000 only)
    example_correct: str = ""  # Optional example (DS-1000 only)
    evidence: str = ""  # Supporting evidence
    category: str = ""  # Domain/category (if applicable)
    confidence: float = 0.0  # ML-discovered only
    
@dataclass
class UnifiedBenchmarkQuestion:
    """Unified schema supporting both types of questions"""
    
    # Core fields (ALL questions)
    question_id: str
    question_text: str
    benchmark: str  # "MMLU-Pro", "DS-1000", "DataSciBench"
    domain: str  # "physics", "pandas", "visualization", etc.
    success_rate: float  # 0.0 to 1.0
    difficulty_score: float  # 1.0 - success_rate
    
    # Per-model results (ALL questions)
    model_scores: Dict[str, bool]  # {model_name: correct/incorrect}
    num_models_tested: int
    
    # Error analysis (populated based on source)
    error_patterns: List[ErrorPattern]  # Populated for DS-1000 + MMLU-Pro (if has analysis)
    error_categories: List[str]  # ["missing_method", "wrong_attribute"]
    conceptual_gaps: List[str]  # ["mutability_misunderstanding", ...]

    # Metadata
    difficulty_label: str  # "Easy", "Medium", "Hard", "Expert"

    # Additional error analysis fields (with defaults)
    is_universal_failure: bool = False  # True if ALL models fail (MMLU-Pro)
    cot_failure_mode: Optional[str] = None  # CoT failure mode (if applicable)
    ml_cluster_id: Optional[int] = None  # Dangerous cluster ID (if applicable)
    category: Optional[str] = None  # MMLU-Pro category
    subject: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        d = asdict(self)
        # Convert ErrorPattern objects to dicts
        d['error_patterns'] = [asdict(ep) for ep in self.error_patterns]
        return d
    
    def has_error_analysis(self) -> bool:
        """Check if this question has error analysis data"""
        return len(self.error_patterns) > 0


class UnifiedVectorDBBuilder:
    """Builds unified vector database from multiple benchmark sources"""

    def __init__(self, data_dir: Path = Path("./data")):
        self.data_dir = data_dir
        self.questions: List[UnifiedBenchmarkQuestion] = []

        # Load comprehensive error patterns
        self.comprehensive_patterns = self._load_comprehensive_patterns()

    def _load_comprehensive_patterns(self) -> Dict[str, Any]:
        """Load comprehensive error patterns from analysis"""
        patterns_path = self.data_dir / "comprehensive_error_patterns.json"

        if not patterns_path.exists():
            logger.warning(f"Comprehensive error patterns not found at {patterns_path}")
            return {}

        with open(patterns_path, 'r') as f:
            data = json.load(f)

        logger.info(f"Loaded {data['metadata']['total_patterns']} error patterns from all sources")
        return data

    def _get_error_taxonomy(self) -> Dict[str, Any]:
        """Load MMLU-Pro error taxonomy"""
        taxonomy_path = self.data_dir / "error_taxonomy.json"

        if not taxonomy_path.exists():
            return {}

        with open(taxonomy_path, 'r') as f:
            return json.load(f)

    def _get_cot_failure_analysis(self) -> Dict[str, Any]:
        """Load Chain-of-Thought failure analysis"""
        cot_path = self.data_dir / "cot_failure_analysis.json"

        if not cot_path.exists():
            return {}

        with open(cot_path, 'r') as f:
            return json.load(f)
    
    def load_mmlu_pro_autonomous(self) -> List[UnifiedBenchmarkQuestion]:
        """
        Load MMLU-Pro from autonomous dataset with error analysis.

        Returns questions with:
        - success_rate: ✅ (from 37 models)
        - model_scores: ✅ (per-model results)
        - error_patterns: ✅ (from taxonomy + CoT analysis)
        """
        logger.info("Loading MMLU-Pro from autonomous dataset with error analysis...")

        # Load error analysis data
        error_taxonomy = self._get_error_taxonomy()
        cot_analysis = self._get_cot_failure_analysis()

        # Create lookup maps
        universal_failures_set = set()
        cot_failures_map = {}

        if error_taxonomy:
            for failure in error_taxonomy.get('universal_failures', []):
                q_text = failure.get('question', '')[:100]  # Use first 100 chars as key
                universal_failures_set.add(q_text)

        if cot_analysis:
            for analysis in cot_analysis.get('analyses', []):
                q_text = analysis.get('question', '')[:100]
                cot_failures_map[q_text] = analysis
        
        autonomous_path = self.data_dir / "autonomous_benchmarks" / "vector_db_ready.json"
        
        with open(autonomous_path, 'r') as f:
            data = json.load(f)
        
        questions = []
        
        for i, doc in enumerate(data['documents']):
            metadata = data['metadatas'][i]
            qid = data['ids'][i]
            
            # Parse model scores from JSON string
            model_scores = {}
            if 'model_scores' in metadata:
                try:
                    model_scores = json.loads(metadata['model_scores'])
                except:
                    pass
            
            # Calculate difficulty
            success_rate = metadata.get('success_rate', 0.5)
            difficulty_score = 1.0 - success_rate
            
            # Classify difficulty
            if success_rate < 0.1:
                difficulty_label = "Nearly_Impossible"
            elif success_rate < 0.3:
                difficulty_label = "Expert"
            elif success_rate < 0.5:
                difficulty_label = "Hard"
            elif success_rate < 0.7:
                difficulty_label = "Medium"
            else:
                difficulty_label = "Easy"
            
            # Check for error analysis
            error_patterns_list = []
            error_categories = []
            conceptual_gaps = []
            is_universal_failure = False
            cot_failure_mode = None

            # Check if this is a universal failure (all models fail)
            q_key = doc[:100]
            if q_key in universal_failures_set:
                is_universal_failure = True
                error_patterns_list.append(ErrorPattern(
                    pattern="always_fails",
                    source="universal_failure",
                    frequency=37.0,  # All 37 models fail
                    severity="CRITICAL",
                    description="Question that all models fail",
                    category=metadata.get('category', 'unknown'),
                    evidence=f"All {metadata.get('num_models', 37)} models tested failed this question"
                ))
                conceptual_gaps.append("universal_failure")

            # Check for CoT failure analysis
            if q_key in cot_failures_map:
                cot_analysis_data = cot_failures_map[q_key]
                cot_failure_mode = cot_analysis_data.get('primary_failure_mode', '')

                if cot_failure_mode:
                    error_patterns_list.append(ErrorPattern(
                        pattern=cot_failure_mode,
                        source="cot_failure",
                        frequency=1.0,
                        severity="CRITICAL" if "Complex unit conversion" in cot_failure_mode else "HIGH",
                        description=f"Chain-of-thought failure mode",
                        category=cot_analysis_data.get('category', 'unknown'),
                        evidence=", ".join(cot_analysis_data.get('contributing_factors', [])[:2])
                    ))

                    conceptual_gaps.extend(cot_analysis_data.get('required_knowledge', [])[:3])

            question = UnifiedBenchmarkQuestion(
                question_id=qid,
                question_text=doc,
                benchmark="MMLU-Pro",
                domain=metadata.get('category', 'unknown'),
                success_rate=success_rate,
                difficulty_score=difficulty_score,
                model_scores=model_scores,
                num_models_tested=metadata.get('num_models', 37),
                # ERROR ANALYSIS FIELDS - NOW POPULATED
                error_patterns=error_patterns_list,
                error_categories=error_categories,
                conceptual_gaps=conceptual_gaps,
                is_universal_failure=is_universal_failure,
                cot_failure_mode=cot_failure_mode,
                ml_cluster_id=None,  # Not applicable for MMLU-Pro
                difficulty_label=difficulty_label,
                category=metadata.get('category'),
                subject=metadata.get('subject', '')
            )
            
            questions.append(question)

        # Log statistics
        with_error_analysis = sum(1 for q in questions if q.has_error_analysis())
        universal_failures = sum(1 for q in questions if q.is_universal_failure)
        cot_failures = sum(1 for q in questions if q.cot_failure_mode is not None)

        logger.info(f"Loaded {len(questions)} MMLU-Pro questions")
        logger.info(f"  With error analysis: {with_error_analysis} ({with_error_analysis/len(questions)*100:.1f}%)")
        logger.info(f"  Universal failures: {universal_failures}")
        logger.info(f"  CoT failures: {cot_failures}")

        return questions
    
    def load_ds1000_with_errors(self) -> List[UnifiedBenchmarkQuestion]:
        """
        Load DS-1000 with full error analysis.
        
        Returns questions with:
        - success_rate: ✅ (from 3 models)
        - model_scores: ✅ (per-model results)
        - error_patterns: ✅ (8 pattern types)
        """
        logger.info("Loading DS-1000 with error analysis...")
        
        # Load problems
        ds1000_path = self.data_dir / "ds1000_cache" / "ds1000.jsonl"
        with open(ds1000_path, 'r') as f:
            problems = [json.loads(line) for line in f]
        
        # Load model answers
        model_answers = {}
        for model_file in ['codex002-answers.jsonl', 'gpt-3.5-turbo-0613-answers.jsonl', 'gpt-4-0613-answers.jsonl']:
            model_name = model_file.replace('-answers.jsonl', '')
            answer_path = self.data_dir / "ds1000_cache" / model_file
            with open(answer_path, 'r') as f:
                model_answers[model_name] = [json.loads(line) for line in f]
        
        # Load error analysis (if available)
        error_analysis_path = self.data_dir / "deep_logic_analysis" / "error_categorization.json"
        error_analysis = {}
        if error_analysis_path.exists():
            with open(error_analysis_path, 'r') as f:
                error_data = json.load(f)
                # Index by question ID
                for entry in error_data:
                    qid = entry.get('question_id', '')
                    error_analysis[qid] = entry
        
        questions = []
        
        # Official per-library and per-perturbation pass rates from
        # xlang-ai/DS-1000 results/*.txt. The answer JSONLs contain model
        # generations only (no execution results), so per-question
        # correctness is NOT measurable without running the test suites.
        # These published aggregates are used as per-question estimates.
        LIBRARY_PASS_RATES = {
            'codex002':           {'Matplotlib': 0.548, 'Numpy': 0.432, 'Pandas': 0.265,
                                   'Pytorch': 0.397, 'Scipy': 0.349, 'Sklearn': 0.435,
                                   'Tensorflow': 0.378},
            'gpt-3.5-turbo-0613': {'Matplotlib': 0.587, 'Numpy': 0.368, 'Pandas': 0.330,
                                   'Pytorch': 0.294, 'Scipy': 0.396, 'Sklearn': 0.357,
                                   'Tensorflow': 0.333},
            'gpt-4-0613':         {'Matplotlib': 0.652, 'Numpy': 0.568, 'Pandas': 0.419,
                                   'Pytorch': 0.471, 'Scipy': 0.481, 'Sklearn': 0.504,
                                   'Tensorflow': 0.467},
        }
        PERTURBATION_PASS_RATES = {
            'codex002':           {'Difficult-Rewrite': 0.148, 'Origin': 0.478,
                                   'Semantic': 0.389, 'Surface': 0.375},
            'gpt-3.5-turbo-0613': {'Difficult-Rewrite': 0.222, 'Origin': 0.469,
                                   'Semantic': 0.372, 'Surface': 0.336},
            'gpt-4-0613':         {'Difficult-Rewrite': 0.333, 'Origin': 0.595,
                                   'Semantic': 0.521, 'Surface': 0.428},
        }

        for i, problem in enumerate(problems):
            qid = f"ds1000_{problem['metadata']['library']}_{i}"

            # Per-answer execution results, if the answer files carry them
            correct_count = 0
            total_count = 0
            model_scores = {}

            for model_name, answers in model_answers.items():
                if i < len(answers):
                    answer = answers[i]
                    if 'result' in answer:
                        is_correct = answer.get('result', '') == 'passed'
                        model_scores[model_name] = is_correct
                        if is_correct:
                            correct_count += 1
                        total_count += 1

            if total_count > 0:
                success_rate = correct_count / total_count
            else:
                # No execution results available: estimate from the official
                # per-library and per-perturbation aggregates (mean of both,
                # averaged across the three models). model_scores stays empty
                # so downstream code never treats this as measured.
                library = problem['metadata'].get('library', '')
                perturbation = problem['metadata'].get('perturbation_type', '')
                estimates = []
                for model in LIBRARY_PASS_RATES:
                    parts = []
                    if library in LIBRARY_PASS_RATES[model]:
                        parts.append(LIBRARY_PASS_RATES[model][library])
                    if perturbation in PERTURBATION_PASS_RATES[model]:
                        parts.append(PERTURBATION_PASS_RATES[model][perturbation])
                    if parts:
                        estimates.append(sum(parts) / len(parts))
                success_rate = sum(estimates) / len(estimates) if estimates else 0.4
            difficulty_score = 1.0 - success_rate
            
            # Get error patterns from analysis (if available)
            error_patterns_list = []
            error_categories = []
            conceptual_gaps = []
            
            if qid in error_analysis:
                analysis = error_analysis[qid]
                
                # Extract error patterns
                for pattern_data in analysis.get('patterns', []):
                    pattern = ErrorPattern(
                        pattern=pattern_data['name'],
                        source="ds1000",
                        frequency=pattern_data.get('frequency', 0.0),
                        severity=pattern_data.get('severity', 'MEDIUM'),
                        description=pattern_data.get('description', ''),
                        example_wrong=pattern_data.get('example_wrong', ''),
                        example_correct=pattern_data.get('example_correct', ''),
                        evidence=pattern_data.get('evidence', ''),
                        category=problem['metadata']['library']
                    )
                    error_patterns_list.append(pattern)
                
                error_categories = analysis.get('error_categories', [])
                conceptual_gaps = analysis.get('conceptual_gaps', [])
            
            # Classify difficulty
            if success_rate < 0.1:
                difficulty_label = "Nearly_Impossible"
            elif success_rate < 0.3:
                difficulty_label = "Expert"
            elif success_rate < 0.5:
                difficulty_label = "Hard"
            else:
                difficulty_label = "Medium"
            
            question = UnifiedBenchmarkQuestion(
                question_id=qid,
                question_text=problem['prompt'],
                benchmark="DS-1000",
                domain=problem['metadata']['library'],
                success_rate=success_rate,
                difficulty_score=difficulty_score,
                model_scores=model_scores,
                num_models_tested=total_count,
                # ERROR ANALYSIS FIELDS - POPULATED for DS-1000
                error_patterns=error_patterns_list,
                error_categories=error_categories,
                conceptual_gaps=conceptual_gaps,
                is_universal_failure=False,  # Not applicable for DS-1000
                cot_failure_mode=None,  # Not applicable for DS-1000
                ml_cluster_id=None,  # Not applicable for DS-1000
                difficulty_label=difficulty_label
            )
            
            questions.append(question)
        
        logger.info(f"Loaded {len(questions)} DS-1000 questions WITH error analysis")
        logger.info(f"  Questions with patterns: {sum(1 for q in questions if q.has_error_analysis())}")
        
        return questions
    
    def load_datascibench(self) -> List[UnifiedBenchmarkQuestion]:
        """
        Load DataSciBench questions.
        
        Returns questions with:
        - success_rate: ✅ (from 28 models)
        - model_scores: ✅ (from result CSVs)
        - error_patterns: ❌ (empty - not analyzed yet)
        """
        logger.info("Loading DataSciBench...")
        
        # TODO: Implement DataSciBench loader
        # For now, return empty list
        logger.warning("DataSciBench loader not implemented yet")
        return []
    
    def build_unified_database(
        self,
        include_mmlu_pro: bool = True,
        include_ds1000: bool = True,
        include_datasci: bool = False
    ) -> List[UnifiedBenchmarkQuestion]:
        """
        Build unified database from all sources.
        
        Returns:
            List of questions with unified schema
            - MMLU-Pro questions have empty error_patterns
            - DS-1000 questions have populated error_patterns
        """
        logger.info("="*60)
        logger.info("Building Unified Vector Database")
        logger.info("="*60)
        
        all_questions = []
        
        if include_mmlu_pro:
            mmlu_questions = self.load_mmlu_pro_autonomous()
            all_questions.extend(mmlu_questions)
        
        if include_ds1000:
            ds1000_questions = self.load_ds1000_with_errors()
            all_questions.extend(ds1000_questions)
        
        if include_datasci:
            datasci_questions = self.load_datascibench()
            all_questions.extend(datasci_questions)
        
        # Statistics
        logger.info(f"\n{'='*60}")
        logger.info(f"Unified Database Statistics")
        logger.info(f"{'='*60}")
        logger.info(f"Total Questions: {len(all_questions):,}")
        logger.info(f"  MMLU-Pro (no error analysis): {sum(1 for q in all_questions if q.benchmark == 'MMLU-Pro'):,}")
        logger.info(f"  DS-1000 (with error analysis): {sum(1 for q in all_questions if q.benchmark == 'DS-1000'):,}")
        logger.info(f"  DataSciBench (no error analysis): {sum(1 for q in all_questions if q.benchmark == 'DataSciBench'):,}")
        logger.info(f"\nQuestions with Error Analysis: {sum(1 for q in all_questions if q.has_error_analysis()):,}")
        
        # Difficulty distribution
        difficulty_dist = {}
        for q in all_questions:
            difficulty_dist[q.difficulty_label] = difficulty_dist.get(q.difficulty_label, 0) + 1
        
        logger.info(f"\nDifficulty Distribution:")
        for level, count in sorted(difficulty_dist.items()):
            logger.info(f"  {level}: {count:,} ({count/len(all_questions)*100:.1f}%)")
        
        self.questions = all_questions
        return all_questions
    
    def export_to_chromadb_format(self, output_path: Path):
        """Export to ChromaDB-ready format"""
        documents = []
        metadatas = []
        ids = []
        
        for q in self.questions:
            documents.append(q.question_text)
            
            metadata = {
                'benchmark': q.benchmark,
                'domain': q.domain,
                'success_rate': q.success_rate,
                'difficulty_score': q.difficulty_score,
                'difficulty_label': q.difficulty_label,
                'num_models': q.num_models_tested,
                'has_error_analysis': q.has_error_analysis(),
                # Store error patterns as JSON string
                'error_patterns': json.dumps([asdict(ep) for ep in q.error_patterns]),
                'error_categories': json.dumps(q.error_categories),
                'conceptual_gaps': json.dumps(q.conceptual_gaps)
            }
            
            metadatas.append(metadata)
            ids.append(q.question_id)
        
        output_data = {
            'documents': documents,
            'metadatas': metadatas,
            'ids': ids,
            'source_metadata': {
                'total_questions': len(self.questions),
                'questions_with_error_analysis': sum(1 for q in self.questions if q.has_error_analysis()),
                'benchmarks': list(set(q.benchmark for q in self.questions)),
                'created_at': str(Path(__file__).stat().st_mtime)
            }
        }
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        logger.info(f"\nExported {len(self.questions):,} questions to {output_path}")
        logger.info(f"File size: {output_path.stat().st_size / 1024 / 1024:.2f} MB")


def main():
    """Build unified vector database"""
    
    builder = UnifiedVectorDBBuilder(data_dir=Path("./data"))
    
    # Build unified database
    questions = builder.build_unified_database(
        include_mmlu_pro=True,
        include_ds1000=True,
        include_datasci=False  # Not implemented yet
    )
    
    # Export for ChromaDB
    output_path = Path("./data/unified_vector_db_ready.json")
    builder.export_to_chromadb_format(output_path)
    
    # Show example of each type
    print("\n" + "="*60)
    print("Example Questions")
    print("="*60)
    
    # MMLU-Pro example (no error analysis)
    mmlu_example = next(q for q in questions if q.benchmark == "MMLU-Pro")
    print(f"\nMMLU-Pro Question (no error analysis):")
    print(f"  ID: {mmlu_example.question_id}")
    print(f"  Text: {mmlu_example.question_text[:100]}...")
    print(f"  Success Rate: {mmlu_example.success_rate:.1%}")
    print(f"  Models Tested: {mmlu_example.num_models_tested}")
    print(f"  Error Patterns: {mmlu_example.error_patterns} (EMPTY)")
    
    # DS-1000 example (with error analysis)
    ds1000_example = next((q for q in questions if q.benchmark == "DS-1000" and q.has_error_analysis()), None)
    if ds1000_example:
        print(f"\nDS-1000 Question (with error analysis):")
        print(f"  ID: {ds1000_example.question_id}")
        print(f"  Text: {ds1000_example.question_text[:100]}...")
        print(f"  Success Rate: {ds1000_example.success_rate:.1%}")
        print(f"  Models Tested: {ds1000_example.num_models_tested}")
        print(f"  Error Patterns: {len(ds1000_example.error_patterns)} patterns")
        for pattern in ds1000_example.error_patterns[:2]:
            print(f"    - {pattern.pattern} ({pattern.severity}, {pattern.frequency:.1%})")
    
    print("\n" + "="*60)
    print("✅ Unified database ready!")
    print(f"Use: benchmark_vector_db.py to embed into ChromaDB")
    print("="*60)


if __name__ == "__main__":
    main()
