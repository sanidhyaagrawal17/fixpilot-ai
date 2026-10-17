"""Scenario 5: JavaScript Nullish Object TypeError
V8 engine error when attempting to access property on undefined object.
"""

DESCRIPTION = "JS TypeError: Cannot read properties of undefined (reading 'name')"

SOURCE_CODE = """function getUserDisplayName(user) {
    // Bug: user can be undefined/null leading to unhandled TypeError
    return user.name.toUpperCase();
}

module.exports = { getUserDisplayName };
"""

ERROR_TRACEBACK = """TypeError: Cannot read properties of undefined (reading 'name')
    at getUserDisplayName (solution.js:3:17)
    at Object.<anonymous> (test_harness.js:4:1)
    at Module._compile (node:internal/modules/cjs/loader:1565:14)"""

TEST_CODE = """const { getUserDisplayName } = require('./solution.js');
const assert = require('assert');

// Test valid user
assert.strictEqual(getUserDisplayName({ name: 'Alice' }), 'ALICE');

// Test null / undefined user safely handled
assert.strictEqual(getUserDisplayName(null), '');
assert.strictEqual(getUserDisplayName(undefined), '');

console.log("ALL JS TESTS PASSED");
"""
