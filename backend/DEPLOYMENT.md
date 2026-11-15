# Deploying and operating Booski Studios

Booski Studios ships as **one container**: the Booski Core API, which also serves the built web app from the same address. It needs a **PostgreSQL 18** database and, before anyone outside the host machine uses it, an **HTTPS reverse proxy** in front.

> Nothing in this repository deploys anything publicly. By default every part listens on `127.0.0.1` only. This guide covers what has to be in place before that changes.

## 1. What runs where

```
browser ──HTTPS──▶ reverse proxy (TLS, rate limits) ──HTTP, private network──▶ booski container :8000
                                                                                 ├─ /api/v1/…  Booski Core API
                                                                                 └─ /…         web app (index.html + /assets)
                                                                                 │
                                                                                 ▼
                                                                         PostgreSQL 18 (managed or container)
```

- Browser and API share one origin, so the session cookie and CSRF protection need no cross-origin (CORS) configuration.
- The image (`backend/Dockerfile`, built from the repository root) runs as an unprivileged user, has a health check, and handles `SIGTERM` by letting in-flight requests finish (10 s).
- `docker compose up --build` (repository root) runs PostgreSQL, applies migrations, then starts the app on `http://127.0.0.1:8000/`.

## 2. First start on a new installation

1. Create an empty PostgreSQL 18 database and a user that owns it.
2. Set the configuration (below) and apply the schema: `booski db upgrade` (Compose runs this for you in the `migrate` service).
3. Create the first owner and their workspace **on the server** (there are no default accounts and no public sign-up):

   ```bash
   booski create-owner --email you@studio.com --name "Your Name" \
       --workspace-name "Booski Studios" --workspace-slug booski
   # prompts for a password (at least 12 characters); --password-stdin reads it from a pipe
   ```

   With Compose: `docker compose run --rm api booski create-owner …`.
4. Sign in at the app's address. Invite everyone else from **Settings → Invite someone**: share the one-time code and the `/join` address. Nothing is emailed.

## 3. Configuration

All settings are environment variables with the `BOOSKI_` prefix (see `backend/README.md` for the full list).

| Variable | Production value |
| --- | --- |
| `BOOSKI_ENVIRONMENT` | `production`. Hides `/api/docs`, adds HSTS, and **refuses to start** unless the next two are set safely. |
| `BOOSKI_ALLOWED_ORIGINS` | JSON list of the public `https://` address(es), e.g. `["https://studio.example.com"]`. `http://` origins are rejected in production. |
| `BOOSKI_DATABASE_URL` | `postgresql+psycopg://user:password@host:5432/booski` (must include a password in production). Keep it in your secret store, never in the repository. |
| `BOOSKI_TRUSTED_PROXIES` | JSON list of the reverse proxy's IP address(es), e.g. `["10.0.0.5"]`. Only then are `X-Forwarded-For` / `X-Forwarded-Proto` believed. Leave empty when nothing sits in front. |
| `BOOSKI_FRONTEND_DIST` | Set by the image (`/app/web`). Outside the image: the `dist/` folder from `npm run build`. |
| `BOOSKI_LOG_LEVEL` | `INFO` (or `WARNING`). Logs go to standard output with timestamps; unexpected errors include the request id shown to the user. |
| `BOOSKI_BACKUP_DIR` | Where `booski backup create` writes (outside the repository). |
| `BOOSKI_ANTHROPIC_API_KEY` | Optional. The Anthropic API key used for every workspace (keep it in your secret store). Without it AI stays unavailable. Each workspace still starts with AI switched off and a monthly budget (default $20) that an owner or admin sets. `booski ai check` sends one tiny request to confirm the key works. |

## 4. Before allowing external access (checklist)

These are required before anyone connects from another machine. None of them is done for you.

