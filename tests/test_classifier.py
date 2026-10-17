import pytest
from core.classifier import ErrorClassifier
from core.models import ErrorSeverity


@pytest.mark.asyncio
async def test_classifier_index_error():
    classifier = ErrorClassifier()
    tb = """Traceback (most recent call last):
  File "main.py", line 4, in <module>
    item = items[len(items)]
IndexError: list index out of range"""
    res = await classifier.classify(tb)
    assert res.error_type == ErrorSeverity.TYPE
    assert "IndexError" in res.error_message or "out of range" in res.error_message.lower()
    assert res.affected_file == "main.py"
    assert res.affected_line == 4


@pytest.mark.asyncio
async def test_classifier_import_error():
    classifier = ErrorClassifier()
    tb = """Traceback (most recent call last):
  File "app.py", line 1, in <module>
    import nonexistent_library
ModuleNotFoundError: No module named 'nonexistent_library'"""
    res = await classifier.classify(tb)
    assert res.error_type == ErrorSeverity.IMPORT
    assert "nonexistent_library" in res.error_message
