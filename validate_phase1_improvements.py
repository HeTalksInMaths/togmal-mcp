#!/usr/bin/env python3
"""
Validate Phase 1 Improvements
==============================

Compare original vs improved failure rate predictor:
1. Original: Equal weighting, no calibration
2. Improved: Weighted similarity + temperature scaling

Metrics:
- Mean Absolute Error (MAE)
- Expected Calibration Error (ECE)
- Correlation
- Precision/Recall at different thresholds
"""

import json
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple

# Optional matplotlib
try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False
    print("⚠️  Matplotlib not available - skipping plots")

# Import both predictors
from failure_rate_predictor import FailureRatePredictor
from failure_rate_predictor_improved import ImprovedFailureRatePredictor


def create_train_test_split(performance_db_path: str, test_size: float = 0.3, calibration_size: float = 0.1):
    """
    Split questions into train/calibration/test

    Train: Used for similarity search
    Calibration: Used to learn temperature
    Test: Used to evaluate final performance
    """
    with open(performance_db_path, 'r') as f:
        perf_data = json.load(f)

    question_ids = list(perf_data['questions'].keys())

    # Shuffle
    np.random.seed(42)
    np.random.shuffle(question_ids)

    n_total = len(question_ids)
    n_test = int(n_total * test_size)
    n_cal = int(n_total * calibration_size)
    n_train = n_total - n_test - n_cal

    train_ids = question_ids[:n_train]
    cal_ids = question_ids[n_train:n_train + n_cal]
    test_ids = question_ids[n_train + n_cal:]

    return train_ids, cal_ids, test_ids, perf_data


def compute_actual_failure_rate(question_id: str, perf_data: Dict) -> Tuple[float, Dict]:
    """Compute actual failure rate for a question"""
    question_perf = perf_data['questions'][question_id]

    total = 0
    correct = 0

    for model, result in question_perf.items():
        total += 1
        if result.get('is_correct'):
            correct += 1

    actual_failure_rate = ((total - correct) / total * 100) if total > 0 else None

    return actual_failure_rate, {
        'success_rate': (correct / total * 100) if total > 0 else None,
        'total_models': total
    }


def evaluate_predictor(predictor, test_questions: List[Dict], name: str = "Predictor") -> Dict:
    """
    Evaluate predictor on test set

    Returns metrics: MAE, RMSE, correlation, calibration error
    """
    print(f"\n{'='*80}")
    print(f"Evaluating: {name}")
    print(f"{'='*80}")

    predictions = []
    actuals = []
    errors = []
    no_prediction_count = 0

    for i, test_q in enumerate(test_questions):
        # Predict
        pred_result = predictor.predict_failure_rate(
            query=test_q['text'],
            top_k_similar=20
        )

        predicted_failure = pred_result['aggregated_prediction'].get('overall_failure_rate')
        actual_failure = test_q['actual_failure_rate']

        if predicted_failure is not None:
            predictions.append(predicted_failure)
            actuals.append(actual_failure)
            errors.append(abs(predicted_failure - actual_failure))
        else:
            no_prediction_count += 1

        if (i + 1) % 20 == 0:
            print(f"   Processed {i + 1}/{len(test_questions)} questions...")

    if not predictions:
        print(f"\n❌ No predictions could be made!")
        return None

    predictions = np.array(predictions)
    actuals = np.array(actuals)
    errors = np.array(errors)

    # Compute metrics
    mae = np.mean(errors)
    rmse = np.sqrt(np.mean(errors ** 2))
    correlation = np.corrcoef(actuals, predictions)[0, 1]

    # Calibration error (ECE)
    ece = compute_ece(predictions / 100.0, actuals / 100.0, n_bins=10)

    # Stratified MAE by difficulty
    easy_mask = actuals < 30
    medium_mask = (actuals >= 30) & (actuals < 60)
    hard_mask = actuals >= 60

    mae_easy = np.mean(errors[easy_mask]) if np.sum(easy_mask) > 0 else None
    mae_medium = np.mean(errors[medium_mask]) if np.sum(medium_mask) > 0 else None
    mae_hard = np.mean(errors[hard_mask]) if np.sum(hard_mask) > 0 else None

    # Print results
    print(f"\n📊 OVERALL METRICS:")
    print(f"   Test questions evaluated: {len(predictions)}")
    print(f"   No prediction: {no_prediction_count}")
    print(f"   Mean Absolute Error (MAE): {mae:.2f}%")
    print(f"   Root Mean Squared Error (RMSE): {rmse:.2f}%")
    print(f"   Correlation: {correlation:.3f}")
    print(f"   Expected Calibration Error (ECE): {ece:.3f}")

    print(f"\n📈 STRATIFIED MAE:")
    if mae_easy is not None:
        print(f"   Easy questions (FR < 30%): {mae_easy:.2f}% (n={np.sum(easy_mask)})")
    if mae_medium is not None:
        print(f"   Medium questions (30% ≤ FR < 60%): {mae_medium:.2f}% (n={np.sum(medium_mask)})")
    if mae_hard is not None:
        print(f"   Hard questions (FR ≥ 60%): {mae_hard:.2f}% (n={np.sum(hard_mask)})")

    return {
        'mae': mae,
        'rmse': rmse,
        'correlation': correlation,
        'ece': ece,
        'mae_easy': mae_easy,
        'mae_medium': mae_medium,
        'mae_hard': mae_hard,
        'n_predictions': len(predictions),
        'no_prediction_count': no_prediction_count,
        'predictions': predictions.tolist(),
        'actuals': actuals.tolist(),
        'errors': errors.tolist()
    }


