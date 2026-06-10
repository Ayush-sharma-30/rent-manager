# Deploying Rent Manager (shareable link)

Two pieces:

- **Backend** (FastAPI + Postgres) → **Render**, from `render.yaml`. Free tier:
  Postgres + web service only. (Celery worker/Redis for auto-scheduled reminders
  are paid and left out — see the commented block in `render.yaml`.)
- **Frontend** (Expo web export) → **Vercel**, static SPA pointed at the backend.

Order matters: deploy the backend first, grab its URL, then build the frontend
with that URL baked in.

---

## 0. Push the repo to GitHub (one time)

Render's Blueprint deploys from a Git repo. This folder isn't a git repo yet.

```bash
cd /Users/ayushsharma/Desktop/rent_manager
git init && git add -A && git commit -m "Rent Manager"
# create an empty repo on github.com first, then:
git remote add origin https://github.com/<you>/rent-manager.git
git branch -M main
git push -u origin main
```

---

## 1. Backend on Render

1. Go to <https://dashboard.render.com> → **New** → **Blueprint**.
2. Connect the GitHub repo you just pushed. Render auto-detects `render.yaml`.
3. The blueprint is **free only**: `rent-db` (Postgres) + `rent-api` (web). No
   paid services. (Automatic scheduled reminders are intentionally left out —
   they'd need a paid Redis + worker; the commented block at the bottom of
   `render.yaml` shows how to add them later. Manual reminders, payments, and
   all CRUD work without them.)
4. Click **Apply**. First build takes a few minutes (Docker build + migrations +
   demo-data seed run automatically on boot).
5. When `rent-api` is **Live**, copy its URL, e.g.
   `https://rent-api-xxxx.onrender.com`.
6. Sanity check: open `https://rent-api-xxxx.onrender.com/health` → `{"status":"ok"}`,
   and `…/docs` for the API explorer.

> Free web services sleep after ~15 min idle, so the very first request after a
> nap takes ~30–60s to wake. Subsequent requests are fast.

---

## 2. Frontend on Vercel

From the mobile app folder, with the Render URL from step 1:

```bash
cd /Users/ayushsharma/Desktop/rent_manager/apps/mobile

# one-time: log in (interactive)
npx vercel login

# point the app at your backend (Preview + Production)
npx vercel env add EXPO_PUBLIC_API_URL
#   → paste https://rent-api-xxxx.onrender.com  (no trailing slash)

# deploy to production
npx vercel --prod
```

`vercel.json` already sets the build (`expo export --platform web`), the output
dir (`dist`), and SPA rewrites — just accept the defaults when the CLI asks to
link the project. Vercel prints your shareable link, e.g.
`https://rent-manager-xxxx.vercel.app`.

> If you set `EXPO_PUBLIC_API_URL` *after* a deploy, run `npx vercel --prod`
> again — the value is baked into the web bundle at build time.

---

## 3. Try it

Open the Vercel link and log in with the seeded owner:

- **Phone:** `9876543210`
- **OTP:** `123456`

(Any phone + `123456` also works — OTP is mocked. Because `ENV=demo`, the verify
screen even shows the code, so anyone you share the link with can sign in.)

---

## Notes / knobs

- **CORS** is `*` (set in the `rent-env` group). The app authenticates with a
  Bearer token, not cookies, so this is safe for a demo. Lock it to your Vercel
  domain later if you like.
- **Security:** mocked OTP means anyone with the link can view/edit the shared
  demo data. Don't put real tenant data here. To hide the OTP hint, set
  `ENV=production` in the `rent-env` group on Render.
- **Re-seeding:** the seed script is idempotent (skips if an org exists). To
  reset the demo, drop/recreate the `rent-db` database on Render and redeploy.
- **WhatsApp / Email / Razorpay** stay stubbed (logged to the DB), so no
  third-party accounts are needed.
