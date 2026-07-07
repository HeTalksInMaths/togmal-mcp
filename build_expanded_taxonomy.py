#!/usr/bin/env python3
"""
Build Expanded Taxonomy
=======================

Generates a comprehensive, data-driven taxonomy of LLM limitations from the
unified benchmark database (13,000 questions, 39 models) plus the enrichment
analyses. Everything is derived from measured model behavior — no hand-waving.

Sections produced:
 1. domain_risk_profiles   — per-domain success, difficulty mix, SOTA gap
 2. subject_risk_index     — fine-grained per-subject risk (100+ subjects)
 3. universal_failures     — questions ALL models fail
 4. near_universal_failures— success rate < 5%
 5. deceptive_questions    — SOTA models fail where the field succeeds
 6. cot_failure_modes      — chain-of-thought failure aggregates
 7. code_error_patterns    — DS-1000 patterns (from comprehensive analysis)
 8. semantic_danger_clusters — ML-discovered clusters of hard questions
                               (MiniBatchKMeans over TF-IDF vectors)
 9. risk_keywords          — terms statistically over-represented in
                             hard questions (log-odds), per domain

Outputs:
    data/expanded_taxonomy.json
    EXPANDED_TAXONOMY.md  (human-readable summary, committed)
"""

import json
import math
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import numpy as np

DATA = Path("./data")
RISKY_THRESHOLD = 0.6
HARD_THRESHOLD = 0.35
N_CLUSTERS = 30


def load_inputs():
    unified = json.load(open(DATA / "unified_database_complete.json"))
    dataset = json.load(open(DATA / "autonomous_benchmarks/autonomous_dataset.json"))
    cot = {}
    comp = {}
    cot_path = DATA / "cot_failure_analysis.json"
    comp_path = DATA / "comprehensive_error_patterns.json"
    if cot_path.exists():
        cot = json.load(open(cot_path))
    if comp_path.exists():
        comp = json.load(open(comp_path))
    return unified, dataset, cot, comp


def sota_model_names(dataset, threshold=0.55):
    return {
        m['name'] for m in dataset['metadata']['models']
        if m.get('accuracy', 0) >= threshold
    }


def domain_risk_profiles(questions, sota_names):
    profiles = {}
    by_domain = defaultdict(list)
    for q in questions:
        by_domain[q['domain']].append(q)

    for domain, qs in by_domain.items():
        rates = [q['success_rate'] for q in qs]
        sota_rates, overall_rates = [], []
        for q in qs:
            scores = q.get('model_scores') or {}
            sota_scores = [v for m, v in scores.items() if m in sota_names]
            if sota_scores and scores:
                sota_rates.append(sum(sota_scores) / len(sota_scores))
                overall_rates.append(sum(scores.values()) / len(scores))

        difficulty = Counter(q.get('difficulty_label', 'unknown') for q in qs)
        hardest = sorted(qs, key=lambda q: q['success_rate'])[:3]

        profiles[domain] = {
            'question_count': len(qs),
            'avg_success_rate': round(float(np.mean(rates)), 4),
            'median_success_rate': round(float(np.median(rates)), 4),
            'pct_risky': round(sum(1 for r in rates if r < RISKY_THRESHOLD) / len(rates), 4),
            'pct_nearly_impossible': round(sum(1 for r in rates if r < 0.2) / len(rates), 4),
            'sota_avg_success': round(float(np.mean(sota_rates)), 4) if sota_rates else None,
            'sota_lift_over_field': (
                round(float(np.mean(sota_rates) - np.mean(overall_rates)), 4)
                if sota_rates else None),
            'difficulty_distribution': dict(difficulty),
            'hardest_examples': [
                {'question_id': q['question_id'],
                 'success_rate': q['success_rate'],
                 'text': q['question_text'][:160]}
                for q in hardest
            ],
        }
    return dict(sorted(profiles.items(), key=lambda kv: kv[1]['avg_success_rate']))


