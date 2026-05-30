# 12 — Connecting Django to PostgreSQL

Switching from the default SQLite (`db.sqlite3` file in the project root)
to PostgreSQL. The Django ORM code does NOT change — only `settings.py`
+ a driver install. That's the whole point of having an ORM.

---

## 1. Run Postgres in Docker

No system install needed — pull the official image and run it as a
container. Same setup works on macOS, Linux, and Windows.

### Pull the image (one-time)

```bash
docker pull postgres:16
```

### Start a container

```bash
docker run --name orm-postgres \
  -e POSTGRES_DB=orm_db \
  -e POSTGRES_USER=orm_user \
  -e POSTGRES_PASSWORD=orm_password \
  -p 5432:5432 \
  -v orm_pg_data:/var/lib/postgresql/data \
  -d postgres:16
```

What each flag does:

| Flag | Purpose |
|---|---|
| `--name orm-postgres` | Name the container so you can `start/stop` it later |
| `-e POSTGRES_DB=orm_db` | Auto-create this database on first start |
| `-e POSTGRES_USER=orm_user` | Auto-create this superuser role |
| `-e POSTGRES_PASSWORD=orm_password` | Password for that user |
| `-p 5432:5432` | Map host port 5432 → container port 5432 |
| `-v orm_pg_data:/var/lib/postgresql/data` | **Named volume** — keeps your data even if you delete the container |
| `-d postgres:16` | Run detached (background), use the postgres:16 image |

The `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` env vars are
read by the image's entrypoint on FIRST run only — they create the
database and user automatically, so you can skip the manual
`CREATE USER` / `CREATE DATABASE` step below.

### Day-to-day commands

```bash
docker ps                       # is it running?
docker stop  orm-postgres       # stop the container
docker start orm-postgres       # start it again (data persists)
docker logs  orm-postgres       # see Postgres logs
docker rm    orm-postgres       # delete the container (volume keeps data)
```

### docker-compose alternative (cleaner)

Drop a `docker-compose.yml` in the project root:

```yaml
services:
  db:
    image: postgres:16
    container_name: orm-postgres
    environment:
      POSTGRES_DB: orm_db
      POSTGRES_USER: orm_user
      POSTGRES_PASSWORD: orm_password
    ports:
      - "5432:5432"
    volumes:
      - orm_pg_data:/var/lib/postgresql/data

volumes:
  orm_pg_data:
```

Then:

```bash
docker compose up -d      # start (creates DB+user on first run)
docker compose down       # stop
docker compose logs -f db # tail logs
```

Easier to share with teammates than a long `docker run` command.

---

## 2. Create / verify the database + user (only if NOT using env vars)

If you used the `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` env
vars above, **skip this step** — the container already created them.

Otherwise, drop into the container's psql:

```bash
docker exec -it orm-postgres psql -U postgres
```

Inside `psql`:

```sql
CREATE USER orm_user WITH PASSWORD 'orm_password';
CREATE DATABASE orm_db OWNER orm_user;
GRANT ALL PRIVILEGES ON DATABASE orm_db TO orm_user;
\q
```

### Quick smoke test from the host

```bash
docker exec -it orm-postgres psql -U orm_user -d orm_db -c "\dt"
```

Empty list = connected, just no tables yet (Django will create them in
step 6).

---

## 3. Install the Python driver

Django talks to Postgres via the `psycopg2` driver. We use the
**binary** wheel so we don't have to install Postgres dev headers
locally:

```bash
# from inside your virtualenv
pip install psycopg2-binary
```

Save it for reproducibility:

```bash
pip freeze > requirements.txt
```

Notes:
- `psycopg2-binary` ships precompiled — no `pg_config` / build tools
  needed. Perfect for local dev.
- For production you'd usually switch to `psycopg2` (source build,
  links against the system's libpq for better performance).
- Newer projects can use `psycopg` (v3), but `psycopg2-binary` is still
  the most common choice and works fine with all current Django versions.

---

## 4. Point Django at Postgres

Edit `orms/settings.py`. Replace the SQLite block:

```python
# BEFORE — SQLite default
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

with:

```python
# AFTER — Postgres
DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.postgresql',
        'NAME':     'orm_db',
        'USER':     'orm_user',
        'PASSWORD': 'orm_password',
        'HOST':     '127.0.0.1',   # 'localhost' also works
        'PORT':     '5432',        # Postgres default
    }
}
```

What each key means:

| Key | What it is |
|---|---|
| `ENGINE` | Which Django backend to use (`postgresql`, `sqlite3`, `mysql`, `oracle`) |
| `NAME`   | The database name (must already exist; Django won't create it) |
| `USER`   | DB role Django logs in as |
| `PASSWORD` | Password for that role |
| `HOST`   | Where Postgres is running. `127.0.0.1` for local. Leave `''` for unix socket on Linux. |
| `PORT`   | TCP port. `5432` is the Postgres default. |

---

## 5. Don't commit your password — use env vars

Putting the password in `settings.py` is fine for local-only learning,
but the moment you push to GitHub or share the project, you've leaked
credentials. Use environment variables instead:

```python
import os

