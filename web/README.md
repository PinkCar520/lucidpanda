# AlphaSignal Web

Next.js frontend for AlphaSignal.

## Development

```bash
npm install
npm run dev
```

## Environment

Create `web/.env.local` if you need local overrides. Most settings are pulled from the root `.env` when running via Docker.

## Tests

```bash
npm test
```

## Notes

- API requests are routed through `/app/api` handlers.
- Authentication uses NextAuth v5 and backend JWT.
