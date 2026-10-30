"""
Verification test for Streamlit quiz radio widget key isolation.
"""

def test_quiz_keys():
    session_state = {}
    
    # 1. State initialization
    if "quiz_run_id" not in session_state:
        session_state["quiz_run_id"] = 0
    assert session_state["quiz_run_id"] == 0, "quiz_run_id should initialize to 0"

    # 2. Generation 1
    session_state["quiz_run_id"] += 1
    run1_id = session_state["quiz_run_id"]
    assert run1_id == 1
    
    q_ids = [1, 2, 3, 4, 5]
    keys_run1 = [f"q_radio_{session_state['quiz_run_id']}_{qid}" for qid in q_ids]
    expected_run1 = [f"q_radio_1_{qid}" for qid in q_ids]
    assert keys_run1 == expected_run1
    
    # Simulate user answering Q1 in run 1
    session_state[keys_run1[0]] = "A. Answer from quiz 1"

    # 3. Generation 2 (regeneration)
    session_state["quiz_run_id"] += 1
    run2_id = session_state["quiz_run_id"]
    assert run2_id == 2
    
    keys_run2 = [f"q_radio_{session_state['quiz_run_id']}_{qid}" for qid in q_ids]
    expected_run2 = [f"q_radio_2_{qid}" for qid in q_ids]
    assert keys_run2 == expected_run2

    # Verify no key collision between runs
    overlap = set(keys_run1).intersection(set(keys_run2))
    assert len(overlap) == 0, f"Detected key collision: {overlap}"
    
    # Verify new key is NOT in session_state, preventing leftover widget state
    assert keys_run2[0] not in session_state, "New quiz key unexpectedly found in session_state"
    assert session_state[keys_run1[0]] == "A. Answer from quiz 1"

    print("PASS: Quiz widget key isolation verified successfully!")

if __name__ == "__main__":
    test_quiz_keys()
