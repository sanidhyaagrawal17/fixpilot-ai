"""Scenario 4: Logic Bug / Algorithm Boundary
Binary search algorithm with incorrect initial high boundary.
"""

DESCRIPTION = "AssertionError: binary search off-by-one boundary failure"

SOURCE_CODE = """def binary_search(arr, target):
    # Bug: high should be len(arr) - 1, not len(arr)
    low = 0
    high = len(arr)
    
    while low <= high:
        mid = (low + high) // 2
        if mid >= len(arr):
            break
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
            
    return -1
"""

ERROR_TRACEBACK = """Traceback (most recent call last):
  File "test_harness.py", line 4, in <module>
    assert binary_search([1, 3, 5, 7, 9], 9) == 4
AssertionError: test assertion failed"""

TEST_CODE = """from solution import binary_search

def test_search():
    arr = [1, 3, 5, 7, 9]
    assert binary_search(arr, 1) == 0
    assert binary_search(arr, 5) == 2
    assert binary_search(arr, 9) == 4
    assert binary_search(arr, 4) == -1
    print("ALL TESTS PASSED")

if __name__ == "__main__":
    test_search()
"""
