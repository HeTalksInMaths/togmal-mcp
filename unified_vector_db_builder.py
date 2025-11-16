#!/usr/bin/env python3
"""
Unified Vector Database Builder
================================

Builds a single vector database combining:
1. MMLU-Pro (12K questions, 37 models, NO error analysis)
2. DS-1000 (1K problems, 3 models, WITH error analysis)
3. DataSciBench (222 tasks, 28 models, NO error analysis yet)

Schema supports both types:
- error_patterns: [] (empty for MMLU-Pro/DataSciBench)
- error_patterns: [...] (populated for DS-1000)
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
    """Represents a specific error pattern (DS-1000 only)"""
    pattern: str  # e.g., "mutability_misunderstanding"
    frequency: float  # 0.0 to 1.0
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    example_wrong: str
    example_correct: str
    evidence: str  # "Most common error in DS-1000: 800+ cases"
    
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
    
    # Error analysis (DS-1000 only, empty for others)
    error_patterns: List[ErrorPattern]  # Populated for DS-1000, [] for others
    error_categories: List[str]  # ["missing_method", "wrong_attribute"]
    conceptual_gaps: List[str]  # ["mutability_misunderstanding", ...]
    
    # Metadata
    difficulty_label: str  # "Easy", "Medium", "Hard", "Expert"
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
    
    def load_mmlu_pro_autonomous(self) -> List[UnifiedBenchmarkQuestion]:
        """
        Load MMLU-Pro from autonomous dataset.
        
        Returns questions with:
        - success_rate: ✅ (from 37 models)
        - model_scores: ✅ (per-model results)
        - error_patterns: ❌ (empty list)
        """
        logger.info("Loading MMLU-Pro from autonomous dataset...")
        
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
            
            question = UnifiedBenchmarkQuestion(
                question_id=qid,
                question_text=doc,
                benchmark="MMLU-Pro",
                domain=metadata.get('category', 'unknown'),
                success_rate=success_rate,
                difficulty_score=difficulty_score,
                model_scores=model_scores,
                num_models_tested=metadata.get('num_models', 37),
                # ERROR ANALYSIS FIELDS - EMPTY for MMLU-Pro
                error_patterns=[],  # NO error analysis available
                error_categories=[],  # NO error categories
                conceptual_gaps=[],  # NO conceptual gap analysis
                difficulty_label=difficulty_label,
                category=metadata.get('category'),
                subject=metadata.get('subject', '')
            )
            
            questions.append(question)
        
        logger.info(f"Loaded {len(questions)} MMLU-Pro questions (no error analysis)")
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
        
        for i, problem in enumerate(problems):
            qid = f"ds1000_{problem['metadata']['library']}_{i}"
            
            # Calculate success rate from model answers
            correct_count = 0
            total_count = 0
            model_scores = {}
            
            for model_name, answers in model_answers.items():
                if i < len(answers):
                    answer = answers[i]
                    is_correct = answer.get('result', '') == 'passed'
                    model_scores[model_name] = is_correct
                    if is_correct:
                        correct_count += 1
                    total_count += 1
            
            success_rate = correct_count / total_count if total_count > 0 else 0.0
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
                        frequency=pattern_data.get('frequency', 0.0),
                        severity=pattern_data.get('severity', 'MEDIUM'),
                        example_wrong=pattern_data.get('example_wrong', ''),
                        example_correct=pattern_data.get('example_correct', ''),
                        evidence=pattern_data.get('evidence', '')
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
