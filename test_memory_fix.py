import copy
import os
import shutil
from pathlib import Path
import memory
from config import MEMORY_FILE

def _run_checks():
    print("=== Running Memory Bug Fix Verification ===")

    backup_path = MEMORY_FILE.with_suffix(".json.bak")
    has_backup = False
    if MEMORY_FILE.exists():
        shutil.copyfile(MEMORY_FILE, backup_path)
        has_backup = True
        MEMORY_FILE.unlink()

    try:
        # 1. Baseline check of DEFAULT_MEMORY_STRUCTURE
        print("1. Checking initial state of DEFAULT_MEMORY_STRUCTURE...")
        assert memory.DEFAULT_MEMORY_STRUCTURE["topics_studied"] == [], "topics_studied should be empty initially"
        assert memory.DEFAULT_MEMORY_STRUCTURE["quiz_history"] == [], "quiz_history should be empty initially"
        assert memory.DEFAULT_MEMORY_STRUCTURE["weak_topics"] == [], "weak_topics should be empty initially"
        assert memory.DEFAULT_MEMORY_STRUCTURE["recent_questions"] == [], "recent_questions should be empty initially"
        print("   PASS: DEFAULT_MEMORY_STRUCTURE is pristine.")

        # 2. Simulate first run when MEMORY_FILE does not exist
        print("2. Simulating cold start: adding a topic without existing memory file...")
        assert not MEMORY_FILE.exists(), "Memory file must not exist before cold start test"
        
        memory.add_topic_studied("Deep Learning Basics")
        
        # Verify DEFAULT_MEMORY_STRUCTURE was NOT mutated
        assert memory.DEFAULT_MEMORY_STRUCTURE["topics_studied"] == [], (
            f"MUTATION DETECTED: DEFAULT_MEMORY_STRUCTURE['topics_studied'] was mutated to "
            f"{memory.DEFAULT_MEMORY_STRUCTURE['topics_studied']}"
        )
        print("   PASS: DEFAULT_MEMORY_STRUCTURE was not mutated after add_topic_studied.")

        # Verify memory file has the topic
        mem = memory.load_memory()
        assert mem["topics_studied"] == ["Deep Learning Basics"], f"Expected ['Deep Learning Basics'], got {mem['topics_studied']}"
        print("   PASS: memory file contains the added topic.")

        # 3. Call clear_memory() and reload
        print("3. Calling clear_memory() and verifying reset...")
        memory.clear_memory()
        reloaded = memory.load_memory()
        assert reloaded["topics_studied"] == [], f"Expected empty topics_studied after clear_memory(), got {reloaded['topics_studied']}"
        assert memory.DEFAULT_MEMORY_STRUCTURE["topics_studied"] == [], "DEFAULT_MEMORY_STRUCTURE must still be empty"
        print("   PASS: clear_memory() completely reset memory to empty list.")

        # 4. Test mutation safety on add_question and add_quiz_result
        print("4. Testing mutation safety for questions and quiz results...")
        memory.add_question("What is backpropagation?", topic="Neural Networks")
        memory.add_quiz_result("Neural Networks", score=2, total=5, percentage=40.0, weak_areas=["Gradients"])
        
        # Check DEFAULT_MEMORY_STRUCTURE integrity
        assert memory.DEFAULT_MEMORY_STRUCTURE["topics_studied"] == []
        assert memory.DEFAULT_MEMORY_STRUCTURE["quiz_history"] == []
        assert memory.DEFAULT_MEMORY_STRUCTURE["weak_topics"] == []
        assert memory.DEFAULT_MEMORY_STRUCTURE["recent_questions"] == []
        print("   PASS: DEFAULT_MEMORY_STRUCTURE remained unaffected by question and quiz additions.")

        # 5. Clear again and verify all lists are empty
        print("5. Clearing memory again...")
        memory.clear_memory()
        clean_mem = memory.load_memory()
        for key in ["topics_studied", "quiz_history", "weak_topics", "recent_questions"]:
            assert clean_mem[key] == [], f"Key {key} was not cleared properly"
            assert memory.DEFAULT_MEMORY_STRUCTURE[key] == [], f"DEFAULT_MEMORY_STRUCTURE key {key} was mutated"
        print("   PASS: All keys clean after clear_memory().")

        # 6. Test corrupted JSON fallback branch
        print("6. Testing corrupted JSON fallback branch...")
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            f.write("{invalid_json: true,")
        corrupt_loaded = memory.load_memory()
        assert corrupt_loaded["topics_studied"] == []
        corrupt_loaded["topics_studied"].append("Testing Mutation on Corrupt Fallback")
        assert memory.DEFAULT_MEMORY_STRUCTURE["topics_studied"] == [], "DEFAULT_MEMORY_STRUCTURE mutated via corrupt branch!"
        print("   PASS: Corrupt fallback branch properly uses isolated deep copy.")

        print("\nALL VERIFICATION TESTS PASSED SUCCESSFULLY!")

    finally:
        # Cleanup and restore backup if it existed
        if has_backup and backup_path.exists():
            shutil.copyfile(backup_path, MEMORY_FILE)
            backup_path.unlink()
            print("Restored original memory.json backup.")
        elif MEMORY_FILE.exists():
            memory.clear_memory()

def run_tests():
    import tempfile
    from unittest.mock import patch
    with tempfile.TemporaryDirectory() as folder:
        isolated = Path(folder) / 'memory.json'
        with patch.object(memory, 'MEMORY_FILE', isolated), patch.dict(globals(), {'MEMORY_FILE': isolated}):
            _run_checks()

if __name__ == "__main__":
    run_tests()
