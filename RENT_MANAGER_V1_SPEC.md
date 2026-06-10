# Rent Manager — V1 Technical Specification

**Document version:** 1.0
**Last updated:** May 2026
**Owner:** Ayush Sharma
**Status:** Pre-build. To be used as input to Claude Code (or any developer) for V1 implementation.
**Target ship date:** 8-10 weeks part-time from start of build.

---

## Table of Contents

1. Product Context
2. V1 Scope and Non-Goals
3. Tech Stack and Rationale
4. System Architecture
5. Repository Layout (Monorepo)
6. Data Model
7. API Specification
8. Authentication and Authorization
9. Frontend Architecture
10. Background Jobs and Schedulers
11. Third-Party Integrations
12. Internationalization (i18n)
13. Scalability and Performance
14. Security and Compliance
15. Observability
16. Testing Strategy
17. CI/CD and Deployment
18. Phased Build Plan
19. Acceptance Criteria per Feature
20. Environment Variables Reference
21. Operational Runbook
22. Glossary

---

## 1. Product Context

Rent Manager is a done-for-you rent management service for residential flat owners and PG operators in India, with Bangalore as the launch city.

The V1 product consists of three deliverables that ship together:

1. A cross-platform native owner app (iOS, Android, Web) built from a single React Native + Expo codebase.
2. A FastAPI backend that serves the app and runs all business logic.
3. A worker tier (Celery) that handles all asynchronous work: outbound WhatsApp messages, email reminders, lease alerts, and weekly summaries.

Tenants do not have any app or login. Tenants only ever interact with the system through outbound WhatsApp messages and emails. This is a deliberate product decision that simplifies V1 scope, removes the cold-start tenant adoption problem, and matches how Indian PG and flat tenants already behave.

The owner pays for the product. The owner is the only user of the app in V1.

---

## 2. V1 Scope and Non-Goals

### In scope for V1

| Capability | Description |
|---|---|
| Owner authentication | Phone OTP login. No passwords. |
| Property and unit management | Owner adds properties (buildings), units (flats), and beds (for PGs). Hierarchical: property contains units, units may contain beds. |
| Tenant records | Name, phone, email, language preference, rent amount, security deposit, lease start, lease end, assigned unit or bed. |
| Lease management | One active lease per unit/bed. Lease has start, end, rent, deposit, frequency (monthly), and renewal status. |
| Payment recording | Owner manually records a payment, optionally with a forwarded UPI screenshot attachment. Backend suggests matches by amount, date, and tenant. |
| Reminder ladder (WhatsApp + Email) | Automated reminders to tenants on Day 3, Day 5, and Day 7 of unpaid status, via WhatsApp and Email. Voice calls deferred to V2. |
| Owner dashboard | Current month collected, pending, overdue. Recently paid list. Needs-attention list. |
| Weekly summary | Automated WhatsApp message to owner every Friday at 11 AM IST: collected, pending, overdue, leases expiring in next 45 days. |
| Lease expiry alerts | Push notification + WhatsApp to owner when any lease is within 45 days of expiry. Daily check. |
| Multilingual UI | English, Hindi, Kannada at V1. UI strings only — backend remains in English. |
| Tenant communication logs | Per-tenant log of every message sent (channel, language, delivery status, read status when available). |
| Excel export | Owner can export all payments for any date range as an XLSX file for ITR or CA. |
| Push notifications | Payment received, payment overdue, lease expiring soon. Via Expo Push API. |
| Owner subscription billing | ₹500 / ₹999 / ₹1,499 monthly plans via Razorpay Subscriptions. |
| Audit log | Every state-changing action is recorded with actor, entity, before/after, timestamp. |

### Not in scope for V1 (deferred)

| Item | Where |
|---|---|
| Voice calls in Indian languages | V2. Use human-made calls during pilot phase. |
| In-app payments by tenants (Razorpay tenant flow) | V2. Tenants continue paying owner directly via UPI. |
| Tenant-facing app or portal | Never (architectural decision). |
| Document signing (rent agreements, NOC) | V3. |
| KYC / Aadhaar verification of tenants | V3. |
| Staff management (cooks, cleaners, security) | V3, PG-segment only. |
| Maintenance ticketing | Not in roadmap. |
| Community announcements, visitor pre-approval, parking, SOS | Killed. Wrong product category. |
| Tamil and Telugu UI | Month 4+ after Hindi/Kannada proves out the i18n pipeline. |

---

## 3. Tech Stack and Rationale

| Layer | Choice | Why |
|---|---|---|
| Mobile (iOS + Android) | React Native 0.74 + Expo SDK 51 (managed workflow) | Single codebase. OTA updates via EAS Update. Strong AI-assisted tooling. Expo Push for free notifications. |
| Web (owner admin) | Expo Web (React Native Web) | Same codebase as mobile. Acceptable UX for V1. Saves 4 weeks of separate web work. |
| Backend API | Python 3.12 + FastAPI 0.110+ | Matches the founder's existing Python skill. Async I/O. Strong typing via Pydantic v2. Excellent OpenAPI generation. |
| Database | PostgreSQL 15 (managed by Supabase) | Supabase gives us Postgres + auth + storage + realtime. Indian data residency available via Supabase's Singapore region (closest to India). PostgreSQL handles 100K+ tenants without breaking a sweat. |
| ORM | SQLAlchemy 2.0 (async) + Alembic for migrations | Mature. Async support. Works with Supabase's Postgres directly. |
| Auth | Supabase Auth (phone OTP via Twilio or MSG91) | Phone OTP is the Indian standard. Supabase handles JWT issuance, refresh tokens, and rotation. |
| Cache + Queue broker | Redis 7 | Caching dashboards, rate limiting, Celery broker. One Redis serves both needs at V1 scale. |
| Async workers | Celery 5.4 + Redis broker | Standard Python async work queue. Beat scheduler for periodic jobs. Mature, well-documented. |
| Object storage | Supabase Storage | For UPI screenshot uploads, exported Excel files. Same auth context as DB. |
| WhatsApp | Meta WhatsApp Cloud API (direct, no BSP) | Cheaper at low volume. Direct webhook control. Skip Gupshup/Wati fees at V1. |
| Email | Amazon SES (Mumbai region) | Cheap (₹0.10 per email at scale), high deliverability, Indian region for data residency. |
| Payments (owner subscriptions) | Razorpay Subscriptions | Indian standard. Auto-recurring debit via UPI Autopay, cards, netbanking. |
| Push notifications | Expo Push API | Free, dead simple, works for iOS + Android. No need for FCM/APNs direct integration at V1. |
| Excel generation | openpyxl | Pure Python. No native dependencies. |
| Error tracking | Sentry (free tier up to 5K errors/month) | Backend + frontend. Catches crashes before owners report them. |
| Analytics | PostHog (self-hosted on the same VPS) | Track which screens owners use. Self-host is free. |
| Hosting (API + workers + Redis + PostHog) | Hetzner CX22 (₹400-500/month) | 2 vCPU, 4 GB RAM, plenty for first 100 customers. Indian users get acceptable latency from Hetzner Falkenstein. |
| Hosting (Database) | Supabase managed | No DBA overhead. Auto-backups. Free tier covers V1; upgrade to Pro (~$25/month) at ~50 customers. |
| CDN | Cloudflare (free tier) | In front of API and web build. |
| CI/CD | GitHub Actions | Free for private repos at this scale. Build, test, deploy. |
| Mobile build & distribution | Expo EAS Build + EAS Submit | Cloud builds, no local Xcode/Android Studio needed. |

**One stack opinion to settle now:** the API and worker tier should run as containers on a single Hetzner VPS at V1. Docker Compose orchestration. Do not introduce Kubernetes until you have 100+ paying customers. Premature orchestration kills bootstrap startups.

---

## 4. System Architecture

### High-level component diagram (text)

```
+-------------------+     +-------------------+     +-------------------+
|  iOS App (Expo)   |     | Android App (Expo)|     |  Web App (Expo)   |
+-------------------+     +-------------------+     +-------------------+
          \                       |                         /
           \                      |                        /
            -----------> HTTPS / JSON over REST <----------
                                  |
                                  v
                       +---------------------+
                       |  Cloudflare (CDN)   |
                       +---------------------+
                                  |
                                  v
                       +---------------------+
                       |  FastAPI App Tier   |
                       |  (uvicorn workers)  |
                       +---------------------+
                          |        |       |
                          |        |       |
                  +-------+        |       +--------+
                  |                |                |
                  v                v                v
        +-----------------+ +------------+ +--------------+
        |   PostgreSQL    | |   Redis    | |  Supabase    |
        |   (Supabase)    | | (cache +   | |   Storage    |
        |                 | |  broker)   | |              |
        +-----------------+ +------------+ +--------------+
                  ^                ^
                  |                |
                  |        +-------+
                  |        |
              +---------------------+
              |   Celery Workers    |
              |  (reminder, summary,|
              |   webhook, export)  |
              +---------------------+
                       |         |
                       v         v
              +-------------+ +--------+
              |  WhatsApp   | |  SES   |
              |  Cloud API  | | Email  |
              +-------------+ +--------+
                       ^
                       |  (inbound webhooks)
              +-------------+
              |  WhatsApp   |
              |   webhook   |
              +-------------+
```

