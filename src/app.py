#!/usr/bin/env python3
"""
Smart Flashcard CLI Application

An interactive flashcard study app that uses ML to prioritize
cards you're likely to forget.
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.scheduler import CardScheduler, ScheduledCard


def clear_screen():
    """Clear the terminal screen."""
    print("\033[2J\033[H", end="")


def print_header(text: str, char: str = "="):
    """Print a formatted header."""
    print()
    print(char * 60)
    print(f"  {text}")
    print(char * 60)


def print_card(scheduled_card: ScheduledCard, card_num: int, total: int):
    """Display a flashcard question."""
    card = scheduled_card.card
    
    print()
    print("-" * 60)
    print(f"  Card {card_num}/{total}  |  Difficulty: {'★' * card.difficulty}{'☆' * (5 - card.difficulty)}")
    print(f"  Predicted recall: {scheduled_card.recall_probability:.0%} ({scheduled_card.priority_reason})")
    print("-" * 60)
    print()
    print(f"  Q: {card.question}")
    print()


def print_result(correct: bool, answer: str, new_prob: float):
    """Display the result after answering."""
    if correct:
        print(f"\n  ✓ Correct! The answer is: {answer}")
    else:
        print(f"\n  ✗ Incorrect. The answer was: {answer}")
    print(f"  (Your next recall probability for this card will be updated)")


def print_session_summary(stats: dict, total_cards: int):
    """Display session summary."""
    print_header("Session Complete!", "~")
    print()
    print(f"  Cards reviewed: {stats['total']}/{total_cards}")
    print(f"  Correct answers: {stats['correct']}")
    print(f"  Accuracy: {stats['accuracy']:.0%}")
    print()
    print("  Your progress has been saved!")
    print("  Cards you struggled with will be prioritized next time.")
    print()


def run_study_session(scheduler: CardScheduler, n_cards: int = 5):
    """
    Run an interactive study session.
    
    Args:
        scheduler: The card scheduler
        n_cards: Number of cards to study
    """
    # Get cards to review
    cards_to_review = scheduler.get_scheduled_cards(n_cards)
    
    if not cards_to_review:
        print("\nNo cards to review! Add some flashcards first.")
        return
    
    print_header("Smart Flashcard Study Session")
    print(f"\n  Cards to review: {len(cards_to_review)}")
    print("  Type your answer, then press Enter.")
    print("  Type 'q' to quit, 's' to skip a card.")
    
    cards_completed = 0
    
    for i, scheduled_card in enumerate(cards_to_review, 1):
        card = scheduled_card.card
        
        # Show the card
        print_card(scheduled_card, i, len(cards_to_review))
        
        # Get user input
        try:
            user_input = input("  Your answer: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n  Session interrupted.")
            break
        
        # Handle special commands
        if user_input.lower() == 'q':
            print("\n  Quitting session...")
            break
        elif user_input.lower() == 's':
            print("  Skipped.")
            continue
        
        # Show the answer and ask if correct
        print(f"\n  Answer: {card.answer}")
        
        while True:
            try:
                check = input("\n  Were you correct? (y/n): ").strip().lower()
                if check in ('y', 'yes', '1'):
                    correct = True
                    break
                elif check in ('n', 'no', '0'):
                    correct = False
                    break
                else:
                    print("  Please enter 'y' or 'n'")
            except (KeyboardInterrupt, EOFError):
                correct = False
                break
        
        # Record the result
        scheduler.record_answer(card.card_id, correct)
        
        # Show feedback
        _, _, new_prob = scheduler.get_card_details(card.card_id)
        print_result(correct, card.answer, new_prob)
        
        cards_completed += 1
        
        # Pause between cards
        if i < len(cards_to_review):
            try:
                input("\n  Press Enter for next card...")
            except (KeyboardInterrupt, EOFError):
                break
    
    # Show session summary
    stats = scheduler.get_session_stats()
    print_session_summary(stats, cards_completed)


def show_all_cards(scheduler: CardScheduler):
    """Display all cards with their current status."""
    print_header("All Flashcards")
    
    cards = scheduler.get_scheduled_cards(n_cards=100)
    
    print(f"\n  {'#':<3} {'Question':<35} {'Recall':<8} {'Reviews':<8} {'Diff'}")
    print("  " + "-" * 65)
    
    for i, sc in enumerate(cards, 1):
        card = sc.card
        q = card.question[:32] + "..." if len(card.question) > 35 else card.question
        print(f"  {i:<3} {q:<35} {sc.recall_probability:>6.0%}  {card.num_reviews:>6}   {'★' * card.difficulty}")
    
    print()


def main_menu():
    """Display the main menu and get user choice."""
    print()
    print("  1. Start study session (5 cards)")
    print("  2. Quick review (3 cards)")
    print("  3. Long session (10 cards)")
    print("  4. View all cards")
    print("  5. Reset progress")
    print("  6. Quit")
    print()
    
    try:
        choice = input("  Select option (1-6): ").strip()
        return choice
    except (KeyboardInterrupt, EOFError):
        return '6'


def main():
    """Main entry point for the CLI app."""
    # Setup paths
    model_path = project_root / "models" / "trained_model.pkl"
    data_dir = project_root / "data"
    
    # Check if model exists
    if not model_path.exists():
        print("Error: Model not found. Please run 'python src/model.py' first.")
        sys.exit(1)
    
    # Initialize scheduler
    try:
        scheduler = CardScheduler(str(model_path), str(data_dir))
    except Exception as e:
        print(f"Error initializing: {e}")
        sys.exit(1)
    
    # Welcome message
    clear_screen()
    print_header("Smart Flashcard Review System")
    print()
    print("  Welcome! This app uses ML to prioritize cards you might forget.")
    print("  Cards with lower predicted recall are shown first.")
    
    # Main loop
    while True:
        choice = main_menu()
        
        if choice == '1':
            run_study_session(scheduler, n_cards=5)
        elif choice == '2':
            run_study_session(scheduler, n_cards=3)
        elif choice == '3':
            run_study_session(scheduler, n_cards=10)
        elif choice == '4':
            show_all_cards(scheduler)
        elif choice == '5':
            confirm = input("  Reset all progress? (y/n): ").strip().lower()
            if confirm == 'y':
                scheduler.reset_progress()
                print("  Progress reset!")
        elif choice == '6' or choice.lower() == 'q':
            print("\n  Thanks for studying! See you next time.\n")
            break
        else:
            print("  Invalid option. Please try again.")


if __name__ == "__main__":
    main()
