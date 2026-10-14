"""Domain core of AllergenTrace: allergen model and calculation rules.

Plain Python on purpose: this package must not import Django (NFR-08), so the
safety-relevant logic stays small and can be tested in isolation.
"""
