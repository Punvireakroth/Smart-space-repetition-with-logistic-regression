/**
 * Smart Flashcards - Frontend Application
 * 
 * Simplified UI with intuitive visualizations for demonstrating
 * how ML-powered active recall works.
 */

// ============================================
// Configuration - Adjust these for visual impact
// ============================================

const CONFIG = {
    // Thresholds for color coding (more aggressive for faster visual distinction)
    THRESHOLD_HIGH: 0.60,    // 60%+ = strong (green)
    THRESHOLD_MEDIUM: 0.35,  // 35-60% = okay (yellow)
    // Below 35% = weak (red)
    
    // Amplification factor - makes small changes more visible
    // Set > 1 to exaggerate changes, 1 = no change
    AMPLIFY_FACTOR: 1.3,
    
    // Total cards for progress tracking
    TOTAL_CARDS: 8
};

// ============================================
// State Management
// ============================================

const state = {
    currentCard: null,
    allCards: [],
    stats: { total: 0, correct: 0, accuracy: 0 }
};

// ============================================
// DOM Elements
// ============================================

const elements = {
    // States
    loadingState: document.getElementById('loadingState'),
    questionState: document.getElementById('questionState'),
    answerState: document.getElementById('answerState'),
    
    // Card content
    questionText: document.getElementById('questionText'),
    questionText2: document.getElementById('questionText2'),
    answerText: document.getElementById('answerText'),
    cardDifficulty: document.getElementById('cardDifficulty'),
    cardDifficulty2: document.getElementById('cardDifficulty2'),
    recallValue: document.getElementById('recallValue'),
    recallValue2: document.getElementById('recallValue2'),
    priorityText: document.getElementById('priorityText'),
    currentCardId: document.getElementById('currentCardId'),
    
    // Explanation items
    explainDays: document.getElementById('explainDays'),
    explainReviews: document.getElementById('explainReviews'),
    explainAccuracy: document.getElementById('explainAccuracy'),
    explainDifficulty: document.getElementById('explainDifficulty'),
    
    // Gauge
    gaugeFill: document.getElementById('gaugeFill'),
    gaugeValue: document.getElementById('gaugeValue'),
    gaugeInterpretation: document.getElementById('gaugeInterpretation'),
    
    // Cards grid
    cardsGrid: document.getElementById('cardsGrid'),
    
    // Stats
    statReviewed: document.getElementById('statReviewed'),
    statCorrect: document.getElementById('statCorrect'),
    statAccuracy: document.getElementById('statAccuracy'),
    
    // Progress
    progressBar: document.getElementById('progressBar'),
    progressText: document.getElementById('progressText'),
    
    // Buttons
    showAnswerBtn: document.getElementById('showAnswerBtn'),
    correctBtn: document.getElementById('correctBtn'),
    incorrectBtn: document.getElementById('incorrectBtn'),
    resetBtn: document.getElementById('resetBtn'),
    viewAllBtn: document.getElementById('viewAllBtn'),
    
    // Modal
    modal: document.getElementById('cardsModal'),
    closeModal: document.getElementById('closeModal'),
    cardsTableBody: document.getElementById('cardsTableBody')
};

// ============================================
// API Functions
// ============================================

async function fetchNextCard() {
    try {
        const response = await fetch('/api/next-card');
        if (!response.ok) throw new Error('Failed to fetch card');
        return await response.json();
    } catch (error) {
        console.error('Error fetching next card:', error);
        return null;
    }
}

async function submitAnswer(cardId, correct) {
    try {
        const response = await fetch('/api/answer', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ card_id: cardId, correct })
        });
        if (!response.ok) throw new Error('Failed to submit answer');
        return await response.json();
    } catch (error) {
        console.error('Error submitting answer:', error);
        return null;
    }
}

async function fetchAllCards() {
    try {
        const response = await fetch('/api/all-cards');
        if (!response.ok) throw new Error('Failed to fetch cards');
        return await response.json();
    } catch (error) {
        console.error('Error fetching all cards:', error);
        return [];
    }
}

async function fetchStats() {
    try {
        const response = await fetch('/api/stats');
        if (!response.ok) throw new Error('Failed to fetch stats');
        return await response.json();
    } catch (error) {
        console.error('Error fetching stats:', error);
        return { total: 0, correct: 0, accuracy: 0 };
    }
}

async function resetProgress() {
    try {
        const response = await fetch('/api/reset', { method: 'POST' });
        if (!response.ok) throw new Error('Failed to reset');
        return await response.json();
    } catch (error) {
        console.error('Error resetting:', error);
        return null;
    }
}

// ============================================
// Helper Functions
// ============================================

/**
 * Amplify probability to make changes more visible
 * Uses a non-linear transformation centered at 0.5
 */
function amplifyProbability(probability) {
    // Apply amplification: push values away from 0.5
    const centered = probability - 0.5;
    const amplified = 0.5 + centered * CONFIG.AMPLIFY_FACTOR;
    // Clamp to valid range
    return Math.max(0, Math.min(1, amplified));
}

