<div align="center">

# 🩺 Pulse: API Monitoring Dashboard

### An API that tells *me* when it's sick, before anyone else has to.

A small FastAPI service that can **break on purpose**, wrapped in the monitoring I'd want on a real one:
metrics, a live dashboard, alerts to **email + Slack + webhook**, and logs I can trace back to a single request.

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-storage-003B57?logo=sqlite&logoColor=white)
![Prometheus](https://img.shields.io/badge/Prometheus-metrics-E6522C?logo=prometheus&logoColor=white)
![Grafana](https://img.shields.io/badge/Grafana-dashboards-F46800?logo=grafana&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)
![Tests](https://img.shields.io/badge/tests-20%20passing-brightgreen)

[Why](#-why-i-built-this) · [Quick start](#-quick-start) · [Notifications](#-notifications-email-slack-webhook) · [Break it](#-break-it-on-purpose) · [Find the cause](#-finding-the-root-cause) · [Troubleshooting](#-troubleshooting)

</div>

---

## 💡 Why I built this

An API usually "works" right up until it quietly doesn't: a few slow responses, a burst of `401`s, a database table that went missing. Most of the time I'd only find out when somebody told me.

I wanted the opposite: the API tells me first, and tells me *why*.

So I built a tiny service with the endpoints you'd expect (`/health`, `/users`, `/products`) plus a handful of endpoints whose only job is to fail in realistic ways: a `500`, a slow response, a `429`, a `401`. Then I put the full observability loop around it:

| 👀 See it | 🔔 Hear about it | 🔎 Explain it |
|---|---|---|
| Prometheus collects metrics every 5 s. Grafana turns them into a live dashboard. | Alertmanager sends a message to **Gmail, Slack and a webhook** when something stays broken. | Every request gets an ID that is returned to the caller and stamped on every log line. |

The whole thing starts with one command, runs in five containers, and needs nothing else installed but Docker.

---

## 🗺️ How it fits together

```mermaid
flowchart LR
    U(["🧑‍💻 You / Swagger / curl"]) -->|"HTTP :8000"| A["⚡ FastAPI<br/>middleware + routers"]
    A <-->|"SQL"| D[("🗄️ SQLite<br/>/data/app.db")]
    A -->|"/metrics every 5s"| P["🔥 Prometheus :9090"]
    A -.->|"JSON logs + request_id"| L[["📜 docker logs"]]
    P -->|"PromQL"| G["📊 Grafana :3000"]
    P -->|"firing alerts"| AM["🚨 Alertmanager :9093"]
    AM -->|"SMTP"| E["📧 Gmail"]
    AM -->|"incoming webhook"| S["💬 Slack"]
    AM -->|"HTTP POST"| R["🧪 alert_receiver<br/>(echo, for local proof)"]
```

**Life of an alert**

```mermaid
stateDiagram-v2
    [*] --> Inactive
    Inactive --> Pending: condition becomes true
    Pending --> Inactive: condition clears
    Pending --> Firing: still true after the for duration
    Firing --> Resolved: condition clears
    Resolved --> Inactive
```

Alertmanager notifies on **Firing** and again on **Resolved**, so the all-clear arrives too.

| Container | Port | What it does |
|---|---|---|
| `fastapi_app` | 8000 | The API, `/metrics`, Swagger docs, SQLite file in a Docker volume |
| `prometheus` | 9090 | Scrapes every 5 s, evaluates 5 alert rules, keeps 7 days of data |
| `alertmanager` | 9093 | Groups alerts and routes them to email, Slack and the webhook |
| `alert_receiver` | internal | Echo container that prints every webhook, so delivery is visible in logs |
| `grafana` | 3000 | Pre-provisioned 12-panel dashboard, no clicking required |

---

## 🚀 Quick start

**You need:** Docker Desktop (WSL 2 on Windows) and free ports `8000`, `9090`, `9093`, `3000`.

```powershell
git clone https://github.com/Nieldave/api-monitoring-dashboard.git
cd api-monitoring-dashboard

# Alertmanager mounts ./secrets, so create it (see "Notifications" to fill it in)
New-Item -ItemType Directory -Force secrets | Out-Null

docker compose up -d --build
docker compose ps
```

After a minute, `docker compose ps` should list all five containers, with the first four marked **healthy**.

> 💡 **Without the secret files** the stack still runs and the webhook still works. Email and Slack just log an error until you add credentials (next section).

### 🔗 Where to look

| What | URL | Login |
|---|---|---|
| 📘 Swagger (try every endpoint) | http://localhost:8000/docs | none |
| 📊 Grafana dashboard | http://localhost:3000 | `admin` / `admin` (skip the password prompt) |
| 🔥 Prometheus alerts | http://localhost:9090/alerts | none |
| 🎯 Prometheus targets | http://localhost:9090/targets | none |
| 🚨 Alertmanager | http://localhost:9093 | none |
| 📈 Raw metrics | http://localhost:8000/metrics | none |

Open Swagger, click **Try it out → Execute** on `/health`, `/users` and `/products`, then watch the Grafana numbers move.

<details>
<summary>▶️ Run only the API, without Docker</summary>

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1      # if blocked: Set-ExecutionPolicy -Scope Process Bypass
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```

macOS / Linux: `source .venv/bin/activate`. The dashboard and alerts need the Docker stack.

</details>

<details>
<summary>🧹 Stop and clean up</summary>

```powershell
docker compose down        # stop containers, keep data
docker compose down -v     # stop and delete everything (Prometheus, Grafana, SQLite)
```

</details>

---

## 🔌 The API

Every endpoint is a `GET`, so Swagger and a browser are all you need.

| Endpoint | Returns | Purpose |
|---|---|---|
| `/health` | `200` / `503` | Status, uptime, dependency checks (including a real SQLite query). Sets `api_up` |
| `/users` | `200` / `500` | Rows from the SQLite `users` table |
| `/products` | `200` / `500` | Rows from the SQLite `products` table |
| `/simulate-auth-error` | `401` | Invalid API key or token |
| `/simulate-timeout` | `200` (slow) | Sleeps 3.5 s. `?seconds=` overrides the delay |
| `/simulate-error` | `500` | `?mode=http`, `?mode=unhandled` (full stack trace) or `random` |
| `/simulate-rate-limit` | `429` | Includes a `Retry-After: 30` header |
| `/metrics` | `200` | Prometheus metrics (not counted in request metrics) |

### 🗄️ Real data, not hard-coded lists

Users and products live in SQLite (`app/database.py`). Tables are created on startup, seeded with 5 rows each, and stored in the `app_data` Docker volume, so data survives restarts.

```powershell
# Look inside the database
docker compose exec fastapi_app python -c "import sqlite3; c=sqlite3.connect('/data/app.db'); print(c.execute('SELECT * FROM users').fetchall())"

# Change a row, then call GET /users again: the API reflects it with no restart
docker compose exec fastapi_app python -c "import sqlite3; c=sqlite3.connect('/data/app.db'); c.execute('UPDATE users SET name=? WHERE id=1',('Demo Live Edit',)); c.commit()"
```

---

## 📡 What gets measured

| Metric | Type | Why it matters |
|---|---|---|
| `http_requests_total{method,endpoint,status_code}` | counter | Traffic, failures, error percentage, per-status rates |
| `http_request_duration_seconds` | histogram (0.05 → 10 s) | Average and p50 / p90 / p95 / p99 latency |
| `http_requests_in_flight` | gauge | Concurrency and pile-ups |
| `api_up` | gauge | `1` when `/health` passes, `0` when a dependency fails |
| `up{job="fastapi"}` | built-in | Can Prometheus reach the API at all? |
| `process_*`, `python_*` | default collectors | Memory, CPU, file descriptors (server health) |

The `endpoint` label is the **route template**, and unknown paths become `unmatched`, so label cardinality stays bounded.

---

## 📊 The dashboard

Grafana loads the datasource and the **FastAPI API Monitoring** dashboard automatically (`grafana/`). It opens as the home page and refreshes every 5 s. Set the range to **Last 15 minutes**.

| Row | Panels |
|---|---|
| 🟢 At a glance | Service status (UP/DOWN) · Uptime % · Average response time · Total requests · Failed requests (4xx + 5xx) · Error rate % |
| 📈 Trends | Throughput by status code · Latency p50/p90/p99 (with the 3 s line) · Failed requests and error trends · 5xx ratio vs the 5 % threshold · In-flight requests · Requests per endpoint |

The **Requests per endpoint** panel is the quickest way to see *which* route is misbehaving.

---

## 🚨 Alerts

Five rules in `monitoring/alerts.yml`, evaluated every 5 s:

| Alert | Fires when | For | Severity |
|---|---|---|---|
| `APIDowntime` | `api_up == 0` or the scrape target is down | 30 s | 🔴 critical |
| `HighResponseTime` | p95 latency over 2 min is above **3 s** | 1 m | 🟠 warning |
| `HTTP500ServerErrors` | 5xx responses exceed **5 %** of requests (2 min window) | 30 s | 🔴 critical |
| `RateLimitSpike` | `429` responses above **0.1 / s** | 15 s | 🟠 warning |
| `AuthFailureSpike` | `401` responses above **0.2 / s** | 15 s | 🟠 warning |

Alerts are grouped by `alertname` and `severity`, so a burst becomes one message instead of fifty. The first message goes out after 5 s, updates follow every 30 s, and repeats every hour.

> ℹ️ Rate and quantile alerts need *sustained* traffic. One bad request won't move a 2-minute ratio, so the scenarios below run in loops.

---

## 📬 Notifications: email, Slack, webhook

All three channels hang off one Alertmanager receiver (`monitoring/alertmanager.yml`), and every firing or resolved alert is delivered to each of them independently. If Gmail is down, Slack and the webhook still work.

Secrets never go into the YAML. They are read from files in `./secrets/` (git-ignored, mounted read-only into the container).

### 🧪 Webhook (works out of the box)

```powershell
docker compose logs alert_receiver --tail 60
```

### 📧 Email via Gmail

1. Turn on 2-Step Verification for the Gmail account, then create an **App Password** (your normal password will not work).
2. Save it:
   ```powershell
   Set-Content -Path .\secrets\smtp_password -Value "your-16-char-app-password" -NoNewline -Encoding ascii
   ```
3. In `monitoring/alertmanager.yml`, set your address in `smtp_from`, `smtp_auth_username` and `email_configs → to / from`.

### 💬 Slack

1. Create an app with **Incoming Webhooks** and add a webhook for a channel (for example `#api-alerts`).
2. Save the URL (no quotes, no extra text):
   ```powershell
   Set-Content -Path .\secrets\slack_webhook_url -Value "https://hooks.slack.com/services/XXXXX/XXXXX/XXXXXXXX" -NoNewline -Encoding ascii
   ```
3. Test the webhook on its own:
   ```powershell
   Invoke-RestMethod -Uri (Get-Content .\secrets\slack_webhook_url -Raw) -Method Post -ContentType "application/json" -Body '{"text":"Hello from the terminal"}'
   ```

### ✅ Apply and test the whole pipeline

```powershell
docker compose exec alertmanager amtool check-config /etc/alertmanager/alertmanager.yml
docker compose restart alertmanager

# Send a fake alert straight to Alertmanager
$body = '[{"labels":{"alertname":"SlackTest","severity":"warning","service":"fastapi-monitoring-demo"},"annotations":{"summary":"Test alert","description":"Manual test alert"}}]'
Invoke-RestMethod -Uri http://localhost:9093/api/v2/alerts -Method Post -ContentType "application/json" -Body $body
```

Within ~10 s a `[FIRING] SlackTest` message should land in Slack and in your inbox, followed by `[RESOLVED]` about a minute later.

> 🔒 Never commit the files in `secrets/`. If a webhook URL or App Password ever leaks, revoke it and create a new one.

---

## 💥 Break it on purpose

This is the fun part. Keep Grafana, `http://localhost:9090/alerts` and Slack open side by side, then pick a scenario. Use `curl.exe` in PowerShell (plain `curl` is an alias for `Invoke-WebRequest`).

| # | Scenario | Endpoint | Alert you should see | Roughly |
|---|---|---|---|---|
| 1 | 🔑 Invalid authentication | `/simulate-auth-error` | `AuthFailureSpike` | 15 to 30 s |
| 2 | 🐢 Slow response | `/simulate-timeout` | `HighResponseTime` | 1 to 2 min |
| 3 | 💣 Server error | `/simulate-error` | `HTTP500ServerErrors` | 30 to 45 s |
| 4 | 🚦 Rate limit | `/simulate-rate-limit` | `RateLimitSpike` | 15 to 30 s |
| 5 | 🔌 Downtime / failed health | stop the container | `APIDowntime` | ~30 s |
| 6 | 🗄️ Database failure | drop a table | `HTTP500ServerErrors` + `APIDowntime` | 30 to 45 s |

<details>
<summary><b>🔑 1. Invalid authentication (401)</b></summary>

```powershell
curl.exe -i http://localhost:8000/simulate-auth-error
1..60 | % { curl.exe -s -o NUL -w "%{http_code} " http://localhost:8000/simulate-auth-error; Start-Sleep 1 }
```

You'll see 401 bars in Grafana and the log line `simulated_auth_failure` with `reason: invalid_api_key`.

</details>

<details>
<summary><b>🐢 2. Slow response / timeout</b></summary>

```powershell
curl.exe -m 3 http://localhost:8000/simulate-timeout        # client gives up: curl error 28
1..60 | % { curl.exe -s -o NUL -w "%{time_total}s " http://localhost:8000/simulate-timeout }
```

p95 and p99 cross the red 3 s line. Logs show `duration_ms` above 3500.

</details>

<details>
<summary><b>💣 3. Server error (500)</b></summary>

```powershell
curl.exe -i "http://localhost:8000/simulate-error?mode=unhandled"
1..80 | % { curl.exe -s -o NUL -w "%{http_code} " http://localhost:8000/simulate-error; Start-Sleep -Milliseconds 500 }
```

The 5xx ratio climbs above the 5 % line. The `unhandled` mode leaves a full stack trace in the logs.

</details>

<details>
<summary><b>🚦 4. Rate limit (429)</b></summary>

```powershell
curl.exe -i http://localhost:8000/simulate-rate-limit        # note the Retry-After header
1..60 | % { curl.exe -s -o NUL -w "%{http_code} " http://localhost:8000/simulate-rate-limit; Start-Sleep -Milliseconds 500 }
```

</details>

<details>
<summary><b>🔌 5. Downtime and failed health check</b></summary>

```powershell
# Hard down: Prometheus can't scrape
docker compose stop fastapi_app
docker compose start fastapi_app

# Soft down: the API is up but reports itself unhealthy (/health returns 503, api_up = 0)
$env:APP_HEALTH_FORCE_FAILURE = "true"; docker compose up -d fastapi_app
Remove-Item Env:APP_HEALTH_FORCE_FAILURE; docker compose up -d fastapi_app
```

The status tile turns **DOWN**. When the service returns, you get a `[RESOLVED]` message.

</details>

<details>
<summary><b>🗄️ 6. Database failure (run this last)</b></summary>

```powershell
docker compose exec fastapi_app python -c "import sqlite3; c=sqlite3.connect('/data/app.db'); c.execute('DROP TABLE users'); c.commit()"
1..80 | % { curl.exe -s -o NUL -w "%{http_code} " http://localhost:8000/users; Start-Sleep -Milliseconds 500 }
```

`/users` returns 500, `/health` returns 503 with `database: unavailable`, and the log contains `sqlite3.OperationalError: no such table: users`.
Recover with `docker compose restart fastapi_app`, which recreates and reseeds the table.

</details>

> ⏱️ Wait about 3 minutes between scenarios (or run `docker compose restart fastapi_app`) so the previous alert's rate window can clear.

---

## 🔎 Finding the root cause

An alert tells you *that* something is wrong. Request IDs tell you *why*. Every request gets an `X-Request-ID` header (an incoming one is honoured), and the same ID appears on every JSON log line written while that request ran.

**The routine:**

1. **Symptom.** Start from the alert or the Grafana panel.
2. **Where.** The *Requests per endpoint* panel names the failing route.
3. **What.** Pull the error log and stack trace:
   ```powershell
   docker compose logs fastapi_app --no-log-prefix --since 15m | Select-String "unhandled_exception" | ForEach-Object { $_.Line | ConvertFrom-Json } | Select-Object -First 1 | Format-List event, request_id, exception
   ```
4. **Which request.** Follow one request end to end:
   ```powershell
   docker compose logs fastapi_app --no-log-prefix | Select-String "PASTE_REQUEST_ID_HERE"
   ```
5. **Database suspects:**
   ```powershell
   docker compose logs fastapi_app --no-log-prefix --since 5m | Select-String "no such table" | Select-Object -First 1
   ```

**A typical log line**

```json
{"event": "http_request", "method": "GET", "path": "/simulate-error", "endpoint": "/simulate-error",
 "status_code": 500, "duration_ms": 3.41, "client": "172.18.0.1",
 "request_id": "9f1c2b7e4a8d4c1f9a0b5d3e7c6a1b22", "level": "error", "logger": "app.access"}
```

**Reading the signals**

| You see | Likely cause | Next step |
|---|---|---|
| 401 spike on one endpoint | Expired or wrong credentials, or a brute-force attempt | Check the client's key; look at the `client` log field |
| p95 high, in-flight requests rising | Slow dependency or exhausted workers | Check `/health` dependencies and `process_*` metrics |
| 5xx with a traceback | Unhandled error in the code path | Read the traceback; correlate with the last change |
| 429 bursts | Client over quota or a retry storm | Make sure clients honour `Retry-After` |
| `up == 0`, no `api_up` | Container crashed or network problem | `docker compose ps`, then the logs |
| `api_up == 0` but scrapes work | A dependency inside `/health` is failing | Read the `dependencies` object in the response |

---

## 🧪 Tests

20 pytest tests cover health (including forced failure and database-unavailable), reading from SQLite, the 401 / 500 / 429 / delay behaviours, metric counters and request-ID handling. They use a temporary SQLite file, so your Docker data is never touched.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -q
```

It takes about 5 seconds, mostly one test that waits out the full 3.5 s delay.

---

## ⚙️ Configuration

Set with environment variables (prefix `APP_`):

| Variable | Default | Effect |
|---|---|---|
| `APP_LOG_LEVEL` | `INFO` | Log verbosity |
| `APP_TIMEOUT_DELAY_SECONDS` | `3.5` | Delay used by `/simulate-timeout` |
| `APP_RATE_LIMIT_RETRY_AFTER_SECONDS` | `30` | `Retry-After` value on `/simulate-rate-limit` |
| `APP_HEALTH_FORCE_FAILURE` | `false` | Makes `/health` return 503 and sets `api_up = 0` |
| `APP_DATABASE_PATH` | `data/app.db` (`/data/app.db` in Docker) | SQLite file location |
| `GRAFANA_ADMIN_PASSWORD` | `admin` | Grafana admin password |

---

## 🗂️ Project layout

```text
api-monitoring-dashboard/
├── app/
│   ├── main.py              # app factory + request middleware (request IDs, metrics, logs)
│   ├── config.py            # settings from APP_* environment variables
│   ├── database.py          # SQLite schema, seed data, connection helper
│   ├── metrics.py           # Prometheus counter, histogram, gauges
│   ├── logging_config.py    # structured JSON logging (structlog)
│   └── routers/             # health, users, products, simulation
├── monitoring/
│   ├── prometheus.yml       # scrape config (every 5 s) + alerting target
│   ├── alerts.yml           # the 5 alert rules
│   └── alertmanager.yml     # routing + email / Slack / webhook receivers
├── grafana/
│   ├── provisioning/        # datasource + dashboard loader
│   └── dashboards/          # api-monitoring.json
├── tests/                   # pytest suite
├── secrets/                 # smtp_password, slack_webhook_url (git-ignored)
├── screenshots/             # evidence from my own test runs
├── Dockerfile               # multi-stage build, non-root user
├── docker-compose.yml       # the 5-container stack
└── requirements.txt
```

---

## 🧠 Design choices worth knowing

- **Alert on ratios and percentiles, not single events.** A `for:` delay on every rule keeps one blip from paging anyone.
- **Route templates as labels.** `/users`, not `/users?x=1`, so Prometheus never drowns in label combinations.
- **Secrets live in files.** Alertmanager can't expand environment variables, and files keep credentials out of YAML and Git.
- **`/health` checks something real.** It runs actual queries against SQLite, so a broken database shows up as `503` and `api_up = 0`.
- **Independent channels.** Email, Slack and the webhook each succeed or fail on their own.
- **Single uvicorn worker.** `prometheus_client`'s default registry is per process. Multiple workers would need multiprocess mode.

---

## 🛠️ Troubleshooting

<details>
<summary><b>Dashboard shows "No data"</b></summary>

Send some requests, check http://localhost:9090/targets shows `fastapi` as **UP**, and set the time range to *Last 15 minutes*.

</details>

<details>
<summary><b>An alert doesn't fire</b></summary>

Keep the loop running. Rate and quantile alerts need sustained traffic and must stay true for their `for:` time. Check the state at http://localhost:9090/alerts.

</details>

<details>
<summary><b>Alert fires but no email arrives</b></summary>

Check the spam folder, then `docker compose logs alertmanager` for SMTP errors. Make sure `secrets/smtp_password` contains the Gmail **App Password** (not the account password) with no trailing newline.

</details>

<details>
<summary><b>Alert fires but nothing in Slack</b></summary>

Run the direct `Invoke-RestMethod` webhook test above. If it fails, the URL is wrong. If it works, check `docker compose logs alertmanager` and confirm `secrets/slack_webhook_url` has only the URL. If Slack complains about the channel, remove the `channel:` line from the config.

</details>

<details>
<summary><b>Docker Desktop won't start, or <code>docker compose</code> returns a 500</b></summary>

Quit Docker Desktop, run `wsl --update` and `wsl --shutdown` in an admin PowerShell, start Docker Desktop again, and wait for "Engine running".

</details>

<details>
<summary><b>Port already in use</b></summary>

Stop the other program, or change the left-hand port in `docker-compose.yml`.

</details>

<details>
<summary><b><code>/users</code> returns 500 or <code>/health</code> says <code>database: unavailable</code></b></summary>

Search the logs for the `sqlite3` error. `docker compose restart fastapi_app` recreates and reseeds missing tables. If the file is damaged: `docker compose down -v`, then `docker compose up -d`.

</details>

<details>
<summary><b>PowerShell prints errors for <code>curl</code></b></summary>

`curl` is an alias for `Invoke-WebRequest`. Use `curl.exe`.

</details>

---

## 🔧 Day-to-day maintenance

| Task | How |
|---|---|
| Tweak alert thresholds | Edit `monitoring/alerts.yml`, then `docker compose exec prometheus promtool check rules /etc/prometheus/alerts.yml` and `curl.exe -X POST http://localhost:9090/-/reload` |
| Change alert routing | Edit `monitoring/alertmanager.yml`, validate with `amtool check-config`, then `docker compose restart alertmanager` |
| Monitor a new endpoint | Add a route under `app/routers/`. The middleware measures it automatically |
| Back up the database | `docker compose cp fastapi_app:/data/app.db .\backup.db` |
| Reset to seed data | `docker compose down -v` then `docker compose up -d` |
| Upgrade a component | Bump the pinned image tag in `docker-compose.yml`, `docker compose pull && docker compose up -d`, then re-run the tests |

---

## 📸 Screenshots

<details>
<summary>Show the dashboard and alerts in action</summary>

| | |
|---|---|
| ![Healthy dashboard](screenshots/01-dashboard-healthy.png) | ![Latency above 3s](screenshots/03-scenario2-timeout.png) |
| Healthy dashboard | Latency crossing the 3 s line |
| ![Alerts firing](screenshots/06-prometheus-alerts-firing.png) | ![Webhook delivery](screenshots/08-notification-proof.png) |
| Alerts firing in Prometheus | Notification delivered |
| ![Slack alert](screenshots/11-slack-alert.png) | ![Email alert](screenshots/12-email-alert.png) |
| The same alert in Slack | …and in the inbox |

</details>

---

## 🧭 What's next

- [ ] Swap SQLite for PostgreSQL and monitor it with a Postgres exporter
- [ ] Ship logs to Loki so Grafana can jump from a metric spike straight to its log lines
- [ ] Add a Blackbox exporter for external, outside-in uptime checks
- [ ] Inhibit rules, so `APIDowntime` silences the secondary alerts while the service is down
- [ ] A phone or on-call channel (PagerDuty / Opsgenie) for critical alerts

---

<div align="center">

Built by **[Niel](https://github.com/Nieldave)**, because I'd rather hear it from my dashboard than from a user. 🩺

</div>