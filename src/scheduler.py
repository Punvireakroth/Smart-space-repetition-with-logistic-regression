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
    
    def __init__(self, model_path: str, data_dir: str = "data"):
        """
        Initialize the scheduler.
        
        Args:
            model_path: Path to the trained model file
            data_dir: Directory containing flashcards and state data
        """
        self.model = load_model(model_path)
        self.extractor = FeatureExtractor(data_dir)
        
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
            recall_prob = self.model.predict_proba(features_df)[0][1]
            
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