/**
 * Get recall level based on adjusted thresholds
 */
function getRecallLevel(probability) {
    const amplified = amplifyProbability(probability);
    if (amplified >= CONFIG.THRESHOLD_HIGH) return 'high';
    if (amplified >= CONFIG.THRESHOLD_MEDIUM) return 'medium';
    return 'low';
}

/**
 * Get color for recall probability
 */
function getRecallColor(probability) {
    const level = getRecallLevel(probability);
    if (level === 'high') return '#22c55e';  // green
    if (level === 'medium') return '#f59e0b'; // yellow
    return '#ef4444'; // red
}

function getRecallInterpretation(probability) {
    const percent = Math.round(probability * 100);
    const level = getRecallLevel(probability);
    
    if (level === 'high') {
        return `Strong memory (${percent}%). You'll likely remember this. Reviewing strengthens it further.`;
    } else if (level === 'medium') {
        return `Moderate recall (${percent}%). Could go either way - good time to review!`;
    } else {
        return `Weak memory (${percent}%). High chance of forgetting - that's why it's prioritized!`;
    }
}

function formatDaysSince(days) {
    if (days >= 30) return 'Never reviewed';
    if (days < 1) return 'Today';
    if (days < 2) return 'Yesterday';
    return `${Math.round(days)} days ago`;
}

// ============================================
// UI Update Functions
// ============================================

function showState(stateName) {
    elements.loadingState.style.display = 'none';
    elements.questionState.style.display = 'none';
    elements.answerState.style.display = 'none';
    
    if (stateName === 'loading') {
        elements.loadingState.style.display = 'flex';
    } else if (stateName === 'question') {
        elements.questionState.style.display = 'flex';
    } else if (stateName === 'answer') {
        elements.answerState.style.display = 'flex';
    }
}

function renderDifficulty(difficulty) {
    let stars = '';
    for (let i = 0; i < 5; i++) {
        if (i < difficulty) {
            stars += '<span class="filled">&#9733;</span>';
        } else {
            stars += '<span class="empty">&#9734;</span>';
        }
    }
    return stars;
}

function updateCardDisplay(card) {
    if (!card) return;
    
    state.currentCard = card;
    elements.currentCardId.dataset.cardId = card.card_id;
    
    // Update question text
    elements.questionText.textContent = card.question;
    elements.questionText2.textContent = card.question;
    elements.answerText.textContent = card.answer;
    
    // Update difficulty stars
    const difficultyHtml = renderDifficulty(card.difficulty);
    elements.cardDifficulty.innerHTML = difficultyHtml;
    elements.cardDifficulty2.innerHTML = difficultyHtml;
    
    // Update recall probability
    const recallPercent = Math.round(card.recall_probability * 100);
    elements.recallValue.textContent = recallPercent;
    elements.recallValue2.textContent = recallPercent;
    
    // Update priority reason
    elements.priorityText.textContent = card.priority_reason;
    
    // Update explanation box
    if (card.features) {
        elements.explainDays.textContent = formatDaysSince(card.features.days_since_review);
        elements.explainReviews.textContent = card.features.num_reviews === 0 
            ? 'Never practiced' 
            : `${card.features.num_reviews} time${card.features.num_reviews > 1 ? 's' : ''}`;
        elements.explainAccuracy.textContent = card.features.num_reviews === 0 
            ? 'No data yet' 
            : `${Math.round(card.features.past_accuracy * 100)}%`;
        elements.explainDifficulty.textContent = ['Easy', 'Easy', 'Medium', 'Hard', 'Hard'][card.difficulty - 1] || 'Medium';
    }
    
    // Update gauge
    updateGauge(card.recall_probability);
    
    // Update cards grid to highlight current
    updateCardsGrid();
    
    showState('question');
}

function updateGauge(probability) {
    const percent = Math.round(probability * 100);
    const level = getRecallLevel(probability);
    
    elements.gaugeFill.style.width = `${percent}%`;
    elements.gaugeFill.className = `gauge-fill ${level}`;
    elements.gaugeValue.textContent = percent;
    elements.gaugeInterpretation.textContent = getRecallInterpretation(probability);
}

function updateStats(stats) {
    state.stats = stats;
    
    elements.statReviewed.textContent = stats.total;
    elements.statCorrect.textContent = stats.correct;
    elements.statAccuracy.textContent = Math.round(stats.accuracy * 100) + '%';
    
    // Update progress bar
    const progressPercent = Math.min(stats.total / CONFIG.TOTAL_CARDS * 100, 100);
    elements.progressBar.style.width = progressPercent + '%';
    elements.progressText.textContent = `${stats.total} of ${CONFIG.TOTAL_CARDS} cards reviewed today`;
}

/**
 * Create SVG circular progress ring
 */
