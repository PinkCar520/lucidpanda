# Architecture Overview

LucidPanda consists of four main components:

1. Collector: RSS ingestion and normalization.
2. Worker: LLM analysis, clustering, and enrichment.
3. API: FastAPI + SSE for real-time delivery.
4. Web: Next.js client for visualization and interaction.

## Runtime Topology

```
[RSS / Feeds] -> Collector -> PostgreSQL -> Worker -> Redis Pub/Sub
                                             |
                                             v
                                       API (SSE)
                                             |
                                             v
                                       Web (Next.js)
```

## Core Modules (backend)

- `src/lucidpanda/api`: FastAPI routers and BFF endpoints.
- `src/lucidpanda/core`: engine, collectors, clustering, and core processing.
- `src/lucidpanda/db`: data access modules and database utilities.
- `src/lucidpanda/providers`: RSS + LLM provider integrations.
- `src/lucidpanda/services`: domain services (market, embeddings, etc.).
- `src/lucidpanda/infra`: caching, streaming, and DB connection helpers.
