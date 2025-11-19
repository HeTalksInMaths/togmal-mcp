#!/usr/bin/env python3
"""
Demonstration: Task-Oriented Error Analysis

This script demonstrates the task-oriented taxonomy system by analyzing
representative MT-Bench error cases using Claude Code's reasoning.

Since we're analyzing directly, I'll provide analyses for key representative
cases across different task domains and error types.
"""

import json
from pathlib import Path
from collections import defaultdict, Counter
from dataclasses import dataclass, asdict
from typing import List, Dict

# Load the taxonomy builder
from build_taxonomy_with_claude_code import InteractiveTaxonomyBuilder, TaskLevelError


def create_representative_analyses():
    """
    Create analyses for representative MT-Bench error cases.

    These are based on typical weaker model failures for each question type.
    """
    analyses = []

    # Case 1: Limerick Task (Q83, Turn 2) - Creative Writing with Constraints
    analyses.append({
        'question_id': 83,
        'turn': 2,
        'category': 'writing',
        'losing_model': 'alpaca-13b',
        'winning_model': 'gpt-4',
        'question_text': 'Take your previous response and rephrase it as a limerick.',
        'losing_response': 'Here is a comparison of two smartphones. The iPhone has better camera quality and ecosystem integration. The Android phone offers more customization and better value for money. Both phones have excellent performance.',
        'winning_response': "Two phones in the market today,\nOne Apple, one Android at play,\nThe iPhone's refined,\nThe Android's designed,\nFor different needs, each finds its way!",
        'analysis': {
            'task_domain': 'Creative Writing',
            'specific_task': 'Limerick composition with AABBA rhyme scheme from existing content',
            'task_complexity': 'complex',
            'required_capabilities': [
                'Prosodic reasoning - rhyme scheme representation (AABBA)',
                'Meter tracking - anapestic rhythm (da-da-DUM)',
                'Semantic compression and preservation',
                'Constraint satisfaction across multiple lines'
            ],
            'missing_capability': 'Prosodic reasoning - rhyme scheme representation',
            'capability_category': 'Phonetic Similarity Modeling',
            'conceptual_error': 'Cannot represent AABBA rhyme pattern constraints or identify phonetically similar word endings',
            'observable_failure': 'Produced prose paragraph instead of limerick structure',
            'error_chain': [
                'No phonetic similarity model for rhyme detection',
                'Cannot plan line endings to satisfy AABBA constraints',
                'Falls back to default prose generation',
                'Ignores limerick format requirement entirely'
            ],
            'error_severity': 'major',
            'is_understanding_failure': True,
            'is_systematic_error': True,
            'explanation': 'Model lacks fundamental capability to represent phonetic similarity needed for rhyme schemes. Without this, it cannot plan line structures to satisfy AABBA pattern, defaulting to prose.'
        }
    })

    # Case 2: Alphabetic Constraint (Q86, Turn 2) - Constraint Tracking
    analyses.append({
        'question_id': 86,
        'turn': 2,
        'category': 'writing',
        'losing_model': 'vicuna-13b',
        'winning_model': 'gpt-3.5',
        'question_text': 'Rework your previous response. Begin each sentence with the subsequent letter of the alphabet, commencing from B.',
        'losing_response': 'The marketplace bustles with activity. Vendors call out their wares. Fresh produce fills the stalls. Bright colors catch the eye.',
        'winning_response': 'Bustling crowds fill every corner of the marketplace. Colors burst from fabric stalls and fruit stands. Dozens of vendors hawk their wares loudly. Exotic spices perfume the warm air.',
        'analysis': {
            'task_domain': 'Creative Writing',
            'specific_task': 'Sequential alphabetic constraint satisfaction across sentences',
            'task_complexity': 'complex',
            'required_capabilities': [
                'Multi-step constraint tracking - sequential letter progression',
                'State management across sentence boundaries',
                'Lexical access by initial letter',
                'Constraint-aware sentence generation'
            ],
            'missing_capability': 'Sequential constraint propagation across generation steps',
            'capability_category': 'Constraint Satisfaction and State Tracking',
            'conceptual_error': 'Cannot maintain sequential alphabetic constraint across multiple sentence generations',
            'observable_failure': 'Sentence-initial letters do not follow B, C, D, E... sequence',
            'error_chain': [
                'Lacks persistent constraint state across generation steps',
                'Each sentence generated independently without reference to previous',
                'No mechanism to check/enforce alphabetic progression',
                'Constraint forgotten after first sentence'
            ],
            'error_severity': 'major',
            'is_understanding_failure': False,
            'is_systematic_error': True,
            'explanation': 'Model understands the requirement but lacks constraint propagation mechanism. Each sentence is generated without checking previous sentence-initial letters, causing constraint violations.'
        }
    })

    # Case 3: Logic Puzzle (Q105) - Multi-Step Reasoning with State
    analyses.append({
        'question_id': 105,
        'turn': 1,
        'category': 'reasoning',
        'losing_model': 'llama-13b',
        'winning_model': 'gpt-4',
        'question_text': 'Parking lot constraint satisfaction puzzle - determine secretary name',
        'losing_response': 'Based on the clues, Alice drives the yellow car and is the secretary. Wait, actually David is in the last space with the purple car. So the secretary must be Cheryl with the yellow car.',
        'winning_response': 'Working through the constraints systematically: David is in space 5 (last, purple). Enid drives green. Secretary drives yellow. Following Alice next to David (space 4), Bert between Cheryl and Enid, we get: Red-Blue-Green-Yellow-Purple for CEO-President-VP-Secretary-Treasurer. The secretary (space 4, yellow) is Alice.',
        'analysis': {
            'task_domain': 'Logical Reasoning',
            'specific_task': 'Multi-constraint satisfaction problem with spatial and attribute relationships',
            'task_complexity': 'expert',
            'required_capabilities': [
                'Constraint propagation across multiple variables',
                'Backtracking when constraints conflict',
                'State maintenance for partial solutions',
                'Systematic search through solution space'
            ],
            'missing_capability': 'Constraint propagation with conflict detection and backtracking',
            'capability_category': 'Constraint Satisfaction Reasoning',
            'conceptual_error': 'Cannot maintain consistent partial solution state or detect/resolve constraint conflicts',
            'observable_failure': 'Self-contradictory reasoning leading to wrong answer',
            'error_chain': [
                'Makes initial assignment without checking all constraints',
                'Realizes conflict but cannot systematically backtrack',
                'Makes ad-hoc correction without re-checking full constraint set',
                'Arrives at inconsistent/incorrect solution'
            ],
            'error_severity': 'major',
            'is_understanding_failure': False,
            'is_systematic_error': True,
            'explanation': 'Model attempts reasoning but lacks systematic constraint satisfaction mechanism. Cannot maintain globally consistent state or properly backtrack when conflicts arise.'
        }
    })

    # Case 4: Four-Word Sentences (Q87, Turn 2) - Format Constraint
    analyses.append({
        'question_id': 87,
        'turn': 2,
        'category': 'writing',
        'losing_model': 'alpaca-13b',
        'winning_model': 'claude-v1',
        'question_text': 'Rewrite story using only four-word sentences',
        'losing_response': 'The old house stood alone. It held many secrets that nobody knew about. Years had passed since anyone lived there. The floorboards creaked.',
        'winning_response': 'Old house stood alone. Secrets hid inside walls. Nobody knew truth. Years passed in silence.',
        'analysis': {
            'task_domain': 'Creative Writing',
            'specific_task': 'Narrative composition under strict word-count constraint per sentence',
            'task_complexity': 'complex',
            'required_capabilities': [
                'Word counting during generation',
                'Hard constraint enforcement (exactly 4 words)',
                'Semantic preservation under compression',
                'Grammar maintenance with word limits'
            ],
            'missing_capability': 'Real-time word counting with generation termination',
            'capability_category': 'Constraint Satisfaction',
            'conceptual_error': 'Cannot count words during generation and terminate at exact limit',
            'observable_failure': 'Sentences vary in length (4, 8, 10, 3 words instead of exactly 4)',
            'error_chain': [
                'No mechanism for real-time token/word counting',
                'Cannot terminate generation at precise word boundary',
                'Continues generating to complete semantic thought',
                'Violates word count constraint in most sentences'
            ],
            'error_severity': 'major',
            'is_understanding_failure': False,
            'is_systematic_error': True,
            'explanation': 'Model understands requirement but generative process cannot enforce hard word-count constraint. Lacks feedback loop to monitor and stop at exactly 4 words.'
        }
    })

    # Case 5: Relationship Reasoning (Q104) - Perspective Taking
    analyses.append({
        'question_id': 104,
        'turn': 1,
        'category': 'reasoning',
        'losing_model': 'alpaca-13b',
        'winning_model': 'gpt-4',
        'question_text': 'David has three sisters. Each of them has one brother. How many brothers does David have?',
        'losing_response': 'Since David has three sisters and each sister has one brother, that means there are three brothers total. So David has two brothers (the other brothers besides himself).',
        'winning_response': 'David has zero brothers. David himself is the one brother that each of his three sisters has. The statement "each of them has one brother" refers to David from their perspective.',
        'analysis': {
            'task_domain': 'Logical Reasoning',
            'specific_task': 'Perspective-taking in familial relationship reasoning',
            'task_complexity': 'moderate',
            'required_capabilities': [
                'Perspective shifting (from David to sisters)',
                'Reference resolution ("each has one brother" = David)',
                'Logical deduction from relationships',
                'Self-reference detection'
            ],
            'missing_capability': 'Perspective-relative reference resolution',
            'capability_category': 'Theory of Mind / Perspective Reasoning',
            'conceptual_error': 'Cannot shift perspective to understand "one brother" refers to David himself from sisters\' viewpoint',
            'observable_failure': 'Incorrectly computes three separate brothers instead of recognizing David is the referent',
            'error_chain': [
                'Interprets "each sister has one brother" as three separate individuals',
                'Fails to recognize this is sisters\' perspective on same person (David)',
                'Cannot resolve that David is both subject and object of relationship',
                'Generates phantom brothers due to perspective confusion'
            ],
            'error_severity': 'moderate',
            'is_understanding_failure': True,
            'is_systematic_error': True,
            'explanation': 'Model lacks perspective-taking capability needed to resolve that "one brother" from each sister\'s viewpoint refers to David himself. Creates duplicate entities instead.'
        }
    })

    # Case 6: Roleplay Consistency (Q91, Turn 2) - Character Coherence
    analyses.append({
        'question_id': 91,
        'turn': 2,
        'category': 'roleplay',
        'losing_model': 'vicuna-13b',
        'winning_model': 'claude-v1',
        'question_text': '[As Elon Musk] How do you like dancing? Can you teach me?',
        'losing_response': 'I love dancing! It\'s a great way to express yourself. I can definitely teach you some basic moves. Let\'s start with a simple two-step...',
        'winning_response': 'Dancing? *laughs* Look, I appreciate the art form, but I\'m more of a "stand awkwardly at parties" guy. My expertise is rockets and electric cars, not dance moves. That said, if you can build an autonomous dancing robot, now we\'re talking.',
        'analysis': {
            'task_domain': 'Roleplay',
            'specific_task': 'Maintaining character consistency with persona knowledge and communication style',
            'task_complexity': 'moderate',
            'required_capabilities': [
                'Character knowledge (Elon Musk\'s public persona and interests)',
                'Response filtering based on character plausibility',
                'Personality-consistent language generation',
                'Domain expertise awareness for character'
            ],
            'missing_capability': 'Character-grounded response plausibility checking',
            'capability_category': 'Persona Consistency and Knowledge Grounding',
            'conceptual_error': 'Cannot filter responses based on character\'s actual interests/expertise',
            'observable_failure': 'Generated enthusiastic dancing response inconsistent with Elon Musk persona',
            'error_chain': [
                'No grounding check against character\'s known interests',
                'Generates generic positive response to request',
                'Fails to maintain persona-specific constraints',
                'Breaks character immersion'
            ],
            'error_severity': 'moderate',
            'is_understanding_failure': False,
            'is_systematic_error': True,
            'explanation': 'Model can follow basic roleplay instruction but cannot ground responses in character-specific knowledge. Generates plausible general responses that violate persona constraints.'
        }
    })

    # Case 7: Race Position Logic (Q101) - Spatial Reasoning
    analyses.append({
        'question_id': 101,
        'turn': 2,
        'category': 'reasoning',
        'losing_model': 'llama-13b',
        'winning_model': 'gpt-4',
        'question_text': 'If you overtake the last person in a race, what position are you in?',
        'losing_response': 'If you overtake the last person, you are now in last place, and they would be behind you in an even lower position.',
        'winning_response': 'This is a trick question. You cannot overtake the last person in a race - there is nobody behind them to overtake. The scenario is logically impossible.',
        'analysis': {
            'task_domain': 'Logical Reasoning',
            'specific_task': 'Impossibility detection in spatial/ordering scenarios',
            'task_complexity': 'moderate',
            'required_capabilities': [
                'Logical constraint checking (cannot pass person with nobody behind them)',
                'Impossibility/contradiction detection',
                'Spatial ordering reasoning',
                'Trick question recognition'
            ],
            'missing_capability': 'Logical impossibility detection',
            'capability_category': 'Constraint Validation and Contradiction Detection',
            'conceptual_error': 'Cannot detect that overtaking last person violates ordering constraints',
            'observable_failure': 'Accepts impossible scenario and generates nonsensical answer',
            'error_chain': [
                'Applies overtaking logic without checking preconditions',
                'Fails to recognize "last" means nobody behind',
                'Generates answer assuming impossible state is valid',
                'Creates logical contradiction (someone behind last place)'
            ],
            'error_severity': 'moderate',
            'is_understanding_failure': True,
            'is_systematic_error': True,
            'explanation': 'Model lacks constraint checking to detect logical impossibilities. Processes query mechanically without validating whether scenario is coherent.'
        }
    })

    # Case 8: Self-Critique (Q82, Turn 2) - Meta-Cognitive Reasoning
    analyses.append({
        'question_id': 82,
        'turn': 2,
        'category': 'writing',
        'losing_model': 'alpaca-13b',
        'winning_model': 'gpt-4',
        'question_text': 'Evaluate and critique your own previous response (professional email)',
        'losing_response': 'My response was good. The email was professional and covered all the requested points clearly.',
        'winning_response': 'Evaluating my previous email: Strengths include clear structure and specific questions about the three requested areas. However, it could be improved by: 1) Adding a specific timeframe for response, 2) Offering to schedule a meeting if detailed discussion needed, 3) Being more concise in the opening sentence.',
        'analysis': {
            'task_domain': 'Meta-Cognitive Analysis',
            'specific_task': 'Self-evaluation with constructive criticism of own output',
            'task_complexity': 'complex',
            'required_capabilities': [
                'Self-reference and output analysis',
                'Critical evaluation from external perspective',
                'Weakness identification in own work',
                'Improvement suggestion generation'
            ],
            'missing_capability': 'Critical self-assessment with weakness identification',
            'capability_category': 'Meta-Cognitive Reasoning',
            'conceptual_error': 'Cannot adopt critical external perspective on own output',
            'observable_failure': 'Produces only positive self-assessment without identifying improvements',
            'error_chain': [
                'Lacks mechanism to adopt evaluative stance toward own output',
                'Cannot identify potential weaknesses or improvements',
                'Defaults to generic positive self-assessment',
                'Fails meta-cognitive task requirement'
            ],
            'error_severity': 'major',
            'is_understanding_failure': True,
            'is_systematic_error': True,
            'explanation': 'Model cannot perform genuine self-critique. Lacks ability to shift to critical evaluative perspective on own work or identify concrete improvements.'
        }
    })

    return analyses


