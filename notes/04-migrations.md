# 04 — Migrations

Migrations are Django's way of turning model changes into SQL schema
changes. You edit `models.py`, run two commands, and Django updates the
database to match.

## The two-step flow

```bash
python manage.py makemigrations   # 1. write a migration file (.py)
python manage.py migrate          # 2. apply it to the database
```

- **`makemigrations`** reads your `models.py`, compares it to the last
  migration file on disk, and writes a new migration file describing the
  diff (e.g. "add column", "create model", "alter field").
- **`migrate`** runs unapplied migration files against the database. It
  also records each one in the `django_migrations` table so it knows what
  has already been applied.

You edit models → makemigrations → migrate. That's the whole loop.

## What triggers a new migration?

| Change | Migration? |
|---|---|
| Add/remove a field, change its type, `null`, `default` | ✅ Yes |
| Add/change `related_name`, `verbose_name`, `help_text` | ✅ Yes (model-state change) |
| Add a `validator=[...]` to a field | ✅ Yes |
| Change `Meta.ordering`, `Meta.verbose_name`, constraints | ✅ Yes |
| Edit `__str__`, `save()`, or any **method** | ❌ No — methods aren't schema |
| Edit a comment / docstring | ❌ No |
| Rename a model or field | ✅ Yes (Django will ASK if it's a rename or remove+add) |

If `makemigrations` says **"No changes detected"** and you expected changes:
- You only edited methods, comments, or behavior — not the schema.
- Or the app isn't in `INSTALLED_APPS`.
- Or the `migrations/` folder is missing `__init__.py` (see "Common gotchas").

## Useful flags

```bash
python manage.py makemigrations --dry-run --verbosity 3   # preview only
python manage.py makemigrations core                       # one app
python manage.py migrate core 0003                         # roll forward/back to a specific migration
python manage.py migrate core zero                         # unapply ALL migrations for `core`
python manage.py showmigrations                            # list every migration and its applied state
python manage.py sqlmigrate core 0001                      # print the SQL a migration will run
```

`sqlmigrate` is great for understanding what's actually happening — Django
shows you the exact `CREATE TABLE` / `ALTER TABLE` it would run.

## Resetting migrations from scratch

Sometimes during learning you want to wipe everything and re-create the
DB and migrations cleanly. The recipe:

```bash
# 1. Delete the SQLite database
rm db.sqlite3

# 2. Delete every migration file BUT keep __init__.py
find core/migrations -type f ! -name '__init__.py' -delete

# 3. Wipe Python bytecode cache (so old .pyc migrations don't sneak back)
rm -rf core/migrations/__pycache__

# 4. Recreate from current models
python manage.py makemigrations
python manage.py migrate
```

Two easy-to-miss things:

1. **Keep `__init__.py`.** Empty file, but Django needs it. Without it,
   the app has no migrations module and `makemigrations` silently does
   nothing ("No changes detected" — confusing if you don't know why).
2. **Wipe `__pycache__`.** Compiled `.pyc` files of deleted migrations
   can confuse Django on the next run.

> ⚠️ This deletes data. Only do this during local learning. In a real
> project, you'd write a new migration to update the schema instead.

## Common gotchas

### "No changes detected"
- Migrations folder is missing `__init__.py` → Django doesn't see the
  migrations module. Touch `__init__.py` and re-run.
- App not in `INSTALLED_APPS`.
- You only edited methods/comments/behaviour, which don't change schema.

### "Cannot resolve keyword …"
That's a query error, not a migration error — typically a wrong field
name in `.filter()` / `.values()` / `.order_by()`.

### Pending migrations on `runserver`
If `runserver` warns "you have 3 unapplied migrations", just run
`python manage.py migrate`.

## Mental model

> `models.py` describes the schema you **want**.
> Migration files describe the **diff** Django needs to apply to get there.
> The `django_migrations` table tracks which diffs have already been applied
> to this database.

If those three things stay in sync, your DB matches your code. When they
drift (e.g. someone deletes the migrations folder, or rolls back the DB
manually), you fix it by either applying missing migrations or running
the "reset from scratch" recipe.

## Try it

```bash
# inspect the SQL of your first migration
python manage.py sqlmigrate core 0001

# see what's applied
python manage.py showmigrations

# preview without writing
python manage.py makemigrations --dry-run --verbosity 3
```
