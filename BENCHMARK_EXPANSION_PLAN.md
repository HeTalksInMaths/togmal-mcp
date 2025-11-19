# Benchmark Data Expansion Plan - CRITICAL GAP

**Date:** 2025-11-19  
**Priority:** 🔴 HIGH - Current bottleneck

---

## 🚨 The Problem

**Current state:**
- Questions in database: 13,100 (MMLU-Pro)
- Questions with LLM performance data: **170** ❌ ONLY 170!

**Impact:**
- Phase 2 meta-learner trained on only 100 questions
- Most user queries have NO similar benchmarks  
- Predictor falls back to meta-features only
- Limited domain coverage

---

## 🎯 Solution: Expand to 5,000+ Questions

**Available benchmarks:**
- MATH: 12,500 questions (✅ HuggingFace)
- HumanEval: 164 (✅ HuggingFace)
- MBPP: 974 (✅ HuggingFace)
- GSM8K: 8,500 (✅ HuggingFace)
- More from OpenLLM Leaderboard

**Immediate action:**
1. Run `expand_benchmark_data.py` (fetch questions)
2. Run `fetch_real_benchmark_data.py` (get LLM results)
3. Integrate into performance DB
4. Retrain meta-predictor

**Timeline:** 10-12 hours of work for 1,500+ questions
