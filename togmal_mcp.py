"""
ToGMAL MCP Server - Taxonomy of Generative Model Apparent Limitations

This MCP server provides tools to detect out-of-distribution behaviors and apparent
limitations in LLM interactions, offering safety interventions when needed.

Features:
- Heuristic-based anomaly detection for prompts and responses
- Pattern matching for known problematic scenarios
- Client-side evidence submission for taxonomy building
- Intervention recommendations (step breakdown, human-in-the-loop, web search)
- Privacy-preserving analysis (no LLM judge, deterministic tests)
"""

from mcp.server.fastmcp import FastMCP, Context
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Dict, Any, Literal
from enum import Enum
import re
import json
import hashlib
from datetime import datetime
import math
import os
from togmal_ml_integration import get_ml_detector, combine_detections
from togmal.context_analyzer import analyze_conversation_context
from togmal.ml_tools import get_ml_discovered_tools
from togmal.config import DYNAMIC_TOOLS_ENABLED, CORE_TOOLS, ML_CLUSTERING_ENABLED, ML_TOOLS_MIN_CONFIDENCE

class FeatureExtractor:
    """
    Shim for unpickling models that reference __main__.FeatureExtractor
    Provides minimal methods used by ML-enhanced detection to avoid pickle import errors.
    The pickled object may populate attributes like 'prompt_vectorizer' and 'scaler'.
    """
    def transform_prompts(self, prompts: List[str]):
        # Try to use stored vectorizer/scaler if available
        try:
            pv = getattr(self, "prompt_vectorizer", None)
            sc = getattr(self, "scaler", None)
            if pv is not None:
                X = pv.transform(prompts)
                X_arr = X.toarray() if hasattr(X, "toarray") else X
                if sc is not None:
                    try:
                        X_arr = sc.transform(X_arr)
                    except Exception:
                        # If scaler fails, return unscaled
                        pass
                return X_arr
        except Exception:
            pass
        # Fallback: safe zero features
        try:
            import numpy as np
            return np.zeros((len(prompts), 1))
        except Exception:
            return [[0] for _ in prompts]

# Initialize MCP server
mcp = FastMCP("togmal_mcp")

# ----------------------------------------------------------------------------
# Environment defaults for stdio MCP server
# Ensures consistent behavior when launched by Inspector or other clients
# ----------------------------------------------------------------------------
try:
    # Derive HOME and USER from workspace path
    _workspace = "/Users/hetalksinmaths/togmal"
    _home_default = "/Users/hetalksinmaths"
    _user_default = "hetalksinmaths"
    _venv_bin = f"{_workspace}/.venv/bin"
except Exception:
    _home_default = os.path.expanduser("~")
    _user_default = os.environ.get("USER", "user")
    _venv_bin = os.path.join(os.getcwd(), ".venv", "bin")

# Set common env defaults if missing
os.environ.setdefault("HOME", _home_default)
os.environ.setdefault("USER", _user_default)
os.environ.setdefault("LOGNAME", _user_default)
os.environ.setdefault("SHELL", "/bin/zsh")
# Do not override TERM; leave as provided by client/terminal

# Ensure venv bin is prefixed on PATH
_path_current = os.environ.get("PATH", "")
if _venv_bin and _venv_bin not in _path_current.split(":"):
    os.environ["PATH"] = f"{_venv_bin}:{_path_current}" if _path_current else _venv_bin


# Constants
CHARACTER_LIMIT = 25000
MAX_EVIDENCE_ENTRIES = 1000

# Get absolute paths relative to this script
from pathlib import Path
SCRIPT_DIR = Path(__file__).parent.resolve()
DATA_DIR = SCRIPT_DIR / "data"
MODELS_DIR = SCRIPT_DIR / "models"

# Persistence for taxonomy (in production, this would use persistent storage)
TAXONOMY_FILE = str(DATA_DIR / "taxonomy.json")
os.makedirs(DATA_DIR, exist_ok=True)

DEFAULT_TAXONOMY: Dict[str, List[Dict[str, Any]]] = {
    "math_physics_speculation": [],
    "ungrounded_medical_advice": [],
    "dangerous_file_operations": [],
    "vibe_coding_overreach": [],
    "unsupported_claims": []
}

# Initialize taxonomy and then optionally load from disk
TAXONOMY_DB: Dict[str, List[Dict[str, Any]]] = DEFAULT_TAXONOMY.copy()
try:
    if os.path.exists(TAXONOMY_FILE):
        with open(TAXONOMY_FILE, "r") as f:
            data = json.load(f)
            if isinstance(data, dict):
                for k, v in data.items():
                    if k in TAXONOMY_DB and isinstance(v, list):
                        TAXONOMY_DB[k] = v
except Exception:
    # If loading fails, continue with default taxonomy
    pass

def save_taxonomy() -> None:
    """Persist taxonomy to disk."""
    try:
        with open(TAXONOMY_FILE, "w") as f:
            json.dump(TAXONOMY_DB, f, indent=2, default=str)
    except Exception:
        # Persistence failures should not break tool execution
        pass

# ============================================================================
# ENUMS AND DATA MODELS
# ============================================================================

class RiskLevel(str, Enum):
    """Risk level classification."""
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"
    CRITICAL = "critical"

class InterventionType(str, Enum):
    """Types of safety interventions."""
    STEP_BREAKDOWN = "step_breakdown"
    HUMAN_IN_LOOP = "human_in_loop"
    WEB_SEARCH = "web_search"
    SIMPLIFIED_SCOPE = "simplified_scope"
    NONE = "none"

class CategoryType(str, Enum):
    """Taxonomy categories for limitations."""
    MATH_PHYSICS_SPECULATION = "math_physics_speculation"
    UNGROUNDED_MEDICAL_ADVICE = "ungrounded_medical_advice"
    DANGEROUS_FILE_OPERATIONS = "dangerous_file_operations"
    VIBE_CODING_OVERREACH = "vibe_coding_overreach"
    UNSUPPORTED_CLAIMS = "unsupported_claims"

class ResponseFormat(str, Enum):
    """Output format for tool responses."""
    MARKDOWN = "markdown"
    JSON = "json"

class SubmissionReason(str, Enum):
    """Why this evidence is being submitted."""
    FALSE_NEGATIVE = "false_negative"  # Detection missed a real issue
    FALSE_POSITIVE = "false_positive"  # Incorrectly flagged content
    NEW_PATTERN = "new_pattern"        # Novel limitation pattern not in taxonomy
    LLM_FAILURE = "llm_failure"        # LLM produced problematic output
    EDGE_CASE = "edge_case"            # Boundary case worth documenting

# ============================================================================
# INPUT MODELS
# ============================================================================

class AnalyzePromptInput(BaseModel):
    """Input model for prompt analysis."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )
    
    prompt: str = Field(
        ...,
        description="The user prompt to analyze for potential limitations (e.g., 'Build me a quantum gravity theory', 'Write 5000 lines of code for a social network')",
        min_length=1,
        max_length=50000
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
    )

class AnalyzeResponseInput(BaseModel):
    """Input model for response analysis."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )
    
    response: str = Field(
        ...,
        description="The LLM response to analyze for potential issues (e.g., medical advice, file operations, speculative claims)",
        min_length=1,
        max_length=100000
    )
    context: Optional[str] = Field(
        default=None,
        description="Optional context about the original prompt for better analysis",
        max_length=10000
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
    )