### Component responsibilities

| Component | Responsibility |
|---|---|
| Mobile/Web app | Render UI, capture owner input, display data from API. Stateless beyond local UI state and auth tokens. |
| Cloudflare | TLS termination, edge caching of static assets, basic DDoS protection. |
| FastAPI app tier | Authentication checks, request validation, business logic, persistence. Synchronous response time target: p99 < 300 ms. |
| PostgreSQL (Supabase) | Source of truth for all data. Multi-tenant by `organization_id` with row-level security. |
| Redis | (1) Cache: dashboard aggregates, tenant lists. (2) Celery broker: task queue. (3) Rate limit counters. |
| Supabase Storage | UPI screenshots uploaded by owner, generated Excel exports, future tenant documents. |
| Celery workers | All work that takes more than 100 ms or involves external APIs: send WhatsApp, send email, run reminder ladder, weekly summary, lease expiry sweep, payment matching, Excel generation. |
| Celery beat | Periodic scheduler. Cron-like definitions for daily and weekly jobs. |
| WhatsApp webhook handler | Receives delivery, read, and inbound message events from Meta. Idempotent. Writes to `notifications_log`. |
| Razorpay webhook handler | Receives subscription events (created, charged, failed, cancelled). Idempotent. Updates `subscriptions` table. |

### Request flow examples

**Owner opens dashboard:**
1. App calls `GET /api/v1/dashboard/summary`.
2. FastAPI checks JWT → resolves `organization_id`.
3. Checks Redis cache `dashboard:<org_id>:<month>`; if hit, returns within 30 ms.
4. If miss, runs aggregate query against Postgres with `org_id` filter, caches result for 60 seconds, returns.

**Owner records a payment:**
1. App posts `POST /api/v1/payments` with tenant_id, amount, date, optional screenshot.
2. FastAPI validates, writes payment row, marks tenant's current-month invoice as paid.
3. Invalidates `dashboard:<org_id>:<month>` cache.
4. Returns 201 with payment object.
5. Audit log entry written async.

**Daily reminder run (background):**
1. Celery beat triggers `run_daily_reminders` at 09:00 IST.
2. Worker scans `invoices` where `status = 'pending'` and day-of-month delta matches 3, 5, or 7.
3. For each, enqueues `send_whatsapp_reminder` and `send_email_reminder` tasks per tenant's language and channel preference.
4. Each send task is idempotent (keyed by invoice_id + day + channel).

---

## 5. Repository Layout (Monorepo)

Use a single Git repository with the following structure. Workspaces managed by `pnpm` for the JS side and `uv` for Python.

```
rent-manager/
  README.md
  .editorconfig
  .gitignore
  .github/
    workflows/
      backend-ci.yml
      mobile-ci.yml
      deploy-backend.yml
      deploy-mobile.yml
  docs/
    SPEC.md                   <- this document
    runbook.md
    onboarding.md
  apps/
    backend/                  <- FastAPI service
      pyproject.toml
      uv.lock
      Dockerfile
      docker-compose.yml      <- local dev (postgres, redis, api, worker)
      alembic.ini
      src/
        rent_manager/
          __init__.py
          main.py             <- FastAPI app factory
          config.py           <- Pydantic settings, env loading
          deps.py             <- shared dependencies (db session, current user)
          db/
            base.py
            session.py
            models/           <- SQLAlchemy models, one file per aggregate
              organization.py
              user.py
              property.py
              unit.py
              tenant.py
              lease.py
              invoice.py
              payment.py
              notification.py
              audit.py
              subscription.py
          api/
            v1/
              auth.py
              organizations.py
              properties.py
              units.py
              tenants.py
              leases.py
              invoices.py
              payments.py
              dashboard.py
              reports.py
              webhooks.py
          services/           <- business logic, framework-independent
            payment_matcher.py
            reminder_orchestrator.py
            lease_checker.py
            summary_builder.py
            export_builder.py
          integrations/
            whatsapp/
              client.py
              templates.py
              webhook_handler.py
            email/
              client.py
              templates.py
            razorpay/
              client.py
              webhook_handler.py
            supabase_storage.py
          workers/
            celery_app.py
            beat_schedule.py
            tasks/
              reminders.py
              summaries.py
              leases.py
              webhooks.py
              exports.py
          utils/
            i18n.py            <- backend message templates per language
            phone.py           <- E.164 normalization for Indian numbers
            currency.py        <- Indian INR formatting
            time.py            <- IST handling
          schemas/             <- Pydantic v2 request/response models
            auth.py
            tenant.py
            payment.py
            ...
      migrations/              <- Alembic
        versions/
      tests/
        unit/
        integration/
        load/
        conftest.py
        factories.py
    mobile/                    <- React Native + Expo
      package.json
      app.json                 <- Expo config
      eas.json                 <- EAS Build profiles
      babel.config.js
      tsconfig.json
      App.tsx
      src/
        app/                   <- file-based routing (Expo Router)
          (auth)/
            login.tsx
            verify-otp.tsx
          (owner)/
            _layout.tsx
            dashboard.tsx
            tenants/
              index.tsx
              [id].tsx
            properties/
              index.tsx
              [id].tsx
            leases/
              index.tsx
            payments/
              record.tsx
              history.tsx
            settings/
              index.tsx
              language.tsx
              subscription.tsx
        components/            <- reusable UI primitives
          Button.tsx
          Card.tsx
          TenantRow.tsx
          StatBlock.tsx
          ...
        screens/               <- complex screen-level components
        api/
          client.ts            <- axios instance with auth interceptor
          endpoints/
            auth.ts
            tenants.ts
            payments.ts
            dashboard.ts
            ...
          types.ts             <- generated from backend OpenAPI
        state/
          auth.store.ts        <- Zustand
          ui.store.ts
        hooks/
          useAuth.ts
          useDashboard.ts
          useTenants.ts        <- TanStack Query wrappers
        i18n/
          index.ts
          locales/
            en.json
            hi.json
            kn.json
        utils/
          currency.ts
          date.ts
          phone.ts
        theme/
          tokens.ts
          colors.ts
      assets/
        fonts/
        images/
      __tests__/
        components/
        screens/
  packages/
    shared-types/              <- shared TS types (generated from backend OpenAPI)
      package.json
      src/
        index.ts
  infra/
    hetzner/
      docker-compose.prod.yml
      caddy/
        Caddyfile
      backup.sh
    scripts/
      seed-dev-data.py
      backup-restore.md
```

---

## 6. Data Model

All times stored as `timestamptz` in UTC. Render in IST in the app.
All money stored as `numeric(12,2)` rupees. No paise. No floats anywhere.
All IDs are UUIDs v4 generated server-side.

### 6.1 organizations

The top-level multi-tenant boundary. One organization per owner.

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | PK |
| `name` | text | Owner's business name or full name |
| `phone_e164` | text | Owner's verified phone in E.164 format |
| `email` | text | Optional |
| `default_language` | text | One of `en`, `hi`, `kn`. Default `en`. |
| `tier` | text | `pilot`, `starter`, `growth`, `scale`. Default `pilot`. |
| `created_at` | timestamptz | |
| `updated_at` | timestamptz | |

**Indexes:** `phone_e164` unique.

### 6.2 users

Currently 1:1 with organizations. Schema designed to allow supervisors and additional users in V2 without migration.

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | PK |
| `organization_id` | uuid | FK, indexed |
| `supabase_user_id` | uuid | The Supabase Auth user ID. Indexed unique. |
| `role` | text | `owner`. Future: `supervisor`, `viewer`. |
| `name` | text | |
| `phone_e164` | text | |
| `email` | text | Nullable |
| `language` | text | UI preference. Falls back to organization default. |
| `last_seen_at` | timestamptz | |
| `created_at` | timestamptz | |

**Indexes:** `(organization_id)`, `(supabase_user_id)` unique.

### 6.3 properties

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | PK |
| `organization_id` | uuid | FK, indexed |
| `name` | text | E.g., "Saraswati Nilaya" |
| `type` | text | `apartment_building` or `pg` |
| `address_line` | text | |
| `area` | text | E.g., "HSR Layout" |
| `city` | text | Default "Bengaluru" |
| `pincode` | text | |
| `created_at` | timestamptz | |
| `updated_at` | timestamptz | |
| `archived_at` | timestamptz | Soft delete. |