def subject_risk_index(dataset):
    by_subject = defaultdict(list)
    for q in dataset['questions']:
        subject = (q.get('metadata') or {}).get('subject') or 'unknown'
        subject = subject.replace('ori_mmlu-', '').replace('stemez-', '')
        by_subject[subject].append(q['success_rate'])

    index = {}
    for subject, rates in by_subject.items():
        if len(rates) < 5:
            continue
        index[subject] = {
            'question_count': len(rates),
            'avg_success_rate': round(float(np.mean(rates)), 4),
            'pct_risky': round(sum(1 for r in rates if r < RISKY_THRESHOLD) / len(rates), 4),
        }
    return dict(sorted(index.items(), key=lambda kv: kv[1]['avg_success_rate']))


def universal_and_near_universal(questions):
    universal, near = [], []
    for q in questions:
        scores = q.get('model_scores') or {}
        entry = {
            'question_id': q['question_id'],
            'domain': q['domain'],
            'benchmark': q['benchmark'],
            'success_rate': q['success_rate'],
            'num_models': len(scores),
            'text': q['question_text'][:200],
        }
        if scores and not any(scores.values()):
            universal.append(entry)
        elif 0 < q['success_rate'] < 0.05:
            near.append(entry)
    return universal, near


def deceptive_questions(questions, sota_names, max_items=50):
    """SOTA models fail where the broader field does noticeably better —
    signals questions that mislead stronger reasoning or contain traps."""
    out = []
    for q in questions:
        scores = q.get('model_scores') or {}
        sota = [v for m, v in scores.items() if m in sota_names]
        rest = [v for m, v in scores.items() if m not in sota_names]
        if len(sota) >= 3 and len(rest) >= 5:
            sota_rate = sum(sota) / len(sota)
            rest_rate = sum(rest) / len(rest)
            if sota_rate <= 0.35 and rest_rate - sota_rate >= 0.2:
                out.append({
                    'question_id': q['question_id'],
                    'domain': q['domain'],
                    'sota_success': round(sota_rate, 3),
                    'field_success': round(rest_rate, 3),
                    'gap': round(rest_rate - sota_rate, 3),
                    'text': q['question_text'][:200],
                })
    out.sort(key=lambda e: -e['gap'])
    return out[:max_items]


def cot_failure_modes(cot):
    analyses = cot.get('analyses', [])
    by_mode = defaultdict(list)
    factor_counts = Counter()
    for a in analyses:
        by_mode[a.get('primary_failure_mode', 'unknown')].append(a)
        factor_counts.update(a.get('contributing_factors', []))
    return {
        'modes': {
            mode: {
                'count': len(items),
                'avg_reasoning_steps': round(float(np.mean(
                    [len(i.get('reasoning_steps') or []) for i in items])), 1),
                'examples': [i.get('question', '')[:160] for i in items[:3]],
            }
            for mode, items in sorted(by_mode.items(), key=lambda kv: -len(kv[1]))
        },
        'contributing_factors': dict(factor_counts.most_common(15)),
    }


def semantic_danger_clusters(questions):
    """Cluster hard questions and name clusters by their top TF-IDF terms.

    Uses the standard LSA recipe (TF-IDF -> TruncatedSVD -> normalize ->
    KMeans): full-dimensional sparse KMeans collapses into one giant cluster
    plus outlier singletons.
    """
    from sklearn.cluster import KMeans
    from sklearn.decomposition import TruncatedSVD
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.preprocessing import normalize

    hard = [q for q in questions if q['success_rate'] < HARD_THRESHOLD]
    texts = [q['question_text'] for q in hard]
    print(f"  Clustering {len(hard):,} hard questions (success < {HARD_THRESHOLD}) "
          f"into {N_CLUSTERS} clusters...")

    vec = TfidfVectorizer(max_features=15000, stop_words='english',
                          ngram_range=(1, 2), sublinear_tf=True)
    X = vec.fit_transform(texts)

    svd = TruncatedSVD(n_components=150, random_state=42)
    X_lsa = normalize(svd.fit_transform(X))

    km = KMeans(n_clusters=N_CLUSTERS, random_state=42, n_init=10)
    labels = km.fit_predict(X_lsa)
    terms = np.array(vec.get_feature_names_out())

    # Map centroids back to term space for naming
    term_centroids = svd.inverse_transform(km.cluster_centers_)

    clusters = []
    for c in range(N_CLUSTERS):
        members = [hard[i] for i in range(len(hard)) if labels[i] == c]
        if not members:
            continue
        top_terms = terms[np.argsort(term_centroids[c])[::-1][:10]].tolist()
        rates = [m['success_rate'] for m in members]
        domains = Counter(m['domain'] for m in members)
        clusters.append({
            'cluster_id': int(c),
            'label': ', '.join(top_terms[:4]),
            'top_terms': top_terms,
            'size': len(members),
            'avg_success_rate': round(float(np.mean(rates)), 4),
            'domains': dict(domains.most_common(5)),
            'examples': [m['question_text'][:160] for m in members[:2]],
        })
    # Singleton/tiny clusters are outliers, not topics — report sizable ones
    # first (by difficulty), tiny ones last
    sizable = sorted((c for c in clusters if c['size'] >= 20),
                     key=lambda c: c['avg_success_rate'])
    tiny = sorted((c for c in clusters if c['size'] < 20),
                  key=lambda c: c['avg_success_rate'])
    return sizable + tiny


