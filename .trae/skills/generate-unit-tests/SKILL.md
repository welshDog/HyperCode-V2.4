---
name: generate-unit-tests
description: Generate a comprehensive unit test suite for the selected code.
---

## Description

This skill analyzes the currently selected code and generates a comprehensive unit test suite using the project's testing framework (Jest or Vitest).

## When to use

- You have an existing function, class, or module without tests.
- You are refactoring code and want to lock in behavior before changes.
- You want to improve coverage for critical business logic.

## Instructions

1. Read the selected code and infer its behavior and edge cases.
2. Identify:
   - Happy Path scenarios (valid inputs and expected outputs).
   - Edge Cases (empty inputs, null/undefined, boundary values).
   - Error Cases (exceptions, rejected promises, invalid inputs).
3. Choose the correct test framework:
   - Use Jest or Vitest depending on what the project already uses.
4. Generate a test file that:
   - Follows the Arrange–Act–Assert pattern.
   - Groups related tests with clear `describe` blocks.
   - Uses mocks or test doubles for external dependencies.
5. Ensure tests are:
   - Deterministic and fast.
   - Easy to read and maintain.
6. At the end, briefly summarize what behavior is covered and what is intentionally not covered.

## Examples

**Example input (user intent)**

Generate unit tests for this `calculateTotal` function.

**Example output (high level)**

- A `calculateTotal.test.ts` file using Vitest.
- Tests for positive numbers, zero, negative numbers, and invalid input.
- Mocking of any external dependencies (e.g. discount service).
