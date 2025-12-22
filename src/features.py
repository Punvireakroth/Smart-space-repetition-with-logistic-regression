"""
Feature Extraction Module

Extracts features from flashcard study history for model predictions.
Manages the study log and card state tracking.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class CardState:
    """Tracks the learning state of a single flashcard."""
    card_id: int
    question: str
    answer: str
    difficulty: int
    last_review: Optional[str] = None  # ISO format datetime
    num_reviews: int = 0
    correct_count: int = 0
    total_attempts: int = 0
    
    @property
    def past_accuracy(self) -> float:
        """Calculate historical accuracy rate."""
        if self.total_attempts == 0:
            return 0.5  # Default for new cards
        return self.correct_count / self.total_attempts
    
    @property
    def days_since_review(self) -> float:
        """Calculate days since last review."""
        if self.last_review is None:
            return 30.0  # Default for never-reviewed cards
        
        last = datetime.fromisoformat(self.last_review)
        delta = datetime.now() - last
        return max(0, delta.total_seconds() / 86400)  # Convert to days


@dataclass
class StudySession:
    """Records a single study session event."""
    card_id: int
    timestamp: str
    correct: bool
    recall_probability: float


class FeatureExtractor:
    """
    Manages card states and extracts features for model predictions.
    
    Handles:
    - Loading/saving card states and study history
    - Extracting features from current card state
    - Recording study feedback and updating states
    """
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize the feature extractor.
        
        Args:
            data_dir: Directory for storing state files
        """
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.cards: Dict[int, CardState] = {}
        self.study_log: List[StudySession] = []
        
        # File paths
        self.cards_state_file = self.data_dir / "cards_state.json"
        self.study_log_file = self.data_dir / "study_log.json"
    
    def load_flashcards(self, flashcards_csv: str):
        """
        Load flashcards from CSV file.
        
        Args:
            flashcards_csv: Path to CSV with card_id, question, answer, difficulty
        """
        import pandas as pd
        df = pd.read_csv(flashcards_csv)
        
        for _, row in df.iterrows():
            card_id = int(row['card_id'])
            self.cards[card_id] = CardState(
                card_id=card_id,
                question=row['question'],
                answer=row['answer'],
                difficulty=int(row['difficulty'])
            )
        
        # Try to load existing state
        self._load_state()
    
    def get_features(self, card_id: int) -> Dict[str, float]:
        """
        Extract features for a card for model prediction.
        
        Args:
            card_id: ID of the flashcard
        
        Returns:
            Dictionary of features for the model
        """
        card = self.cards[card_id]
        
        return {
            'days_since_review': card.days_since_review,
            'num_reviews': card.num_reviews,
            'past_accuracy': card.past_accuracy,
            'difficulty': card.difficulty
        }
    
    def record_feedback(self, card_id: int, correct: bool, recall_prob: float):
        """
        Record study feedback and update card state.
        
        Args:
            card_id: ID of the reviewed card
            correct: Whether the answer was correct
            recall_prob: Model's predicted recall probability
        """
        card = self.cards[card_id]
        
        # Update card state
        card.last_review = datetime.now().isoformat()
        card.num_reviews += 1
        card.total_attempts += 1
        if correct:
            card.correct_count += 1
        
        # Log the session
        session = StudySession(
            card_id=card_id,
            timestamp=datetime.now().isoformat(),
            correct=correct,
            recall_probability=recall_prob
        )
        self.study_log.append(session)
        
        # Save state
        self._save_state()
    
    def get_all_cards(self) -> List[CardState]:
        """Get all flashcards."""
        return list(self.cards.values())
    
    def get_card(self, card_id: int) -> CardState:
        """Get a specific card by ID."""
        return self.cards[card_id]
    
    def get_session_stats(self) -> Dict:
        """Get statistics for the current session."""
        if not self.study_log:
            return {'total': 0, 'correct': 0, 'accuracy': 0.0}
        
        # Get today's sessions
        today = datetime.now().date()
        today_sessions = [
            s for s in self.study_log
            if datetime.fromisoformat(s.timestamp).date() == today
        ]
        
        if not today_sessions:
            return {'total': 0, 'correct': 0, 'accuracy': 0.0}
        
        correct = sum(1 for s in today_sessions if s.correct)
        total = len(today_sessions)
        
        return {
            'total': total,
            'correct': correct,
            'accuracy': correct / total if total > 0 else 0.0
        }
    
    def _save_state(self):
        """Save card states and study log to disk."""
        # Save card states
        cards_data = {
            str(cid): asdict(card) for cid, card in self.cards.items()
        }
        with open(self.cards_state_file, 'w') as f:
            json.dump(cards_data, f, indent=2)
        
        # Save study log
        log_data = [asdict(s) for s in self.study_log]
        with open(self.study_log_file, 'w') as f:
            json.dump(log_data, f, indent=2)
    
    def _load_state(self):
        """Load existing card states and study log."""
        # Load card states
        if self.cards_state_file.exists():
            with open(self.cards_state_file, 'r') as f:
                cards_data = json.load(f)
            
            for cid_str, data in cards_data.items():
                cid = int(cid_str)
                if cid in self.cards:
                    # Update existing card with saved state
                    self.cards[cid].last_review = data.get('last_review')
                    self.cards[cid].num_reviews = data.get('num_reviews', 0)
                    self.cards[cid].correct_count = data.get('correct_count', 0)
                    self.cards[cid].total_attempts = data.get('total_attempts', 0)
        
        # Load study log
        if self.study_log_file.exists():
            with open(self.study_log_file, 'r') as f:
                log_data = json.load(f)
            
            self.study_log = [
                StudySession(**s) for s in log_data
            ]
    
    def reset_progress(self):
        """Reset all learning progress (for testing)."""
        for card in self.cards.values():
            card.last_review = None
            card.num_reviews = 0
            card.correct_count = 0
            card.total_attempts = 0
        
        self.study_log = []
        self._save_state()


if __name__ == "__main__":
    # Test the feature extractor
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    
    extractor = FeatureExtractor(data_dir="data")
    extractor.load_flashcards("data/flashcards.csv")
    
    print("Loaded cards:")
    for card in extractor.get_all_cards()[:5]:
        features = extractor.get_features(card.card_id)
        print(f"  Card {card.card_id}: {card.question[:30]}...")
        print(f"    Features: {features}")
