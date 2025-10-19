#!/usr/bin/env python3
"""
Test if we can actually access OpenLLM Leaderboard per-question results
"""

from datasets import load_dataset

print("Testing access to OpenLLM Leaderboard detailed results...")
print("="*80)

# Test model
model = "meta-llama__Meta-Llama-3-70B-Instruct"

print(f"\nTrying to load: open-llm-leaderboard/details_{model}")
print("Config: harness_mmlu_5")

try:
    results = load_dataset(
        f"open-llm-leaderboard/details_{model}",
        "harness_mmlu_5"
    )
    
    print(f"\n✓ SUCCESS! Loaded dataset")
    print(f"Available splits: {list(results.keys())}")
    
    # Check if 'latest' split exists
    if 'latest' in results:
        latest = results['latest']
        print(f"Latest split has {len(latest)} rows")
        
        # Show first few rows
        print(f"\nFirst 3 rows:")
        for i, row in enumerate(latest[:3]):
            print(f"\nRow {i}:")
            print(f"  Keys: {list(row.keys())}")
            if 'doc_id' in row:
                print(f"  doc_id: {row['doc_id']}")
            if 'pred' in row:
                print(f"  pred: {row['pred']}")
            if 'target' in row:
                print(f"  target: {row['target']}")
            
            # Check if correct
            if 'pred' in row and 'target' in row:
                is_correct = (row['pred'] == row['target'])
                print(f"  Correct: {'✓' if is_correct else '✗'}")
    
    print("\n" + "="*80)
    print("✓ Per-question data IS available!")
    print("="*80)
    
except Exception as e:
    print(f"\n✗ FAILED: {e}")
    print("\nTrying alternative configs...")
    
    # Try other possible configs
    for config in ["harness_mmlu_pro_5", "harness_gpqa_0", "results"]:
        try:
            print(f"\nTrying config: {config}")
            results = load_dataset(f"open-llm-leaderboard/details_{model}", config)
            print(f"  ✓ {config} works! Splits: {list(results.keys())}")
        except Exception as e2:
            print(f"  ✗ {config} failed: {e2}")
