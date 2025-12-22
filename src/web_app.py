#!/usr/bin/env python3
"""
Flask Web Application for Smart Flashcard System

Provides a web-based UI with real-time ML visualizations
for demonstrating the adaptive active recall system.
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from flask import Flask, render_template, jsonify, request
from src.scheduler import CardScheduler
from src.model import FEATURE_COLS, load_model

# Initialize Flask app
app = Flask(
    __name__,
    template_folder=str(project_root / "templates"),
    static_folder=str(project_root / "static")
)

# Paths
MODEL_PATH = project_root / "models" / "trained_model.pkl"
DATA_DIR = project_root / "data"

# Initialize scheduler (global instance)
scheduler = None


def get_scheduler():
    """Get or initialize the card scheduler."""
    global scheduler
    if scheduler is None:
        scheduler = CardScheduler(str(MODEL_PATH), str(DATA_DIR))
    return scheduler


# ============================================
# Page Routes
# ============================================

@app.route('/')
def index():
    """Main study interface."""
    return render_template('index.html')


# ============================================
# API Routes
# ============================================

@app.route('/api/next-card')
def api_next_card():
    """Get the next card to review."""
    sched = get_scheduler()
    card = sched.get_next_card()
    
    if card is None:
        return jsonify({'error': 'No cards available'}), 404
    
    features = sched.extractor.get_features(card.card.card_id)
    
    return jsonify({
        'card_id': card.card.card_id,
        'question': card.card.question,
        'answer': card.card.answer,
        'difficulty': card.card.difficulty,
        'recall_probability': round(card.recall_probability, 4),
        'priority': round(card.priority, 4),
        'priority_reason': card.priority_reason,
        'features': {
            'days_since_review': round(features['days_since_review'], 2),
            'num_reviews': features['num_reviews'],
            'past_accuracy': round(features['past_accuracy'], 3),
            'difficulty': features['difficulty']
        }
    })


@app.route('/api/answer', methods=['POST'])
def api_answer():
    """Submit an answer and get updated data."""
    sched = get_scheduler()
    data = request.get_json()
    
    card_id = data.get('card_id')
    correct = data.get('correct', False)
    
    if card_id is None:
        return jsonify({'error': 'card_id required'}), 400
    
    # Record the answer
    sched.record_answer(card_id, correct)
    
    # Get updated stats
    stats = sched.get_session_stats()
    
    # Get next card
    next_card = sched.get_next_card()
    next_card_data = None
    
    if next_card:
        features = sched.extractor.get_features(next_card.card.card_id)
        next_card_data = {
            'card_id': next_card.card.card_id,
            'question': next_card.card.question,
            'answer': next_card.card.answer,
            'difficulty': next_card.card.difficulty,
            'recall_probability': round(next_card.recall_probability, 4),
            'priority': round(next_card.priority, 4),
            'priority_reason': next_card.priority_reason,
            'features': {
                'days_since_review': round(features['days_since_review'], 2),
                'num_reviews': features['num_reviews'],
                'past_accuracy': round(features['past_accuracy'], 3),
                'difficulty': features['difficulty']
            }
        }
    
    return jsonify({
        'success': True,
        'recorded': {
            'card_id': card_id,
            'correct': correct
        },
        'stats': stats,
        'next_card': next_card_data
    })


@app.route('/api/stats')
def api_stats():
    """Get current session statistics."""
    sched = get_scheduler()
    stats = sched.get_session_stats()
    return jsonify(stats)


@app.route('/api/all-cards')
def api_all_cards():
    """Get all cards with their current probabilities."""
    sched = get_scheduler()
    cards = sched.get_scheduled_cards(n_cards=100)
    
    result = []
    for sc in cards:
        features = sched.extractor.get_features(sc.card.card_id)
        result.append({
            'card_id': sc.card.card_id,
            'question': sc.card.question[:50] + ('...' if len(sc.card.question) > 50 else ''),
            'difficulty': sc.card.difficulty,
            'recall_probability': round(sc.recall_probability, 4),
            'priority': round(sc.priority, 4),
            'num_reviews': features['num_reviews'],
            'past_accuracy': round(features['past_accuracy'], 3)
        })
    
    return jsonify(result)


@app.route('/api/model-info')
def api_model_info():
    """Get model information including feature coefficients."""
    model = load_model(str(MODEL_PATH))
    
    coefficients = {}
    for feat, coef in zip(FEATURE_COLS, model.coef_[0]):
        coefficients[feat] = round(float(coef), 4)
    
    return jsonify({
        'feature_names': FEATURE_COLS,
        'coefficients': coefficients,
        'intercept': round(float(model.intercept_[0]), 4)
    })


@app.route('/api/reset', methods=['POST'])
def api_reset():
    """Reset all study progress."""
    sched = get_scheduler()
    sched.reset_progress()
    return jsonify({'success': True, 'message': 'Progress reset'})


@app.route('/api/card/<int:card_id>')
def api_card_details(card_id):
    """Get detailed information about a specific card."""
    sched = get_scheduler()
    
    try:
        card, features, recall_prob = sched.get_card_details(card_id)
        return jsonify({
            'card_id': card.card_id,
            'question': card.question,
            'answer': card.answer,
            'difficulty': card.difficulty,
            'recall_probability': round(recall_prob, 4),
            'features': {
                'days_since_review': round(features['days_since_review'], 2),
                'num_reviews': features['num_reviews'],
                'past_accuracy': round(features['past_accuracy'], 3),
                'difficulty': features['difficulty']
            },
            'history': {
                'total_attempts': card.total_attempts,
                'correct_count': card.correct_count,
                'last_review': card.last_review
            }
        })
    except KeyError:
        return jsonify({'error': 'Card not found'}), 404


# ============================================
# Main Entry Point
# ============================================

if __name__ == '__main__':
    print("=" * 50)
    print("Smart Flashcard Web Application")
    print("=" * 50)
    print(f"\nStarting server at http://localhost:5000")
    print("Press Ctrl+C to stop\n")
    
    app.run(debug=True, host='0.0.0.0', port=5000)
