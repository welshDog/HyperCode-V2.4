# Frontend Patterns & Gotchas

## Adding a new dashboard panel

1. Create `agents/dashboard/components/MyPanel.tsx`
2. Accept `className?: string` prop for layout flexibility
3. Fetch data with SWR: `const { data } = useSWR('/api/v1/my-endpoint', fetcher)`
4. Wrap in `<Suspense>` if async
5. Add to page layout in `agents/dashboard/pages/index.tsx`
6. Add emoji anchor to heading (e.g. `## 🔥 My Panel`)

## useSensoryProfile — applying to components

```typescript
const { profile } = useSensoryProfile()

<motion.div
  animate={profile.reducedMotion ? {} : { opacity: 1, y: 0 }}
  className={profile.compactDensity ? 'p-2' : 'p-6'}
  style={{ fontFamily: profile.dyslexiaFont ? 'OpenDyslexic' : 'inherit' }}
>
```

## WS not connecting in Docker?

- Check `NEXT_PUBLIC_WS_URL` env var — should match crew-orchestrator port (8081)
- Nginx reverse proxy config: `nginx/` — ensure `/ws/` path is proxied with upgrade headers
- Use `ws://` not `wss://` in local dev; `wss://` for production with TLS

## Type the api.ts client

- All API calls go through `agents/dashboard/lib/api.ts`
- Add typed function per endpoint — no raw `fetch` in components
- Errors surface as `ApiError` with `status` + `message`
