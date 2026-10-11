# Deployment

Covers transport security, which the SRS requires ("the system shall encrypt
all data in transit via HTTPS/TLS", §5.3, with TLS 1.3 named in §3.4) but which
is a deployment concern rather than application code.

---

## Local development — no TLS

The default stack serves plain HTTP on port 5173. That is appropriate for
development on `localhost`, where traffic never leaves the machine.

```bash
docker compose up -d --build
# http://localhost:5173
```

---

## Local TLS testing — self-signed certificate

Proves the TLS configuration works end to end before a real certificate is
involved.

```bash
bash scripts/generate_dev_certs.sh certs
docker compose -f docker-compose.yml -f docker-compose.tls.yml up -d --build
# https://localhost  (the browser will warn — see below)
```

**The browser warning is expected and correct.** A self-signed certificate
encrypts the connection but nothing vouches for who presented it, so the
browser cannot distinguish it from an interception. Accept the warning for
local testing; never do so for a real deployment.

### Verified behaviour

| Check | Result |
|---|---|
| Protocol negotiated | TLS 1.3 |
| Cipher suite | `TLS_AES_256_GCM_SHA384` |
| `http://` → `https://` | 301 redirect |
| `Strict-Transport-Security` | `max-age=63072000` |
| `Content-Security-Policy` | `default-src 'self'`, no third-party origins |
| `X-Frame-Options` | `DENY` |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| API over HTTPS | `/api/v1/health` returns `"database": true` |

---

## Production — CA-issued certificate

### Option A: Let's Encrypt via certbot (recommended)

Free, automated, and renews itself. Needs a real domain name resolving to the
host, because the HTTP-01 challenge proves control of that domain.

**1. Point DNS at the host** and confirm it resolves before going further — a
failed challenge counts against Let's Encrypt's rate limits.

**2. Obtain the first certificate.** The TLS config already exposes the ACME
challenge path over plain HTTP, which must stay reachable:

```bash
mkdir -p certbot-webroot certs

docker run --rm \
  -v "$PWD/certbot-webroot:/var/www/certbot" \
  -v "$PWD/letsencrypt:/etc/letsencrypt" \
  -p 80:80 \
  certbot/certbot certonly \
    --standalone \
    -d clauseguard.example.in \
    --email you@example.in \
    --agree-tos --no-eff-email

cp letsencrypt/live/clauseguard.example.in/fullchain.pem certs/
cp letsencrypt/live/clauseguard.example.in/privkey.pem   certs/
```

**3. Set `server_name`** in `frontend/nginx.tls.conf` to the real domain,
replacing the `_` catch-all. A catch-all works but means the server answers for
any hostname pointed at it.

**4. Start the TLS stack:**

```bash
docker compose -f docker-compose.yml -f docker-compose.tls.yml up -d --build
```

**5. Automate renewal.** Let's Encrypt certificates last 90 days. A monthly
cron entry is sufficient:

```cron
0 3 1 * * cd /srv/clauseguard && docker run --rm \
  -v "$PWD/certbot-webroot:/var/www/certbot" \
  -v "$PWD/letsencrypt:/etc/letsencrypt" \
  certbot/certbot renew --webroot -w /var/www/certbot \
  && cp letsencrypt/live/*/fullchain.pem certs/ \
  && cp letsencrypt/live/*/privkey.pem certs/ \
  && docker compose exec web nginx -s reload
```

`nginx -s reload` rather than a restart: reload picks up the new certificate
without dropping in-flight connections.

### Option B: TLS terminated upstream

If deploying behind a cloud load balancer, a reverse proxy or an ingress
controller that already terminates TLS, use the **base** `docker-compose.yml`
rather than the TLS overlay — terminating twice adds nothing.

In that case the upstream terminator must:

- Redirect HTTP to HTTPS.
- Send `X-Forwarded-Proto: https`, so the backend does not generate
  downgraded URLs.
- Set `Strict-Transport-Security`, since nginx no longer will.
- Permit a request body of at least 12 MB, or the 10 MB upload limit (TBD-1)
  will be rejected upstream before the API can return its own clear message.

---

## Pre-deployment checklist

Items that are safe in development and **not** safe in production:

| Setting | Development | Production |
|---|---|---|
| `SECRET_KEY` | `dev-only-insecure-change-me` | **Generate a fresh one.** Every issued JWT is signed with it; a known key means anyone can mint a valid token for any account. `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `POSTGRES_PASSWORD` | `clauseguard` | A generated password |
| `ENVIRONMENT` | `development` | `production` |
| `CORS_ORIGINS` | `http://localhost:5173` | The real origin only. With nginx proxying `/api`, browser traffic is same-origin and this can be empty. |
| Database port 5433 | Published to the host | **Not published.** Remove the `ports` block from the `db` service so the database is reachable only inside the compose network. |
| `--reload` on uvicorn | Enabled | Removed — it watches the filesystem and costs performance |
| Volume mount of `./backend/app` | Enabled for live editing | Removed, so the image is what runs |

Uploaded contracts live in the `contracts` Docker volume. They are commercially
sensitive (§5.3), so that volume needs the same backup and access treatment as
the database.

---

## What is deliberately not automated

There is **no CI deployment step and no committed certificate.** Private keys
and production secrets do not belong in a repository, and `.gitignore` excludes
`certs/`, `*.pem` and `*.key` to make committing one harder. Deployment is a
documented manual procedure rather than a pipeline, which is proportionate for
a project at this stage.
