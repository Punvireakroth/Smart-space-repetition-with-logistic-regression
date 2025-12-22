"""
Model Training and Prediction Module

Handles training the logistic regression model and making predictions
for flashcard recall probability.
"""

import pickle
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report


# Feature columns used by the model
FEATURE_COLS = ['days_since_review', 'num_reviews', 'past_accuracy', 'difficulty']


def train_model(data_path: str, model_save_path: str = None) -> LogisticRegression:
    """
    Train logistic regression model on flashcard study data.
    
    Args:
        data_path: Path to CSV file with training data
        model_save_path: Optional path to save the trained model
    
    Returns:
        Trained LogisticRegression model
    """
    # Load data
    df = pd.read_csv(data_path)
    
    # Prepare features and target
    X = df[FEATURE_COLS]
    y = df['correct']
    
    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    # Train model
    model = LogisticRegression(random_state=42, max_iter=1000)
    model.fit(X_train, y_train)
    
    # Evaluate
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"Model trained on {len(X_train)} samples")
    print(f"Test accuracy: {accuracy:.1%}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=['Incorrect', 'Correct']))
    
    # Feature importance
    print("Feature Coefficients:")
    for feat, coef in zip(FEATURE_COLS, model.coef_[0]):
        direction = "↑ recall" if coef > 0 else "↓ recall"
        print(f"  {feat}: {coef:+.3f} ({direction})")
    
    # Save model if path provided
    if model_save_path:
        Path(model_save_path).parent.mkdir(parents=True, exist_ok=True)
        with open(model_save_path, 'wb') as f:
            pickle.dump(model, f)
        print(f"\nModel saved to {model_save_path}")
    
    return model


def load_model(model_path: str) -> LogisticRegression:
    """
    Load a trained model from disk.
    
    Args:
        model_path: Path to the saved model file
    
    Returns:
        Trained LogisticRegression model
    """
    with open(model_path, 'rb') as f:
        return pickle.load(f)


def predict_recall_probability(
    model: LogisticRegression,
    days_since_review: float,
    num_reviews: int,
    past_accuracy: float,
    difficulty: int
) -> float:
    """
    Predict the probability that a student will correctly recall a flashcard.
    
    Args:
        model: Trained logistic regression model
        days_since_review: Days since the card was last reviewed
        num_reviews: Number of previous reviews
        past_accuracy: Historical correct rate (0-1)
        difficulty: Card difficulty (1-5)
    
    Returns:
        Probability of correct recall (0-1)
    """
    features = pd.DataFrame([{
        'days_since_review': days_since_review,
        'num_reviews': num_reviews,
        'past_accuracy': past_accuracy,
        'difficulty': difficulty
    }])
    
    return model.predict_proba(features)[0][1]


class RecallPredictor:
    """
    Wrapper class for the recall prediction model.
    
    Provides a clean interface for making predictions and handles
    model loading/saving.
    """
    
    def __init__(self, model_path: str = None):
        """
        Initialize predictor with an optional pre-trained model.
        
        Args:
            model_path: Path to load a pre-trained model from
        """
        self.model = None
        if model_path and Path(model_path).exists():
            self.model = load_model(model_path)
    
    def train(self, data_path: str, save_path: str = None):
        """Train the model on data."""
        self.model = train_model(data_path, save_path)
    
    def predict(
        self,
        days_since_review: float,
        num_reviews: int,
        past_accuracy: float,
        difficulty: int
    ) -> float:
        """Predict recall probability for a single card."""
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        return predict_recall_probability(
            self.model, days_since_review, num_reviews, past_accuracy, difficulty
        )
    
    def get_accuracy(self) -> float:
        """Get the model's test accuracy (if available)."""
        return getattr(self, '_test_accuracy', None)


if __name__ == "__main__":
    import sys
    
    # Default paths
    project_root = Path(__file__).parent.parent
    data_path = project_root / "data" / "synthetic_data.csv"
    model_path = project_root / "models" / "trained_model.pkl"
    
    print("=" * 50)
    print("Training Flashcard Recall Prediction Model")
    print("=" * 50)
    
    # Train and save model
    model = train_model(str(data_path), str(model_path))
    
    # Test predictions
    print("\n" + "=" * 50)
    print("Sample Predictions")
    print("=" * 50)
    
    test_cases = [
        (0, 5, 0.8, 2, "Just reviewed, good history, easy card"),
        (30, 1, 0.3, 4, "30 days ago, poor history, hard card"),
        (7, 3, 0.5, 3, "Week ago, medium history, medium difficulty"),
    ]
    
    for days, reviews, acc, diff, desc in test_cases:
        prob = predict_recall_probability(model, days, reviews, acc, diff)
        print(f"\n{desc}:")
        print(f"  Days since review: {days}, Reviews: {reviews}, Past accuracy: {acc}, Difficulty: {diff}")
        print(f"  → Predicted recall probability: {prob:.1%}")
