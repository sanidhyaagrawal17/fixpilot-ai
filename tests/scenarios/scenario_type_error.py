"""Scenario 2: TypeError (NoneType object is not subscriptable)
Missing guard clause when an API or DB query returns None.
"""

DESCRIPTION = "TypeError: 'NoneType' object is not subscriptable in user profile parser"

SOURCE_CODE = """def process_user_profile(user_record):
    # Bug: user_record can be None if lookup fails
    return user_record["name"].upper()
"""

ERROR_TRACEBACK = """Traceback (most recent call last):
  File "solution.py", line 3, in process_user_profile
    return user_record["name"].upper()
TypeError: 'NoneType' object is not subscriptable"""

TEST_CODE = """from solution import process_user_profile

def test_profile_handler():
    assert process_user_profile({"name": "Sanidhya"}) == "SANIDHYA"
    # Null safe handling check:
    try:
        res = process_user_profile(None)
        assert res == "" or res is None or res == "UNKNOWN"
    except TypeError:
        assert False, "TypeError raised on None input"
    print("ALL TESTS PASSED")

if __name__ == "__main__":
    test_profile_handler()
"""