class SubmitEvidenceInput(BaseModel):
    """Input model for submitting evidence of limitations."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )
    
    category: CategoryType = Field(
        ...,
        description="Category of limitation: 'math_physics_speculation', 'ungrounded_medical_advice', 'dangerous_file_operations', 'vibe_coding_overreach', or 'unsupported_claims'"
    )
    prompt: str = Field(
        ...,
        description="The prompt that led to the limitation",
        min_length=1,
        max_length=10000
    )
    response: str = Field(
        ...,
        description="The problematic response from the LLM",
        min_length=1,
        max_length=50000
    )
    description: str = Field(
        ...,
        description="Description of why this is problematic (e.g., 'Made up physics equations', 'Suggested dangerous medication without sources')",
        min_length=10,
        max_length=2000
    )
    severity: RiskLevel = Field(
        ...,
        description="Severity level: 'low', 'moderate', 'high', or 'critical'"
    )
    reason: SubmissionReason = Field(
        ...,
        description="Why this evidence is being submitted (false_negative, false_positive, new_pattern, llm_failure, edge_case)"
    )
    reason_details: Optional[str] = Field(
        default=None,
        description="Optional free-text elaboration about the reason"
    )

class GetTaxonomyInput(BaseModel):
    """Input model for retrieving taxonomy entries."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )
    
    category: Optional[CategoryType] = Field(
        default=None,
        description="Filter by category, or None for all categories"
    )
    min_severity: Optional[RiskLevel] = Field(
        default=None,
        description="Minimum severity level to include"
    )
    limit: int = Field(
        default=20,
        description="Maximum number of entries to return",
        ge=1,
        le=100
    )
    offset: int = Field(
        default=0,
        description="Number of entries to skip for pagination",
        ge=0
    )
    response_format: ResponseFormat = Field(
        default=ResponseFormat.MARKDOWN,
        description="Output format: 'markdown' for human-readable or 'json' for machine-readable"
    )

# ============================================================================
# HELPER FUNCTIONS - HEURISTIC DETECTION
# ============================================================================

def detect_math_physics_speculation(text: str) -> Dict[str, Any]:
    """Detect speculative math/physics theories without proper grounding."""
    patterns = {
        'grand_unification': [
            r'theory of everything',
            r'unified (field )?theory',
            r'grand unification',
            r'quantum gravity (theory|model|solution)',
        ],
        'equation_invention': [
            r'new equation',
            r'i discovered',
            r'my formula',
            r'novel equation',
        ],
        'fundamental_constants': [
            r'(redefine|change|modify) (the )?(gravitational|planck|speed of light)',
            r'new fundamental constant',
        ],
        'particle_invention': [
            r'new particle',
            r'i propose a particle',
            r'undiscovered particle',
        ]
    }
    
    matches = []
    for category, pattern_list in patterns.items():
        for pattern in pattern_list:
            if re.search(pattern, text.lower()):
                matches.append(category)
                break
    
    # Check for excessive use of mathematical notation without context
    math_notation_count = len(re.findall(r'[∂∫∑∏√±×÷≠≈≤≥∞∇⊗⊕]', text))
    if math_notation_count > 20:
        matches.append('excessive_notation')
    
    return {
        'detected': len(matches) > 0,
        'categories': matches,
        'confidence': min(len(matches) * 0.25, 1.0)
    }

def detect_ungrounded_medical_advice(text: str) -> Dict[str, Any]:
    """Detect medical advice that lacks proper sources or qualifications."""
    patterns = {
        'diagnosis_claims': [
            r'you (probably|definitely|likely) have',
            r'sounds like (you have|it\'s)',
            r'this is (clearly|obviously) (a case of)?',
        ],
        'treatment_recommendations': [
            r'you should (take|use|try)',
            r'i recommend (taking|using)',
            r'(the )?(best|recommended) treatment is',
        ],
        'drug_suggestions': [
            r'(take|try) \d+\s?(mg|mcg|ml)',
            r'(start|begin) (taking|with)',
        ],
        'dismissive': [
            r'(don\'t|no need to) (worry|see a doctor)',
            r'(it\'s|that\'s) (nothing|not serious)',
        ]
    }
    
    # Check for medical terms
    medical_terms = [
        'diagnosis', 'treatment', 'medication', 'dosage', 'prescription',
        'disease', 'condition', 'syndrome', 'disorder', 'therapy'
    ]
    
    matches = []
    medical_term_count = sum(1 for term in medical_terms if term in text.lower())
    
    for category, pattern_list in patterns.items():
        for pattern in pattern_list:
            if re.search(pattern, text.lower()):
                matches.append(category)
                break
    
    # Check if sources are cited
    has_sources = bool(re.search(r'(according to|source:|study|research|clinical trial)', text.lower()))
    
    is_problematic = len(matches) > 0 and medical_term_count > 2 and not has_sources
    
    return {
        'detected': is_problematic,
        'categories': matches,
        'medical_term_count': medical_term_count,
        'has_sources': has_sources,
        'confidence': min((len(matches) + medical_term_count / 5) * 0.2, 1.0) if not has_sources else 0.0
    }

def detect_dangerous_file_operations(text: str) -> Dict[str, Any]:
    """Detect potentially dangerous file operations without safeguards."""
    patterns = {
        'mass_deletion': [
            r'(rm|del|delete|remove) (-rf?|/s|all)',
            r'(shutil\.)?rmtree',
            r'delete.*\*',
            r'unlink.*\*',
        ],
        'test_file_operations': [
            r'(rm|del|delete|remove).*test',
            r'delete.*"test"',
        ],
        'recursive_operations': [
            r'(recursive|recursively) (delete|remove)',
            r'walk.*delete',
            r'glob.*delete',
        ],
        'no_confirmation': [
            r'(delete|remove).*(without|no).*(prompt|confirm|ask)',
            r'force.*delete',
        ]
    }
    
    matches = []
    for category, pattern_list in patterns.items():
        for pattern in pattern_list:
            if re.search(pattern, text.lower()):
                matches.append(category)
                break
    
    # Check for safeguards
    has_safeguards = bool(re.search(
        r'(confirm|prompt|ask|verify|check|backup|dry.?run|human.?in.?the.?loop)',
        text.lower()
    ))
    
    is_dangerous = len(matches) > 0 and not has_safeguards
    
    return {
        'detected': is_dangerous,
        'categories': matches,
        'has_safeguards': has_safeguards,
        'confidence': min(len(matches) * 0.3, 1.0) if not has_safeguards else 0.0
    }