function createProgressRing(percent, color, cardNum, isCurrent) {
    const size = 56;
    const strokeWidth = 4;
    const radius = (size - strokeWidth) / 2;
    const circumference = radius * 2 * Math.PI;
    const offset = circumference - (percent / 100) * circumference;
    
    return `
        <div class="card-ring ${isCurrent ? 'current' : ''}" data-card-id="${cardNum - 1}">
            <svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}">
                <!-- Background circle -->
                <circle 
                    cx="${size/2}" 
                    cy="${size/2}" 
                    r="${radius}"
                    fill="none"
                    stroke="#e5e7eb"
                    stroke-width="${strokeWidth}"
                />
                <!-- Progress circle -->
                <circle 
                    cx="${size/2}" 
                    cy="${size/2}" 
                    r="${radius}"
                    fill="none"
                    stroke="${color}"
                    stroke-width="${strokeWidth}"
                    stroke-linecap="round"
                    stroke-dasharray="${circumference}"
                    stroke-dashoffset="${offset}"
                    transform="rotate(-90 ${size/2} ${size/2})"
                    class="progress-ring-circle"
                />
            </svg>
            <div class="card-ring-content">
                <span class="card-ring-num">${cardNum}</span>
                <span class="card-ring-percent">${percent}%</span>
            </div>
        </div>
    `;
}

function updateCardsGrid() {
    if (state.allCards.length === 0) return;
    
    const currentId = state.currentCard?.card_id;
    
    elements.cardsGrid.innerHTML = state.allCards.map(card => {
        const percent = Math.round(card.recall_probability * 100);
        const color = getRecallColor(card.recall_probability);
        const isCurrent = card.card_id === currentId;
        
        return createProgressRing(percent, color, card.card_id + 1, isCurrent);
    }).join('');
}

function updateCardsTable() {
    const currentId = state.currentCard?.card_id;
    
    elements.cardsTableBody.innerHTML = state.allCards.map(card => {
        const level = getRecallLevel(card.recall_probability);
        const isCurrent = card.card_id === currentId;
        const percent = Math.round(card.recall_probability * 100);
        
        return `
            <tr class="${isCurrent ? 'current-row' : ''}">
                <td>${card.card_id + 1}</td>
                <td>${card.question}</td>
                <td class="recall-cell ${level}">${percent}%</td>
                <td>${card.num_reviews}</td>
                <td>${card.num_reviews > 0 ? Math.round(card.past_accuracy * 100) + '%' : '-'}</td>
                <td>${'&#9733;'.repeat(card.difficulty)}${'&#9734;'.repeat(5 - card.difficulty)}</td>
            </tr>
        `;
    }).join('');
}

// ============================================
// Event Handlers
// ============================================

async function handleShowAnswer() {
    showState('answer');
}

async function handleAnswer(correct) {
    if (!state.currentCard) return;
    
    showState('loading');
    
    const result = await submitAnswer(state.currentCard.card_id, correct);
    
    if (result) {
        // Update stats
        updateStats(result.stats);
        
        // Refresh all cards data
        state.allCards = await fetchAllCards();
        updateCardsGrid();
        
        // Show next card
        if (result.next_card) {
            updateCardDisplay(result.next_card);
        } else {
            elements.loadingState.innerHTML = '<p>All cards reviewed! Great job!</p>';
            showState('loading');
        }
    }
}

async function handleReset() {
    if (!confirm('Are you sure you want to reset all progress? This will clear your study history.')) return;
    
    showState('loading');
    await resetProgress();
    
    // Reload everything
    await init();
}

function handleViewAll() {
    updateCardsTable();
    elements.modal.classList.add('active');
}

function handleCloseModal() {
    elements.modal.classList.remove('active');
}

// ============================================
// Initialization
// ============================================

async function init() {
    // Show loading state
    showState('loading');
    
    // Load initial data
    const [card, stats, allCards] = await Promise.all([
        fetchNextCard(),
        fetchStats(),
        fetchAllCards()
    ]);
    
    // Store all cards
    state.allCards = allCards;
    
    // Update stats
    updateStats(stats);
    
    // Update cards grid
    updateCardsGrid();
    
    // Show first card
    if (card) {
        updateCardDisplay(card);
    } else {
        elements.loadingState.innerHTML = '<p>No cards available. Please add flashcards first.</p>';
    }
}

// ============================================
// Event Listeners
// ============================================

document.addEventListener('DOMContentLoaded', () => {
    // Initialize the app
    init();
    
    // Button event listeners
    elements.showAnswerBtn.addEventListener('click', handleShowAnswer);
    elements.correctBtn.addEventListener('click', () => handleAnswer(true));
    elements.incorrectBtn.addEventListener('click', () => handleAnswer(false));
    elements.resetBtn.addEventListener('click', handleReset);
    elements.viewAllBtn.addEventListener('click', handleViewAll);
    elements.closeModal.addEventListener('click', handleCloseModal);
    
    // Close modal on background click
    elements.modal.addEventListener('click', (e) => {
        if (e.target === elements.modal) {
            handleCloseModal();
        }
    });
    
    // Close modal on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && elements.modal.classList.contains('active')) {
            handleCloseModal();
        }
    });
});
