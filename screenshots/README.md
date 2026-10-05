# Screenshots

Capture these after running the failure simulations from the main README
(`../README.md#failure-simulation-manual`). Use the file names below so the
evidence package is consistent.

| File | What to capture |
| --- | --- |
| `01-dashboard-healthy.png` | Grafana dashboard (http://localhost:3000) with traffic flowing: status UP, uptime ~100%, error rate near 0 |
| `02-scenario1-auth-401.png` | Dashboard showing the HTTP 401 spike in the RPS/failed-requests panels |
| `03-scenario2-timeout.png` | Latency panel with p95/p99 above the 3s threshold line |
| `04-scenario3-server-error-500.png` | 5xx error ratio panel above the 5% line plus failed-requests trend |
| `05-scenario4-rate-limit-429.png` | Failed-requests panel showing the HTTP 429 bars |
| `06-prometheus-alerts-firing.png` | http://localhost:9090/alerts with alerts in FIRING state |
| `07-alertmanager-active.png` | http://localhost:9093 showing active alerts, grouped by alertname |
| `08-notification-proof.png` | Terminal output of `docker compose logs alert_receiver` (or the Slack/email message) |
| `09-structured-log-rca.png` | Terminal showing a `jq` filtered log line with the `request_id` and stack trace |
| `10-pytest-passing.png` | `pytest -q` output with all tests passing |

Guidelines:

- Include the full browser window with the time range visible (last 15m).
- Show alert names and timestamps so firing/resolved order can be verified.
- Redact webhook URLs, tokens and e-mail addresses before committing images.
- Optional: record a 2-3 minute screen capture walking through scenarios 1-4.