- [ ] **HTTPS everywhere.** Terminate TLS at a reverse proxy (Caddy, nginx, Traefik or a cloud load balancer) with a valid certificate. The session cookie is `Secure` and `__Host-` prefixed, so sign-in does not work over plain HTTP except on `localhost`.
- [ ] **Redirect HTTP to HTTPS** at the proxy. In production the app also sends `Strict-Transport-Security`.
- [ ] **Trusted proxy configuration.** Set `BOOSKI_TRUSTED_PROXIES` to the proxy's address, and make the proxy *overwrite* (not append to) `X-Forwarded-For`. Without this, every request appears to come from the proxy, so per-IP sign-in limits apply to everyone together; with a wrong value, clients could fake their IP.
- [ ] **Run the container privately.** Only the proxy should reach port 8000 (Compose already binds it to `127.0.0.1`). `booski serve` refuses non-local addresses unless `--allow-non-loopback` is given, which the image does *inside the container only*.
- [ ] **Rate limiting at the proxy.** Booski Core limits failed sign-ins per email and per IP, but the proxy should also limit request rates per client (especially `POST /api/v1/auth/login` and `/api/v1/invitations/*`) and cap request body size (documents allow up to 1 MB of text).
- [ ] **Multi-factor authentication or single sign-on.** Not built yet. For external access, put the app behind an identity-aware proxy (for example Cloudflare Access, Tailscale, or an OAuth2 proxy in front of the studio's identity provider) until Booski Core supports MFA/SSO itself.
- [ ] **Operational monitoring.** Poll `GET /api/v1/health/ready` (returns 503 when the database is unreachable or migrations are behind) and alert on failures; collect container logs; alert on repeated 5xx responses.
- [ ] **Backups with tested restores** (section 6), stored off the host, with a retention policy.
- [ ] **Database hardening.** A dedicated database user, TLS to a managed database (`?sslmode=require` in the URL), automated provider snapshots in addition to `booski backup`.
- [ ] **Secrets.** `BOOSKI_DATABASE_URL` and the Compose `.env` come from a secret store; they are git-ignored and excluded from the image build (`.dockerignore`).

## 5. Security headers (already in place)

Every response carries `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: same-origin`, `Cross-Origin-Opener-Policy` / `Cross-Origin-Resource-Policy: same-origin` and a restrictive `Permissions-Policy`.

- **API responses** (`/api/…`): `Content-Security-Policy: default-src 'none'; frame-ancestors 'none'` and `Cache-Control: no-store`, so authenticated data is never cached by browsers or proxies.
- **Web app pages**: a Content Security Policy allowing only the app's own scripts (no inline scripts), Google Fonts, HTTPS images, and API calls to its own origin; `frame-ancestors 'none'`. `index.html` is revalidated on every load; hashed `/assets/*` files are cached for a year.
- **Server software** is not advertised (no `Server` header).
- **Production** adds `Strict-Transport-Security: max-age=31536000; includeSubDomains`.

## 6. Backups and restoring

Backups use PostgreSQL's own tools (`pg_dump` custom format, `pg_restore`). Each backup is a `.dump` file plus a `.json` manifest holding its SHA-256 checksum, the migration revision and the exact row count of every table, taken from the same database snapshot as the dump. Credentials are passed to the tools through environment variables, never on the command line, and are never written into the manifest.

The tools must be PostgreSQL **18** or newer. `booski devdb setup` provides them on Windows; elsewhere install the PostgreSQL 18 client tools or set `BOOSKI_PG_BIN`.

```bash
# Back up the configured database (default folder: BOOSKI_BACKUP_DIR, var/backups)
booski backup create [--dir /secure/backups]

# Prove a backup restores: restores into a throwaway database on the same server,
# compares every table's row count and the migration revision with the manifest, then drops it.
booski backup verify /secure/backups/booski-booski-20261114T093000Z.dump

# Restore into a NEW, EMPTY database on the same server (never overwrites data):
createdb -h <host> -U <user> booski_restored
booski backup restore /secure/backups/booski-booski-20261114T093000Z.dump --target-database booski_restored
```

**Restore procedure after data loss**

1. Stop the app (`docker compose stop api`) so nothing writes during the switch.
2. Create a new empty database and `booski backup restore … --target-database <new>`. The command checks the checksum first and the row counts afterwards, and fails loudly on any mismatch.
3. Point `BOOSKI_DATABASE_URL` at the restored database, run `booski db upgrade` (a no-op unless the backup predates newer migrations), start the app, and check `/api/v1/health/ready`.
4. Keep the old database until you have confirmed the restore.

**Verify needs `CREATEDB`.** `booski backup verify` creates a scratch database; the `booski devdb` user and the official PostgreSQL image's user can. On a managed database without that permission, restore into a separate scratch server instead.

**Containers.** The app image doesn't contain `pg_dump`. Run backups from a machine with the PostgreSQL 18 client tools pointed at the database, or from the database container: `docker compose exec db pg_dump -U booski -Fc booski > booski.dump` (then restore with `pg_restore`).

**Retention (recommended starting point).** Daily backups kept for 14 days, weekly for 8 weeks, monthly for 12 months; copies stored off the host (encrypted object storage); `booski backup verify` run on the latest backup at least weekly. Backups contain every account's data and password hashes: restrict access to them like the database itself.

## 7. Health, start-up and shutdown

- `GET /api/v1/health/live`: the process is up (container health check).
- `GET /api/v1/health/ready`: the database is reachable and migrations are at head. Use it for load-balancer readiness and monitoring.
- Start-up validates the configuration and refuses unsafe production settings with a clear message.
- Migrations run separately (`booski db upgrade`, the Compose `migrate` service) before the app starts, so several app containers never race to migrate.
- Shutdown: on `SIGTERM` the server stops accepting connections and gives in-flight requests 10 seconds (Compose allows 15).

### The agent worker (PR 3.4)

Agent runs are executed by a separate process, `booski agent-worker` (the Compose `agent-worker` service), not by the API. Run at least one alongside the API, with the same database and `BOOSKI_ANTHROPIC_API_KEY`; without a worker, runs stay queued. Several workers can run side by side. On `SIGTERM` a worker stops; a run it was working on is picked up again by any worker once its 10-minute lease expires, and continues from its last completed step.

## 8. Known gaps (later phases)

MFA/SSO, email delivery of invitations, file storage for attachments and assets, scheduled backups, metrics export, and multi-instance session cleanup are not part of Phase 2.