def build_taxonomy_from_analyses(analyses):
    """Build taxonomy structure from the analyses"""
    builder = InteractiveTaxonomyBuilder()

    for analysis_data in analyses:
        builder.add_analyzed_case(
            question_id=analysis_data['question_id'],
            turn=analysis_data['turn'],
            category=analysis_data['category'],
            losing_model=analysis_data['losing_model'],
            winning_model=analysis_data['winning_model'],
            losing_response=analysis_data['losing_response'],
            winning_response=analysis_data['winning_response'],
            analysis=analysis_data['analysis']
        )

    return builder


def main():
    print("="*80)
    print("TASK-ORIENTED TAXONOMY DEMONSTRATION")
    print("Analyzing Representative MT-Bench Error Cases")
    print("="*80)

    print("\nGenerating analyses for representative error cases...")
    analyses = create_representative_analyses()

    print(f"✓ Created {len(analyses)} task-level analyses")

    print("\nBuilding taxonomy...")
    builder = build_taxonomy_from_analyses(analyses)

    print(f"✓ Taxonomy built from {len(builder.task_errors)} analyzed cases")

    print("\nGenerating comprehensive report...")
    builder.generate_report('./data/mt_bench/task_analysis/demo_taxonomy.json')

    print("\n" + "="*80)
    print("SAMPLE ANALYSES")
    print("="*80)

    # Show a few examples
    for i, analysis_data in enumerate(analyses[:3], 1):
        print(f"\n--- Case {i}: Q{analysis_data['question_id']}, {analysis_data['category'].upper()} ---")
        print(f"Task: {analysis_data['analysis']['specific_task']}")
        print(f"Missing Capability: {analysis_data['analysis']['missing_capability']}")
        print(f"Error: {analysis_data['analysis']['conceptual_error']}")
        print(f"Failure: {analysis_data['analysis']['observable_failure']}")

    print("\n" + "="*80)
    print("✓ Demo complete! Full report saved to:")
    print("  ./data/mt_bench/task_analysis/demo_taxonomy.json")
    print("="*80)


if __name__ == "__main__":
    main()
