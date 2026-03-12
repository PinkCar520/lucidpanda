# Contributing

Thanks for your interest in contributing.

## Development Setup

Backend:
```bash
python -m venv venv
./venv/bin/pip install -r requirements.txt
cp .env.example .env
./venv/bin/python3 run.py
```

Web:
```bash
cd web
npm install
npm run dev
```

## Tests

Backend:
```bash
pytest
```

Web:
```bash
cd web
npm test
```

## Pull Requests

- Keep changes focused and small where possible.
- Add tests for new behavior.
- Update documentation when you change user-facing behavior.

## Security

Do not open public issues for security vulnerabilities. See `SECURITY.md`.
