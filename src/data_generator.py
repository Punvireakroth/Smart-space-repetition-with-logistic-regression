"""
Synthetic Data Generator for Smart Flashcard System

Simulates realistic study patterns based on:
- Ebbinghaus forgetting curve (memory decays exponentially over time)
- Strengthening effect (more reviews = better retention)
- Difficulty effect (harder cards = lower base recall)
"""

import numpy as np
import pandas as pd
from typing import Tuple


def calculate_recall_probability(
    days_since_review: float,
    num_reviews: int,
    past_accuracy: float,
    difficulty: int,
    noise_std: float = 0.08
) -> float:
    """
    Calculate probability of correct recall based on memory model.
    
    Uses a simplified forgetting curve model:
    P(recall) = base_strength * decay_factor + noise
    
    Args:
        days_since_review: Days since last review (0 = today)
        num_reviews: Number of previous reviews
        past_accuracy: Historical accuracy (0-1)
        difficulty: Card difficulty (1=easy, 5=hard)
        noise_std: Standard deviation of random noise
    
    Returns:
        Probability of correct recall (0-1)
    """
    # Base strength from reviews and past performance
    # More reviews and better past accuracy = stronger memory
    review_strength = min(1.0, 0.4 + 0.12 * num_reviews)  # Caps at 1.0
    accuracy_bonus = 0.15 * past_accuracy
    
    # Difficulty penalty (harder cards are harder to recall)
    difficulty_penalty = 0.05 * (difficulty - 1)  # 0 for easy, 0.2 for hardest
    
    # Base memory strength
    base_strength = review_strength + accuracy_bonus - difficulty_penalty
    base_strength = np.clip(base_strength, 0.2, 0.95)
    
    # Forgetting curve: exponential decay over time
    # Memory strength determines decay rate (stronger = slower decay)
    # Gentler decay for more realistic retention
    decay_rate = 0.08 / (0.5 + 0.5 * base_strength)  # Stronger memory = slower decay
    decay_factor = np.exp(-decay_rate * days_since_review)
    
    # Final probability
    prob = base_strength * decay_factor
    
    # Add noise to simulate real-world variability
    prob += np.random.normal(0, noise_std)
    
    return np.clip(prob, 0.05, 0.95)


def generate_synthetic_data(
    n_cards: int = 50,
    n_study_sessions: int = 500,
    random_seed: int = 42
) -> pd.DataFrame:
    """
    Generate synthetic flashcard study data.
    
    Simulates a student studying flashcards over multiple sessions,
    with realistic forgetting patterns and learning effects.
    
    Args:
        n_cards: Number of unique flashcards
        n_study_sessions: Total number of card reviews to simulate
        random_seed: Random seed for reproducibility
    
    Returns:
        DataFrame with columns: card_id, days_since_review, num_reviews,
                               past_accuracy, difficulty, correct
    """
    np.random.seed(random_seed)
    
    # Initialize cards with random difficulties
    card_difficulties = np.random.randint(1, 6, size=n_cards)
    
    # Track card state: [last_review_day, num_reviews, total_correct, total_attempts]
    card_states = {
        i: {'last_review': -np.random.randint(1, 10), 'reviews': 0, 'correct': 0, 'attempts': 0}
        for i in range(n_cards)
    }
    
    data = []
    current_day = 0
    
    for session in range(n_study_sessions):
        # Progress time (some days pass between reviews) - gentler progression
        if session > 0 and np.random.random() < 0.2:
            current_day += np.random.randint(1, 3)
        
        # Select a random card to review
        card_id = np.random.randint(0, n_cards)
        state = card_states[card_id]
        
        # Calculate features
        days_since = max(0, current_day - state['last_review'])
        num_reviews = state['reviews']
        past_accuracy = state['correct'] / state['attempts'] if state['attempts'] > 0 else 0.5
        difficulty = card_difficulties[card_id]
        
        # Calculate recall probability and simulate outcome
        recall_prob = calculate_recall_probability(
            days_since, num_reviews, past_accuracy, difficulty
        )
        correct = 1 if np.random.random() < recall_prob else 0
        
        # Record this study event
        data.append({
            'card_id': card_id,
            'days_since_review': days_since,
            'num_reviews': num_reviews,
            'past_accuracy': round(past_accuracy, 3),
            'difficulty': difficulty,
            'correct': correct
        })
        
        # Update card state
        state['last_review'] = current_day
        state['reviews'] += 1
        state['attempts'] += 1
        state['correct'] += correct
    
    return pd.DataFrame(data)


def generate_sample_flashcards(n_cards: int = 20) -> pd.DataFrame:
    """
    Generate sample flashcard content for the demo.
    
    Args:
        n_cards: Number of flashcards to generate
    
    Returns:
        DataFrame with columns: card_id, question, answer, difficulty
    """
    # Sample flashcard content (mix of topics)
    sample_cards = [
        ("What is the capital of France?", "Paris", 1),
        ("What is the derivative of x^2?", "2x", 2),
        ("What is the chemical symbol for gold?", "Au", 2),
        ("Who wrote 'Romeo and Juliet'?", "William Shakespeare", 1),
        ("What is the powerhouse of the cell?", "Mitochondria", 2),
        ("What is 12 x 12?", "144", 1),
        ("What is the largest planet in our solar system?", "Jupiter", 2),
        ("What is the quadratic formula?", "x = (-b ± √(b²-4ac)) / 2a", 4),
        ("What is the speed of light (approx)?", "3 x 10^8 m/s", 3),
        ("What is Newton's second law?", "F = ma", 2),
        ("What is the integral of 1/x?", "ln|x| + C", 3),
        ("What year did World War II end?", "1945", 2),
        ("What is the Pythagorean theorem?", "a² + b² = c²", 2),
        ("What is the capital of Japan?", "Tokyo", 1),
        ("What is the chemical formula for water?", "H2O", 1),
        ("Who developed the theory of relativity?", "Albert Einstein", 2),
        ("What is the binary representation of 10?", "1010", 3),
        ("What is the definition of a derivative?", "lim(h→0) [f(x+h) - f(x)] / h", 5),
        ("What is the square root of 169?", "13", 2),
        ("What programming language is known for ML?", "Python", 1),
    ]
    
    # Extend if needed
    while len(sample_cards) < n_cards:
        i = len(sample_cards)
        sample_cards.append((f"Question {i+1}?", f"Answer {i+1}", np.random.randint(1, 6)))
    
    cards = []
    for i, (q, a, d) in enumerate(sample_cards[:n_cards]):
        cards.append({
            'card_id': i,
            'question': q,
            'answer': a,
            'difficulty': d
        })
    
    return pd.DataFrame(cards)


if __name__ == "__main__":
    # Generate and save synthetic data
    print("Generating synthetic study data...")
    df = generate_synthetic_data(n_cards=50, n_study_sessions=1000)
    df.to_csv("data/synthetic_data.csv", index=False)
    print(f"Generated {len(df)} study records")
    print(f"\nFeature distributions:")
    print(df.describe())
    
    # Generate sample flashcards
    print("\nGenerating sample flashcards...")
    cards_df = generate_sample_flashcards(20)
    cards_df.to_csv("data/flashcards.csv", index=False)
    print(f"Generated {len(cards_df)} flashcards")