**Indexes:** `(organization_id, archived_at)`.

### 6.4 units

A unit is either a flat (in an apartment_building property) or a bed (in a pg property). One row per rentable entity.

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | PK |
| `organization_id` | uuid | FK, indexed (denormalized for RLS) |
| `property_id` | uuid | FK, indexed |
| `type` | text | `flat`, `room`, `bed`, `shared_bed` |
| `identifier` | text | "Flat 302", "Bed 12", "Room 4A" |
| `default_rent` | numeric(12,2) | Stored for reference; actual rent lives on lease |
| `notes` | text | |
| `created_at` | timestamptz | |
| `updated_at` | timestamptz | |
| `archived_at` | timestamptz | |

**Indexes:** `(organization_id)`, `(property_id, archived_at)`.

### 6.5 tenants

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | PK |
| `organization_id` | uuid | FK, indexed |
| `name` | text | |
| `phone_e164` | text | Required |
| `email` | text | Nullable |
| `language` | text | `en`, `hi`, `kn`. Default `hi`. Used for outbound message language. |
| `whatsapp_opt_in` | boolean | Default true; set false if WhatsApp returns hard-fail |
| `email_opt_in` | boolean | Default true if email present |
| `notes` | text | |
| `created_at` | timestamptz | |
| `updated_at` | timestamptz | |
| `archived_at` | timestamptz | |

**Indexes:** `(organization_id, phone_e164)`, `(organization_id, archived_at)`.

### 6.6 leases

Each active lease binds a tenant to a unit. Only one active lease per (unit, tenant) at a time.

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | PK |
| `organization_id` | uuid | FK, indexed |
| `unit_id` | uuid | FK, indexed |
| `tenant_id` | uuid | FK, indexed |
| `start_date` | date | |
| `end_date` | date | |
| `monthly_rent` | numeric(12,2) | |
| `security_deposit` | numeric(12,2) | |
| `billing_day` | integer | 1-28 (avoid month-end edge cases). Defaults to 1. |
| `status` | text | `active`, `ended`, `terminated_early` |
| `renewal_status` | text | `not_started`, `proposed`, `renewed`, `replacing` |
| `notes` | text | |
| `created_at` | timestamptz | |
| `updated_at` | timestamptz | |

**Indexes:** `(organization_id, status)`, `(unit_id, status)`, `(end_date, status)` for expiry sweeps.
**Constraint:** at most one row per `unit_id` with `status = 'active'`. Enforced via partial unique index.

### 6.7 invoices

A monthly billable instance for a lease. Created automatically by a job on the lease's `billing_day` each month while the lease is active.

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | PK |
| `organization_id` | uuid | FK, indexed |
| `lease_id` | uuid | FK, indexed |
| `tenant_id` | uuid | FK, indexed |
| `unit_id` | uuid | FK, indexed |
| `billing_month` | date | First day of month, e.g., `2026-05-01` |
| `due_date` | date | |
| `amount_due` | numeric(12,2) | |
| `amount_paid` | numeric(12,2) | Default 0 |
| `status` | text | `pending`, `partial`, `paid`, `overdue`, `waived` |
| `paid_at` | timestamptz | Nullable |
| `last_reminder_day` | integer | 0, 3, 5, 7 |
| `created_at` | timestamptz | |
| `updated_at` | timestamptz | |

**Indexes:** `(organization_id, billing_month, status)`, `(lease_id, billing_month)` unique, `(due_date, status)` partial on `status in ('pending','partial','overdue')`.

### 6.8 payments

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | PK |
| `organization_id` | uuid | FK, indexed |
| `invoice_id` | uuid | FK, indexed; nullable until matched |
| `tenant_id` | uuid | FK, indexed |
| `amount` | numeric(12,2) | |
| `paid_on` | date | Owner's specified date |
| `method` | text | `upi`, `bank_transfer`, `cash`, `other` |
| `reference` | text | UPI ref, bank ref, etc. Nullable |
| `screenshot_path` | text | Supabase Storage path. Nullable |
| `notes` | text | |
| `match_confidence` | numeric(5,2) | 0.00 to 100.00, suggested by matcher |
| `matched_automatically` | boolean | True if owner accepted suggestion |
| `recorded_by_user_id` | uuid | FK to `users` |
| `created_at` | timestamptz | |

**Indexes:** `(organization_id, paid_on)`, `(invoice_id)`, `(tenant_id)`.

### 6.9 notifications_log

Every outbound message (WhatsApp or Email) gets one row. Used for delivery tracking, deduplication, audit.

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | PK |
| `organization_id` | uuid | FK, indexed |
| `tenant_id` | uuid | FK, indexed; nullable for owner messages |
| `user_id` | uuid | FK, indexed; nullable for tenant messages |
| `channel` | text | `whatsapp`, `email`, `push` |
| `purpose` | text | `reminder_day_3`, `reminder_day_5`, `reminder_day_7`, `weekly_summary`, `lease_expiring`, `payment_received_owner`, etc. |
| `language` | text | |
| `template_key` | text | E.g., `reminder_v1_hi` |
| `payload_snapshot` | jsonb | The rendered message body and variables, for audit |
| `external_id` | text | WhatsApp message ID, SES message ID |
| `status` | text | `queued`, `sent`, `delivered`, `read`, `failed` |
| `error_code` | text | Nullable |
| `idempotency_key` | text | Unique within `(organization_id, idempotency_key)` |
| `created_at` | timestamptz | |
| `updated_at` | timestamptz | |

**Indexes:** `(organization_id, created_at desc)`, `(external_id)`, `(idempotency_key, organization_id)` unique.

### 6.10 audit_log

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | PK |
| `organization_id` | uuid | FK, indexed |
| `actor_user_id` | uuid | FK; nullable for system actions |
| `action` | text | E.g., `payment.created`, `tenant.updated`, `lease.renewed` |
| `entity_type` | text | |
| `entity_id` | uuid | |
| `before` | jsonb | Nullable |
| `after` | jsonb | Nullable |
| `request_id` | text | Correlation ID from API request |
| `ip_address` | inet | |
| `user_agent` | text | |
| `created_at` | timestamptz | |

**Indexes:** `(organization_id, created_at desc)`, `(entity_type, entity_id)`.

### 6.11 subscriptions

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | PK |
| `organization_id` | uuid | FK, indexed unique |
| `razorpay_subscription_id` | text | Indexed unique |
| `razorpay_plan_id` | text | |
| `plan_name` | text | `starter`, `growth`, `scale` |
| `monthly_price_inr` | numeric(12,2) | |
| `status` | text | `created`, `authenticated`, `active`, `paused`, `halted`, `cancelled`, `expired` |
| `current_period_start` | timestamptz | |
| `current_period_end` | timestamptz | |
| `started_at` | timestamptz | |
| `cancelled_at` | timestamptz | |
| `created_at` | timestamptz | |
| `updated_at` | timestamptz | |

### 6.12 webhook_inbox

Idempotency table for inbound webhooks (WhatsApp, Razorpay). Prevents double processing.

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | PK |
| `provider` | text | `whatsapp`, `razorpay` |
| `external_event_id` | text | Provider's event/message ID |
| `received_at` | timestamptz | |
| `processed_at` | timestamptz | Nullable until done |
| `payload` | jsonb | Raw payload |
| `processing_error` | text | Nullable |

**Indexes:** `(provider, external_event_id)` unique.

### 6.13 Row-Level Security (RLS)

Enable RLS on every multi-tenant table. The Supabase session JWT carries the `organization_id` claim. Policy template:

```sql
CREATE POLICY tenant_isolation ON tenants
FOR ALL
USING (organization_id = (auth.jwt() ->> 'organization_id')::uuid)
WITH CHECK (organization_id = (auth.jwt() ->> 'organization_id')::uuid);
```

Apply to: `properties`, `units`, `tenants`, `leases`, `invoices`, `payments`, `notifications_log`, `audit_log`, `subscriptions`, `users`. The `organizations` table allows reads only of own row; webhook tables are accessed only by service role key (bypasses RLS).

### 6.14 Migrations

Use Alembic. All migrations live in `apps/backend/migrations/versions/`. Conventions:

- Forward-only. No `downgrade()` body needed beyond raising NotImplementedError. Rollback is via restore-from-backup.
- One concern per migration. Don't combine schema changes with data backfills.
- Data backfills go in separate, reversible idempotent Python scripts under `apps/backend/scripts/`.
- Naming: `YYYYMMDD_HHMM_short_description.py`.

---

## 7. API Specification

### 7.1 Conventions

