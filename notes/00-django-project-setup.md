# 00 — Django Project Setup

How a Django backend is structured: projects, apps, the files you get for
free, and the commands that create them. Examples use my own setup —
project `orms`, app `core`.

## Step 0 — Install Django

Django is a Python package. Install it into a virtual environment so it
stays isolated from other projects:

```bash
python3 -m venv .venv          # create the virtual environment
source .venv/bin/activate      # activate it (Mac/Linux)
pip install django             # install Django into it
```

My `.venv/` folder at the project root is exactly this. The `(.venv)` at
the start of my terminal prompt means it's active.

## Project vs App — the key difference

This is the concept to get straight:

| | **Project** | **App** |
|---|---|---|
| What it is | The whole website + its configuration | One feature/module of the site |
| How many | Exactly **one** per site | **Many** per project |
| Reusable? | No — it's this specific site | Yes — an app can be dropped into another project |
| In my repo | `orms/` (+ `manage.py`) | `core/` |

> Analogy: the **project** is the house. **Apps** are the rooms. The house
> has wiring and plumbing shared by everything (settings); each room has a
> specific job (kitchen, bedroom). You could lift a "room" and reuse its
> design in another house.

A real site might have apps like `accounts`, `blog`, `payments` — each a
self-contained piece — all inside one project.

## Step 1 — Create the project

```bash
django-admin startproject orms .
```

- `django-admin` is the tool that ships with Django.
- `orms` is the project name.
- The trailing `.` means "create it **here**, in the current folder."
  Without the dot you'd get an extra nested `orms/` wrapper folder.

This generates:

```
orm/                  ← my project root folder
├── manage.py         ← command-line tool (created at the root)
└── orms/             ← the project CONFIG package
    ├── __init__.py
    ├── settings.py
    ├── urls.py
    ├── wsgi.py
    └── asgi.py
```

### What each project file does

| File | Purpose |
|------|---------|
| `manage.py` | The command runner. Every `python manage.py ...` goes through it. I don't edit it. |
| `__init__.py` | Empty file that marks the folder as a Python **package**. |
| `settings.py` | **All configuration** — installed apps, database, time zone, etc. I edit this a lot. |
| `urls.py` | The **root URL map** — which URL goes to which view. |
| `wsgi.py` | Entry point for **deployment** on a traditional (sync) web server. |
| `asgi.py` | Entry point for **deployment** on an async server (websockets, etc.). |

For now I only touch `settings.py` and `urls.py`. `wsgi.py`/`asgi.py`
matter later, when the site goes live on a real server.

## Step 2 — Create an app

```bash
python manage.py startapp core
```

This generates the `core/` folder:

```
core/
├── __init__.py
├── admin.py
├── apps.py
├── models.py
├── views.py
├── tests.py
└── migrations/
    └── __init__.py
```

### What each app file does

| File | Purpose |
|------|---------|
| `__init__.py` | Marks `core` as a Python package. |
| `models.py` | **Database models** — my tables (`RestaurantModel`, etc.). |
| `admin.py` | Registers models so they show up in the admin site. |
| `views.py` | **Views** — functions/classes that handle a request and return a response. |
| `apps.py` | Config class for this app (name, default settings). |
| `tests.py` | Where automated tests for the app go. |
| `migrations/` | Holds **migration files** — the history of model changes (topic 03). |

> Note: an app does **not** come with a `urls.py`. If an app needs its own
> URL routes, I create that file myself.

## Step 3 — Register the app

Creating the app folder isn't enough — Django ignores it until I list it
in `settings.py`:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',   # 3rd-party (I added this for runscript)
    'core',                # ← my app
]
```

**Why register?** Django only scans `INSTALLED_APPS` for models, migrations,
admin, templates, and management commands. An unregistered app is invisible.

## What's installed by default — the 6 `django.contrib.*` apps

These come pre-listed in a fresh project. They're Django's own built-in
apps:

| App | What it gives me |
|-----|------------------|
| `admin` | The `/admin/` web dashboard. |
| `auth` | Users, passwords, permissions, login — the `User` model I import. |
| `contenttypes` | A registry of all models; auth & generic relations depend on it. |
| `sessions` | Server-side session storage (keeps users logged in). |
| `messages` | One-off "flash" messages ("Saved successfully"). |
| `staticfiles` | Collects/serves CSS, JS, images. |

That's why a brand-new project already has an admin and a login system
before I write any code.

## Commands that came from one install

After `pip install django`, these are available via `manage.py`:

| Command | What it does |
|---------|--------------|
| `runserver` | Starts the local development web server. |
| `startapp <name>` | Creates a new app folder. |
| `makemigrations` | Turns model changes into migration files (topic 03). |
| `migrate` | Applies migrations — builds/updates the database tables. |
| `createsuperuser` | Creates an admin login. |
| `shell` | Opens a Python shell with Django loaded. |
| `test` | Runs the tests in `tests.py`. |

`runscript` is **not** in this list — it came from the third-party
`django-extensions` package I installed separately.

## The typical first-run sequence

```bash
django-admin startproject orms .     # 1. create project
python manage.py startapp core       # 2. create app
# 3. add 'core' to INSTALLED_APPS in settings.py
python manage.py migrate             # 4. build the default DB tables
python manage.py createsuperuser     # 5. make an admin login
python manage.py runserver           # 6. start the server → http://127.0.0.1:8000
```

## What I should remember

1. **One project, many apps.** Project = config + the whole site. App = one feature.
2. `django-admin startproject` makes the project; `manage.py startapp` makes an app.
3. An app is dead until it's added to `INSTALLED_APPS`.
4. A fresh project ships with 6 `django.contrib` apps — that's why admin + auth already work.
5. `settings.py` and `urls.py` are the project files I actually edit.
6. The `migrations/` folder records every model change over time.

Next: [01 — What is an ORM](01-what-is-an-orm.md)
