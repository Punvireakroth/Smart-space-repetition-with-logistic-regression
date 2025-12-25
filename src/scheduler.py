"""
Card Scheduling Module

Implements adaptive scheduling based on ML-predicted recall probability.
Cards with lower predicted recall are prioritized for review.
"""

from typing import List, Tuple
from dataclasses import dataclass
from pathlib import Path
import pandas as pd

from .features import FeatureExtractor, CardState
from .model import RecallPredictor, load_model, FEATURE_COLS


@dataclass
class ScheduledCard:
    """A card with its predicted recall probability and priority score."""
    card: CardState
    recall_probability: float
    priority: float  # Higher = needs review more urgently
    
    @property
    def priority_reason(self) -> str:
        """Explain why this card has its priority."""
        if self.recall_probability < 0.3:
            return "High risk of forgetting!"
        elif self.recall_probability < 0.5:
            return "Moderate risk of forgetting"
        elif self.recall_probability < 0.7:
            return "Good retention, but review helps"
        else:
            return "Strong memory - low priority"


class CardScheduler:
    """
    Schedules flashcards for review based on predicted recall probability.
    
    Uses a trained ML model to predict how likely a student is to remember
    each card, then prioritizes cards with lower recall probability.
    """
    
    # Demo mode settings - make differences more visible
    WRONG_ANSWER_PENALTY = 0.35  # Multiply recall by this when wrong
    
    # Difficulty modifiers - harder cards have inherently lower recall
    # This makes the demo more realistic and educational
    DIFFICULTY_MODIFIERS = {
        1: 1.15,   # Easy cards - 15% boost
        2: 1.0,    # Medium cards - baseline
        3: 0.75,   # Hard cards - 25% reduction
        4: 0.55,   # Very hard - 45% reduction
        5: 0.40,   # Expert level - 60% reduction
    }
    
    # Time decay - harder cards are forgotten faster
    TIME_DECAY_RATES = {
        1: 0.02,   # Easy cards decay slowly
        2: 0.04,   # Medium decay
        3: 0.07,   # Hard cards decay faster
        4: 0.10,   # Very hard decay quickly
        5: 0.15,   # Expert cards decay very quickly
    }
    
    def __init__(self, model_path: str, data_dir: str = "data"):
        """
        Initialize the scheduler.
        
        Args:
            model_path: Path to the trained model file
            data_dir: Directory containing flashcards and state data
        """
        self.model = load_model(model_path)
        self.extractor = FeatureExtractor(data_dir)
        
        # Track recent wrong answers for dramatic effect
        self._recent_wrong: dict = {}  # card_id -> penalty_factor
        
        # Load flashcards
        flashcards_path = Path(data_dir) / "flashcards.csv"
        self.extractor.load_flashcards(str(flashcards_path))
    
    def get_scheduled_cards(
        self,
        n_cards: int = 5,
        min_priority: float = 0.0
    ) -> List[ScheduledCard]:
        """
        Get the top N cards that need review most urgently.
        
        Args:
            n_cards: Maximum number of cards to return
            min_priority: Minimum priority threshold (0-1)
        
        Returns:
            List of ScheduledCard objects, sorted by priority (highest first)
        """
        scheduled = []
        
        for card in self.extractor.get_all_cards():
            # Get features and predict recall probability
            features = self.extractor.get_features(card.card_id)
            features_df = pd.DataFrame([features])[FEATURE_COLS]
            base_recall_prob = self.model.predict_proba(features_df)[0][1]
            
            # Start with base probability
            recall_prob = base_recall_prob
            
            # 1. Apply DIFFICULTY modifier - this is the key differentiator!
            difficulty = card.difficulty
            diff_modifier = self.DIFFICULTY_MODIFIERS.get(difficulty, 1.0)
            recall_prob *= diff_modifier
            
            # 2. Apply TIME DECAY based on difficulty
            # Harder cards are forgotten faster
            days = features['days_since_review']
            decay_rate = self.TIME_DECAY_RATES.get(difficulty, 0.04)
            time_penalty = max(0.3, 1.0 - (days * decay_rate))
            recall_prob *= time_penalty
            
            # 3. Apply ACCURACY modifier - cards you get wrong more have lower recall
            if card.total_attempts > 0:
                accuracy = card.correct_count / card.total_attempts
                # Scale: 0% accuracy = 0.4x, 50% = 0.7x, 100% = 1.0x
                accuracy_modifier = 0.4 + (accuracy * 0.6)
                recall_prob *= accuracy_modifier
            
            # 4. Apply REVIEW COUNT bonus - more reviews = better retention
            num_reviews = features['num_reviews']
            if num_reviews > 0:
                # Each review adds ~5% to recall, up to 25% bonus
                review_bonus = min(1.25, 1.0 + (num_reviews * 0.05))
                recall_prob *= review_bonus
            
            # 5. Apply RECENT WRONG penalty (dramatic for demo)
            if card.card_id in self._recent_wrong:
                penalty = self._recent_wrong[card.card_id]
                recall_prob *= penalty
            
            # Clamp to valid range
            recall_prob = max(0.05, min(0.95, recall_prob))
            
            # Priority = 1 - recall_prob (lower recall = higher priority)
            priority = 1.0 - recall_prob
            
            if priority >= min_priority:
                scheduled.append(ScheduledCard(
                    card=card,
                    recall_probability=recall_prob,
                    priority=priority
                ))
        
        # Sort by priority (highest first) and return top N
        scheduled.sort(key=lambda x: x.priority, reverse=True)
        return scheduled[:n_cards]
    
    def get_next_card(self) -> ScheduledCard:
        """Get the single most urgent card to review."""
        cards = self.get_scheduled_cards(n_cards=1)
        return cards[0] if cards else None
    
    def record_answer(self, card_id: int, correct: bool):
        """
        Record the result of a card review.
        
        Args:
            card_id: ID of the reviewed card
            correct: Whether the answer was correct
        """
        # Get current recall probability for logging
        features = self.extractor.get_features(card_id)
        features_df = pd.DataFrame([features])[FEATURE_COLS]
        recall_prob = self.model.predict_proba(features_df)[0][1]
        
        # Apply dramatic penalty/boost for demo purposes
        if correct:
            # Remove any penalty and boost slightly
            if card_id in self._recent_wrong:
                del self._recent_wrong[card_id]
        else:
            # Apply dramatic penalty for wrong answers
            current_penalty = self._recent_wrong.get(card_id, 1.0)
            self._recent_wrong[card_id] = current_penalty * self.WRONG_ANSWER_PENALTY
        
        # Record feedback
        self.extractor.record_feedback(card_id, correct, recall_prob)
    
    def get_session_stats(self) -> dict:
        """Get statistics for the current study session."""
        return self.extractor.get_session_stats()
    
    def get_card_details(self, card_id: int) -> Tuple[CardState, dict, float]:
        """
        Get detailed information about a card.
        
        Returns:
            Tuple of (CardState, features dict, recall probability)
        """
        card = self.extractor.get_card(card_id)
        features = self.extractor.get_features(card_id)
        features_df = pd.DataFrame([features])[FEATURE_COLS]
        recall_prob = self.model.predict_proba(features_df)[0][1]
        
        return card, features, recall_prob
    
    def reset_progress(self):
        """Reset all learning progress."""
        self._recent_wrong = {}  # Clear penalties
        self.extractor.reset_progress()


if __name__ == "__main__":
    # Test the scheduler
    project_root = Path(__file__).parent.parent
    model_path = project_root / "models" / "trained_model.pkl"
    data_dir = project_root / "data"
    
    print("Testing Card Scheduler")
    print("=" * 50)
    
    scheduler = CardScheduler(str(model_path), str(data_dir))
    
    # Get scheduled cards
    print("\nTop 5 cards to review (by priority):")
    print("-" * 50)
    
    for i, sc in enumerate(scheduler.get_scheduled_cards(5), 1):
        print(f"\n{i}. {sc.card.question}")
        print(f"   Recall probability: {sc.recall_probability:.1%}")
        print(f"   Priority: {sc.priority:.2f}")
        print(f"   Reason: {sc.priority_reason}")
        print(f"   Difficulty: {sc.card.difficulty}/5")
