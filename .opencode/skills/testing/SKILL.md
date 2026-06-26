---
name: testing
description: >-
  Use for testing tasks: writing unit, integration, and e2e tests; setting up
  test frameworks; achieving coverage goals; and testing strategies.
---

# Testing

## When to use
- Writing new tests for features
- Setting up a testing framework for a project
- Improving test coverage
- Debugging flaky tests
- Implementing TDD or property-based testing
- Reviewing test quality and completeness

## Test types & pyramid

```
        /\
       / e2e \
      /   ~10%  \
     /------------\
    / integration  \
   /    ~20%       \
  /------------------\
 /    unit ~70%       \
/______________________\
```

### Unit tests
- Test one function/class in isolation
- Mock/fake I/O (DB, network, file system)
- Run in milliseconds
- Structure: Arrange → Act → Assert

### Integration tests
- Test interaction between layers (route → controller → service → repo)
- Use test containers, in-memory DB, or dedicated test DB
- Run in seconds
- Cover: DB queries, API endpoints, middleware

### E2E tests
- Full system: browser → API → DB
- Use Playwright, Cypress, or Puppeteer
- Cover critical user flows (login, purchase, signup)
- Run in minutes (small set)

## AAA pattern
```python
def test_charge_fails_when_card_declined():
    # Arrange
    card = Card(number="4000000000000002", expiry="12/28")
    amount = Money(5000, "CLP")

    # Act
    result = payment_service.charge(card, amount)

    # Assert
    assert result.is_error()
    assert result.error == "card_declined"
```

## FIRST principles
- **Fast** — tests run in ms, not minutes
- **Isolated** — no shared state, no ordering dependency
- **Repeatable** — same result every time, any environment
- **Self-validating** — pass/fail, no manual interpretation
- **Thorough** — happy path + edge cases + errors
- **Timely** — written before or with the code

## Coverage targets
| Metric | Target |
|--------|--------|
| Line coverage | ≥ 80% |
| Branch coverage | ≥ 70% |
| Mutation score | ≥ 60% |
| Critical logic | 100% |

Coverage is a floor, not a goal. What matters is what you test.

## Language/testing tool reference

| Language | Unit | Integration | E2E |
|----------|------|-------------|-----|
| Python | pytest | pytest + httpx | Playwright |
| TypeScript | vitest / jest | supertest + vitest | Playwright |
| Go | go test | go test + httptest | Playwright |
| Java | JUnit 5 | SpringBootTest | Playwright |
| Rust | cargo test | cargo test + reqwest | — |

## TDD workflow
1. **Red** — write a test that fails
2. **Green** — write minimum code to pass
3. **Refactor** — clean up while tests stay green

## Property-based testing
Test invariants with random inputs:
```python
# Python (Hypothesis)
@given(st.lists(st.integers()))
def test_sort_always_returns_sorted(lst):
    result = sorted(lst)
    for i in range(len(result) - 1):
        assert result[i] <= result[i + 1]
```

## Good vs bad tests

### Good tests
- Test behaviors, not methods
- One logical assertion per test
- Descriptive names in English (sentence form)
- Fast and independent
- Readable from top to bottom

### Bad tests
- Test internal implementation (refactoring breaks them)
- Check multiple concerns in one test
- Use `sleep()` or time-dependent logic
- Depend on environment variables or external state
- Flaky (pass/fail unpredictably)

## Resources
- [Testing Trophy](https://kentcdodds.com/blog/the-testing-trophy-and-testing-classifications) — Kent C. Dodds
- [xUnit Test Patterns](http://xunitpatterns.com/) — Gerard Meszaros
- [Mutation Testing](https://pitest.org/) — PIT for Java
