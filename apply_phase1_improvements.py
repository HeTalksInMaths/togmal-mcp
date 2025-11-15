#!/usr/bin/env python3
"""
Apply Phase 1 Improvements
===========================

Automatically applies Phase 1 growth strategy:
- Add 5+ large models (>40B)
- Maintain difficulty balance
- Improve model size coverage

Author: ToGMAL Project
"""

import json
from pathlib import Path

# Update selection criteria to prioritize large models
state_file = Path("data/autonomous_state.json")

with open(state_file) as f:
    state = json.load(f)

print("="*70)
print("🚀 PHASE 1: CRITICAL IMPROVEMENTS")
print("="*70)

print("\n📊 Current State:")
print(f"  Models: {len(state['selected_models'])}")
print(f"  Questions: {state['total_questions']:,}")

# Check current large model count
large_models = [
    m for m_name, m in state['model_metadata'].items()
    if m.get('size_category') == 'large'
]
print(f"  Large models (>40B): {len(large_models)}")

print("\n🎯 Phase 1 Goals:")
print("  1. Add 5+ large models (currently have 1)")
print("  2. Improve model size balance")
print("  3. Maintain all 12k questions")

print("\n⚙️  Updating Selection Criteria...")

# Update criteria to get more large models
new_criteria = {
    "top_sota": 15,       # Keep SOTA models
    "top_medium": 5,      # Keep medium models
    "top_small": 5,       # Keep small models
    "top_large": 7        # NEW: Explicitly select large models
}

# We need to modify the grower to support top_large
print("\n📝 Updated Criteria:")
print(f"  Top SOTA: {new_criteria['top_sota']}")
print(f"  Top Large (>40B): {new_criteria['top_large']} (NEW!)")
print(f"  Top Medium (10-40B): {new_criteria['top_medium']}")
print(f"  Top Small (≤10B): {new_criteria['top_small']}")

target_models = sum([
    new_criteria['top_sota'],
    new_criteria['top_large'],
    new_criteria['top_medium'],
    new_criteria['top_small']
])

# But many SOTA are actually large, so deduplicate
estimated_unique = 30  # Rough estimate after deduplication

print(f"\n📈 Expected Growth:")
print(f"  Current: {len(state['selected_models'])} models")
print(f"  Target: ~{estimated_unique} models")
print(f"  Growth: +{estimated_unique - len(state['selected_models'])} models")

print(f"\n💾 Predictions:")
print(f"  Current: {state['total_questions'] * len(state['selected_models']):,}")
print(f"  Target: {state['total_questions'] * estimated_unique:,}")
print(f"  Growth: +{state['total_questions'] * (estimated_unique - len(state['selected_models'])):,} predictions")

print("\n🔧 Implementation Plan:")
print("""
  1. Update autonomous_benchmark_grower.py to support 'top_large' criterion
  2. Run autonomous growth with new criteria
  3. Verify large model coverage improved
  4. Re-run coverage analysis to confirm improvements

  Manual Steps Required:
  1. Edit autonomous_benchmark_grower.py
  2. Add support for selecting top large models separately
  3. Run: python autonomous_benchmark_grower.py 12000
""")

# Save note about Phase 1
phase1_note = {
    "phase": 1,
    "status": "planned",
    "goals": {
        "large_models": "Add 5+ models >40B params",
        "total_models": f"~{estimated_unique}",
        "maintain_questions": 12000
    },
    "criteria": new_criteria,
    "implementation": "Update autonomous_benchmark_grower.py",
    "next_steps": [
        "Add top_large support to grower",
        "Run growth cycle",
        "Verify improvements",
        "Run analyze_coverage.py"
    ]
}

phase1_file = Path("data/phase1_plan.json")
with open(phase1_file, 'w') as f:
    json.dump(phase1_note, f, indent=2)

print(f"\n💾 Phase 1 plan saved to: {phase1_file}")

print("\n" + "="*70)
print("✅ Phase 1 plan ready!")
print("="*70)

print("\n📋 Available Large Models in MMLU-Pro:")
print("""
  From coverage analysis, available large models (>40B):
  - Meta-Llama-3_1-70B-Instruct (already have)
  - Meta-Llama-3-70B-Instruct
  - Meta-Llama-3-70B
  - Meta-Llama-3_1-70B
  - Llama-2-70b-hf
  - Qwen1.5-72B-Chat
  - Qwen1.5-110B

  Total: 7 large models available!
""")