def detect_vibe_coding_overreach(text: str) -> Dict[str, Any]:
    """Detect requests for overly ambitious coding projects without proper scoping."""
    patterns = {
        'massive_scope': [
            r'build (me |a )?(complete|full|entire|whole) (app|application|system|platform)',
            r'create.*social network',
            r'make.*operating system',
            r'build.*from scratch',
        ],
        'line_count': [
            r'\d{4,}\s*(lines?|loc)',
            r'(thousand|several thousand|5000|10000).*lines',
        ],
        'everything': [
            r'(all|everything|every) (feature|function|capability)',
            r'complete (implementation|solution)',
        ],
        'unrealistic_timeframe': [
            r'(in|within) (one|a single|5|ten) (minute|hour|day)',
        ]
    }
    
    matches = []
    for category, pattern_list in patterns.items():
        for pattern in pattern_list:
            if re.search(pattern, text.lower()):
                matches.append(category)
                break
    
    # Check for architectural planning words (suggests proper scoping)
    has_planning = bool(re.search(
        r'(architecture|design|plan|structure|module|component|phase|step)',
        text.lower()
    ))
    
    # Extract potential line count
    line_match = re.search(r'(\d+)\s*lines', text.lower())
    estimated_lines = int(line_match.group(1)) if line_match else 0
    
    is_overreach = len(matches) > 0 or estimated_lines > 500
    
    return {
        'detected': is_overreach,
        'categories': matches,
        'estimated_lines': estimated_lines,
        'has_planning': has_planning,
        'confidence': min((len(matches) * 0.25 + (estimated_lines / 1000)) * 0.5, 1.0)
    }

def detect_unsupported_claims(text: str) -> Dict[str, Any]:
    """Detect strong claims without evidence or sources."""
    patterns = {
        'absolute_statements': [
            r'(always|never|definitely|certainly|absolutely|guaranteed)',
            r'(all|every|no) (scientists|experts|doctors|researchers)',
        ],
        'statistical_claims': [
            r'\d+%.*(?!according|source|study)',
            r'(most|majority|minority).*(?!according|source|study)',
        ],
        'future_predictions': [
            r'will (definitely|certainly|surely)',
            r'guaranteed to (happen|work|succeed)',
        ]
    }

    matches = []
    for category, pattern_list in patterns.items():
        for pattern in pattern_list:
            if re.search(pattern, text.lower()):
                matches.append(category)

    # Check for hedging language (shows appropriate uncertainty)
    hedging = bool(re.search(
        r'(may|might|could|possibly|potentially|likely|probably|suggests|indicates)',
        text.lower()
    ))

    # Check for sources
    has_sources = bool(re.search(
        r'(according to|source:|study|research|citation|reference|\[\d+\])',
        text.lower()
    ))

    is_unsupported = len(matches) > 2 and not has_sources and not hedging

    return {
        'detected': is_unsupported,
        'categories': matches,
        'has_hedging': hedging,
        'has_sources': has_sources,
        'confidence': min(len(matches) * 0.15, 1.0) if not (has_sources or hedging) else 0.0
    }

def detect_pandas_code_issues(text: str) -> Dict[str, Any]:
    """Detect common data science code errors based on DS-1000 benchmark analysis.

    This detector identifies 8 critical error patterns discovered from analyzing
    8,934 logic errors across 3 models (Codex, GPT-3.5, GPT-4) on DS-1000 benchmark.

    Patterns detected:
    - mutability_misunderstanding: Missing .copy() (25.6% of errors, 800+ cases)
    - indexing_semantics: .loc vs .iloc confusion (35.8% of errors)
    - vectorization_concept: For-loops instead of vectorized ops (9.6% of errors)
    - api_evolution: Deprecated .values vs .to_numpy() (27.6% of errors)
    - index_persistence: Missing .reset_index() after groupby (21.6% of errors)
    - transformation_pipelines: Incomplete multi-step solutions (28% of errors)
    - method_semantics: Wrong method for task (4.2% of errors)
    - dimensional_operations: Wrong axis parameter (4.0% of errors)
    """

    # Check if this is data science code
    is_pandas_code = bool(re.search(r'(pandas|pd\.|df\[|df\.|dataframe)', text.lower()))
    if not is_pandas_code:
        return {
            'detected': False,
            'categories': [],
            'confidence': 0.0
        }

    matches = []
    details = []

    # 1. Mutability misunderstanding - Missing .copy()
    # THE #1 error in DS-1000 (800+ cases, 25.6% of missing_method errors)
    has_copy = '.copy()' in text
    has_df_modification = bool(re.search(r'(df\[|df\.|\.iloc\[|\.loc\[)', text))

    if has_df_modification and not has_copy:
        matches.append('mutability_misunderstanding')
        details.append({
            'pattern': 'mutability_misunderstanding',
            'severity': 'CRITICAL',
            'message': 'Missing .copy() - DataFrame modifications may affect original data',
            'recommendation': 'Use df.copy() before modifications to avoid unintended side effects',
            'evidence': 'Most common error in DS-1000: 800+ cases (25.6% of errors)',
            'example': 'result = g(df.copy(), List)  # NOT: result = df.iloc[List]'
        })

    # 2. Indexing semantics - .loc vs .iloc confusion
    # 35.8% of errors (wrong_indexing + wrong_attribute)
    iloc_with_strings = bool(re.search(r'\.iloc\[[^\]]*["\'][^\]]*\]', text))
    loc_with_integers = bool(re.search(r'\.loc\[[^\]]*\d+[^\]]*\]', text))

    if iloc_with_strings or loc_with_integers:
        matches.append('indexing_semantics')
        details.append({
            'pattern': 'indexing_semantics',
            'severity': 'HIGH',
            'message': 'Indexing confusion: .iloc[] is position-based, .loc[] is label-based',
            'recommendation': 'Use .loc[] for string labels, .iloc[] for integer positions',
            'evidence': '35.8% of DS-1000 errors involve wrong indexing',
            'example': 'df.loc["row_label"]  # Labels\ndf.iloc[0]  # Positions'
        })

    # 3. Vectorization concept - For-loops over DataFrames
    # 9.6% of errors (overcomplicated)
    has_for_loop = bool(re.search(r'for\s+\w+\s+in\s+(df|dataframe)', text.lower()))
    has_iterrows = bool(re.search(r'\.iterrows\(\)', text))

    if has_for_loop or has_iterrows:
        matches.append('vectorization_concept')
        details.append({
            'pattern': 'vectorization_concept',
            'severity': 'MEDIUM',
            'message': 'For-loop over DataFrame (100x slower than vectorized operations)',
            'recommendation': 'Use vectorized operations (.apply(), .transform(), .agg()) instead of loops',
            'evidence': '9.6% of DS-1000 errors use overcomplicated loops',
            'example': 'df.groupby("col").agg("mean")  # NOT: for group in df...'
        })

    # 4. API evolution - Deprecated .values
    # 27.6% of errors (portion of wrong_attribute)
    uses_values = bool(re.search(r'\.values(?!\s*\()', text))
    uses_to_numpy = '.to_numpy()' in text

    if uses_values and not uses_to_numpy:
        matches.append('api_evolution')
        details.append({
            'pattern': 'api_evolution',
            'severity': 'MEDIUM',
            'message': 'Using deprecated .values - use .to_numpy() instead',
            'recommendation': 'Replace df.values with df.to_numpy() (Pandas best practice)',
            'evidence': '27.6% of DS-1000 errors use wrong attributes (including .values)',
            'example': 'arr = df.to_numpy()  # NOT: arr = df.values'
        })

    # 5. Index persistence - Missing .reset_index() after groupby
    # 21.6% of errors (missing_method)
    has_groupby = '.groupby(' in text
    has_reset_index = '.reset_index()' in text

    if has_groupby and not has_reset_index:
        matches.append('index_persistence')
        details.append({
            'pattern': 'index_persistence',
            'severity': 'HIGH',
            'message': 'groupby without .reset_index() - grouped column becomes index',
            'recommendation': 'Use .reset_index() to convert index back to regular column',
            'evidence': '21.6% of DS-1000 errors involve missing methods (often reset_index)',
            'example': 'df.groupby("col").sum().reset_index()  # Makes "col" a column again'
        })

    # 6. Transformation pipelines - Incomplete solutions
    # 28% of errors (missing_method + incomplete_solution)
    code_lines = len([l for l in text.split('\n') if l.strip() and not l.strip().startswith('#')])
    has_complex_task_keywords = bool(re.search(
        r'(reorder|filter|transform|aggregate|pivot|merge|join|concat)',
        text.lower()
    ))

    if has_complex_task_keywords and code_lines < 3:
        matches.append('transformation_pipelines')
        details.append({
            'pattern': 'transformation_pipelines',
            'severity': 'CRITICAL',
            'message': 'Code appears too short for multi-step transformation task',
            'recommendation': 'Verify all pipeline steps: filter → transform → aggregate → format',
            'evidence': '28% of DS-1000 errors are incomplete pipelines',
            'example': 'df.filter() → .transform() → .aggregate() → .reset_index()'
        })

    # 7. Method semantics - .replace() vs .apply() confusion
    # 4.2% of errors (wrong_method)
    has_replace = '.replace(' in text
    has_conditional = bool(re.search(r'(if|lambda|apply)', text))

    if has_replace and has_conditional:
        matches.append('method_semantics')
        details.append({
            'pattern': 'method_semantics',
            'severity': 'MEDIUM',
            'message': 'Using .replace() with conditional logic - consider .apply() instead',
            'recommendation': 'Use .apply(lambda) for conditional transformations, .replace() for simple mappings',
            'evidence': '4.2% of DS-1000 errors use wrong methods',
            'example': 'df["col"].apply(lambda x: x if condition else "other")'
        })

    # 8. Dimensional operations - Missing axis parameter
    # 4.0% of errors (wrong_parameter)
    has_concat_join = bool(re.search(r'(concat|join|merge)\(', text))
    has_axis = 'axis=' in text

    if has_concat_join and not has_axis:
        matches.append('dimensional_operations')
        details.append({
            'pattern': 'dimensional_operations',
            'severity': 'MEDIUM',
            'message': 'concat/join without axis parameter - defaults to axis=0 (rows)',
            'recommendation': 'Explicitly specify axis=0 (rows) or axis=1 (columns)',
            'evidence': '4.0% of DS-1000 errors involve wrong/missing parameters',
            'example': 'pd.concat([df1, df2], axis=1)  # axis=1 for column-wise'
        })

    # Calculate confidence
    confidence = 0.0
    if matches:
        # Weight by severity
        critical_count = sum(1 for d in details if d['severity'] == 'CRITICAL')
        high_count = sum(1 for d in details if d['severity'] == 'HIGH')
        medium_count = sum(1 for d in details if d['severity'] == 'MEDIUM')

        confidence = min(
            (critical_count * 0.4 + high_count * 0.3 + medium_count * 0.2),
            1.0
        )

    return {
        'detected': len(matches) > 0,
        'categories': matches,
        'details': details,
        'confidence': confidence,
        'ds1000_coverage': f"{len(matches)} of 8 common patterns detected" if matches else None
    }

