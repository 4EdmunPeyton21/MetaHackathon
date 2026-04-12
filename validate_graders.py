"""Quick validation: verify grader functions are importable and return valid scores."""
import importlib
import sys
import os

# Ensure project root is in path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_grader_import_and_call(module_path, func_name, label):
    """Simulate what the deep validator does: import module, get function, call it."""
    try:
        mod = importlib.import_module(module_path)
        grader_fn = getattr(mod, func_name)
        print(f"  [OK] {label}: imported {module_path}:{func_name}")
    except Exception as e:
        print(f"  [FAIL] {label}: import failed - {e}")
        return False

    # Test with seed data as both workspace and baseline (simulates smoke test)
    base = os.path.dirname(os.path.abspath(__file__))
    data_dirs = {
        "grade_easy": os.path.join(base, "pii_redactor_env", "data", "easy"),
        "grade_medium": os.path.join(base, "pii_redactor_env", "data", "medium"),
        "grade_hard": os.path.join(base, "pii_redactor_env", "data", "hard"),
    }
    
    data_dir = data_dirs.get(func_name, "")
    if not os.path.isdir(data_dir):
        print(f"  [WARN] {label}: data dir not found at {data_dir}")
        return True  # Import worked, just can't test score

    try:
        score = grader_fn(workspace_dir=data_dir, baseline_dir=data_dir)
        print(f"  [OK] {label}: score = {score}")
        
        if score <= 0.0 or score >= 1.0:
            print(f"  [FAIL] {label}: score {score} is OUT OF RANGE (must be 0 < score < 1)")
            return False
        else:
            print(f"  [OK] {label}: score {score} is in valid range (0, 1)")
            return True
    except Exception as e:
        print(f"  [FAIL] {label}: grader call failed - {e}")
        return False


print("=" * 60)
print("Phase 2 Deep Validation - Local Pre-check")
print("=" * 60)

graders = [
    ("pii_redactor_env.tasks.grader_easy", "grade_easy", "Easy"),
    ("pii_redactor_env.tasks.grader_medium", "grade_medium", "Medium"),
    ("pii_redactor_env.tasks.grader_hard", "grade_hard", "Hard"),
]

passed = 0
for mod, func, label in graders:
    print(f"\nTask: {label}")
    if test_grader_import_and_call(mod, func, label):
        passed += 1

print(f"\n{'=' * 60}")
if passed == 3:
    print(f"RESULT: ALL {passed}/3 graders PASSED")
else:
    print(f"RESULT: {passed}/3 graders passed - NEEDS FIXING")
print("=" * 60)
