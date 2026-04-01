# Crypto Trading Bot

## 🚀 Project Overview

**Crypto Trading Bot** is a Python-based framework that combines market data ingestion, technical indicators, strategy-driven signal generation, risk management, and optional LLM-powered analysis to produce actionable crypto trading signals.

Key capabilities:
- Binance historical and WebSocket price data ingestion
- Indicator library: EMA, SMA, RSI, MACD, Bollinger Bands, ATR, Ichimoku, Supertrend, VWAP, etc.
- Strategy plugins: RSI, MACD, Bollinger squeeze, Supertrend, Ichimoku, stochastic RSI, volume breakout
- Signal engine with entry/exit, take-profit/stop-loss, risk controls
- FastAPI API endpoints + health checks + WebSockets
- PostgreSQL backend + SQLAlchemy ORM + Redis cache
- Docker + Kubernetes deployment manifests
- Monitoring and logging via structured logger

---

## 🧩 Quick setup

### 1. Requirements
- Python 3.11+
- Poiect/Curl/Make (optional)
- Docker (optional for containerized run)

### 2. Install

```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 3. Configuration

Copy and customize environment file:

```bash
cp .env.example .env
# update DB, Binance, Redis, LLM provider keys
```

### 4. Database init

```bash
scripts/create_db.sh
alembic upgrade head
```

### 5. Run server

```bash
python scripts/run_server.py
# or with uvicorn
uvicorn src.api.server:app --reload
```

---

## 🧪 Tests

```bash
pytest --maxfail=1 --disable-warnings -q
```

---

## 📁 Project layout

- `src/api` - API server and routes
- `apps/planitt-admin` - Next.js admin dashboard (hybrid NestJS/FastAPI proxy)
- `src/data` - Binance client and data fetcher
- `src/indicators` - indicator implementations
- `src/signals` - strategies and signal engine
- `src/risk` - position sizing and risk manager
- `src/llm` - optional LLM analysis plugin
- `src/database` - models, CRUD, migrations
- `scripts` - setup helpers
- `tests` - tests

## Admin Dashboard

- New admin dashboard lives at `apps/planitt-admin`.
- Cutover/migration guide: `ADMIN_DASHBOARD_CUTOVER.md`.
- Production admin deployment (`planitt-crypto.netlify.app`) uses server-side Next routes.
- Recommended full hosted-admin setup with private ops: `ADMIN_DEPLOYMENT_MODE=hybrid`.
- Set these Netlify environment variables for admin API calls:
  - `NEST_API_BASE_URL=https://planitt-backend-crypto.onrender.com`
  - `NEST_API_INTERNAL_API_KEY=<same value as backend PLANITT_INTERNAL_API_KEY>`
  - `ADMIN_DEPLOYMENT_MODE=hybrid`
  - `FASTAPI_BASE_URL=<private FastAPI ops service URL>`
  - `FASTAPI_INTERNAL_API_KEY=<same value as PLANITT_PROCESSOR_INTERNAL_API_KEY>`
  - `NEXTAUTH_SECRET`, `ADMIN_USERNAME`, `ADMIN_PASSWORD`
- Keep auto-generation local-only by setting `ENABLE_BACKGROUND_SCANNER=true` locally and `ENABLE_BACKGROUND_SCANNER=false` on hosted FastAPI ops service.
- For hosted FastAPI ops service, restrict ingress and set `FASTAPI_CORS_ORIGINS`/`FASTAPI_TRUSTED_HOSTS`.
- Important naming: `NEST_API_BASE_URL` is for admin panel routes, while `PLANITT_BACKEND_BASE_URL` is for local FastAPI processor-to-backend calls.

---

## 🛠 Development

- Use formatting: `black src tests scripts`.
- Lint: `ruff check src tests scripts`
- Type check: `mypy src tests`

### Recommended workflow
1. create feature branch
2. run tests locally
3. open PR with clear description and resolvers

---

## 🧾 Contribution

Open issues or PRs for bugs, improvements, new strategies, or docs updates.

- Add strategy tests under `tests/`
- Keep deterministic behavior in signal generation
- Document new config keys in `config/settings.py`

---

## 📄 License

MIT License (or your chosen license)

---

## ⚠️ Safety Disclaimer

Trading digital assets involves risk. This project is for educational purposes only; not financial advice.
