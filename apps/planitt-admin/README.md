Planitt Admin Dashboard (Next.js App Router).

## Local setup

1. Copy environment:

```bash
cp .env.example .env.local
```

2. Run dashboard:

```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

## Run with full stack (single command)

From repo root:

```bash
docker-compose -f docker-compose.planitt.yml up --build
```

Admin dashboard will be available at [http://localhost:3100](http://localhost:3100).

## Required backend services

- NestJS backend (`NEST_API_BASE_URL`) for all admin reads and actions.

## Scripts

- `npm run dev` - start dev server
- `npm run build` - production build
- `npm run start` - run built app
- `npm run lint` - ESLint
- `npm run typecheck` - TypeScript check
- `npm run smoke` - basic route smoke checks

## Architecture notes

- Browser never calls internal endpoints directly.
- Next.js route handlers (`/api/admin/*`) proxy calls and inject internal keys server-side.
- Session auth is cookie-based and guards all `/dashboard/*` routes.
- Production mode should set `ADMIN_DEPLOYMENT_MODE=single_backend`.
