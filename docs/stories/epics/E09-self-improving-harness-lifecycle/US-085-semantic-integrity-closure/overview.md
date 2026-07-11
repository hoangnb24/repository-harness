# US-085 Semantic Integrity Closure

Close review findings F-023 through F-029 by enforcing one canonical timestamp
contract across version 2 lifecycle operations, rejecting malformed JSON-like
CLI list input, and making validator tests causally exercise selection,
operation parsing, and SQL proof validation independently.

Historical version 1 operations and malformed traces remain untouched.