- Base path: `/api/v1`
- All payloads JSON. Request bodies and responses validated by Pydantic v2.
- Authentication: `Authorization: Bearer <supabase_jwt>` header on every endpoint except `/auth/*` and webhook endpoints.
- Pagination: cursor-based via `cursor` and `limit` query params. Default `limit=50`, max `200`.
- Filtering: query string. Field-based, e.g., `?status=pending&billing_month=2026-05`.
- Sorting: `?sort=field,-other_field` (prefix `-` for descending).
- Errors follow [Problem Details for HTTP APIs (RFC 9457)](https://datatracker.ietf.org/doc/html/rfc9457):
  ```json
  {
    "type": "https://rentmanager.in/errors/validation",
    "title": "Validation failed",
    "status": 422,
    "detail": "field 'phone_e164' must be E.164 format",
    "instance": "/api/v1/tenants",
    "errors": [{ "field": "phone_e164", "message": "..." }]
  }
  ```
- All endpoints accept and return `X-Request-ID` header for tracing.
- Idempotency: `POST` endpoints that create resources accept `Idempotency-Key` header. Stored for 24 hours.

### 7.2 Endpoint list

**Auth**

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/auth/otp/send` | `{ phone_e164 }` | `{ request_id }` |
| POST | `/auth/otp/verify` | `{ phone_e164, otp, request_id }` | `{ access_token, refresh_token, user, organization }` |
| POST | `/auth/refresh` | `{ refresh_token }` | `{ access_token, refresh_token }` |
| POST | `/auth/logout` | `{}` | `{}` |
| GET | `/auth/me` | | `{ user, organization }` |

**Onboarding**

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/organizations` | `{ name, default_language }` | `{ organization }` |
| PATCH | `/organizations/me` | partial fields | `{ organization }` |

**Properties**

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/properties` | | paginated list |
| POST | `/properties` | `{ name, type, area, city, pincode }` | `{ property }` |
| GET | `/properties/{id}` | | `{ property, units_count, tenants_count }` |
| PATCH | `/properties/{id}` | partial | `{ property }` |
| DELETE | `/properties/{id}` | (soft delete) | 204 |

**Units**

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/properties/{property_id}/units` | | paginated list |
| POST | `/properties/{property_id}/units` | `{ type, identifier, default_rent }` | `{ unit }` |
| POST | `/properties/{property_id}/units/bulk` | `{ units: [...] }` | `{ created_count }` |
| GET | `/units/{id}` | | `{ unit, active_lease, active_tenant }` |
| PATCH | `/units/{id}` | partial | `{ unit }` |
| DELETE | `/units/{id}` | | 204 |

**Tenants**

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/tenants` | `?q=&unit_id=&active=true` | paginated list |
| POST | `/tenants` | `{ name, phone_e164, email, language, ... }` | `{ tenant }` |
| GET | `/tenants/{id}` | | `{ tenant, active_lease, recent_payments, recent_notifications }` |
| PATCH | `/tenants/{id}` | partial | `{ tenant }` |
| DELETE | `/tenants/{id}` | | 204 |

**Leases**

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/leases` | `?status=&expiring_within_days=45` | paginated list |
| POST | `/leases` | `{ unit_id, tenant_id, start_date, end_date, monthly_rent, security_deposit, billing_day }` | `{ lease }` |
| GET | `/leases/{id}` | | `{ lease, tenant, unit }` |
| POST | `/leases/{id}/renew` | `{ new_end_date, new_monthly_rent }` | `{ lease }` |
| POST | `/leases/{id}/end` | `{ ended_on, reason }` | `{ lease }` |

**Invoices and Payments**

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/invoices` | `?status=&month=&tenant_id=` | paginated list |
| GET | `/invoices/{id}` | | `{ invoice, lease, tenant, payments }` |
| POST | `/payments` | `{ tenant_id, amount, paid_on, method, reference, screenshot_path, invoice_id? }` | `{ payment, suggested_invoice_match }` |
| GET | `/payments` | `?from=&to=&tenant_id=` | paginated list |
| POST | `/payments/match-suggestions` | `{ amount, paid_on, screenshot_path? }` | `{ suggestions: [{ tenant, invoice, confidence }] }` |
| POST | `/payments/{id}/match` | `{ invoice_id }` | `{ payment, invoice }` |
| DELETE | `/payments/{id}` | | 204 (reverses invoice paid amount) |

**Dashboard**

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/dashboard/summary` | `?month=2026-05` | `{ month, collected, target, paid_count, pending_count, overdue_count, needs_attention: [...], recently_paid: [...] }` |
| GET | `/dashboard/leases-expiring` | `?within_days=45` | `{ leases: [...] }` |

**Reports**

| Method | Path | Body | Returns |
|---|---|---|---|
| POST | `/reports/payments-excel` | `{ from, to, property_id? }` | `{ job_id }` (async) |
| GET | `/reports/jobs/{job_id}` | | `{ status, download_url? }` |

**Subscriptions**

| Method | Path | Body | Returns |
|---|---|---|---|
| GET | `/subscriptions/plans` | | list of plans |
| POST | `/subscriptions/checkout` | `{ plan_name }` | `{ razorpay_subscription_id, short_url }` |
| GET | `/subscriptions/current` | | current subscription |
| POST | `/subscriptions/cancel` | `{}` | `{ subscription }` |

**Webhooks (no auth, signature-verified)**

| Method | Path | Notes |
|---|---|---|
| POST | `/webhooks/whatsapp` | Meta Cloud API webhook. Verify with `X-Hub-Signature-256`. |
| GET | `/webhooks/whatsapp` | Meta verify challenge. |
| POST | `/webhooks/razorpay` | Razorpay webhook. Verify with `X-Razorpay-Signature`. |

### 7.3 OpenAPI

FastAPI auto-generates the OpenAPI 3.1 schema at `/openapi.json`. Use `openapi-typescript` in the mobile workspace to generate TS types into `packages/shared-types/`. Regen on every backend change. This keeps frontend types in sync without manual duplication.

---

## 8. Authentication and Authorization

### 8.1 Flow

1. Owner enters phone in app → `POST /auth/otp/send`.
2. Backend calls Supabase Auth `signInWithOtp`. Supabase dispatches OTP via configured SMS provider (MSG91 for India).
3. Owner enters OTP → `POST /auth/otp/verify`.
4. Backend verifies via Supabase, receives session.
5. Backend either creates an `organization` + `user` row (first-time) or fetches existing.
6. Backend issues a custom JWT containing `sub`, `organization_id`, `role`, `language`, expiring in 60 minutes. Refresh token (90 days, rotated on use) stored httpOnly cookie on web, secure storage on mobile.
7. Every subsequent request: `Authorization: Bearer <jwt>`.

### 8.2 Token handling on client

- Mobile: tokens in `expo-secure-store`.
- Web: access token in memory, refresh token in `Secure; HttpOnly` cookie set by API.
- Axios interceptor automatically refreshes access tokens on 401, retries once.

### 8.3 Authorization rules (V1)

| Action | Allowed by |
|---|---|
| Read or write anything within an organization | `role = owner` of that organization |
| Anything else | Denied |

Implemented at two layers:
1. **API layer:** FastAPI dependency `current_user` resolves `organization_id`; all queries filter by it.
2. **Database layer:** Postgres RLS policies enforce the same filter as a defense in depth.

### 8.4 Rate limits

| Endpoint group | Limit |
|---|---|
| `/auth/otp/send` | 3 per phone per 15 minutes; 10 per IP per hour |
| `/auth/otp/verify` | 5 per phone per 15 minutes |
| All other authenticated endpoints | 120 per user per minute |
| Webhook endpoints | No app-level rate limit; Cloudflare handles abuse |

Implemented via `slowapi` (FastAPI + Redis) middleware.

---

## 9. Frontend Architecture

### 9.1 Navigation

Use Expo Router (file-based). Two route groups:

- `(auth)` — login, OTP verify. Unauthenticated layout.
- `(owner)` — main app. Authenticated layout with bottom tab nav: Home, Tenants, Payments, Leases, Settings.

### 9.2 State management

- **Server state:** TanStack Query (`@tanstack/react-query`). One hook per resource (`useDashboard`, `useTenants`, `useTenantById`). 30-second stale time for dashboard, 5 minutes for tenant lists. Mutations invalidate relevant queries.
- **Client state:** Zustand. Stores for `auth`, `ui` (language, theme), `pending uploads`. No Redux, no Context-as-state.

### 9.3 Forms and validation

- React Hook Form + Zod resolver. Zod schemas mirror backend Pydantic schemas. Reuse from `packages/shared-types/` where possible.

### 9.4 UI primitives and styling

- Use NativeWind (Tailwind for React Native) for styling. Tokens defined in `theme/tokens.ts`.
- Color palette and type scale: derive from the prototype HTML. Single source of truth in `theme/tokens.ts`.
- No third-party UI kit. Build primitives (Button, Card, Modal, BottomSheet, Input) directly. Five-day investment that pays back for the life of the product.

### 9.5 Internationalization on the app

- `i18next` + `react-i18next` + `expo-localization`.
- Locale files at `apps/mobile/src/i18n/locales/{en,hi,kn}.json`.
- All UI strings keyed; no inline literals in components.
- Numerals rendered via `Intl.NumberFormat('en-IN')` for Indian lakh/crore grouping. Currency: `₹1,42,500` not `₹142,500`.
- Dates rendered via `date-fns` with locale-specific formatters. Format: `15 May 2026` for all languages (Hindi/Kannada speakers in India read this format fluently).

### 9.6 Offline behavior

V1 does not need offline write. Reads should gracefully show cached data via TanStack Query's persistence (use `@tanstack/query-async-storage-persister`). Writes fail with a friendly retry message.

### 9.7 Accessibility

- Minimum 4.5:1 contrast on body text.
- Touch targets minimum 44×44 px.
- `accessibilityLabel` on every interactive element.
- Dynamic type support via `PixelRatio.getFontScale()`.

### 9.8 Asset pipeline

- All images optimized via `sharp` pre-commit.
- Use `expo-image` not `react-native Image` (better caching).
- Custom fonts (`Plus Jakarta Sans`, `Fraunces`) loaded via `expo-font` in app root.

---

## 10. Background Jobs and Schedulers

All scheduled work runs via Celery Beat. All async work runs via Celery workers.

### 10.1 Job catalog

| Job | Schedule | Purpose |
|---|---|---|
| `generate_monthly_invoices` | Daily at 02:00 IST | For each active lease whose `billing_day == today.day`, create the month's invoice if not present. |
| `mark_overdue_invoices` | Daily at 02:30 IST | Set invoices to `overdue` once `due_date` passes by 1 day. |
| `run_reminder_ladder` | Daily at 09:00 IST | For invoices that are at day 3, 5, or 7 of unpaid, dispatch reminders. |
| `send_lease_expiry_alerts` | Daily at 09:30 IST | For leases expiring in exactly 45 days, send push + WhatsApp to owner. |
| `send_weekly_summary` | Friday at 11:00 IST | Send WhatsApp summary message to each owner. |
| `subscription_health_check` | Daily at 03:00 IST | Reconcile Razorpay subscription statuses. |
| `cleanup_expired_otps` | Daily at 04:00 IST | Purge OTP records older than 24 hours. |
| `rotate_audit_logs` | Monthly | Move audit_log rows older than 12 months to cold storage. |

### 10.2 Reminder ladder algorithm

```
For each invoice where status in ('pending', 'partial'):
    days_overdue = today - invoice.due_date
    if days_overdue == 3 and invoice.last_reminder_day < 3:
        enqueue send_whatsapp_reminder(invoice_id, day=3)
        enqueue send_email_reminder(invoice_id, day=3)
        set invoice.last_reminder_day = 3
    elif days_overdue == 5 and invoice.last_reminder_day < 5:
        enqueue send_whatsapp_reminder(invoice_id, day=5)
        enqueue send_email_reminder(invoice_id, day=5)
        set invoice.last_reminder_day = 5
    elif days_overdue == 7 and invoice.last_reminder_day < 7:
        enqueue send_whatsapp_reminder(invoice_id, day=7)
        enqueue send_email_reminder(invoice_id, day=7)
        set invoice.last_reminder_day = 7
        enqueue notify_owner_overdue(invoice_id)
```

Each send task is idempotent via `idempotency_key = f"{invoice_id}:{day}:{channel}"`. The `notifications_log` row will already exist if a previous attempt was queued, so a duplicate insert is a no-op.

### 10.3 Payment matching algorithm

Triggered synchronously when owner records a payment without specifying an invoice. Returns top 3 suggestions.

Scoring formula per candidate invoice:

```
score = 0
if abs(invoice.amount_due - payment.amount) < 1:        score += 60
elif abs(invoice.amount_due - payment.amount) <= 100:   score += 40
elif abs(invoice.amount_due - payment.amount) <= 1000:  score += 20

days_diff = abs(invoice.due_date - payment.paid_on)
if days_diff <= 2:    score += 25
elif days_diff <= 7:  score += 15
elif days_diff <= 14: score += 5

if invoice.tenant_id == payment.tenant_id (when provided): score += 15

# Future enhancement: OCR on screenshot to extract UPI ref, payer name
```

Threshold: only return suggestions where `score >= 30`. Top suggestion gets `match_confidence = score`.

### 10.4 Weekly summary builder

For each organization with `subscription.status in ('active', 'pilot')`:

1. Compute current-month aggregates: collected, paid_count, pending_count, overdue_count, leases_expiring_in_45_days.
2. Render the WhatsApp message in the organization's default language.
3. Enqueue `send_whatsapp_owner_summary` task with idempotency key `summary:{org_id}:{iso_week}`.

### 10.5 Worker concurrency and queues

Separate queues for separation of concerns and ability to scale independently:

| Queue | Worker concurrency (V1) | Tasks |
|---|---|---|
| `default` | 4 | misc, exports |
| `notifications` | 8 | send_whatsapp_*, send_email_* |
| `webhooks` | 4 | process_whatsapp_webhook, process_razorpay_webhook |
| `scheduled` | 2 | beat-triggered jobs |

Configure via `CELERY_TASK_ROUTES` in `celery_app.py`.

### 10.6 Task retry policy

| Task category | Max retries | Backoff |
|---|---|---|
| External API (WhatsApp, SES, Razorpay) | 5 | exponential, 30s → 16 min, plus jitter |
| Database writes | 3 | exponential, 1s → 8s |
| Webhook processing | 5 | exponential |
| Scheduled jobs | 2 | linear, 60s |

Permanently failed tasks go to a dead-letter queue table (`tasks_dlq`) for manual inspection. Alert via Sentry when DLQ count exceeds 10 in 1 hour.

---

## 11. Third-Party Integrations

### 11.1 WhatsApp Cloud API

**Setup prerequisites** (do before code):

1. Register business (Pvt Ltd or LLP). GST optional initially.
2. Create Meta Business account. Verify via document upload (2-3 weeks).
3. Set up WhatsApp Business Account (WABA). Get phone number verified.
4. Create message templates and submit for approval (each one takes 1-3 days).

**Template catalog for V1** (each needed in `en`, `hi`, `kn`):

| Template key | Category | Purpose |
|---|---|---|
| `reminder_day_3` | UTILITY | Day 3 polite nudge |
| `reminder_day_5` | UTILITY | Day 5 firmer reminder |
| `reminder_day_7` | UTILITY | Day 7 final reminder before owner escalation |
| `owner_weekly_summary` | UTILITY | Friday digest to owner |
| `owner_lease_expiring` | UTILITY | 45-day lease expiry alert to owner |
| `owner_payment_received` | UTILITY | Real-time alert when owner records a payment (optional opt-in) |
| `tenant_payment_confirmed` | UTILITY | Confirmation to tenant when payment is marked received |

Total templates: 7 × 3 languages = 21 to submit for approval. Submit all on day 1 of the build because approval is the slowest external dependency.

**Outbound send flow:**

```python
def send_whatsapp_message(
    tenant_phone: str,
    template_key: str,
    language: str,
    variables: dict,
    idempotency_key: str,
) -> str:
    # 1. Check notifications_log for existing row with this idempotency_key
    # 2. If exists and status in (sent, delivered, read), return existing external_id
    # 3. Construct Cloud API payload
    # 4. POST to https://graph.facebook.com/v20.0/{phone_number_id}/messages
    # 5. On success, write to notifications_log with external_id
    # 6. On failure, retry per policy
```

**Inbound webhook flow:**

```python
@app.post("/webhooks/whatsapp")
async def whatsapp_webhook(request: Request):
    # 1. Verify X-Hub-Signature-256 with WHATSAPP_APP_SECRET
    # 2. Parse payload
    # 3. For each entry/change:
    #    - Extract external_event_id (statuses[i].id or messages[i].id)
    #    - INSERT INTO webhook_inbox ... ON CONFLICT DO NOTHING
    #    - If insert succeeded (new event), enqueue process_whatsapp_webhook task
    # 4. Return 200 immediately
```

### 11.2 Email (Amazon SES)

- SES Mumbai region (`ap-south-1`).
- Verify domain `rentmanager.in` with SPF, DKIM, DMARC at DNS.
- Two configuration sets: `transactional` (reminders, summaries) and `system` (auth, ops alerts).
- Bounces and complaints sent to SNS → Lambda (out of scope for V1) OR polled from SQS by a Celery task.

Email templates rendered server-side via Jinja2. Each template has 3 language variants. Plain-text and HTML alternative parts. Subject and body keys live in `apps/backend/src/rent_manager/integrations/email/templates/`.

### 11.3 Razorpay Subscriptions

- Create 3 plans in Razorpay dashboard: `starter` (₹500/mo), `growth` (₹999/mo), `scale` (₹1499/mo).
- Owner clicks "Upgrade" in app → API creates subscription via Razorpay API → returns `short_url`.
- App opens `short_url` in WebView (mobile) or new tab (web).
- Owner completes payment authorization.
- Razorpay sends webhooks for each event (subscription created, charged, failed, cancelled).
- Webhook handler updates `subscriptions` table and `organizations.tier` accordingly.

Test mode for development. Live mode requires KYC completion (5-7 business days).

### 11.4 Supabase Storage

Two buckets:

- `payment-screenshots` — private. Owner uploads via signed upload URL. Path pattern: `{organization_id}/{year}/{month}/{payment_id}.{ext}`. Max 5 MB.
- `exports` — private. System writes generated Excel files. Path pattern: `{organization_id}/exports/{job_id}.xlsx`. Auto-delete after 7 days via Supabase cron or pg_cron.

Owner gets signed download URLs (15-minute expiry) for export retrieval.

### 11.5 Expo Push Notifications

- Mobile app registers for push permission on first dashboard load.
- Token stored in `users.push_token` (add column to users table).
- Backend uses `httpx` to call `https://exp.host/--/api/v2/push/send` with array of messages.
- Push purposes (V1): `payment_received`, `tenant_overdue`, `lease_expiring_soon`, `weekly_summary_ready`.

---

## 12. Internationalization (i18n)

### 12.1 Languages at V1

- English (`en`) — fallback default
- Hindi (`hi`) — Devanagari script
- Kannada (`kn`) — Kannada script

### 12.2 Translation approach

1. All UI strings live in `apps/mobile/src/i18n/locales/{lang}.json` and `apps/backend/src/rent_manager/integrations/.../templates/{lang}/`.
2. English written first. Hindi and Kannada produced via professional translator review (₹3-5/word; ~500 strings × 3 langs = ₹15-20K one-time).
3. Do **not** use machine translation without human review for the Indian languages. Hindi from Google Translate sounds wrong to native speakers; trust matters.
4. WhatsApp template approval requires the message in each language, so locking translation early is critical-path.

### 12.3 Pluralization, gender, formality

- Hindi has formal/informal "you" (आप / तुम). Use formal आप everywhere.
- Use gender-neutral phrasing where possible. Hindi defaults to masculine, which can read as cold; prefer constructions like "किराया जमा करें" over "किराया जमा करो/करें."
- Pluralization handled by i18next's ICU MessageFormat support.

### 12.4 Number and date formats

- All currency: `Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR' })` → `₹1,42,500.00`. Trim trailing `.00`.
- All dates: `dd MMM yyyy` (e.g., `15 May 2026`) in all languages. Don't translate month names — Indians read English month names fine.

### 12.5 Sending the right language

- Tenant's `language` field controls outbound tenant messages.
- Owner's `language` field controls UI and outbound owner messages.
- Both default to the organization's `default_language`.

---

## 13. Scalability and Performance

V1 sizing assumption: 100 paying owners by month 6, each with average 30 tenants. That's 3,000 tenants, ~36,000 invoices/year, ~30,000 payments/year, ~200,000 outbound messages/year. Single Postgres handles this with room to spare.

Design for the next 10x (1,000 owners, 30,000 tenants) without rewrites.

### 13.1 Database scalability

- **Indexing:** every foreign key, every column used in WHERE/ORDER BY of frequent queries. See Section 6 for explicit indexes.
- **Partial indexes:** for hot status filters (e.g., `WHERE status IN ('pending','partial','overdue')`).
- **Composite indexes:** `(organization_id, billing_month, status)` matches the dashboard query exactly.
- **No N+1 queries:** use SQLAlchemy `selectinload` and explicit JOINs. Add a CI check that fails the build if more than 5 SQL queries fire per API request in tests.
- **Connection pooling:** PgBouncer in transaction-pooling mode on the API server. Max DB connections per API container: 10. Total budget across containers: 40.
- **Read replicas:** not needed at V1. Plan to add at ~500 owners.
- **Vacuum and autovacuum:** Supabase manages this. Monitor bloat at the dashboard level monthly.

### 13.2 Caching strategy

| Cache key pattern | TTL | Invalidated by |
|---|---|---|
| `dashboard:{org_id}:{month_iso}` | 60s | Any payment write, any invoice status change |
| `tenants:list:{org_id}:{filter_hash}` | 300s | Any tenant write |
| `lease:expiring:{org_id}` | 600s | Any lease status change |
| `organization:{org_id}` | 600s | Any org write |

Cache key invalidation handled in domain services. Never invalidate caches from the API layer directly — always in the service responsible for the write.

### 13.3 Async-by-default for outbound work

Every external API call (WhatsApp, SES, Razorpay outbound, Expo Push) happens in a Celery task, not in the API request path. API response p99 target: 300 ms.

### 13.4 Idempotency

Every state-changing operation is idempotent via one of these mechanisms:

- API `POST` accepts `Idempotency-Key` header; result cached 24 hours in Redis keyed by `(user_id, key)`.
- Celery tasks use `idempotency_key` parameter; service layer checks `notifications_log` (or task-specific table) before performing the work.
- Webhook events deduplicated via `webhook_inbox.external_event_id` unique constraint.

### 13.5 Load assumptions and validation

Run a Locust load test before launch with this profile:

- 50 concurrent owners performing typical browse sequences.
- 5 owners recording payments simultaneously.
- 100 WhatsApp delivery webhooks per second (burst from a campaign).

Pass criteria: API p99 < 500 ms, no 5xx errors, no Celery queue backlog growth beyond 1 minute.

---

## 14. Security and Compliance

### 14.1 Threat model summary

| Threat | Mitigation |
|---|---|
| Cross-tenant data access | RLS at DB + `organization_id` filter at API layer. Tested with multi-tenant integration tests. |
| Stolen JWT | Short-lived (60 min), rotation of refresh tokens, ability to revoke via `users.token_version` bump. |
| Webhook spoofing | Signature verification on every webhook payload (HMAC-SHA256 with provider secret). |
| SQL injection | SQLAlchemy parameterized queries only. Never use raw string SQL. |
| Mass enumeration of tenants | Rate limits per user, audit log captures all reads. |
| Stolen UPI screenshot | Stored in private bucket; signed URLs only; never exposed publicly. |
| OTP brute force | 5 attempts per OTP, OTP expires in 5 minutes, rate limit per phone (3 sends per 15 min). |
| API abuse | Cloudflare rate limiting + slowapi at app layer. |
| Credential leakage in logs | Mask PII (phone, OTP) in log formatters. |
| Insider access | Service role key stored only in env vars, rotated every 90 days. |

### 14.2 PII handling

PII fields: tenant name, phone, email, screenshots. Owner name, phone, email.

- Encrypted at rest by Supabase by default (AES-256).
- Encrypted in transit via TLS 1.2+.
- Logs scrub phone numbers and email addresses by default (configure `LOG_REDACT_FIELDS` env).
- Database backups are encrypted by Supabase.

### 14.3 DPDP Act compliance (Indian Digital Personal Data Protection Act)

- Consent: tenant gets first WhatsApp message with explicit consent prompt: "Reply STOP to opt out." Recorded in `tenants.whatsapp_opt_in`.
- Purpose limitation: data used only for rent management. Documented in privacy policy.
- Data minimization: collect only what's needed; no Aadhaar at V1.
- Right to erasure: owner can delete a tenant; soft-delete then hard-delete after 30 days. Pre-emptive design even though DPDP enforcement is rolling out gradually.
- Data localization: Supabase Singapore region (closest to India until Mumbai is available). Plan migration when Mumbai region launches.
- Privacy policy and terms of service: written, reviewed, published before launch. Linked in app from `Settings → Legal`.

### 14.4 Secrets management

- Local dev: `.env` files, gitignored.
- Production: env vars injected via Docker Compose from a `production.env` file on the host, mode 600, root-owned.
- No secrets in code. CI scans with `gitleaks` on every push.

### 14.5 Audit log requirements

Every state-changing API request produces an `audit_log` entry. Audit log is append-only (no UPDATE or DELETE). Retained 12 months active, then archived to cold storage.

---

## 15. Observability

### 15.1 Logs

- Structured JSON logs via `structlog`. One log line per request with `request_id`, `user_id`, `organization_id`, `path`, `method`, `status`, `duration_ms`.
- Worker tasks log start, success, and failure with the same fields.
- Log levels: `DEBUG` (dev only), `INFO` (everything in prod), `WARNING`, `ERROR`.
- Shipped to a single file on the VPS, rotated daily via `logrotate`. View with `journalctl` or `tail -f`. At ~50 customers, add a centralized log shipper (Loki, Vector) if needed.

### 15.2 Metrics

- Prometheus-format metrics exposed at `/metrics` on the API.
- Key metrics:
  - `http_requests_total{method, route, status}`
  - `http_request_duration_seconds{method, route}` (histogram)
  - `celery_task_duration_seconds{task_name}` (histogram)
  - `celery_task_failures_total{task_name}`
  - `whatsapp_messages_sent_total{template, language, status}`
  - `dashboard_cache_hit_total`, `dashboard_cache_miss_total`
- Grafana on the same VPS reads from Prometheus. Three dashboards: API health, Worker health, Business KPIs.

### 15.3 Error tracking

- Sentry SDK in backend and mobile. Capture all unhandled exceptions.
- PII scrubbing config in Sentry: drop `phone`, `email`, `otp`, `payment.reference`.

### 15.4 Tracing

- OpenTelemetry traces from API → DB and API → Celery. Optional at V1; recommended at 25+ customers.

### 15.5 Alerts (V1 minimum)

| Alert | Condition | Action |
|---|---|---|
| API down | No successful health check for 2 minutes | Page owner |
| DB connections > 80% | Sustained 5 min | Investigate |
| Celery DLQ count > 10 | In 1 hour | Investigate |
| WhatsApp send failure rate > 5% | In 15 min | Likely template/account issue |
| Sentry new issue (level=error) | First occurrence | Email |

Alerts go to a Telegram bot or PagerDuty free tier.

---

## 16. Testing Strategy

### 16.1 Backend testing

- **Unit tests** (`pytest`): pure-function tests of services and utils. No DB. No network. Coverage target: 80% of `services/` and `utils/`.
- **Integration tests** (`pytest` + `testcontainers-postgres` + `fakeredis`): exercise the API with a real Postgres in Docker. One container per test session. Covers full request → DB → response. Coverage target: 70% of API routes.
- **Contract tests** (`pytest`): mock external APIs (WhatsApp, SES, Razorpay) and verify request shape and response handling.
- **Factories** (`factory_boy`): one factory per model. `OrgFactory`, `TenantFactory`, `LeaseFactory`, `InvoiceFactory`, `PaymentFactory`. Use these in every integration test.
- **Multi-tenant tests**: explicit test class for every protected route asserting that requests from organization A cannot read or write organization B's data.

Example structure:

```
apps/backend/tests/
  unit/
    test_payment_matcher.py
    test_phone_normalizer.py
    test_currency_format.py
  integration/
    test_auth_flow.py
    test_tenants_crud.py
    test_payments_create.py
    test_dashboard_summary.py
    test_multi_tenant_isolation.py
    test_webhook_whatsapp.py
    test_webhook_razorpay.py
    test_reminder_job.py
  load/
    locustfile.py
  factories.py
  conftest.py
```

### 16.2 Frontend testing

- **Unit tests** (`jest` + `@testing-library/react-native`): component rendering, prop handling, basic interactions.
- **Hook tests**: TanStack Query hooks with mocked API responses.
- **Snapshot tests**: avoided as primary testing strategy (brittle). Use only for icon/SVG output.
- **E2E tests** (`maestro`): three smoke flows that must pass before every release:
  1. OTP login → dashboard renders → tenant list opens.
  2. Add tenant → record payment → dashboard updates.
  3. Open lease list → expiring lease visible.
- Coverage target: 50% of `components/` and `hooks/`. E2E covers happy paths.

### 16.3 Test data and fixtures

A seed script `apps/backend/scripts/seed-dev-data.py` produces a realistic dev dataset:

- 3 organizations (small, medium, large)
- 5-30 tenants each
- 1-3 properties each
- Active leases at various points
- Mix of paid, pending, and overdue invoices
- Some payment history

Run on `make seed-dev` after `make migrate`.

### 16.4 CI test gates

PRs cannot merge unless:

1. Backend: `ruff` lint passes, `mypy` strict passes, all tests pass, coverage delta is not negative.
2. Mobile: `eslint` passes, `tsc --noEmit` passes, jest tests pass.
3. No new high-severity Sentry issues introduced (require manual ack).

### 16.5 Load testing

Run `locust` against staging once per phase milestone. Profile in Section 13.5.

### 16.6 Manual QA checklist

Before every production release, manually verify:

- [ ] OTP login works on iOS, Android, Web
- [ ] Push notification arrives on iOS and Android
- [ ] Hindi and Kannada UI render without truncation
- [ ] WhatsApp template renders correctly with all variables substituted
- [ ] Excel export downloads and opens cleanly
- [ ] Subscription upgrade flow completes via Razorpay test card
- [ ] Multi-tenant isolation spot-check (manual, with two test orgs)

---

## 17. CI/CD and Deployment

### 17.1 Branching

- `main` is always deployable.
- Feature branches: `feat/<short-name>`.
- Hotfix branches: `fix/<short-name>`.
- All changes via PR. Squash-merge to `main`.

### 17.2 CI (GitHub Actions)

Three workflows:

**`backend-ci.yml`** — runs on PRs touching `apps/backend/**`:
- Setup Python 3.12, install via `uv`.
- Lint (`ruff check`).
- Type check (`mypy --strict`).
- Unit tests (`pytest tests/unit`).
- Integration tests (`pytest tests/integration` with testcontainers).
- Coverage report uploaded to Codecov.

**`mobile-ci.yml`** — runs on PRs touching `apps/mobile/**`:
- Setup Node 20, install via `pnpm`.
- Lint (`eslint`).
- Type check (`tsc --noEmit`).
- Unit tests (`jest`).
- Type sync check: regenerate `packages/shared-types` from staging OpenAPI and assert no diff.

**`deploy-backend.yml`** — runs on push to `main`:
- Build Docker image.
- Push to GitHub Container Registry.
- SSH to Hetzner host, pull image, run `docker compose up -d`.
- Run Alembic migrations.
- Smoke test: `curl https://api.rentmanager.in/health`.
- Notify Telegram on success or failure.

**`deploy-mobile.yml`** — runs manually:
- `eas build --profile production --platform all`.
- `eas update` for OTA updates on minor changes.
- `eas submit` for Play Store and App Store releases.

### 17.3 Environments

| Env | Purpose | URL |
|---|---|---|
| `local` | Dev laptop. Docker Compose. | `http://localhost:8000` |
| `staging` | Pre-prod testing. Same VPS, different subdomain and DB. | `https://staging-api.rentmanager.in` |
| `production` | Live customers. | `https://api.rentmanager.in` |

Each env has its own Supabase project, Razorpay account (test vs live), WhatsApp number.

### 17.4 Deployment topology (production V1)

Single Hetzner CX22 VPS running Docker Compose with these services:

- `caddy` — reverse proxy + auto-TLS via Caddy. Routes to `api` and `posthog`.
- `api` — 2 containers behind Caddy load-balance (`uvicorn` with 2 workers each).
- `worker-default` — 1 container, 4 concurrency.
- `worker-notifications` — 1 container, 8 concurrency.
- `worker-webhooks` — 1 container, 4 concurrency.
- `beat` — 1 container, Celery beat scheduler.
- `redis` — 1 container, AOF persistence enabled.
- `prometheus` — metrics scraper.
- `grafana` — dashboards.
- `posthog` — analytics (single-node deploy).

Postgres is **not** on this VPS. It's managed by Supabase.

Backups:
- Supabase auto-backs up DB daily (retained 7 days on free tier, 30 days on Pro).
- Weekly logical dump via `pg_dump` from a cron on the VPS, encrypted, uploaded to a separate cloud bucket (Cloudflare R2 or Backblaze B2). Retain 90 days.

### 17.5 Migration deploy order

1. Run forward-compatible DB migration first.
2. Deploy new API code.
3. Restart workers.

Migrations must not break the previous deployed API version (e.g., never `DROP COLUMN` in the same release that stops writing to it; do drop in the next release).

---

## 18. Phased Build Plan

8 phases. Each is 1 week part-time or 3 days full-time. Total realistic: 10-12 weeks part-time.

### Phase 0 — Pre-build (Week 0, in parallel with everything)

- Register business (LLP or Pvt Ltd).
- Start Meta Business verification.
- Start DLT registration.
- Buy domain `rentmanager.in`.
- Create Supabase project, Razorpay account, AWS account (for SES), Apple Developer account, Play Console account.
- Write privacy policy and terms of service.
- Submit all 21 WhatsApp templates for approval.

### Phase 1 — Foundation (Week 1)

- Monorepo setup, tooling, linters, CI scaffolding.
- Backend: FastAPI skeleton, Supabase Auth integration, OTP flow working end-to-end, `users` and `organizations` tables.
- Mobile: Expo project, Expo Router, login screen, OTP screen, JWT storage.
- Caddy + Docker Compose dev setup.
- Sentry on both sides.

**Done means:** Owner can log in via OTP and see a placeholder dashboard.

### Phase 2 — Core CRUD (Week 2)

- `properties`, `units`, `tenants` tables + API + UI.
- Add property, add unit (flat or bed), add tenant.
- Bulk-add units (for PG owners with 20 beds in one go).
- Tenant list with search and filter.

**Done means:** Owner can set up their entire property portfolio in under 30 minutes.

### Phase 3 — Leases and Invoices (Week 3)

- `leases` table + API + UI. Create lease, view active leases.
- `invoices` table + the `generate_monthly_invoices` job.
- Invoice list view per tenant.

**Done means:** When a lease is added, an invoice gets auto-generated each month on the billing day.

### Phase 4 — Payments (Week 4)

- `payments` table + API + UI.
- Record payment flow with optional UPI screenshot upload to Supabase Storage.
- Payment matching algorithm (Section 10.3).
- Mark invoice paid/partial flow.

**Done means:** Owner can record a payment in 15 seconds, see it tagged to the right invoice.

### Phase 5 — Dashboard and Reminders (Week 5)

- Dashboard summary endpoint + screen.
- Tenant detail screen with payment history and notification log.
- WhatsApp Cloud API client.
- SES email client.
- Reminder ladder job (Day 3, 5, 7).
- Push notification setup (Expo).

**Done means:** Pending invoices automatically fire WhatsApp + Email reminders on schedule. Owner sees dashboard updating.

### Phase 6 — Summaries, Alerts, Reports (Week 6)

- Weekly summary job + WhatsApp owner template.
- Lease expiry alert job.
- Excel export job (async, with signed download URL).
- Settings screen.

**Done means:** Owner receives Friday WhatsApp summary, lease alerts arrive 45 days ahead, Excel exports work.

### Phase 7 — i18n and Polish (Week 7)

- All UI strings extracted into locale files.
- Hindi and Kannada translations integrated.
- All WhatsApp templates rendered in correct language per tenant.
- Pixel polish, empty states, error states, loading states.
- Accessibility pass.

**Done means:** Switching the app to Kannada renders cleanly. Hindi WhatsApp message goes to Hindi-speaking tenant.

### Phase 8 — Subscriptions, Hardening, Launch Prep (Week 8)

- Razorpay Subscriptions integration end-to-end.
- Load test (Section 13.5).
- Security review against Section 14 threat model.
- Production deployment, monitoring dashboards, alerts.
- Manual QA checklist pass.
- 5 pilot customers migrated from manual operations to the app.

**Done means:** V1 is live. Pilot customers are using the app. Subscriptions are billing.

---

## 19. Acceptance Criteria per Feature

For each feature listed in Section 2, the following is "done":

### Phone OTP login
- OTP delivered in under 30 seconds for 95% of attempts.
- Three attempts allowed per OTP before re-send required.
- Session persists across app restarts.
- Logout clears all local credentials.

### Property and unit management
- Owner can create, view, edit, and archive properties.
- Bulk-create units (up to 50) in one request.
- Archived properties hidden from default lists but accessible via filter.

### Tenant records
- Phone number normalized to E.164 on save.
- Duplicate phone within an organization rejected with clear error.
- Language preference defaults to organization default.

### Lease management
- Cannot create overlapping active leases on the same unit.
- Lease ending or renewal updates `renewal_status` correctly.
- Lease history visible per unit.

### Payment recording
- Recording a payment under 5 seconds (excluding upload).
- Match suggestion latency under 800 ms.
- Match accuracy above 90% on exact-amount matches.

### Reminder ladder
- Reminder dispatched within 15 minutes of the scheduled run.
- No duplicate reminders for the same invoice/day/channel.
- Tenant marked opted-out (replied STOP) never receives further WhatsApp.

### Owner dashboard
- Initial load under 500 ms on warm cache.
- Initial load under 1.5 s on cold cache.
- Updates within 2 seconds of any payment write.

### Weekly summary
- Delivered Friday between 11:00 and 11:05 IST.
- Contains all metrics specified in Section 10.4.
- Idempotent within a calendar week.

### Lease expiry alert
- Fires exactly once at 45-day mark (push + WhatsApp).
- Owner can see all expiring leases on a dedicated screen.

### Multilingual UI
- English, Hindi, Kannada selectable from settings.
- 100% of user-facing strings translated (verified by extraction script).
- Currency and dates locale-aware.

### Tenant communication logs
- Every outbound message visible per tenant.
- Channel, language, status, timestamp shown.

### Excel export
- Generated for any date range under 12 months.
- Includes all payment fields per Section 6.8.
- Download URL works for 15 minutes from generation.

### Push notifications
- Token registered on first dashboard visit.
- Notifications deliverable on both iOS and Android.
- Deep link to the relevant screen.

### Subscription billing
- Owner can subscribe via Razorpay Subscriptions.
- Subscription status synced to organization tier in under 1 minute of payment.
- Cancellation works without escalation.

### Audit log
- Every state change written to `audit_log`.
- Audit log not visible to owners in V1 (admin-only).

---

## 20. Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `ENV` | yes | `local`, `staging`, `production` |
| `DATABASE_URL` | yes | Postgres connection string (Supabase pooled) |
| `DATABASE_DIRECT_URL` | yes | Postgres direct (for migrations) |
| `REDIS_URL` | yes | `redis://...` |
| `SUPABASE_URL` | yes | `https://xxx.supabase.co` |
| `SUPABASE_ANON_KEY` | yes | Public anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | yes | For server-side privileged calls |
| `JWT_SECRET` | yes | For custom token signing |
| `JWT_EXPIRY_MINUTES` | no | Default 60 |
| `WHATSAPP_PHONE_NUMBER_ID` | yes | Meta Cloud API phone ID |
| `WHATSAPP_ACCESS_TOKEN` | yes | Meta Cloud API access token |
| `WHATSAPP_APP_SECRET` | yes | For webhook signature verification |
| `WHATSAPP_WEBHOOK_VERIFY_TOKEN` | yes | Echo token Meta uses to verify endpoint |
| `AWS_ACCESS_KEY_ID` | yes | For SES |
| `AWS_SECRET_ACCESS_KEY` | yes | For SES |
| `AWS_REGION` | yes | `ap-south-1` |
| `SES_FROM_EMAIL` | yes | `noreply@rentmanager.in` |
| `RAZORPAY_KEY_ID` | yes | |
| `RAZORPAY_KEY_SECRET` | yes | |
| `RAZORPAY_WEBHOOK_SECRET` | yes | |
| `EXPO_ACCESS_TOKEN` | yes | For push notifications |
| `SENTRY_DSN_BACKEND` | yes | |
| `SENTRY_DSN_MOBILE` | yes | |
| `MSG91_AUTH_KEY` | yes (via Supabase) | OTP delivery |
| `LOG_LEVEL` | no | Default `INFO` |
| `LOG_REDACT_FIELDS` | no | Comma-separated. Default: `phone_e164,otp,email,reference` |
| `CORS_ALLOWED_ORIGINS` | yes | Comma-separated origins |

Document this in `apps/backend/.env.example` with sensible local defaults.

---

## 21. Operational Runbook

Maintain `docs/runbook.md` covering, at minimum:

1. How to deploy a hotfix.
2. How to restart workers without dropping queued tasks.
3. How to replay failed WhatsApp messages from the DLQ.
4. How to restore the DB from a Supabase backup.
5. How to add or update a WhatsApp template.
6. How to add a new language.
7. How to onboard a new pilot customer.
8. How to handle a tenant's "delete my data" (DPDP) request.

---

## 22. Glossary

| Term | Meaning |
|---|---|
| Owner | The paying user of the system. Has 1 or more properties. |
| Tenant | A person renting a unit or bed. Never logs into the app. |
| Property | A building or PG location. |
| Unit | A rentable entity within a property. Either a flat or a bed. |
| Lease | The agreement binding a tenant to a unit for a duration at a price. |
| Invoice | The monthly rent obligation generated from an active lease. |
| Payment | Money received against an invoice. |
| Reminder ladder | The Day-3, Day-5, Day-7 sequence of nudges sent on unpaid invoices. |
| Organization | The multi-tenant boundary. One owner = one organization (V1). |
| BSP | Business Solution Provider (WhatsApp middlemen, e.g., Gupshup). Skipped in V1. |
| DLT | Distributed Ledger Technology registration for telecom communications in India. |

---

**End of specification. Build the V1, ship in 8 phases, validate with the 5 pilot customers waiting on the prototype, then iterate based on what they actually use.**
