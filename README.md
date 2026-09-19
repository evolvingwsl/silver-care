# Silver Care — Community Chronic Disease Management Support System

A WeChat-based medication management loop for elderly chronic-disease patients
in community healthcare settings. It closes the three gaps of traditional
community follow-up — reminders that never arrive, confirmations that never
come back, and anomalies that reach no one — with one lightweight service.

```
register → plan → remind → confirm → resend → alert → export
```

> **Showcase notice**: this repository is the public showcase edition.
> The data model, patient-facing H5 pages, admin console, statistics and
> export modules are fully preserved; the core messaging, scheduling and
> escalation implementations (WeChat token management, template-message
> sender, reminder scheduler, timeout escalation chain) are intentionally
> omitted. The code is for architecture demonstration and is not runnable
> as-is.

---

## The Service Loop

| Stage | What happens |
|---|---|
| 1. Register | Resident follows the Official Account → signup link is pushed automatically → profile filed with explicit PIPL consent (`consent_flag` / `consent_time` audit trail) |
| 2. Plan | A community health worker enters the medication plan (drug / dosage / time slots) in the admin console |
| 3. Remind | At each scheduled slot, a template message is pushed with a one-tap confirmation link |
| 4. Confirm | The patient taps once on a zero-JS, elderly-phone-friendly H5 page; the confirmation is timestamped |
| 5. Resend | If unconfirmed after `RETRY_MINUTES` (default 30 min), the reminder is resent **once** — an anti-disturbance guarantee |
| 6. Alert | If still unconfirmed after a second timeout, a multi-channel alert chain escalates to human workers (group-bot webhook → doctor-side template → WeCom app) |
| 7. Export | All unconfirmed tasks become a CSV follow-up ledger (UTF-8 BOM, opens cleanly in Excel/WPS) — the workers' daily call list |

## Architecture

```
┌────────────────┐   template msg    ┌──────────────────────────┐
│  Patient (H5)  │ ◄──────────────── │                          │
│  zero-JS pages │ ── one-tap ─────► │   FastAPI service        │
└────────────────┘    confirmation   │                          │
                                     │   ┌──────────────────┐   │
┌────────────────┐   admin console   │   │ scheduler        │   │
│ Community      │ ◄───────────────► │   │ escalation chain │   │
│ health workers │                   │   └──────────────────┘   │
└────────────────┘                   │                          │
        ▲  multi-channel alert       │   SQLite (WAL)           │
        └─────────────────────────── │   patient/plan/          │
                                     │   task/confirmation      │
                                     └──────────────────────────┘
```

## Features

- **Four-table data model** — `patient` / `plan` / `task` / `confirmation`,
  with a task state machine: `pending → sent → resent → confirmed / failed`
- **Follow-up classification** — every task resolves to a clear bucket:
  first-time confirmed / confirmed after resend / still unconfirmed / failed
- **Admin console** — live dashboard (auto-refresh), patient roster with
  search and plan quick-entry, timeline statistics (funnel, per-slot
  confirmation rate, average confirmation latency), one-click CSV ledger,
  pre-flight self-check page
- **Privacy by design** — explicit consent recorded per patient;
  data-minimizing registration form
- **WeChat ecosystem integration** — Official Account callbacks
  (signature verification, subscribe auto-registration, keyword quick
  confirm) and WeCom callbacks (AES-CBC message decryption)

## Tech Stack

Python 3 · FastAPI · SQLite (WAL mode) · server-rendered H5 (zero-JS) ·
WeChat Official Account / WeCom APIs · pycryptodome

## Project Layout

```
.
├── app.py             # the whole service (single-file FastAPI app)
├── requirements.txt   # runtime dependencies
└── README.md
```

## Configuration

All configuration is injected via environment variables — no credentials
live in the repository:

| Variable | Purpose |
|---|---|
| `WX_TOKEN` / `WX_APPID` / `WX_SECRET` | Official Account credentials |
| `WX_TPL_ID` | Medication reminder template ID |
| `WC_CORPID` / `WC_AGENTID` / `WC_SECRET` | WeCom application |
| `WC_CB_TOKEN` / `WC_AESKEY` | WeCom callback encryption |
| `WC_WEBHOOK` | Optional group-bot webhook (alert chain head) |
| `DOC_TPL` / `DOC_OPENID` | Doctor-side alert template / receiver |
| `ADMIN_KEY` | Admin console access key |
| `BASE_URL` | Public base URL of the deployment |
| `RETRY_MINUTES` | Confirmation timeout before resend (default 30) |
| `DB_PATH` | SQLite database file path |

## Disclaimer

This showcase omits the core messaging/scheduling/escalation implementation
by design. All patient data used in development and demonstrations is
fictional. If you are interested in the full system, please open an issue
or contact the maintainer.

## License

MIT
