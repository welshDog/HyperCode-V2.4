# 🛠️ Agent Skills Library

**Instructions:**
1. Go to **Settings > Rules & Skills > Skills**.
2. Click **Create Skill** for each item below.
3. Paste the provided prompt content.

---

## Skill 1: Generate Unit Tests
**Name:** `generate-unit-tests`
**Description:** Generates comprehensive unit tests for the selected code.
**Prompt Content:**
```
Analyze the selected code. Generate a comprehensive unit test suite using our project's testing framework (Jest/Vitest).
Include:
1. Happy Path tests (valid inputs).
2. Edge Case tests (empty inputs, null values, limits).
3. Error Handling tests (exceptions, failed promises).
4. Mocking for external dependencies.
Ensure the tests follow the Arrange-Act-Assert pattern.
```
**Usage Tip:** Open a file and type `@QA Engineer /skill generate-unit-tests`

---

## Skill 2: Generate API Documentation
**Name:** `generate-api-docs`
**Description:** Creates OpenAPI/Swagger documentation for an endpoint.
**Prompt Content:**
```
Analyze the selected API route handler. Generate a structured API documentation snippet.
Include:
1. Endpoint Path and Method (GET/POST/etc).
2. Request Parameters (Query, Body, Headers) with types and validation rules.
3. Response Schemas for 200 (Success), 400 (Bad Request), 401 (Unauthorized), 500 (Server Error).
4. Example JSON request and response.
Format the output as a Markdown table or OpenAPI YAML.
```
**Usage Tip:** Select an API route and type `@Backend Specialist /skill generate-api-docs`

---

## Skill 3: Security Audit
**Name:** `security-audit`
**Description:** Scans code for security vulnerabilities.
**Prompt Content:**
```
Act as a Security Engineer. Audit the selected code for vulnerabilities.
Check for:
1. Injection flaws (SQL, NoSQL, Command).
2. XSS (Cross-Site Scripting).
3. Improper Authentication/Authorization.
4. Sensitive Data Exposure (logging secrets).
5. Insecure Dependencies.
If issues are found, list them with Severity (High/Medium/Low) and provide the Fixed Code.
```
**Usage Tip:** Select code and type `@Security Engineer /skill security-audit`

---

## Skill 4: Refactor for Performance
**Name:** `refactor-performance`
**Description:** Optimizes code for speed and efficiency.
**Prompt Content:**
```
Analyze the selected code for performance bottlenecks.
Look for:
1. Unnecessary re-renders (React).
2. N+1 queries (Database).
3. Heavy computations blocking the main thread.
4. Memory leaks.
Propose a refactored version that improves performance. Explain the specific gains (e.g., Time Complexity O(n^2) -> O(n)).
```
**Usage Tip:** Select slow code and type `@System Architect /skill refactor-performance`
