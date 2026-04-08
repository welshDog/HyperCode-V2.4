---
name: generate-api-docs
description: Create structured API documentation for a selected endpoint.
---

## Description

This skill scans the selected API route handler or server action and generates structured API documentation (Markdown or OpenAPI style).

## When to use

- You have implemented or modified an API endpoint and need documentation.
- You are standardizing API docs across the project.
- You want to quickly share endpoint details with Frontend or external consumers.

## Instructions

1. Analyze the selected API handler:
   - HTTP method.
   - Path or route.
   - Expected request shape (query, params, body, headers).
   - Response types and status codes.
2. Identify and document:
   - Request parameters with types and validation rules (e.g. Zod schemas).
   - Response schemas for:
     - 200 (Success)
     - 400 (Bad Request)
     - 401 (Unauthorized) if applicable
     - 500 (Server Error)
3. Generate documentation in one of these formats:
   - A Markdown section with tables for request and response.
   - An OpenAPI-style YAML snippet.
4. Include example payloads:
   - One example request body.
   - One example success response.
   - One example error response if relevant.
5. Keep naming consistent with the project conventions.

## Examples

**Example input (user intent)**

Generate API docs for this `POST /api/orders` handler.

**Example output (high level)**

- Markdown section describing:
  - Path: `/api/orders`
  - Method: `POST`
  - Request body schema
  - Responses for 201, 400, 401, 500
- Example request and response JSON.