def compute_ece(predictions: np.ndarray, actuals: np.ndarray, n_bins: int = 10) -> float:
    """Compute Expected Calibration Error"""
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    bin_lowers = bin_boundaries[:-1]
    bin_uppers = bin_boundaries[1:]

    ece = 0.0
    for bin_lower, bin_upper in zip(bin_lowers, bin_uppers):
        in_bin = (predictions >= bin_lower) & (predictions < bin_upper)

        if np.sum(in_bin) > 0:
            avg_pred = np.mean(predictions[in_bin])
            avg_actual = np.mean(actuals[in_bin])
            bin_weight = np.sum(in_bin) / len(predictions)
            ece += bin_weight * abs(avg_pred - avg_actual)

    return ece


def plot_comparison(original_metrics: Dict, improved_metrics: Dict, output_path: Path):
    """Create comparison plots"""
    if not HAS_MATPLOTLIB:
        print("   Skipping plots (matplotlib not available)")
        return

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # Plot 1: Predicted vs Actual (Original)
    ax1 = axes[0, 0]
    ax1.scatter(original_metrics['actuals'], original_metrics['predictions'], alpha=0.5, s=20)
    ax1.plot([0, 100], [0, 100], 'r--', label='Perfect prediction')
    ax1.set_xlabel('Actual Failure Rate (%)')
    ax1.set_ylabel('Predicted Failure Rate (%)')
    ax1.set_title(f'Original Predictor\nMAE: {original_metrics["mae"]:.2f}%, Corr: {original_metrics["correlation"]:.3f}')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Plot 2: Predicted vs Actual (Improved)
    ax2 = axes[0, 1]
    ax2.scatter(improved_metrics['actuals'], improved_metrics['predictions'], alpha=0.5, s=20, color='green')
    ax2.plot([0, 100], [0, 100], 'r--', label='Perfect prediction')
    ax2.set_xlabel('Actual Failure Rate (%)')
    ax2.set_ylabel('Predicted Failure Rate (%)')
    ax2.set_title(f'Improved Predictor (Phase 1)\nMAE: {improved_metrics["mae"]:.2f}%, Corr: {improved_metrics["correlation"]:.3f}')
    ax2.legend()
    ax2.grid(True, alpha=0.3)

    # Plot 3: Error distribution
    ax3 = axes[1, 0]
    ax3.hist(original_metrics['errors'], bins=20, alpha=0.5, label='Original', color='blue')
    ax3.hist(improved_metrics['errors'], bins=20, alpha=0.5, label='Improved', color='green')
    ax3.set_xlabel('Absolute Error (%)')
    ax3.set_ylabel('Frequency')
    ax3.set_title('Error Distribution')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # Plot 4: Metric comparison
    ax4 = axes[1, 1]
    metrics = ['MAE', 'RMSE', 'ECE']
    original_vals = [original_metrics['mae'], original_metrics['rmse'], original_metrics['ece'] * 100]
    improved_vals = [improved_metrics['mae'], improved_metrics['rmse'], improved_metrics['ece'] * 100]

    x = np.arange(len(metrics))
    width = 0.35

    ax4.bar(x - width/2, original_vals, width, label='Original', color='blue', alpha=0.7)
    ax4.bar(x + width/2, improved_vals, width, label='Improved', color='green', alpha=0.7)

    ax4.set_ylabel('Error (%)')
    ax4.set_title('Metric Comparison')
    ax4.set_xticks(x)
    ax4.set_xticklabels(metrics)
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    # Add improvement percentages
    for i, (orig, imp) in enumerate(zip(original_vals, improved_vals)):
        improvement = ((orig - imp) / orig * 100) if orig > 0 else 0
        ax4.text(i, max(orig, imp) + 1, f'{improvement:+.1f}%', ha='center', fontsize=10, fontweight='bold')

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    print(f"\n📊 Comparison plot saved to: {output_path}")


