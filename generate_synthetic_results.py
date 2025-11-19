"""
Generate Synthetic Model Results for Demonstration

Since we can't fetch real model results (403 error from HF), this creates
realistic synthetic results based on:
- Question difficulty heuristics
- Domain-specific error patterns
- Realistic model performance profiles

This allows us to demonstrate the validation framework.
"""

import json
import random
from pathlib import Path
from collections import Counter

# Set seed for reproducibility
random.seed(42)

# Model performance profiles (based on research)
MODEL_PROFILES = {
    "meta-llama/Meta-Llama-3.1-70B-Instruct": {
        "base_accuracy": 0.72,
        "strength_domains": ["history", "psychology", "business"],
        "weakness_domains": ["physics", "chemistry", "math"]
    },
    "Qwen/Qwen2.5-72B-Instruct": {
        "base_accuracy": 0.70,
        "strength_domains": ["math", "physics", "computer_science"],
        "weakness_domains": ["law", "philosophy"]
    },
    "mistralai/Mixtral-8x22B-Instruct-v0.1": {
        "base_accuracy": 0.68,
        "strength_domains": ["economics", "computer_science"],
        "weakness_domains": ["biology", "chemistry"]
    },
    "meta-llama/Meta-Llama-3.1-8B-Instruct": {
        "base_accuracy": 0.58,
        "strength_domains": ["history", "business"],
        "weakness_domains": ["math", "physics", "chemistry", "law"]
    },
    "mistralai/Mistral-7B-Instruct-v0.3": {
        "base_accuracy": 0.55,
        "strength_domains": ["psychology", "health"],
        "weakness_domains": ["law", "engineering", "math"]
    }
}

def estimate_question_difficulty(question_text: str, domain: str) -> float:
    """
    Estimate question difficulty based on heuristics.
    Returns 0-1, where 1 = hardest
    """
    difficulty = 0.5  # baseline

    # Length-based heuristic
    if len(question_text) > 500:
        difficulty += 0.1  # Longer questions tend to be harder

    # Keyword-based heuristics
    hard_keywords = ['calculate', 'derive', 'prove', 'analyze', 'evaluate',
                     'compare', 'contrast', 'synthesize']
    easy_keywords = ['what is', 'define', 'identify', 'list', 'name']

    text_lower = question_text.lower()

    if any(kw in text_lower for kw in hard_keywords):
        difficulty += 0.15

    if any(kw in text_lower for kw in easy_keywords):
        difficulty -= 0.15

    # Domain-specific difficulty
    hard_domains = ['physics', 'math', 'chemistry', 'engineering', 'law']
    if domain.lower() in hard_domains:
        difficulty += 0.1

    # Clamp to 0-1
    return max(0.0, min(1.0, difficulty))

def generate_model_answer(
    question: dict,
    model_name: str,
    profile: dict
) -> dict:
    """
    Generate realistic model answer based on question and model profile.
    """
    domain = question.get('domain', 'unknown')
    question_text = question.get('question_text', '')
    correct_answer = question.get('correct_answer', 'A')
    choices = question.get('choices', [])

    # Estimate difficulty
    difficulty = estimate_question_difficulty(question_text, domain)

    # Adjust model accuracy based on domain strength/weakness
    base_acc = profile['base_accuracy']

    if domain in profile['strength_domains']:
        accuracy = base_acc + 0.15
    elif domain in profile['weakness_domains']:
        accuracy = base_acc - 0.15
    else:
        accuracy = base_acc

    # Further adjust by difficulty
    accuracy = accuracy * (1 - difficulty * 0.3)

    # Clamp
    accuracy = max(0.1, min(0.95, accuracy))

    # Determine if correct
    is_correct = random.random() < accuracy

    if is_correct:
        answer = correct_answer
    else:
        # Generate plausible wrong answer
        # Prefer answers close to correct (common error pattern)
        if len(choices) > 0:
            correct_idx = ord(correct_answer) - ord('A')

            # 60% chance: choose adjacent answer (off-by-one error)
            if random.random() < 0.6:
                offset = random.choice([-1, 1])
                wrong_idx = (correct_idx + offset) % len(choices)
            else:
                # Otherwise: random wrong answer
                wrong_idx = random.choice([i for i in range(len(choices)) if i != correct_idx])

            answer = chr(ord('A') + wrong_idx)
        else:
            answer = "B" if correct_answer != "B" else "C"

    return {
        "is_correct": is_correct,
        "answer": answer,
        "confidence": None  # Not simulated
    }