def risk_keywords(questions, top_n=40):
    """Terms over-represented in risky questions vs safe ones (log-odds with
    +1 smoothing). Candidate triggers for future Tier-1 improvements.

    Computed separately for prose (MMLU-Pro) and code (DS-1000) — otherwise
    code tokens dominate because nearly all DS-1000 questions are risky.
    """
    from sklearn.feature_extraction.text import CountVectorizer

    def log_odds_terms(risky_texts, safe_texts):
        if len(risky_texts) < 20 or len(safe_texts) < 20:
            return []
        vec = CountVectorizer(max_features=20000, stop_words='english', min_df=10)
        all_counts = vec.fit_transform(risky_texts + safe_texts)
        n_risky = len(risky_texts)
        risky_counts = np.asarray(all_counts[:n_risky].sum(axis=0)).ravel()
        safe_counts = np.asarray(all_counts[n_risky:].sum(axis=0)).ravel()
        log_odds = (np.log((risky_counts + 1) / (risky_counts.sum() + 1))
                    - np.log((safe_counts + 1) / (safe_counts.sum() + 1)))
        terms = vec.get_feature_names_out()
        order = np.argsort(log_odds)[::-1][:top_n]
        return [
            {'term': terms[i],
             'log_odds': round(float(log_odds[i]), 3),
             'risky_count': int(risky_counts[i]),
             'safe_count': int(safe_counts[i])}
            for i in order
        ]

    out = {}
    for name, bench in (('prose', 'MMLU-Pro'), ('code', 'DS-1000')):
        subset = [q for q in questions if q['benchmark'] == bench]
        out[name] = log_odds_terms(
            [q['question_text'] for q in subset if q['success_rate'] < RISKY_THRESHOLD],
            [q['question_text'] for q in subset if q['success_rate'] >= RISKY_THRESHOLD],
        )
    return out