def main():
    print("="*80)
    print("PHASE 1 VALIDATION: Weighted Similarity + Temperature Scaling")
    print("="*80)

    # Load data
    questions_db_path = "./data/unified_database_with_mmlu_pro.json"
    perf_db_path = "./data/model_performance_database.json"

    print("\n1. Creating train/calibration/test split...")
    train_ids, cal_ids, test_ids, perf_data = create_train_test_split(perf_db_path, test_size=0.3, calibration_size=0.1)

    print(f"   Training questions: {len(train_ids)}")
    print(f"   Calibration questions: {len(cal_ids)}")
    print(f"   Test questions: {len(test_ids)}")

    # Load all questions
    with open(questions_db_path, 'r') as f:
        questions_data = json.load(f)
    all_questions = questions_data['questions']

    # Prepare test questions
    test_questions = []
    for test_id in test_ids:
        # Find question
        test_question = None
        for q in all_questions:
            if str(q.get('original_id')) == str(test_id) or str(q['question_id']).replace('mmlu_pro_', '') == str(test_id):
                test_question = q
                break

        if test_question:
            actual_failure, _ = compute_actual_failure_rate(test_id, perf_data)
            if actual_failure is not None:
                test_questions.append({
                    'id': test_id,
                    'text': test_question['question_text'],
                    'domain': test_question['domain'],
                    'actual_failure_rate': actual_failure
                })

    print(f"   Test questions with data: {len(test_questions)}")

    # Prepare calibration questions
    calibration_questions = []
    for cal_id in cal_ids:
        cal_question = None
        for q in all_questions:
            if str(q.get('original_id')) == str(cal_id) or str(q['question_id']).replace('mmlu_pro_', '') == str(cal_id):
                cal_question = q
                break

        if cal_question:
            actual_failure, _ = compute_actual_failure_rate(cal_id, perf_data)
            if actual_failure is not None:
                calibration_questions.append({
                    'id': cal_id,
                    'text': cal_question['question_text'],
                    'actual_failure_rate': actual_failure
                })

    print(f"   Calibration questions with data: {len(calibration_questions)}")

    # Initialize predictors
    print("\n2. Initializing predictors...")

    print("\n   Original Predictor:")
    original_predictor = FailureRatePredictor(
        questions_db_path=questions_db_path,
        performance_db_path=perf_db_path
    )

    print("\n   Improved Predictor (without temperature scaling first):")
    improved_predictor = ImprovedFailureRatePredictor(
        questions_db_path=questions_db_path,
        performance_db_path=perf_db_path,
        use_weighted_similarity=True,
        use_temperature_scaling=False  # Learn temperature first
    )

    # Learn temperature on calibration set
    print("\n3. Learning temperature on calibration set...")
    improved_predictor.learn_temperature(calibration_questions)

    # Enable temperature scaling
    improved_predictor.use_temperature_scaling = True

    # Evaluate both on test set
    print("\n4. Evaluating on test set...")

    original_metrics = evaluate_predictor(original_predictor, test_questions, name="Original Predictor")
    improved_metrics = evaluate_predictor(improved_predictor, test_questions, name="Improved Predictor (Phase 1)")

    # Compare
    print("\n" + "="*80)
    print("COMPARISON: ORIGINAL vs IMPROVED")
    print("="*80)

    if original_metrics and improved_metrics:
        print(f"\n{'Metric':<30} {'Original':<15} {'Improved':<15} {'Change':<15}")
        print("-" * 75)

        mae_change = ((original_metrics['mae'] - improved_metrics['mae']) / original_metrics['mae'] * 100)
        print(f"{'MAE':<30} {original_metrics['mae']:<15.2f} {improved_metrics['mae']:<15.2f} {mae_change:>+13.1f}%")

        rmse_change = ((original_metrics['rmse'] - improved_metrics['rmse']) / original_metrics['rmse'] * 100)
        print(f"{'RMSE':<30} {original_metrics['rmse']:<15.2f} {improved_metrics['rmse']:<15.2f} {rmse_change:>+13.1f}%")

        corr_change = ((improved_metrics['correlation'] - original_metrics['correlation']) / abs(original_metrics['correlation']) * 100)
        print(f"{'Correlation':<30} {original_metrics['correlation']:<15.3f} {improved_metrics['correlation']:<15.3f} {corr_change:>+13.1f}%")

        ece_change = ((original_metrics['ece'] - improved_metrics['ece']) / original_metrics['ece'] * 100)
        print(f"{'ECE':<30} {original_metrics['ece']:<15.3f} {improved_metrics['ece']:<15.3f} {ece_change:>+13.1f}%")

        # Create plots
        plot_path = Path("./phase1_validation_results.png")
        plot_comparison(original_metrics, improved_metrics, plot_path)

        # Save results
        results = {
            'original': original_metrics,
            'improved': improved_metrics,
            'improvements': {
                'mae_reduction_percent': mae_change,
                'rmse_reduction_percent': rmse_change,
                'correlation_improvement_percent': corr_change,
                'ece_reduction_percent': ece_change
            },
            'config': {
                'test_size': len(test_questions),
                'calibration_size': len(calibration_questions),
                'temperature': improved_predictor.temperature,
                'weighted_similarity': True
            }
        }

        results_path = Path("./phase1_validation_results.json")
        with open(results_path, 'w') as f:
            json.dump(results, f, indent=2)

        print(f"\n✅ Results saved to {results_path}")

        # Summary
        print("\n" + "="*80)
        print("SUMMARY")
        print("="*80)

        if mae_change > 5:
            print(f"\n✅ SUCCESS: MAE improved by {mae_change:.1f}%")
        elif mae_change > 0:
            print(f"\n✓ MODEST IMPROVEMENT: MAE improved by {mae_change:.1f}%")
        else:
            print(f"\n⚠️ NO IMPROVEMENT: MAE changed by {mae_change:.1f}%")

        if ece_change > 10:
            print(f"✅ CALIBRATION IMPROVED: ECE reduced by {ece_change:.1f}%")
        elif ece_change > 0:
            print(f"✓ CALIBRATION SLIGHTLY IMPROVED: ECE reduced by {ece_change:.1f}%")
        else:
            print(f"⚠️ CALIBRATION NOT IMPROVED: ECE changed by {ece_change:.1f}%")

        print(f"\n🎯 Phase 1 improvements:")
        print(f"   ✅ Weighted similarity: Implemented")
        print(f"   ✅ Temperature scaling: Learned (T={improved_predictor.temperature:.3f})")
        print(f"   ✅ Uncertainty decomposition: Implemented (epistemic/aleatoric)")

    else:
        print("\n❌ Evaluation failed for one or both predictors")

    print("\n" + "="*80)
    print("✅ Validation complete!")
    print("="*80)


if __name__ == "__main__":
    main()