def populate_synthetic_results(input_path: str, output_path: str):
    """
    Populate synthetic model results for all questions.
    """
    print("Loading dataset...")
    with open(input_path, 'r') as f:
        data = json.load(f)

    questions = data.get('questions', {})
    print(f"Found {len(questions)} questions")

    print("\nGenerating synthetic model results...")
    print("(Using realistic performance profiles based on research)\n")

    for model_name, profile in MODEL_PROFILES.items():
        print(f"  Generating results for {model_name.split('/')[-1]}...")

        for qid, question in questions.items():
            if 'model_results' not in question:
                question['model_results'] = {}

            # Generate answer
            result = generate_model_answer(question, model_name, profile)
            question['model_results'][model_name] = result

    # Compute success rates
    print("\nComputing success rates...")

    for qid, question in questions.items():
        model_results = question['model_results']

        if model_results:
            correct_count = sum(
                1 for r in model_results.values()
                if r.get('is_correct', False)
            )

            total = len(model_results)
            success_rate = correct_count / total

            question['success_rate'] = success_rate
            question['num_models'] = total

            # Classify difficulty
            if success_rate < 0.3:
                question['difficulty_tier'] = 'low'
                question['difficulty_label'] = 'Hard'
            elif success_rate < 0.7:
                question['difficulty_tier'] = 'medium'
                question['difficulty_label'] = 'Moderate'
            else:
                question['difficulty_tier'] = 'high'
                question['difficulty_label'] = 'Easy'

    # Update metadata
    data['metadata']['models_generated'] = list(MODEL_PROFILES.keys())
    data['metadata']['note'] = 'Synthetic results for demonstration'

    # Save
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    print(f"\nSaving to {output_path}...")
    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)

    # Generate statistics
    print("\n" + "="*80)
    print("SYNTHETIC DATA STATISTICS")
    print("="*80)

    total_inferences = len(questions) * len(MODEL_PROFILES)
    total_errors = sum(
        1 for q in questions.values()
        for r in q['model_results'].values()
        if not r.get('is_correct', True)
    )

    print(f"\nTotal inferences: {total_inferences:,}")
    print(f"Total errors: {total_errors:,} ({total_errors/total_inferences*100:.1f}%)")

    print(f"\n📊 Model Performance:")
    for model_name, profile in MODEL_PROFILES.items():
        model_short = model_name.split('/')[-1]

        # Count model errors
        model_correct = 0
        model_total = 0

        for q in questions.values():
            result = q['model_results'].get(model_name, {})
            if result:
                model_total += 1
                if result.get('is_correct', False):
                    model_correct += 1

        accuracy = model_correct / model_total if model_total > 0 else 0
        print(f"  {model_short}: {accuracy*100:.1f}% ({model_correct}/{model_total})")

    print(f"\n📊 Difficulty Distribution:")
    difficulty_dist = Counter(q.get('difficulty_label', 'Unknown')
                              for q in questions.values())
    for label, count in difficulty_dist.most_common():
        print(f"  {label}: {count} ({count/len(questions)*100:.1f}%)")

    print(f"\n✅ Synthetic data generated successfully!")
    print(f"   Ready for validation: python week1_2_validation.py")

if __name__ == "__main__":
    populate_synthetic_results(
        input_path="data/benchmark_results/raw_benchmark_results.json",
        output_path="data/benchmark_results/synthetic_results.json"
    )
