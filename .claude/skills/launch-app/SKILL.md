---
name: launch-app
description: Launch and drive the TTRPG Campaign Manager locally — backend (FastAPI) and frontend (Vue 3), database, migrations, and a seeded default user with a pre-filled campaign. Use this whenever you need to run, start, preview, or verify the app in a browser.
---

# Launching TTRPG Campaign Manager locally

Two apps: `backend/` (FastAPI, port 8000) and `frontend/` (Vue 3 + Vite, port 5173).
Both need to be running to drive the app in a browser.

## 1. Prerequisites (one-time, per machine)

Check first — a fresh machine has none of these:

```bash
which poetry docker just node npm
```

Missing pieces:

- **Docker** and **Node/npm**: `sudo apt install -y docker.io docker-compose-v2 nodejs npm`
  — then `sudo usermod -aG docker $USER` and **log out and back in** (group membership
  does not apply to the current session; `newgrp docker` or a subshell does not persist
  across separate tool calls either — a real re-login is the only fix).
- **just**: `sudo apt install -y just` (packaged in Ubuntu 26.04's default repos).
- **Poetry**: `curl -sSL https://install.python-poetry.org | python3 -` — no sudo, installs
  to `~/.local/bin`. Make sure that's on `PATH`.

All of the above need `sudo` — hand the command to the user (e.g. via the terminal tool)
rather than trying to type a password.

## 2. Project setup (one-time, per clone)

From the repo root:

```bash
cd backend && poetry install && cd ..
cp .env.example .env
```

`.env.example` needs `BREVO_API_KEY` / `MAIL_FROM` filled in for real email sending —
**but they don't need to be real for local dev.** Any string works and unblocks
registration; only actually calling Brevo's API needs a real key. Discord/Google
SSO env vars only matter if those buttons are clicked. See the comments in
`.env.example` for what each one is for and why it's required with no default.

Generate the JWT secret so it isn't the placeholder:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
# paste into JWT_SECRET_KEY= in .env
```

```bash
just db-up       # starts PostgreSQL via Docker
just migrate      # applies all migrations
cd frontend && npm install && cd ..
```

## 3. Start both servers

Prefer the browser tool's `preview_start` over a bare shell command — it gives you logs,
a live tab, and screenshot/console access. A `.claude/launch.json` is already checked
into this repo with `backend` (port 8000) and `frontend` (port 5173) entries — just:

```
preview_start(name: "backend")
preview_start(name: "frontend")
```

If `.claude/launch.json` is missing or stale, the equivalent manual commands are:

```bash
just dev              # backend, from repo root
cd frontend && npm run dev   # frontend
```

Verify the backend before touching the frontend: `GET http://localhost:8000/docs` should
render Swagger UI with no errors. Check `preview_logs` for a traceback if it doesn't —
a missing/invalid `.env` var is the most common cause (see §2).

## 4. Seed a default user and a filled campaign

Empty state is not a useful thing to look at. One command creates a default user and a
campaign with acts, a sequence, scenes in every status, two characters, and a source:

```bash
just seed
```

Idempotent — safe to run again any time; it finds the existing user/campaign by name and
does nothing further if they're already there. That's a floor, not a sync: it will
never *update* a campaign it already created, even if `campaign.py` changes underneath
it. **For a genuinely clean slate — new seed content included — use `just reset`**
instead of `just seed`: it drops the database volume, recreates it, migrates, and
re-seeds from nothing. That's also the go-to when local manual testing has mutated the
seeded data enough that it's no longer a good baseline.

**Login:** username `gm`, password `DevPassword123!`, at `http://localhost:5173/login`.
Lands on "Les Landes Oubliées" — two acts, five scenes across all three statuses
(planned/done/skipped), one sequence, two characters, one source.

The seed lives at `backend/scripts/seed/`, one module per context (`user.py`,
`campaign.py`, `source.py`) plus `__main__.py` orchestrating them — mirrors how
`tests/unit/`, `tests/integration/` etc. are organised by context without living inside
`app/`. Need a *different* shape of data? Edit the relevant module directly rather than
fighting the UI by hand — each one composes the same application services the API
routers use, nothing more.

## 5. Driving it

- Frontend at `http://localhost:5173` — login page is the entry point.
- Backend API docs at `http://localhost:8000/docs`.
- A first-load `POST /users/refresh → 401` in the console/network tab is expected and
  not a bug: the SPA always tries to resume a session on load, and there isn't one yet.
- To confirm a change actually works, don't just load a page — click through the flow it
  touches (log in, open the seeded campaign, navigate the outline) and read the result,
  not just the exit code of the dev server.

## Known gaps (not fixed by this skill)

- `.env.example`'s Brevo/Discord/Google vars are placeholders. Real email delivery and
  SSO need real credentials from those providers.
- `just seed` only covers the `user`, `campaign` and `source` contexts (whatever existed
  when this skill was written). If a new context is added and worth seeding, add a
  module under `backend/scripts/seed/` and call it from `__main__.py` rather than
  writing a second seed path.
