# Smart Flashcard Review System

An adaptive flashcard study system that uses **logistic regression** to predict recall probability and intelligently schedule reviews based on student feedback.

## Project Overview

This project demonstrates supervised machine learning applied to spaced repetition learning. The system:

1. **Predicts** whether you'll correctly recall a flashcard
2. **Prioritizes** cards you're likely to forget
3. **Adapts** to your learning patterns based on feedback

## Features

- **ML-Based Scheduling**: Uses logistic regression to predict recall probability
- **Adaptive Learning**: System improves as you study more
- **Forgetting Curve Simulation**: Synthetic data models realistic memory decay
- **Interactive CLI**: Simple command-line interface for study sessions
- **Web UI with Visualizations**: Flask-based web interface with real-time ML insights

## Installation

```bash
# Create virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Option 1: Web Interface (Recommended for Demos)

```bash
python src/web_app.py
```

Then open http://localhost:5000 in your browser.

The web interface features:
- **Left Panel (70%)**: Interactive flashcard study session
- **Right Panel (30%)**: Real-time ML visualizations showing:
  - Current card features (how the model "sees" the card)
  - Recall probability distribution across all cards
  - Feature importance (model coefficients)
  - Session progress tracking

### Option 2: Command Line Interface

```bash
python src/app.py
```

## Project Structure

```
smart_flashcards/
├── data/
│   ├── flashcards.csv          # Sample flashcard content
│   ├── synthetic_data.csv      # Generated training data
│   ├── cards_state.json        # Learning progress (runtime)
│   └── study_log.json          # Session history (runtime)
├── src/
│   ├── data_generator.py       # Synthetic data creation
│   ├── features.py             # Feature extraction
│   ├── model.py                # Model training/prediction
│   ├── scheduler.py            # Card scheduling logic
│   ├── app.py                  # CLI demo
│   └── web_app.py              # Flask web application
├── templates/
│   ├── base.html               # Base HTML template
│   └── index.html              # Main study interface
├── static/
│   ├── css/style.css           # Minimalist styles
│   └── js/app.js               # Frontend logic + Chart.js
├── models/
│   └── trained_model.pkl       # Saved model
├── notebooks/
│   └── exploration.ipynb       # Data analysis + model tuning
├── docs/
│   └── PROJECT_SUMMARY.md      # Detailed project documentation
├── requirements.txt
└── README.md
```

## How It Works

### The Classification Problem

**Goal**: Predict P(student recalls card correctly)

**Features**:
| Feature | Description |
|---------|-------------|
| `days_since_review` | Days since last study session |
| `num_reviews` | Total times this card was reviewed |
| `past_accuracy` | Historical correct rate for this card |
| `difficulty` | Card difficulty rating (1-5) |

### The Adaptive Feedback Loop

1. Model predicts recall probability for each card
2. Cards with LOW probability are prioritized (you might forget them!)
3. After you answer, feedback is recorded
4. Features update, changing future predictions

## API Endpoints (Web App)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main study interface |
| `/api/next-card` | GET | Get next card to review |
| `/api/answer` | POST | Submit answer, get next card |
| `/api/stats` | GET | Session statistics |
| `/api/all-cards` | GET | All cards with probabilities |
| `/api/model-info` | GET | Feature coefficients |
| `/api/reset` | POST | Reset study progress |

## Learning Outcomes

- Feature engineering for ML problems
- Logistic regression for binary classification
- Model evaluation (accuracy, precision, recall)
- End-to-end ML pipeline: data → training → inference → feedback
- Web application development with Flask
- Real-time data visualization with Chart.js
