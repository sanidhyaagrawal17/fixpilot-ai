"""Scenario 3: ModuleNotFoundError / ImportError
Typo in standard or internal helper import statement.
"""

DESCRIPTION = "ModuleNotFoundError: No module named 'utils.helper' in pipeline"

SOURCE_CODE = """# Bug: should import math instead of nonexistent math_tools
import math_tools

def calculate_circle_area(radius):
    return math_tools.pi * (radius ** 2)
"""

ERROR_TRACEBACK = """Traceback (most recent call last):
  File "solution.py", line 2, in <module>
    import math_tools
ModuleNotFoundError: No module named 'math_tools'"""

TEST_CODE = """from solution import calculate_circle_area
import math

def test_area():
    expected = math.pi * 4
    actual = calculate_circle_area(2)
    assert abs(actual - expected) < 1e-5
    print("ALL TESTS PASSED")

if __name__ == "__main__":
    test_area()
"""
