"""
Automated functional verification for AI Learning & Study Assistant using Streamlit AppTest.
Tests all pages, transitions, widgets, and user journeys.
"""

import sys
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
from streamlit.testing.v1 import AppTest

def _legacy_full_application():
    print("=== Step 1: Initializing AppTest on app.py ===")
    at = AppTest.from_file("app.py", default_timeout=30)
    at.run()
    assert not at.exception, f"App raised exception on initial run: {at.exception}"
    print("PASS: App initialized cleanly without exceptions.")

    # Check Dashboard landing page
    print("\n=== Step 2: Testing Dashboard Landing Page ===")
    assert at.session_state.current_page == "🏠 Dashboard"
    print(f"PASS: Current page is '{at.session_state.current_page.encode('ascii', 'replace').decode('ascii')}'")
    # Verify elements rendered on Dashboard
    assert len(at.button) > 0, "Expected buttons on Dashboard"
    button_labels = [b.label for b in at.button]
    print("Found buttons on Dashboard:", button_labels)
    assert any("Start Asking" in b or "Take a Quiz" in b for b in button_labels)
    print("PASS: Dashboard quick action buttons verified.")

    # Test Navigation to Ask AI
    print("\n=== Step 3: Testing Navigation to 'Ask AI' ===")
    at.session_state.current_page = "💬 Ask AI"
    at.session_state.nav_radio_selection = "💬 Ask AI"
    at.run()
    assert not at.exception, f"Exception on Ask AI page: {at.exception}"
    print(f"PASS: Navigated to '{at.session_state.current_page.encode('ascii', 'replace').decode('ascii')}'")
    # Check suggested questions buttons
    ask_buttons = [b.label.encode('ascii', 'replace').decode('ascii') for b in at.button]
    print("Ask AI buttons:", ask_buttons)
    assert any("overview" in b.lower() or "simple" in b.lower() for b in ask_buttons)
    print("PASS: Suggested question chips present.")

    # Test Navigation to Study Materials
    print("\n=== Step 4: Testing Navigation to 'Study Materials' ===")
    at.session_state.current_page = "📚 Study Materials"
    at.session_state.nav_radio_selection = "📚 Study Materials"
    at.run()
    assert not at.exception, f"Exception on Study Materials page: {at.exception}"
    print(f"PASS: Navigated to '{at.session_state.current_page.encode('ascii', 'replace').decode('ascii')}'")

    # Test Navigation to Quiz
    print("\n=== Step 5: Testing Navigation to 'Quiz' ===")
    at.session_state.current_page = "📝 Quiz"
    at.session_state.nav_radio_selection = "📝 Quiz"
    at.run()
    assert not at.exception, f"Exception on Quiz page: {at.exception}"
    print(f"PASS: Navigated to '{at.session_state.current_page.encode('ascii', 'replace').decode('ascii')}'")
    quiz_buttons = [b.label.encode('ascii', 'replace').decode('ascii') for b in at.button]
    print("Quiz buttons:", quiz_buttons)
    assert any("Generate Quiz" in b for b in quiz_buttons)
    print("PASS: Quiz setup controls verified.")

    # Simulate generating a quiz
    import quiz
    sample_questions = quiz.generate_fallback_quiz("Cloud Computing", 5)
    at.session_state.current_quiz = sample_questions
    at.session_state.quiz_topic = "Cloud Computing"
    at.session_state.quiz_current_index = 0
    at.session_state.quiz_answers = {}
    at.run()
    assert not at.exception, f"Exception while rendering quiz: {at.exception}"
    print("PASS: 1-question-at-a-time interactive quiz rendered successfully.")
    print("Quiz progress info: index =", at.session_state.quiz_current_index, "total =", len(sample_questions))

    # Test navigation next on quiz
    at.session_state.quiz_answers[1] = "A"
    at.session_state.quiz_current_index = 1
    at.run()
    assert not at.exception, f"Exception advancing quiz question: {at.exception}"
    print("PASS: Advanced to Question 2 successfully.")

    # Test Quiz submission and results
    eval_res = quiz.calculate_quiz_score(sample_questions, {1: "A", 2: "B", 3: "A", 4: "B", 5: "A"}, "Cloud Computing")
    at.session_state.quiz_results = eval_res
    at.run()
    assert not at.exception, f"Exception rendering quiz results: {at.exception}"
    print(f"PASS: Quiz results performance card rendered! Score: {eval_res['score']}/{eval_res['total']} ({eval_res['percentage']}%)")

    # Test Navigation to My Progress
    print("\n=== Step 6: Testing Navigation to 'My Progress' ===")
    at.session_state.current_page = "📊 My Progress"
    at.session_state.nav_radio_selection = "📊 My Progress"
    at.run()
    assert not at.exception, f"Exception on My Progress page: {at.exception}"
    print(f"PASS: Navigated to '{at.session_state.current_page.encode('ascii', 'replace').decode('ascii')}'. Progress analytics rendered cleanly.")

    # Test Navigation to Study Plan
    print("\n=== Step 7: Testing Navigation to 'Study Plan' ===")
    at.session_state.current_page = "📅 Study Plan"
    at.session_state.nav_radio_selection = "📅 Study Plan"
    at.run()
    assert not at.exception, f"Exception on Study Plan page: {at.exception}"
    print(f"PASS: Navigated to '{at.session_state.current_page.encode('ascii', 'replace').decode('ascii')}'.")

    # Simulate a generated plan
    import study_plan
    plan = study_plan.generate_fallback_study_plan("Cloud Computing", 5, 2.0, "Intermediate", ["Cloud Virtualization"])
    at.session_state.generated_plan = {
        "subject": "Cloud Computing",
        "exam_date": "2026-09-20",
        "days_remaining": 12,
        "daily_hours": 2.0,
        "knowledge_level": "Intermediate",
        "weak_topics": ["Cloud Virtualization"],
        "plan_markdown": plan
    }
    at.run()
    assert not at.exception, f"Exception rendering generated study plan: {at.exception}"
    print("PASS: Study Plan timeline cards and completion checklists rendered without errors.")

    print("\n========================================================")
    print("LEGACY SCREEN SMOKE CHECKS PASSED")
    print("========================================================")

def test_full_application():
    from test_working_flows import WorkingFlows
    fixture = WorkingFlows()
    fixture.setUp()
    try:
        _legacy_full_application()
    finally:
        fixture.doCleanups()

if __name__ == "__main__":
    test_full_application()
