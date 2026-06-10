# Rent Manager — V1 Prototype

A working slice of the V1 spec ([RENT_MANAGER_V1_SPEC.md](./RENT_MANAGER_V1_SPEC.md)). Two parts:

1. **Backend** — FastAPI + Postgres + Redis + Celery, as a Docker Compose stack
2. **Mobile/Web app** — Expo Router (React Native + React Native Web), runs in the browser via `npx expo start --web` and on a phone via Expo Go

This is the demo you show prospects.

## What's in it

**Mobile app screens** — Login → OTP verify → Dashboard (collected/pending/overdue stats, needs attention, recently paid, leases expiring), Tenants list with search + Add tenant form, Properties list with Add property modal, Leases list with expiry badges, Record payment flow, Settings with logout.

**Backend** — all 12 data models from §6, core CRUD per §7, payment matcher per §10.3, Celery beat schedule per §10.1, stubbed WhatsApp/SES/Razorpay integrations that log to `notifications_log`, Excel export.

## Run it on your local

### Step 1: start the backend

You need Docker Desktop.

```bash
cd /Users/ayushsharma/Desktop/rent_manager
docker compose up --build
```

Wait for `Uvicorn running on http://0.0.0.0:8000`. Then, in another terminal:

```bash
# Seed an owner + 5 tenants + 3 properties + leases + invoices
docker compose exec api python -m scripts.seed_dev_data
```

Backend is up at:
- API: http://localhost:8000
- Swagger: http://localhost:8000/docs

### Step 2: start the mobile app (web mode)

You need Node 20+, npm, and **watchman** (on macOS — without it Metro hits `EMFILE: too many open files, watch` on the first run).

```bash
# One-time on macOS:
brew install watchman

# Then:
cd apps/mobile
npm install
npx expo start --web
```

The web app opens at `http://localhost:8081` (Expo's dev server proxies to a build at `http://localhost:19006` depending on version — follow the URL Expo prints in the terminal).

Demo login:

- Phone: **9876543210** (the seeded owner)
- Name: anything (it's only used when creating a new org)
- OTP: **123456** (the dev OTP is also displayed on the verify screen)

You'll land on the dashboard. Try:

- Tap **Add tenant** → fill the form → see it appear in Tenants
- Tap **Record payment** → pick a tenant → enter amount → save → dashboard updates
- Open **Properties** → tap **Add** → fill the modal → see the new property
- Open **Leases** → see the active leases with expiry badges
- Open **Settings** → see your org info and the API endpoint → **Log out**

### Optional: demo on a real phone

Install **Expo Go** on your iPhone/Android, then in the same `apps/mobile` directory:

```bash
npx expo start
```

Scan the QR code with the Expo Go app (Android) or the camera (iOS). The app loads onto your phone. The API client uses Expo's `hostUri` to find the backend, so the phone hits `http://<your-laptop-LAN-IP>:8000`. Your laptop and phone must be on the same Wi-Fi.

## Project layout

```
apps/
  backend/                   FastAPI + Celery (Docker Compose)
    src/rent_manager/
      main.py                app factory
      config.py              pydantic-settings
      db/                    SQLAlchemy models (12 entities)
      api/v1/                REST endpoints
      schemas/               Pydantic v2 schemas
      services/              business logic (payment matcher)
      integrations/          WhatsApp / SES / Razorpay clients (stubbed)
      workers/               Celery app + beat + tasks
    migrations/              Alembic
    scripts/seed_dev_data.py
  mobile/                    Expo Router app
    app/
      _layout.tsx            root layout + auth gate
      (auth)/                login + verify-otp
      (owner)/               bottom tab nav: dashboard, tenants, properties, leases, settings
    src/
      api/                   fetch client + types + QueryClient
      components/            Button, Card, Input, StatBlock, Badge, Icon, SectionHeader
      state/                 Zustand auth store (AsyncStorage-backed)
      theme/                 design tokens
      utils/                 INR + date formatters
docker-compose.yml           postgres + redis + api + worker + beat
README.md                    this file
RENT_MANAGER_V1_SPEC.md      the original spec
```

## Common operations

### Backend

- **Watch logs** — `docker compose logs -f api worker beat`
- **Open Postgres** — `docker compose exec postgres psql -U rent -d rent_manager`
- **Trigger a Celery task** — `docker compose exec worker python -c "from rent_manager.workers.tasks.summaries import send_weekly_summary; print(send_weekly_summary.apply().get())"` (watch `notifications_log` afterwards)
- **Stop everything** — `docker compose down` (add `-v` to wipe DB volume too)

### Mobile

- **Web mode** — `npx expo start --web`
- **Clear cache** — `npx expo start --clear`
- **Phone via Expo Go** — `npx expo start` then scan the QR
- **iOS simulator** — `npx expo start --ios` (needs Xcode installed)
- **Android emulator** — `npx expo start --android` (needs Android Studio + an emulator running)

## What this prototype doesn't have (vs. the full spec)

- Real Supabase Auth (we use mock OTP; any 6-digit `OTP_FIXED` works)
- Real WhatsApp / SES / Razorpay calls (the integrations are stubbed; flip `*_ENABLED=true` in `apps/backend/.env` and fill creds to go live)
- Row-level security at the DB (we enforce `organization_id` at the API layer instead)
- Sentry / PostHog / Prometheus / Grafana
- i18next on the client (UI strings are in English; backend templates already support `en`/`hi`/`kn`)
- Hetzner deploy / Caddy / CI workflows / EAS Build
- Push notifications (the user model has the column, but Expo Push isn't wired)

These are phases 7–8 in spec §18, plus the production deployment work. The prototype is enough to walk a prospect through the entire workflow.

## Switching to real integrations

In `apps/backend/.env`:

- WhatsApp: set `WHATSAPP_ENABLED=true` and fill `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_APP_SECRET`, `WHATSAPP_WEBHOOK_VERIFY_TOKEN`. Submit the 7 templates × 3 languages in Meta Business Manager. The existing send function in `integrations/whatsapp.py` switches from logging to real HTTP calls automatically.
- SES: set `SES_ENABLED=true`, AWS creds, region, `SES_FROM_EMAIL`. Drop boto3 client into the `NotImplementedError` branch of `integrations/email.py`.
- Razorpay: set `RAZORPAY_ENABLED=true`, key id/secret, webhook secret.

Restart the stack: `docker compose up -d --build`.