DATABASES = {
    'default': {
        'ENGINE':   'django.db.backends.postgresql',
        'NAME':     os.environ.get('DB_NAME', 'orm_db'),
        'USER':     os.environ.get('DB_USER', 'orm_user'),
        'PASSWORD': os.environ['DB_PASSWORD'],          # required, will KeyError if missing
        'HOST':     os.environ.get('DB_HOST', '127.0.0.1'),
        'PORT':     os.environ.get('DB_PORT', '5432'),
    }
}
```

Locally, set them in a `.env` file (and add `.env` to `.gitignore`!):

```dotenv
DB_NAME=orm_db
DB_USER=orm_user
DB_PASSWORD=orm_password
DB_HOST=127.0.0.1
DB_PORT=5432
```

Load it automatically with `python-dotenv`:

```bash
pip install python-dotenv
```

Top of `manage.py` (or `settings.py`):

```python
from dotenv import load_dotenv
load_dotenv()
```

---

## 6. Run migrations against the new DB

Postgres is fresh — no tables yet. Run:

```bash
python manage.py migrate
```

Django will recreate every table, including the auth/admin tables,
in `orm_db`. SQLite's `db.sqlite3` file is now ignored; you can delete it
or keep it around as a backup.

Create a fresh admin user:

```bash
python manage.py createsuperuser
```

---

## 7. Verify the switch worked

```bash
python manage.py dbshell
```

That opens `psql` connected as your Django user. Inside:

```sql
\dt                       -- list all tables
SELECT * FROM core_restaurantmodel;
\q
```

Seeing your tables = Django is talking to Postgres successfully.

Or from a Python shell:

```bash
python manage.py shell
```

```python
from django.db import connection
print(connection.vendor)   # -> 'postgresql'
```

---

## 8. Moving existing data from SQLite to Postgres

If you already had data in SQLite that you want to keep:

```bash
# 1. Dump from old DB (still on SQLite settings)
python manage.py dumpdata --natural-foreign --natural-primary \
    -e contenttypes -e auth.permission > data.json

# 2. Switch settings.py to Postgres, then:
python manage.py migrate           # create empty tables
python manage.py loaddata data.json
```

`-e contenttypes -e auth.permission` excludes Django-managed tables that
get auto-created and would otherwise clash.

---

## 9. Common errors

| Error | Cause | Fix |
|---|---|---|
| `django.db.utils.OperationalError: could not connect to server` | Container not running | `docker start orm-postgres` (or `docker compose up -d`) |
| `FATAL: database "orm_db" does not exist` | Env vars weren't set on FIRST container start | Recreate container with `POSTGRES_DB=orm_db`, or create it manually via `docker exec -it orm-postgres psql -U postgres` |
| `FATAL: password authentication failed for user "orm_user"` | Wrong password / wrong user | Re-check `settings.py` matches the `POSTGRES_USER` / `POSTGRES_PASSWORD` env vars |
| `django.core.exceptions.ImproperlyConfigured: Error loading psycopg2 module` | Driver not installed | `pip install psycopg2-binary` |
| `permission denied for schema public` | Newer Postgres (15+) restricts `public` schema | `GRANT ALL ON SCHEMA public TO orm_user;` via `docker exec -it orm-postgres psql -U postgres -d orm_db` |
| `port is already allocated` on `docker run` | Port 5432 in use (system Postgres, or old container) | Stop the conflicting service, or map a different host port: `-p 5433:5432` |

---

## 10. Why bother switching from SQLite?

SQLite is great for learning, but it has hard limits:

| | SQLite | Postgres |
|---|---|---|
| Concurrent writes | One writer at a time (file lock) | Many writers, MVCC |
| Data types | Loose (numbers stored as TEXT sometimes) | Strict, rich (JSONB, arrays, UUID native, …) |
| Constraints | Limited (`CHECK` is basic) | Full `CHECK`, partial indexes, exclusion constraints |
| ORM features | Most work | Everything (`ArrayField`, `JSONField` with operators, full-text search, …) |
| Production-ready | No | Yes |

The Django ORM code you wrote — `Q`, `F`, `Subquery`, `OuterRef`,
`Exists`, `annotate`, `prefetch_related` — runs unchanged. That's the
whole appeal: the ORM abstracts the SQL dialect, you just swap the engine.

---

## Cheat sheet

```bash
# 1. Pull image + start container (DB + user auto-created from env vars)
docker pull postgres:16
docker run --name orm-postgres \
  -e POSTGRES_DB=orm_db \
  -e POSTGRES_USER=orm_user \
  -e POSTGRES_PASSWORD=orm_password \
  -p 5432:5432 \
  -v orm_pg_data:/var/lib/postgresql/data \
  -d postgres:16

# 2. Install driver
pip install psycopg2-binary

# 3. Edit settings.py DATABASES block to use postgresql backend

# 4. Migrate + create superuser
python manage.py migrate
python manage.py createsuperuser

# 6. Verify
python manage.py dbshell
> \dt
```
