#!/usr/bin/env python3
"""
Test 10 Sample Questions Through the Predictor
===============================================

Run diverse questions through the trained predictor and analyze:
1. Prediction accuracy
2. Confidence scores
3. Similar questions found
4. Credibility of predictions
"""

import json
import numpy as np
from pathlib import Path
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def load_predictor():
    """Load the trained predictor (trained on full 13k dataset)"""

    # Load data
    with open('data/unified_database_with_real_mle.json') as f:
        unified_db = json.load(f)

    with open('data/model_performance_database.json') as f:
        perf_db = json.load(f)

    # Extract ALL failure rates
    failure_rates = {}

    # From unified DB (13k questions)
    for q in unified_db['questions']:
        qid = str(q['question_id'])
        if 'success_rate' in q and q['success_rate'] is not None:
            failure_rate = 1.0 - q['success_rate']
            failure_rates[qid] = failure_rate

    # Override with performance DB (252 questions, 170 duplicates)
    for qid, data in perf_db['questions'].items():
        if 'failure_rate' in data:
            failure_rates[str(qid)] = data['failure_rate']
        else:
            correct_count = sum(1 for m, r in data.items()
                              if isinstance(r, dict) and r.get('is_correct', False))
            total_count = sum(1 for m, r in data.items()
                            if isinstance(r, dict) and 'is_correct' in r)
            if total_count > 0:
                failure_rates[str(qid)] = 1.0 - (correct_count / total_count)

    # Split into train/test (use same seed as before)
    all_questions = [q for q in unified_db['questions']
                    if str(q['question_id']) in failure_rates]

    np.random.seed(42)
    indices = np.random.permutation(len(all_questions))
    n_test = int(len(all_questions) * 0.2)
    train_indices = indices[n_test:]

    train_questions = [all_questions[i] for i in train_indices]

    # Train TF-IDF
    vectorizer = TfidfVectorizer(
        max_features=2000,
        ngram_range=(1, 2),
        min_df=1,
        stop_words='english'
    )

    train_texts = [q.get('question_text', '') for q in train_questions]
    train_vectors = vectorizer.fit_transform(train_texts)

    train_failure_rates = {
        str(q['question_id']): failure_rates[str(q['question_id'])]
        for q in train_questions
    }

    return {
        'vectorizer': vectorizer,
        'train_vectors': train_vectors,
        'train_questions': train_questions,
        'train_failure_rates': train_failure_rates,
        'all_failure_rates': failure_rates
    }


def predict(predictor, query_text, top_k=20):
    """Make a prediction for a query"""

    # Transform query
    query_vector = predictor['vectorizer'].transform([query_text])

    # Find similar
    similarities = cosine_similarity(query_vector, predictor['train_vectors'])[0]
    top_indices = np.argsort(similarities)[::-1][:top_k]

    # Get similar questions with rates
    similar = []
    for idx in top_indices:
        train_qid = str(predictor['train_questions'][idx]['question_id'])
        sim = similarities[idx]

        if train_qid in predictor['train_failure_rates'] and sim > 0:
            fr = predictor['train_failure_rates'][train_qid]
            similar.append({
                'qid': train_qid,
                'similarity': float(sim),
                'failure_rate': fr,
                'text': predictor['train_questions'][idx].get('question_text', '')[:100],
                'domain': predictor['train_questions'][idx].get('domain', 'unknown'),
                'benchmark': predictor['train_questions'][idx].get('benchmark', 'unknown')
            })

    # Weighted average
    if similar:
        total_weight = sum(s['similarity'] for s in similar)
        weighted_sum = sum(s['similarity'] * s['failure_rate'] for s in similar)

        pred_fr = weighted_sum / total_weight if total_weight > 0 else 0.5
        confidence = total_weight / top_k
    else:
        pred_fr = 0.5
        confidence = 0.0

    return {
        'predicted_failure_rate': pred_fr,
        'confidence': confidence,
        'n_similar': len(similar),
        'top_5_similar': similar[:5]
    }


