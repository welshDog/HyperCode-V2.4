# API Input-Validation Standard

## Overview
All new REST and GraphQL endpoints must utilize strict input validation schemas. This ensures that invalid data is rejected at the API boundary, protecting the core logic and database integrity.

## Standard
- **Library**: `zod` (TypeScript) or `pydantic` (Python).
- **Coverage**: 100% of request bodies, query parameters, and path parameters.
- **Enforcement**: CI pipeline will fail if schemas are missing (via lint rules).

## Implementation Example (Next.js/Zod)

```typescript
import { z } from 'zod';
import { NextResponse } from 'next/server';

const CreateUserSchema = z.object({
  username: z.string().min(3),
  email: z.string().email(),
  role: z.enum(['admin', 'user']),
});

export async function POST(request: Request) {
  const body = await request.json();
  const result = CreateUserSchema.safeParse(body);

  if (!result.success) {
    return NextResponse.json(
      { error: 'Validation Failed', details: result.error.format() },
      { status: 400 }
    );
  }

  // Proceed with valid data
  return NextResponse.json({ status: 'created' });
}
```

## Checklist
- [ ] Define Zod schema for input.
- [ ] Use `safeParse` to validate.
- [ ] Return 400 Bad Request on failure.
- [ ] Add unit test for success case.
- [ ] Add unit test for validation error case.
