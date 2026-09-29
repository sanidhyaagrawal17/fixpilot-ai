# FixPilot Demo Scenarios Walkthrough

This document outlines the four pre-built demonstration scenarios packaged into FixPilot for evaluation and the video demonstration.

---

## Scenario 1: Collection Retriever (IndexError)
- **Error**: `IndexError: list index out of range`
- **Fault**: Accessing `items[len(items)]` instead of `items[len(items) - 1]`.
- **Classification**: `TYPE` / Boundary Error via Nemotron Nano.
- **Tavily Grounding**: Queries Python documentation for zero-based indexing patterns.
- **Analysis**: Nemotron Ultra pinpoints off-by-one boundary failure.
- **Fix**: Replaces index with `len(items) - 1` and inserts null-guard for empty collections.
- **Verification**: Sandbox runs `test_retriever()` assertions → Passes.

---

## Scenario 2: Profile Record Parser (TypeError)
- **Error**: `TypeError: 'NoneType' object is not subscriptable`
- **Fault**: Accessing `user_record["name"]` when `user_record` can evaluate to `None`.
- **Classification**: `TYPE` via Nemotron Nano.
- **Tavily Grounding**: Queries Real Python guide on handling `None` in Python.
- **Analysis**: Nemotron Ultra reasons that API/database lookup misses return `None`.
- **Fix**: Replaces direct subscript access with `user_record.get("name", "") if user_record else ""`.
- **Verification**: Sandbox tests both valid dict and `None` parameter → Passes.

---

## Scenario 3: Pipeline Import (ModuleNotFoundError)
- **Error**: `ModuleNotFoundError: No module named 'math_tools'`
- **Fault**: Importing deprecated or incorrect module name.
- **Classification**: `IMPORT` via Nemotron Nano.
- **Analysis**: Identifies target function `pi` belonging to standard library `math`.
- **Fix**: Replaces `import math_tools` with standard library `import math`.
- **Verification**: Sandbox verifies `calculate_circle_area()` calculation matches `math.pi * 4` → Passes.

---

## Scenario 4: Binary Search Boundary (AssertionError)
- **Error**: `AssertionError: test assertion failed`
- **Fault**: Binary search initialized with `high = len(arr)` causing out-of-bounds or missed searches.
- **Classification**: `LOGIC` via Nemotron Nano.
- **Analysis**: Nemotron Ultra diagnoses off-by-one algorithm invariant in binary search.
- **Fix**: Corrects `high = len(arr) - 1`.
- **Verification**: Sandbox tests search across beginning, middle, end, and missing elements → Passes.