# ============================================================================
# HELPER FUNCTIONS - INTERVENTION RECOMMENDATIONS
# ============================================================================

def recommend_interventions(analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Recommend appropriate interventions based on analysis results."""
    interventions = []

    # Math/physics speculation -> step breakdown + web search
    if analysis_results['math_physics']['detected']:
        interventions.append({
            'type': InterventionType.STEP_BREAKDOWN,
            'reason': 'Complex theoretical physics/math requires step-by-step verification',
            'suggestion': 'Break down the theory into testable components and verify each against established physics'
        })
        interventions.append({
            'type': InterventionType.WEB_SEARCH,
            'reason': 'Claims should be validated against peer-reviewed literature',
            'suggestion': 'Search for existing research on similar theories and fundamental physics principles'
        })

    # Medical advice -> human in loop + web search
    if analysis_results['medical_advice']['detected']:
        interventions.append({
            'type': InterventionType.HUMAN_IN_LOOP,
            'reason': 'Medical decisions require professional oversight',
            'suggestion': 'Consult with a qualified healthcare professional before acting on this advice'
        })
        interventions.append({
            'type': InterventionType.WEB_SEARCH,
            'reason': 'Medical recommendations should cite authoritative sources',
            'suggestion': 'Search for peer-reviewed medical literature and clinical guidelines'
        })

    # Dangerous file operations -> human in loop + simplified scope
    if analysis_results['file_operations']['detected']:
        interventions.append({
            'type': InterventionType.HUMAN_IN_LOOP,
            'reason': 'Destructive file operations are irreversible',
            'suggestion': 'Implement confirmation prompts before executing any delete operations'
        })
        interventions.append({
            'type': InterventionType.STEP_BREAKDOWN,
            'reason': 'File operations should be explicit and reviewable',
            'suggestion': 'Show exactly which files will be affected before proceeding'
        })

    # Vibe coding -> step breakdown + simplified scope
    if analysis_results['vibe_coding']['detected']:
        interventions.append({
            'type': InterventionType.SIMPLIFIED_SCOPE,
            'reason': 'Overly ambitious scope leads to poor quality and maintainability',
            'suggestion': 'Start with a minimal viable product focusing on core functionality'
        })
        interventions.append({
            'type': InterventionType.STEP_BREAKDOWN,
            'reason': 'Large projects need proper architectural planning',
            'suggestion': 'Create a phased implementation plan with clear milestones'
        })

    # Unsupported claims -> web search
    if analysis_results['unsupported_claims']['detected']:
        interventions.append({
            'type': InterventionType.WEB_SEARCH,
            'reason': 'Claims need verification from authoritative sources',
            'suggestion': 'Search for credible sources to support or refute these claims'
        })

    # Pandas code issues -> step breakdown + web search (for documentation)
    if analysis_results.get('pandas_code', {}).get('detected'):
        pandas_details = analysis_results['pandas_code'].get('details', [])

        # Add specific interventions based on detected patterns
        critical_patterns = [d for d in pandas_details if d['severity'] == 'CRITICAL']
        if critical_patterns:
            interventions.append({
                'type': InterventionType.STEP_BREAKDOWN,
                'reason': 'Data science code has critical issues that may cause subtle bugs',
                'suggestion': 'Review code step-by-step, testing each transformation on sample data'
            })

        # If multiple patterns detected, recommend documentation review
        if len(pandas_details) >= 2:
            interventions.append({
                'type': InterventionType.WEB_SEARCH,
                'reason': 'Multiple pandas anti-patterns detected - review best practices',
                'suggestion': 'Search Pandas documentation for correct usage of detected methods'
            })

    return interventions

def calculate_risk_level(analysis_results: Dict[str, Any]) -> RiskLevel:
    """Calculate overall risk level from analysis results."""
    risk_score = 0.0

    # Weight different types of issues
    if analysis_results['math_physics']['detected']:
        risk_score += analysis_results['math_physics']['confidence'] * 0.5

    if analysis_results['medical_advice']['detected']:
        risk_score += analysis_results['medical_advice']['confidence'] * 1.5  # Higher weight

    if analysis_results['file_operations']['detected']:
        risk_score += analysis_results['file_operations']['confidence'] * 2.0  # Highest weight

    if analysis_results['vibe_coding']['detected']:
        risk_score += analysis_results['vibe_coding']['confidence'] * 0.4

    if analysis_results['unsupported_claims']['detected']:
        risk_score += analysis_results['unsupported_claims']['confidence'] * 0.3

    # Pandas code issues - weight based on evidence from DS-1000
    if analysis_results.get('pandas_code', {}).get('detected'):
        pandas_confidence = analysis_results['pandas_code'].get('confidence', 0.0)
        # Moderate weight - data science bugs can be subtle but impactful
        risk_score += pandas_confidence * 1.0

    # ML enhancement contribution
    if analysis_results.get('ml', {}).get('detected'):
        risk_score += analysis_results['ml'].get('confidence', 0.0) * 0.3

    # Map score to risk level
    if risk_score >= 1.5:
        return RiskLevel.CRITICAL
    elif risk_score >= 1.0:
        return RiskLevel.HIGH
    elif risk_score >= 0.5:
        return RiskLevel.MODERATE
    else:
        return RiskLevel.LOW

def format_analysis_markdown(analysis: Dict[str, Any]) -> str:
    """Format analysis results as markdown."""
    output = []
    
    output.append(f"# ToGMAL Analysis Report\n")
    output.append(f"**Risk Level:** {analysis['risk_level'].upper()}\n")
    output.append(f"**Analysis Type:** {analysis['type']}\n\n")
    
    # Detection results
    output.append("## Detection Results\n")
    
    if analysis['math_physics']['detected']:
        output.append(f"### ⚠️ Math/Physics Speculation Detected")
        output.append(f"- **Confidence:** {analysis['math_physics']['confidence']:.2%}")
        output.append(f"- **Categories:** {', '.join(analysis['math_physics']['categories'])}\n")
    
    if analysis['medical_advice']['detected']:
        output.append(f"### 🏥 Ungrounded Medical Advice Detected")
        output.append(f"- **Confidence:** {analysis['medical_advice']['confidence']:.2%}")
        output.append(f"- **Categories:** {', '.join(analysis['medical_advice']['categories'])}")
        output.append(f"- **Has Sources:** {'Yes' if analysis['medical_advice']['has_sources'] else 'No'}\n")
    
    if analysis['file_operations']['detected']:
        output.append(f"### 💾 Dangerous File Operations Detected")
        output.append(f"- **Confidence:** {analysis['file_operations']['confidence']:.2%}")
        output.append(f"- **Categories:** {', '.join(analysis['file_operations']['categories'])}")
        output.append(f"- **Has Safeguards:** {'Yes' if analysis['file_operations']['has_safeguards'] else 'No'}\n")
    
    if analysis['vibe_coding']['detected']:
        output.append(f"### 💻 Vibe Coding Overreach Detected")
        output.append(f"- **Confidence:** {analysis['vibe_coding']['confidence']:.2%}")
        output.append(f"- **Categories:** {', '.join(analysis['vibe_coding']['categories'])}")
        if analysis['vibe_coding']['estimated_lines'] > 0:
            output.append(f"- **Estimated Lines:** {analysis['vibe_coding']['estimated_lines']}\n")
    
    if analysis['unsupported_claims']['detected']:
        output.append(f"### 📊 Unsupported Claims Detected")
        output.append(f"- **Confidence:** {analysis['unsupported_claims']['confidence']:.2%}")
        output.append(f"- **Has Hedging:** {'Yes' if analysis['unsupported_claims']['has_hedging'] else 'No'}")
        output.append(f"- **Has Sources:** {'Yes' if analysis['unsupported_claims']['has_sources'] else 'No'}\n")
    
    # Pandas code issues (DS-1000 patterns)
    if analysis.get('pandas_code', {}).get('detected'):
        pandas = analysis['pandas_code']
        output.append(f"### 🐼 Data Science Code Issues Detected (DS-1000 Patterns)")
        output.append(f"- **Confidence:** {pandas['confidence']:.2%}")
        output.append(f"- **Coverage:** {pandas.get('ds1000_coverage', 'N/A')}")

        details = pandas.get('details', [])
        if details:
            output.append(f"\n**Detected Patterns:**\n")
            for detail in details:
                severity_emoji = {'CRITICAL': '🔴', 'HIGH': '🟠', 'MEDIUM': '🟡'}.get(detail['severity'], '⚪')
                output.append(f"{severity_emoji} **{detail['severity']}**: {detail['message']}")
                output.append(f"   - **Recommendation:** {detail['recommendation']}")
                output.append(f"   - **Evidence:** {detail['evidence']}")
                output.append(f"   - **Example:** `{detail['example']}`\n")

    # ML Clustering results (if available)
    if 'ml' in analysis:
        output.append(f"### 🤖 ML Clustering Signal")
        output.append(f"- **Detected:** {'Yes' if analysis['ml'].get('detected') else 'No'}")
        output.append(f"- **Confidence:** {analysis['ml'].get('confidence', 0.0):.2%}")
        if 'cluster_id' in analysis['ml']:
            output.append(f"- **Cluster ID:** {analysis['ml'].get('cluster_id', -1)}")
        if 'is_dangerous_cluster' in analysis['ml']:
            output.append(f"- **Dangerous Cluster:** {'Yes' if analysis['ml'].get('is_dangerous_cluster') else 'No'}\n")


    # Recommendations
    if analysis['interventions']:
        output.append("\n## Recommended Interventions\n")
        for i, intervention in enumerate(analysis['interventions'], 1):
            output.append(f"### {i}. {intervention['type'].replace('_', ' ').title()}")
            output.append(f"**Reason:** {intervention['reason']}")
            output.append(f"**Suggestion:** {intervention['suggestion']}\n")

    if not any([
        analysis['math_physics']['detected'],
        analysis['medical_advice']['detected'],
        analysis['file_operations']['detected'],
        analysis['vibe_coding']['detected'],
        analysis['unsupported_claims']['detected'],
        analysis.get('pandas_code', {}).get('detected')
    ]):
        output.append("\n✅ No significant issues detected. The content appears to be within normal parameters.\n")

    return '\n'.join(output)

# ============================================================================
# MCP TOOLS
# ============================================================================

@mcp.tool(
    name="togmal_analyze_prompt",
    annotations={
        "title": "Analyze Prompt for Potential Limitations",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }  # type: ignore[arg-type]
)
async def analyze_prompt(params: AnalyzePromptInput) -> str:
    """Analyze a user prompt for potential out-of-distribution behaviors and apparent limitations.
    
    This tool performs deterministic heuristic analysis to detect:
    - Speculative math/physics theories (theory of everything, quantum gravity, etc.)
    - Requests for medical diagnoses or treatment advice
    - Dangerous file operations (mass deletion, recursive removal)
    - Vibe coding overreach (overly ambitious scope, thousands of lines)
    - Unsupported claims requiring verification
    
    The analysis is privacy-preserving (no external API calls) and provides intervention
    recommendations when issues are detected.
    
    Args:
        params (AnalyzePromptInput): Input parameters containing:
            - prompt (str): The user prompt to analyze
            - response_format (str): Output format ('markdown' or 'json')
    
    Returns:
        str: Analysis results with risk level, detected issues, and intervention recommendations
    """
    
    # Run all detection heuristics
    analysis_results = {
        'type': 'prompt_analysis',
        'math_physics': detect_math_physics_speculation(params.prompt),
        'medical_advice': detect_ungrounded_medical_advice(params.prompt),
        'file_operations': detect_dangerous_file_operations(params.prompt),
        'vibe_coding': detect_vibe_coding_overreach(params.prompt),
        'unsupported_claims': detect_unsupported_claims(params.prompt),
        'pandas_code': detect_pandas_code_issues(params.prompt)
    }

    # Optional ML enhancement
    try:
        ml_detector = get_ml_detector(models_dir=str(MODELS_DIR))
        analysis_results['ml'] = ml_detector.analyze_prompt_ml(params.prompt)
    except Exception:
        analysis_results['ml'] = {'detected': False, 'confidence': 0.0, 'method': 'ml_clustering_unavailable'}

    # Calculate risk level
    analysis_results['risk_level'] = calculate_risk_level(analysis_results)

    # Get intervention recommendations
    analysis_results['interventions'] = recommend_interventions(analysis_results)
    
    # Format response
    if params.response_format == ResponseFormat.JSON:
        result = json.dumps(analysis_results, indent=2, default=str)
    else:
        result = format_analysis_markdown(analysis_results)
    
    # Check character limit
    if len(result) > CHARACTER_LIMIT:
        truncated = result[:CHARACTER_LIMIT]
        result = truncated + f"\n\n[Truncated at {CHARACTER_LIMIT} characters. Use JSON format for complete results.]"
    
    return result

@mcp.tool(
    name="togmal_analyze_response",
    annotations={
        "title": "Analyze LLM Response for Issues",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }  # type: ignore[arg-type]
)
async def analyze_response(params: AnalyzeResponseInput) -> str:
    """Analyze an LLM response for potential issues and limitation indicators.
    
    This tool examines responses for:
    - Ungrounded medical advice without proper sources
    - Speculative physics/math claims
    - Dangerous file operation instructions without safeguards
    - Unsupported statistical or factual claims
    - Over-confident predictions without hedging
    
    Particularly useful for detecting when an LLM has given advice on:
    - Medical diagnoses or treatments (should have human oversight)
    - Destructive file operations (should have confirmations)
    - Speculative scientific theories (should cite sources)
    
    Args:
        params (AnalyzeResponseInput): Input parameters containing:
            - response (str): The LLM response to analyze
            - context (Optional[str]): Original prompt context
            - response_format (str): Output format ('markdown' or 'json')
    
    Returns:
        str: Analysis results with detected issues and recommended safety interventions
    """
    
    # Combine response with context for better analysis
    text_to_analyze = params.response
    if params.context:
        text_to_analyze = f"{params.context}\n\n{params.response}"
    
    # Run all detection heuristics
    analysis_results = {
        'type': 'response_analysis',
        'math_physics': detect_math_physics_speculation(text_to_analyze),
        'medical_advice': detect_ungrounded_medical_advice(text_to_analyze),
        'file_operations': detect_dangerous_file_operations(text_to_analyze),
        'vibe_coding': detect_vibe_coding_overreach(text_to_analyze),
        'unsupported_claims': detect_unsupported_claims(text_to_analyze),
        'pandas_code': detect_pandas_code_issues(text_to_analyze)
    }

    # Optional ML enhancement
    try:
        ml_detector = get_ml_detector(models_dir=str(MODELS_DIR))
        if params.context:
            analysis_results['ml'] = ml_detector.analyze_pair_ml(params.context, params.response)
        else:
            analysis_results['ml'] = ml_detector.analyze_prompt_ml(text_to_analyze)
    except Exception:
        analysis_results['ml'] = {'detected': False, 'confidence': 0.0, 'method': 'ml_clustering_unavailable'}

    # Calculate risk level
    analysis_results['risk_level'] = calculate_risk_level(analysis_results)

    # Get intervention recommendations
    analysis_results['interventions'] = recommend_interventions(analysis_results)
    
    # Format response
    if params.response_format == ResponseFormat.JSON:
        result = json.dumps(analysis_results, indent=2, default=str)
    else:
        result = format_analysis_markdown(analysis_results)
    
    # Check character limit
    if len(result) > CHARACTER_LIMIT:
        truncated = result[:CHARACTER_LIMIT]
        result = truncated + f"\n\n[Truncated at {CHARACTER_LIMIT} characters. Use JSON format for complete results.]"
    
    return result

@mcp.tool(
    name="togmal_submit_evidence",
    annotations={
        "title": "Submit Evidence of LLM Limitation",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }  # type: ignore[arg-type]
)
async def submit_evidence(params: SubmitEvidenceInput, ctx: Context = None) -> str:
    """Submit evidence of an LLM limitation to build the taxonomy database.
    
    This tool allows users to contribute examples of problematic LLM behaviors to improve
    the detection system. All submissions are stored with metadata and can be retrieved
    for analysis and pattern detection.
    
    Use this when you encounter:
    - LLM generating speculative physics/math without proper grounding
    - Medical advice that lacks sources or professional disclaimers
    - Code that performs dangerous file operations without confirmations
    - Overly confident claims without evidence
    - Any other concerning out-of-distribution behavior
    
    The system will prompt for confirmation before submitting to ensure intentional reporting.
    
    Args:
        params (SubmitEvidenceInput): Evidence details containing:
            - category (CategoryType): Type of limitation
            - prompt (str): The prompt that triggered the issue
            - response (str): The problematic LLM response
            - description (str): Why this is problematic
            - severity (RiskLevel): How severe the issue is
    
    Returns:
        str: Confirmation of submission with assigned entry ID
    """
    
    # Try to request confirmation from user (human-in-the-loop) if context available
    if ctx is not None:
        try:
            confirmation = await ctx.elicit(
                prompt=f"You are about to submit evidence of a '{params.category}' limitation with severity '{params.severity}' and reason '{params.reason}'. This will be added to the taxonomy database. Confirm submission? (yes/no)",
                input_type="text"
            )  # type: ignore[call-arg]
            
            if confirmation.lower() not in ['yes', 'y']:
                return "Evidence submission cancelled by user."
        except Exception:
            # If elicit fails (e.g., in some MCP clients), proceed without confirmation
            pass
    
    # Check if taxonomy is getting too large
    total_entries = sum(len(entries) for entries in TAXONOMY_DB.values())
    if total_entries >= MAX_EVIDENCE_ENTRIES:
        return json.dumps({
            "status": "error",
            "message": f"Taxonomy database is at capacity ({MAX_EVIDENCE_ENTRIES} entries). Cannot accept new submissions."
        }, indent=2)
    
    # Create evidence entry
    entry_id = hashlib.sha256(
        f"{params.category}{params.prompt}{params.response}{datetime.now().isoformat()}".encode()
    ).hexdigest()[:12]
    
    evidence_entry = {
        'id': entry_id,
        'category': params.category,
        'prompt': params.prompt,
        'response': params.response,
        'description': params.description,
        'severity': params.severity,
        'reason': params.reason,
        'reason_details': params.reason_details,
        'timestamp': datetime.now().isoformat(),
        'prompt_hash': hashlib.sha256(params.prompt.encode()).hexdigest()[:8]
    }
    
    # Add to taxonomy
    TAXONOMY_DB[params.category].append(evidence_entry)
    save_taxonomy()
    
    result = {
        'status': 'success',
        'entry_id': entry_id,
        'category': params.category,
        'severity': params.severity,
        'total_entries_in_category': len(TAXONOMY_DB[params.category]),
        'message': 'Evidence successfully submitted to taxonomy database'
    }
    
    return json.dumps(result, indent=2)

@mcp.tool(
    name="togmal_get_taxonomy",
    annotations={
        "title": "Retrieve Taxonomy Entries",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }  # type: ignore[arg-type]
)
async def get_taxonomy(params: GetTaxonomyInput) -> str:
    """Retrieve entries from the taxonomy database of LLM limitations.
    
    This tool provides access to the accumulated evidence of LLM limitations, allowing
    analysis of patterns and trends. Useful for:
    - Understanding common failure modes
    - Training improved detection heuristics
    - Research into LLM behavior patterns
    - Building better safety interventions
    
    Results can be filtered by category and severity, and support pagination for
    large result sets.
    
    Args:
        params (GetTaxonomyInput): Query parameters containing:
            - category (Optional[CategoryType]): Filter by limitation type
            - min_severity (Optional[RiskLevel]): Minimum severity to include
            - limit (int): Maximum entries to return (1-100)
            - offset (int): Pagination offset
            - response_format (str): Output format ('markdown' or 'json')
    
    Returns:
        str: Filtered taxonomy entries with pagination information
    """
    
    # Collect relevant entries
    all_entries = []
    
    if params.category:
        # Filter by category
        all_entries = TAXONOMY_DB.get(params.category, [])
    else:
        # Get all entries
        for entries in TAXONOMY_DB.values():
            all_entries.extend(entries)
    
    # Filter by severity if specified
    if params.min_severity:
        severity_order = {
            RiskLevel.LOW: 0,
            RiskLevel.MODERATE: 1,
            RiskLevel.HIGH: 2,
            RiskLevel.CRITICAL: 3
        }
        min_level = severity_order[params.min_severity]
        all_entries = [
            e for e in all_entries
            if severity_order.get(e['severity'], 0) >= min_level
        ]
    
    # Sort by timestamp (newest first)
    all_entries.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    
    # Apply pagination
    total_count = len(all_entries)
    paginated_entries = all_entries[params.offset:params.offset + params.limit]
    
    # Prepare response
    response_data = {
        'total': total_count,
        'count': len(paginated_entries),
        'offset': params.offset,
        'limit': params.limit,
        'has_more': total_count > params.offset + params.limit,
        'next_offset': params.offset + params.limit if total_count > params.offset + params.limit else None,
        'entries': paginated_entries
    }
    
    # Format output
    if params.response_format == ResponseFormat.JSON:
        result = json.dumps(response_data, indent=2, default=str)
    else:
        # Markdown format
        output = []
        output.append("# ToGMAL Taxonomy Database\n")
        output.append(f"**Total Entries:** {total_count}")
        output.append(f"**Showing:** {len(paginated_entries)} entries (offset: {params.offset})")
        if response_data['has_more']:
            output.append(f"**More Available:** Use offset={response_data['next_offset']} to see more\n")
        output.append("")
        
        for i, entry in enumerate(paginated_entries, 1):
            output.append(f"## Entry {params.offset + i}: {entry['id']}")
            output.append(f"- **Category:** {entry['category']}")
            output.append(f"- **Severity:** {entry['severity']}")
            output.append(f"- **Timestamp:** {entry['timestamp']}")
            output.append(f"- **Description:** {entry['description']}")
            output.append(f"- **Prompt Hash:** {entry['prompt_hash']}")
            output.append(f"- **Reason:** {entry.get('reason', 'N/A')}")
            if entry.get('reason_details'):
                output.append(f"- **Reason Details:** {entry['reason_details']}")
            output.append("")
        
        result = '\n'.join(output)
    
    # Check character limit
    if len(result) > CHARACTER_LIMIT:
        truncated = result[:CHARACTER_LIMIT]
        result = truncated + f"\n\n[Truncated at {CHARACTER_LIMIT} characters. Reduce limit or use offset parameter.]"
    
    return result

@mcp.tool(
    name="togmal_get_statistics",
    annotations={
        "title": "Get Taxonomy Statistics",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }  # type: ignore[arg-type]
)
async def get_statistics(response_format: ResponseFormat = ResponseFormat.MARKDOWN) -> str:
    """Get statistical overview of the taxonomy database.
    
    Provides aggregate statistics about the taxonomy including:
    - Total entries by category
    - Severity distribution
    - Most common limitation patterns
    - Temporal trends
    
    Useful for understanding the landscape of LLM limitations and identifying
    areas where additional safety measures are most needed.
    
    Args:
        response_format (ResponseFormat): Output format ('markdown' or 'json')
    
    Returns:
        str: Statistical summary of taxonomy database
    """
    
    # Calculate statistics
    stats = {
        'total_entries': sum(len(entries) for entries in TAXONOMY_DB.values()),
        'by_category': {},
        'by_severity': {
            'low': 0,
            'moderate': 0,
            'high': 0,
            'critical': 0
        },
        'database_capacity': MAX_EVIDENCE_ENTRIES
    }
    
    for category, entries in TAXONOMY_DB.items():
        stats['by_category'][category] = len(entries)
        for entry in entries:
            severity = entry.get('severity', 'low')
            stats['by_severity'][severity] = stats['by_severity'].get(severity, 0) + 1
    
    # Format output
    if response_format == ResponseFormat.JSON:
        return json.dumps(stats, indent=2)
    else:
        output = []
        output.append("# ToGMAL Taxonomy Statistics\n")
        output.append(f"**Total Entries:** {stats['total_entries']} / {stats['database_capacity']}\n")
        
        output.append("## Entries by Category\n")
        for category, count in stats['by_category'].items():
            percentage = (count / stats['total_entries'] * 100) if stats['total_entries'] > 0 else 0
            output.append(f"- **{category}:** {count} ({percentage:.1f}%)")
        
        output.append("\n## Entries by Severity\n")
        for severity, count in stats['by_severity'].items():
            percentage = (count / stats['total_entries'] * 100) if stats['total_entries'] > 0 else 0
            output.append(f"- **{severity.title()}:** {count} ({percentage:.1f}%)")
        
        return '\n'.join(output)

# ============================================================================
# DYNAMIC CHECKS TOOL
# ============================================================================

@mcp.tool(
    name="togmal_get_recommended_checks",
    annotations={
        "title": "Get Recommended Checks Based on Conversation Context",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }  # type: ignore[arg-type]
)
async def get_recommended_checks(
    conversation_history: Optional[List[Dict[str, str]]] = None,
    user_context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Recommend which ToGMAL checks are most relevant given the conversation context.
    Returns JSON with detected domains and recommended checks.
    """
    if not DYNAMIC_TOOLS_ENABLED:
        return json.dumps({
            "mode": "static",
            "recommended_tools": ["togmal_analyze_prompt", "togmal_analyze_response", "togmal_get_taxonomy", "togmal_get_statistics"],
            "recommended_checks": ["math_physics_speculation", "ungrounded_medical_advice", "dangerous_file_operations", "vibe_coding_overreach", "unsupported_claims"]
        }, indent=2)

    domains = await analyze_conversation_context(
        conversation_history=conversation_history,
        user_context=user_context
    )

    # Map domains to internal checks
    domain_to_checks = {
        "mathematics": ["math_physics_speculation"],
        "physics": ["math_physics_speculation"],
        "medicine": ["ungrounded_medical_advice"],
        "healthcare": ["ungrounded_medical_advice"],
        "coding": ["vibe_coding_overreach", "dangerous_file_operations", "unsupported_claims"],
        "file_system": ["dangerous_file_operations"],
        "finance": ["unsupported_claims"],
        "law": ["unsupported_claims"]
    }

    checks = set()
    for d in domains:
        for c in domain_to_checks.get(d, []):
            checks.add(c)

    # Core checks are always available via analyze tools
    if not checks:
        checks.update(["unsupported_claims"])

    response = {
        "mode": "dynamic",
        "domains_detected": domains,
        "recommended_tools": ["togmal_analyze_prompt", "togmal_analyze_response"],
        "core_tools": CORE_TOOLS,
        "recommended_checks": sorted(list(checks)),
        "ml_tools_enabled": ML_CLUSTERING_ENABLED
    }

    return json.dumps(response, indent=2)

# ============================================================================
# LIST TOOLS DYNAMIC ENDPOINT
# ============================================================================

@mcp.tool(
    name="togmal_list_tools_dynamic",
    annotations={
        "title": "List Tools Dynamically Based on Context",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }  # type: ignore[arg-type]
)
async def togmal_list_tools_dynamic(
    conversation_history: Optional[List[Dict[str, str]]] = None,
    user_context: Optional[Dict[str, Any]] = None
) -> str:
    """
    Return a context-filtered list of MCP tools and checks to use.
    Also includes optional ML-discovered pattern IDs if enabled and available.
    """
    # Base tool names (MCP tools provided by this server)
    base_tools = [
        "togmal_analyze_prompt",
        "togmal_analyze_response",
        "togmal_get_taxonomy",
        "togmal_get_statistics",
        "togmal_check_prompt_difficulty"  # New vector DB tool
    ]

    # Detect domains
    domains = await analyze_conversation_context(
        conversation_history=conversation_history,
        user_context=user_context
    )

    # Map domains to internal checks
    domain_to_checks = {
        "mathematics": ["math_physics_speculation"],
        "physics": ["math_physics_speculation"],
        "medicine": ["ungrounded_medical_advice"],
        "healthcare": ["ungrounded_medical_advice"],
        "coding": ["vibe_coding_overreach", "dangerous_file_operations", "unsupported_claims"],
        "file_system": ["dangerous_file_operations"],
        "finance": ["unsupported_claims"],
        "law": ["unsupported_claims"]
    }

    checks = set()
    for d in domains:
        for c in domain_to_checks.get(d, []):
            checks.add(c)

    if not checks:
        checks.update(["unsupported_claims"])  # sensible default

    # Optionally include ML-discovered patterns
    ml_patterns: List[str] = []
    if ML_CLUSTERING_ENABLED:
        try:
            ml_tools = await get_ml_discovered_tools(
                relevant_domains=domains or None,
                min_confidence=ML_TOOLS_MIN_CONFIDENCE
            )
            # Return pattern IDs (strip the "check_" prefix)
            ml_patterns = [t["name"].replace("check_", "") for t in ml_tools]
        except Exception:
            ml_patterns = []

    response = {
        "mode": "dynamic",
        "domains_detected": domains,
        "tool_names": base_tools,
        "check_names": sorted(list(checks)),
        "ml_patterns": ml_patterns,
        "core_tools": CORE_TOOLS
    }

    return json.dumps(response, indent=2)


@mcp.tool(
    name="togmal_check_prompt_difficulty",
    annotations={
        "title": "Check Prompt Difficulty Using Vector Similarity",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }  # type: ignore[arg-type]
)
async def togmal_check_prompt_difficulty(
    prompt: str,
    k: int = 5,
    domain_filter: Optional[str] = None
) -> str:
    """
    Check if a prompt is similar to hard benchmark questions using vector similarity.
    
    Uses a vector database of benchmark questions (GPQA, MMLU-Pro, MATH) to find
    the k most similar questions and compute a weighted difficulty score.
    
    Args:
        prompt: The user's prompt/question to check
        k: Number of similar benchmark questions to retrieve (default: 5)
        domain_filter: Optional domain filter (e.g., 'physics', 'mathematics')
    
    Returns:
        JSON with difficulty assessment, similar questions, and recommendations
    """
    try:
        from benchmark_vector_db import BenchmarkVectorDB
        from pathlib import Path
        
        # Validate inputs
        if not prompt or not prompt.strip():
            return json.dumps({
                "error": "Invalid input",
                "message": "Prompt cannot be empty"
            }, indent=2)
        
        if k < 1 or k > 20:
            return json.dumps({
                "error": "Invalid input",
                "message": "k must be between 1 and 20"
            }, indent=2)
        
        # Initialize vector DB (uses persistent storage)
        db = BenchmarkVectorDB(
            db_path=DATA_DIR / "benchmark_vector_db",
            embedding_model="all-MiniLM-L6-v2"
        )
        
        # Check if database is populated
        stats = db.get_statistics()
        if stats.get("total_questions", 0) == 0:
            return json.dumps({
                "error": "Vector database not initialized",
                "message": "Run 'python benchmark_vector_db.py' to build the database first",
                "hint": "The database should be in ./data/benchmark_vector_db/"
            }, indent=2)
        
        # Query similar questions
        result = db.query_similar_questions(
            prompt=prompt,
            k=k,
            domain_filter=domain_filter
        )
        
        # Add metadata
        result["database_stats"] = stats
        result["query_params"] = {
            "k": k,
            "domain_filter": domain_filter
        }
        
        # Convert numpy types to native Python types for JSON serialization
        def convert_to_serializable(obj):
            """Convert numpy/other types to JSON-serializable types"""
            try:
                import numpy as np
                if isinstance(obj, np.integer):
                    return int(obj)
                elif isinstance(obj, np.floating):
                    return float(obj)
                elif isinstance(obj, np.ndarray):
                    return obj.tolist()
            except ImportError:
                pass
            
            if isinstance(obj, dict):
                return {k: convert_to_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_to_serializable(item) for item in obj]
            return obj
        
        result = convert_to_serializable(result)
        
        return json.dumps(result, indent=2, ensure_ascii=False)
        
    except ImportError as e:
        return json.dumps({
            "error": "Dependencies not installed",
            "message": "Run: uv pip install sentence-transformers chromadb datasets",
            "details": str(e)
        }, indent=2)
    except Exception as e:
        import traceback
        return json.dumps({
            "error": "Failed to check prompt difficulty",
            "message": str(e),
            "traceback": traceback.format_exc()
        }, indent=2)

# ============================================================================
# SERVER ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Preload ML models into memory if available
    try:
        get_ml_detector(models_dir=str(MODELS_DIR))
    except Exception:
        pass
    mcp.run()
