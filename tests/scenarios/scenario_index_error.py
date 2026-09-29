"""Scenario 1: Off-by-one IndexError
Common list boundary condition error when indexing the last element.
"""

DESCRIPTION = "IndexError: list index out of range in collection retriever"

SOURCE_CODE = """def get_last_item(items):
    # Bug: len(items) is 1 past the valid index boundary
    return items[len(items)]
"""

ERROR_TRACEBACK = """Traceback (most recent call last):
  File "solution.py", line 3, in get_last_item
    return items[len(items)]
IndexError: list index out of range"""

TEST_CODE = """from solution import get_last_item

def test_retriever():
    assert get_last_item([10, 20, 30]) == 30
    assert get_last_item(["alpha", "beta"]) == "beta"
    print("ALL TESTS PASSED")

if __name__ == "__main__":
    test_retriever()
"""
