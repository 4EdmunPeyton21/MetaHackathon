"""Root-level tasks package for validator discovery."""
from tasks.grader_easy import grade_easy
from tasks.grader_medium import grade_medium
from tasks.grader_hard import grade_hard

__all__ = ["grade_easy", "grade_medium", "grade_hard"]
