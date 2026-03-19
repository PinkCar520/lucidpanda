# LucidPanda

LucidPanda is an investment intelligence system that ingests market news and signals, performs LLM-assisted analysis, and serves real-time insights to web clients.

## Scope

- Open-source scope: backend + web.
- Mobile client is excluded from this repository's open-source surface.

## Architecture

```
Collector (RSS) -> PostgreSQL -> Worker (LLM analysis) -> Redis Pub/Sub
                                        |
                                        v
                                     API (SSE)
                                        |
                                        v
                                     Web (Next.js)
```

## Features

- RSS ingestion with deduplication and clustering
- LLM-based analysis (Gemini/DeepSeek/OpenAI)
- Real-time streaming updates via SSE + Redis
- Fund watchlist, market snapshots, and backtesting

## Quickstart

### Backend (local)

```bash
python -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env
./venv/bin/python3 run.py
```

### Web (local)

```bash
cd web
npm install
npm run dev
```

### Docker (recommended)

```bash
cp .env.example .env
docker compose up -d
```

## Configuration

All secrets and API keys are configured via `.env`. Never commit `.env` into version control. See `.env.example` for all required values.

## Documentation

- Architecture: `docs/architecture.md`
- Open-source readiness: `docs/OPEN_SOURCE_READINESS.md`
- Security: `docs/SECURITY_GUIDE.md`
- Auth system: `docs/AUTH_SYSTEM_DESIGN_V2.md`

## Contributing

See `CONTRIBUTING.md` for development workflow and guidelines.

## License

MIT. See `LICENSE`.
