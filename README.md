# Event Ticketing API

Django API for event ticketing with **general admission** (inventory-based) and **reserved seating** (hall layout, seat map, hold, payment, expiry). Includes a small browser UI, Celery workers for background jobs, and Docker Compose for local development.

## Features

- **General admission**: purchase by quantity with idempotency and concurrent-safe inventory.
- **Reserved seating**: venue → hall → zones → sections → seats; per-event `EventSeat` state (`available` / `reserved` / `sold`).
- **Reservation flow**: hold seats with TTL, confirm to create an order, fake payment gateway for demos, optional Celery task to expire unpaid holds.
- **Modular payment flow**: provider-oriented payment service with callback finalization, idempotent payment creation, and safe re-callback handling.
- **Redis seat locks (load shedding)**: per-seat Redis locks before DB transactions to reduce hot-spot contention during bursts.
- **Outbox pattern**: `OutboxEvent` rows for downstream integration (processed by a periodic task).
- **Sample data**: `seed_teatrshahr` management command for a demo hall and events.

## Stack

- Python 3.12, Django 5+
- PostgreSQL
- Redis (Celery broker/result backend and per-seat locking)
- Celery + Celery Beat
- Structlog (JSON logs)

## Repository layout

| Path | Role |
|------|------|
| `core/` | Settings, URLs, Celery app, home view |
| `events/` | `Event` model and list API |
| `venues/` | Venue, hall, zones, sections, seats, seat map JSON API |
| `tickets/` | Orders, reservations, inventory, services, tasks |
| `templates/frontend/` | Single-page UI for orders and seat map |

## Quick start (Docker)

1. Copy the example Compose file and environment file:

   ```bash
   cp docker-compose.example.yml docker-compose.yml
   cp .env.example .env
   ```

   Edit `.env` and set a strong `POSTGRES_PASSWORD` (and any other values you need).

2. For **VS Code debugging** (debugpy on ports `5678` / `5679`), use the debug example instead:

   ```bash
   cp docker-compose.debug.example.yml docker-compose.yml
   ```

3. Build and run:

   ```bash
   docker compose up --build
   ```

4. Apply migrations and (optionally) load demo data:

   ```bash
   docker compose exec web python manage.py migrate
   docker compose exec web python manage.py seed_teatrshahr
   ```

5. Open **http://127.0.0.1:8000/** for the UI, or **http://127.0.0.1:8000/events/** for the JSON event list.

## Quick start (local, without Docker)

Requires PostgreSQL and Redis running locally; set `DATABASE_HOST`, `DATABASE_PORT`, and Celery URLs in `.env` or the environment.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py seed_teatrshahr
python manage.py runserver
```

In separate terminals (with the same env):

```bash
celery -A core worker -l info
celery -A core beat -l info
```

## Environment variables

See **`.env.example`**. Common keys:

| Variable | Purpose |
|----------|---------|
| `POSTGRES_*` | Database name, user, password |
| `DATABASE_HOST` / `DATABASE_PORT` | DB host (e.g. `db` in Compose, `127.0.0.1` locally) |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Redis URLs |
| `RESERVATION_MINUTES` | How long a seat hold lasts before expiry cleanup |
| `EXPIRE_RESERVATIONS_INTERVAL_SECONDS` | How often Beat enqueues the expiry task |
| `PROCESS_OUTBOX_INTERVAL_SECONDS` | How often Beat enqueues outbox processing |
| `SEAT_LOCK_TTL_SECONDS` | Redis lock TTL for seat holds (prevents lock leaks on crash) |
| `REDIS_LOCK_URL` | Redis URL for locking (defaults to `CELERY_BROKER_URL`) |

## Redis locking notes (reserved seating)

Reserved seating uses Postgres row locks as the correctness layer, and adds **per-seat Redis locks** to reduce DB load when many users try to reserve the same seats.

- **Wrong unlock prevention**: locks store a unique token; release deletes the key only if the token matches (Lua check) so an expired lock cannot delete a newer lock acquired by someone else.
- **Multi-lock deadlock prevention**: when reserving multiple seats, lock keys are acquired in a deterministic order (sorted seat IDs) so competing requests do not deadlock.
- **Lock leak protection**: every lock has a TTL so if the process crashes mid-flight the lock expires automatically.

## Payment architecture notes

Payments are implemented in a modular way under `tickets/payments/` so the fake provider can later be swapped with a real gateway (e.g. Zarinpal) without changing reservation/order core logic.

- **Idempotent payment creation**: each payment is created with an idempotency key and reused on retries instead of creating duplicate payment rows.
- **Authority-based callback**: payment callback finalization is keyed by payment `authority` (provider reference), not by client session.
- **Transactional finalize**: callback finalization runs in a DB transaction with row locks to update payment, order, reservation, and seats atomically.
- **Replay-safe callback**: repeated callbacks for the same authority are safe (already-finalized payments return current state instead of double-processing).
- **Seat state synchronization**: payment success moves seats to `sold`; payment failure/cancel moves them back to `available`.

## API overview

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Web UI |
| GET | `/events/` | List events (GA uses `TicketInventory`; reserved uses `EventSeat` counts) |
| POST | `/events/<id>/tickets/` | General admission purchase (`Idempotency-Key` header, form `quantity`) |
| GET | `/events/<id>/seatmap/` | Reserved event seat map JSON |
| POST | `/events/<id>/reservations/` | Hold seats (JSON `seat_ids`, `Idempotency-Key`) |
| POST | `/events/<id>/reservations/confirm/` | Create order from hold (then pay via fake gateway) |
| POST | `/payments/fake/callback/` | Finalize payment by `authority` (`success` / `failed`) |
| POST | `/orders/<id>/pay/` | Fake payment (`{"status":"success"}` or `"failed"`) |
| GET | `/payments/fake/<authority>/` | Demo payment page |
| GET/PATCH | `/events/<id>/orders/`, `/orders/<id>/`, `/orders/<id>/cancel/` | Orders |

## Load testing

With the app running:

```bash
locust -f locustfile.py --host=http://127.0.0.1:8000
```
