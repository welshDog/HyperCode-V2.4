---
name: refactor-performance
description: Analyze and refactor selected code to improve performance.
---

## Description

This skill inspects the selected code for performance bottlenecks and proposes a refactored version that is more efficient and scalable.

## When to use

- A function or component feels slow or heavy.
- You see repeated computations or large loops.
- You suspect N+1 database queries or unnecessary re-renders.

## Instructions

1. Analyze the selected code for:
   - Unnecessary re-renders (React components).
   - N+1 query patterns or inefficient database access.
   - Heavy synchronous computations on the main thread.
   - Memory leaks or unnecessary object retention.
2. Explain the main performance issues found.
3. Propose a refactored version of the code that:
   - Reduces time complexity where possible.
   - Minimizes redundant computations or network calls.
   - Uses appropriate memoization, batching, or pagination techniques.
4. Clearly state:
   - Before vs after complexity (e.g. O(n²) to O(n)).
   - Any trade-offs introduced by the refactor.
5. Ensure the refactored code stays readable and maintainable.

## Examples

**Example input (user intent)**

Refactor this list rendering logic; it feels slow on large datasets.

**Example output (high level)**

- Explanation of why the current implementation is slow.
- Refactored React component using virtualization or memoization.
- Note on expected performance improvement.