def write_markdown(tax, path=Path("EXPANDED_TAXONOMY.md")):
    lines = [
        "# Expanded Taxonomy of LLM Limitations",
        "",
        f"Generated {tax['metadata']['generated_at'][:10]} from "
        f"{tax['metadata']['total_questions']:,} benchmark questions "
        f"({tax['metadata']['num_models']} models). All figures are measured.",
        "",
        "## Domain Risk Profiles (hardest first)",
        "",
        "| Domain | Questions | Avg Success | % Risky | % Nearly Impossible | SOTA Lift |",
        "|--------|-----------|-------------|---------|---------------------|-----------|",
    ]
    for d, p in tax['domain_risk_profiles'].items():
        lift = f"+{p['sota_lift_over_field']:.0%}" if p['sota_lift_over_field'] else "—"
        lines.append(
            f"| {d} | {p['question_count']:,} | {p['avg_success_rate']:.1%} "
            f"| {p['pct_risky']:.0%} | {p['pct_nearly_impossible']:.0%} | {lift} |")

    lines += ["", "## Riskiest Subjects (≥5 questions)", "",
              "| Subject | Questions | Avg Success |",
              "|---------|-----------|-------------|"]
    for s, p in list(tax['subject_risk_index'].items())[:25]:
        lines.append(f"| {s} | {p['question_count']} | {p['avg_success_rate']:.1%} |")

    lines += ["", f"## Universal Failures ({len(tax['universal_failures'])} questions all "
              f"{tax['metadata']['num_models']} models fail)", ""]
    for u in tax['universal_failures'][:10]:
        lines.append(f"- **{u['domain']}**: {u['text'][:120]}…")

    sizable = [c for c in tax['semantic_danger_clusters'] if c['size'] >= 20]
    lines += ["", f"## Semantic Danger Clusters ({len(sizable)} ML-discovered topic "
              "clusters of hard questions, hardest first)", "",
              "| Cluster | Size | Avg Success | Top Domains |",
              "|---------|------|-------------|-------------|"]
    for c in sizable[:20]:
        doms = ', '.join(list(c['domains'])[:2])
        lines.append(f"| {c['label']} | {c['size']} | {c['avg_success_rate']:.1%} | {doms} |")

    lines += ["", "## Chain-of-Thought Failure Modes", ""]
    for mode, m in tax['cot_failure_modes'].get('modes', {}).items():
        lines.append(f"- **{mode}**: {m['count']} questions "
                     f"(avg {m['avg_reasoning_steps']} reasoning steps)")
    factors = tax['cot_failure_modes'].get('contributing_factors', {})
    if factors:
        lines += ["", "Contributing factors: " +
                  ', '.join(f"{k} ({v})" for k, v in list(factors.items())[:8])]

    lines += ["", "## Deceptive Questions (SOTA fails, field succeeds)", "",
              f"{len(tax['deceptive_questions'])} questions where strong models "
              "underperform weaker ones by ≥20 points — likely traps or "
              "misleading phrasing.", ""]
    for dq in tax['deceptive_questions'][:5]:
        lines.append(f"- **{dq['domain']}** (SOTA {dq['sota_success']:.0%} vs field "
                     f"{dq['field_success']:.0%}): {dq['text'][:120]}…")

    lines += ["", "## Top Risk Keywords (log-odds, risky vs safe questions)", "",
              "**Prose (MMLU-Pro):** " +
              ', '.join(f"`{k['term']}`" for k in tax['risk_keywords'].get('prose', [])[:25]),
              "",
              "**Code (DS-1000):** " +
              ', '.join(f"`{k['term']}`" for k in tax['risk_keywords'].get('code', [])[:25]),
              ""]

    path.write_text('\n'.join(lines))
    print(f"✅ Markdown summary: {path}")


def main():
    print("Loading inputs...")
    unified, dataset, cot, comp = load_inputs()
    questions = unified['questions']
    sota = sota_model_names(dataset)
    print(f"  {len(questions):,} questions, {len(sota)} SOTA models: {sorted(sota)}")

    print("Building domain risk profiles...")
    domains = domain_risk_profiles(questions, sota)
    print("Building subject risk index...")
    subjects = subject_risk_index(dataset)
    print("Extracting universal failures...")
    universal, near_universal = universal_and_near_universal(questions)
    print(f"  {len(universal)} universal, {len(near_universal)} near-universal")
    print("Finding deceptive questions...")
    deceptive = deceptive_questions(questions, sota)
    print(f"  {len(deceptive)} deceptive questions")
    print("Aggregating CoT failure modes...")
    cot_modes = cot_failure_modes(cot)
    print("Clustering hard questions...")
    clusters = semantic_danger_clusters(questions)
    print("Extracting risk keywords...")
    keywords = risk_keywords(questions)

    taxonomy = {
        'metadata': {
            'generated_at': datetime.now().isoformat(),
            'total_questions': len(questions),
            'num_models': dataset['metadata']['num_models'],
            'sota_models': sorted(sota),
            'risky_threshold': RISKY_THRESHOLD,
            'hard_threshold': HARD_THRESHOLD,
        },
        'domain_risk_profiles': domains,
        'subject_risk_index': subjects,
        'universal_failures': universal,
        'near_universal_failures': near_universal,
        'deceptive_questions': deceptive,
        'cot_failure_modes': cot_modes,
        'code_error_patterns': comp.get('all_patterns', comp),
        'semantic_danger_clusters': clusters,
        'risk_keywords': keywords,
    }

    out = DATA / "expanded_taxonomy.json"
    with open(out, 'w') as f:
        json.dump(taxonomy, f, indent=2)
    print(f"✅ Saved {out} ({out.stat().st_size / 1024:.0f} KB)")

    write_markdown(taxonomy)


if __name__ == '__main__':
    main()