def main():
    print("="*80)
    print("TESTING 10 SAMPLE QUESTIONS")
    print("="*80)

    # Load predictor
    print("\nLoading predictor...")
    predictor = load_predictor()
    print(f"  Trained on {len(predictor['train_questions']):,} questions")

    # Load test questions
    with open('data/unified_database_with_real_mle.json') as f:
        unified_db = json.load(f)

    # Select 10 diverse test questions
    np.random.seed(42)

    # Get test set
    all_questions = [q for q in unified_db['questions']
                    if str(q['question_id']) in predictor['all_failure_rates']]

    indices = np.random.permutation(len(all_questions))
    n_test = int(len(all_questions) * 0.2)
    test_indices = indices[:n_test]
    test_questions = [all_questions[i] for i in test_indices]

    # Select 10 diverse samples from test set
    # Get different domains and difficulty levels
    samples = []

    # Get easy, medium, hard from different domains
    domains_covered = set()
    difficulties = []

    for q in test_questions:
        domain = q.get('domain', 'unknown')
        qid = str(q['question_id'])

        if qid in predictor['all_failure_rates']:
            actual_fr = predictor['all_failure_rates'][qid]

            # Categorize difficulty
            if actual_fr < 0.3:
                difficulty = 'easy'
            elif actual_fr < 0.7:
                difficulty = 'medium'
            else:
                difficulty = 'hard'

            # Try to get diverse samples
            if domain not in domains_covered or difficulty not in difficulties:
                samples.append(q)
                domains_covered.add(domain)
                difficulties.append(difficulty)

                if len(samples) >= 10:
                    break

    # Fill remaining with random
    if len(samples) < 10:
        for q in test_questions:
            if q not in samples:
                samples.append(q)
                if len(samples) >= 10:
                    break

    print(f"\nSelected {len(samples)} test questions")
    print(f"Domains covered: {domains_covered}")

    # Test each question
    results = []

    for i, q in enumerate(samples, 1):
        qid = str(q['question_id'])
        actual_fr = predictor['all_failure_rates'][qid]

        print(f"\n{'='*80}")
        print(f"SAMPLE {i}/10")
        print(f"{'='*80}")

        print(f"\nQuestion ID: {qid}")
        print(f"Domain: {q.get('domain', 'unknown')}")
        print(f"Benchmark: {q.get('benchmark', 'unknown')}")
        print(f"Text: {q.get('question_text', '')[:150]}...")
        print(f"\nActual failure rate: {actual_fr:.1%}")

        # Predict
        prediction = predict(predictor, q.get('question_text', ''))

        pred_fr = prediction['predicted_failure_rate']
        confidence = prediction['confidence']

        print(f"Predicted failure rate: {pred_fr:.1%}")
        print(f"Error: {abs(pred_fr - actual_fr):.1%}")
        print(f"Confidence: {confidence:.3f}")
        print(f"Similar questions found: {prediction['n_similar']}")

        print(f"\nTop 3 most similar questions:")
        for j, sim_q in enumerate(prediction['top_5_similar'][:3], 1):
            print(f"\n  {j}. Similarity: {sim_q['similarity']:.3f}")
            print(f"     Failure rate: {sim_q['failure_rate']:.1%}")
            print(f"     Domain: {sim_q['domain']}")
            print(f"     Text: {sim_q['text']}...")

        # Analyze credibility
        print(f"\n📊 CREDIBILITY ANALYSIS:")

        # Error magnitude
        error = abs(pred_fr - actual_fr)
        if error < 0.10:
            error_rating = "✅ Excellent (< 10% error)"
        elif error < 0.20:
            error_rating = "✅ Good (< 20% error)"
        elif error < 0.30:
            error_rating = "⚠️  Fair (< 30% error)"
        else:
            error_rating = "❌ Poor (> 30% error)"

        print(f"  Error magnitude: {error_rating}")

        # Confidence
        if confidence > 0.5:
            conf_rating = "✅ High confidence"
        elif confidence > 0.3:
            conf_rating = "⚠️  Medium confidence"
        else:
            conf_rating = "❌ Low confidence"

        print(f"  Confidence: {conf_rating}")

        # Similar questions quality
        if prediction['n_similar'] >= 15:
            similar_rating = "✅ Many similar questions found"
        elif prediction['n_similar'] >= 10:
            similar_rating = "⚠️  Moderate similar questions"
        else:
            similar_rating = "❌ Few similar questions"

        print(f"  Coverage: {similar_rating}")

        # Domain consistency
        top_domains = [s['domain'] for s in prediction['top_5_similar'][:5]]
        same_domain_count = sum(1 for d in top_domains if d == q.get('domain', 'unknown'))

        if same_domain_count >= 3:
            domain_rating = "✅ Strong domain match"
        elif same_domain_count >= 2:
            domain_rating = "⚠️  Moderate domain match"
        else:
            domain_rating = "❌ Weak domain match"

        print(f"  Domain consistency: {domain_rating} ({same_domain_count}/5 in same domain)")

        # Overall credibility
        credible = error < 0.20 and confidence > 0.3 and prediction['n_similar'] >= 10

        if credible:
            print(f"\n  ✅ OVERALL: CREDIBLE PREDICTION")
        else:
            print(f"\n  ⚠️  OVERALL: Use with caution")
            if error >= 0.20:
                print(f"      - High error ({error:.1%})")
            if confidence <= 0.3:
                print(f"      - Low confidence ({confidence:.3f})")
            if prediction['n_similar'] < 10:
                print(f"      - Few similar questions ({prediction['n_similar']})")

        results.append({
            'qid': qid,
            'domain': q.get('domain', 'unknown'),
            'actual': actual_fr,
            'predicted': pred_fr,
            'error': error,
            'confidence': confidence,
            'n_similar': prediction['n_similar'],
            'credible': credible
        })

    # Summary statistics
    print(f"\n{'='*80}")
    print("SUMMARY STATISTICS")
    print(f"{'='*80}\n")

    errors = [r['error'] for r in results]
    confidences = [r['confidence'] for r in results]
    credible_count = sum(1 for r in results if r['credible'])

    print(f"Average error: {np.mean(errors):.1%}")
    print(f"Median error: {np.median(errors):.1%}")
    print(f"Max error: {np.max(errors):.1%}")
    print(f"Min error: {np.min(errors):.1%}")

    print(f"\nAverage confidence: {np.mean(confidences):.3f}")
    print(f"Median confidence: {np.median(confidences):.3f}")

    print(f"\nCredible predictions: {credible_count}/10 ({credible_count*10}%)")

    # Error distribution
    excellent = sum(1 for e in errors if e < 0.10)
    good = sum(1 for e in errors if 0.10 <= e < 0.20)
    fair = sum(1 for e in errors if 0.20 <= e < 0.30)
    poor = sum(1 for e in errors if e >= 0.30)

    print(f"\nError distribution:")
    print(f"  Excellent (< 10%): {excellent}/10")
    print(f"  Good (10-20%): {good}/10")
    print(f"  Fair (20-30%): {fair}/10")
    print(f"  Poor (> 30%): {poor}/10")

    # Save results
    with open('data/sample_predictions_analysis.json', 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\n💾 Results saved to: data/sample_predictions_analysis.json")

    print(f"\n{'='*80}")
    print("CREDIBILITY ASSESSMENT")
    print(f"{'='*80}\n")

    if credible_count >= 8:
        print("✅ HIGH CREDIBILITY: 80%+ predictions are reliable")
        print("   The predictor is production-ready for most use cases")
    elif credible_count >= 6:
        print("⚠️  MODERATE CREDIBILITY: 60-70% predictions are reliable")
        print("   Use with caution, verify predictions for critical decisions")
    else:
        print("❌ LOW CREDIBILITY: <60% predictions are reliable")
        print("   Needs improvement before production use")

    print(f"\nKey strengths:")
    if np.mean(confidences) > 0.4:
        print("  ✅ High average confidence ({:.3f})".format(np.mean(confidences)))
    if excellent + good >= 7:
        print(f"  ✅ Most predictions within 20% error ({excellent + good}/10)")

    print(f"\nAreas for improvement:")
    if poor > 0:
        print(f"  ⚠️  {poor} predictions with >30% error")
    if np.mean(confidences) < 0.4:
        print(f"  ⚠️  Low average confidence ({np.mean(confidences):.3f})")


if __name__ == "__main__":
    main()
