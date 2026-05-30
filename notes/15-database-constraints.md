# 15 — Database Constraints (`CheckConstraint`, `UniqueConstraint`)

Validators (note 03) run in Python during `full_clean()`. **Constraints** run
in the **database itself** — they're enforced no matter how the row is
written (admin, shell, raw SQL, another app), and they can't be bypassed.

You declare them in a model's `Meta.constraints` list.

| Constraint | Enforces |
|---|---|
| `CheckConstraint` | a row must satisfy a condition (e.g. `1 <= rating <= 5`) |
| `UniqueConstraint` | a column (or combination) must be unique across rows |

Both live in `django.db.models`.

---

## 1. `CheckConstraint` — value rules

```python
from django.db import models
from django.db.models import Q

class RatingModel(models.Model):
    rating = models.PositiveSmallIntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(
                name='rating_range',
                condition=Q(rating__range=(1, 5)),
                violation_error_message='Rating should be between 1 and 5',
            )
        ]
```

- **`name`** — required, must be unique per database. Used in the migration
  and in the error if violated.
- **`condition`** — a `Q()` expression the row must satisfy.
- **`violation_error_message`** — optional custom message shown when
  `full_clean()` catches the violation.

### ⚠️ Django 5.1+ renamed `check` → `condition`

Older tutorials use `check=Q(...)`. In Django 5.1 that argument was renamed:

```python
models.CheckConstraint(check=Q(rating__range=(1,5)))       # OLD — deprecated, removed in 6.0
models.CheckConstraint(condition=Q(rating__range=(1,5)))   # NEW — use this
```

If you see `TypeError: CheckConstraint.__init__() got an unexpected keyword
argument 'check'`, this rename is why.

### ⚠️ `message=` is NOT a valid argument

`CheckConstraint` never accepted `message`. For a custom message use
**`violation_error_message`**:

```python
models.CheckConstraint(
    name='lat_range',
    condition=Q(latitude__range=(-90, 90)),
    violation_error_message="Latitude should be between -90 and 90",   # correct
)
```

### Real examples from this project (RestaurantModel)

```python
class Meta:
    constraints = [
        models.CheckConstraint(
            name='latitude_range',
            condition=Q(latitude__range=(-90, 90)),
            violation_error_message="Latitude should be between -90 and 90",
        ),
        models.CheckConstraint(
            name='longitude_range',
            condition=Q(longitude__range=(-180, 180)),
            violation_error_message="Longitude should be between -180 and 180",
        ),
    ]
```

---

## 2. `UniqueConstraint` — uniqueness rules

### Single / multi-column uniqueness with `fields`

"a user can rate a given restaurant only once":

```python
class Meta:
    constraints = [
        models.UniqueConstraint(
            fields=['user', 'restaurant'],
            name='unique_rating_per_user_per_restaurant',
        )
    ]
```

This is the modern replacement for the old `unique_together = [...]`.

### Expression uniqueness (case-insensitive, etc.)

Pass an **expression** (positionally, not via `fields`) to make uniqueness
case-insensitive — so `"Taco Bell"` and `"taco bell"` collide:

```python
from django.db.models.functions import Lower

class Meta:
    constraints = [
        models.UniqueConstraint(
            Lower('name'),
            name='check_name_unique_constraints',
        )
    ]
```

---

## 3. `field(unique=True)` vs `UniqueConstraint` — and a trap

Putting `unique=True` on a field is the quick way to make ONE column unique:

```python
name = models.CharField(max_length=100, unique=True)
```

**Trap I hit:** I added `unique=True` to `restaurant_type`:

```python
restaurant_type = models.CharField(..., unique=True)   # WRONG
```

That means only **one** restaurant of each type can exist in the whole table
— one Indian, one Chinese, ever. The migration then failed with:

```
IntegrityError: UNIQUE constraint failed: core_restaurantmodel.restaurant_type
```

…because the existing data already had 5 Italian, 3 Chinese, etc. **Lesson:
`unique=True` belongs on identity-like fields (email, slug, username), not on
category/type fields that are meant to repeat.** Removing it fixed the
migration.

Rule of thumb:
- One field, simple → `unique=True` on the field.
- Multiple fields together, or an expression (`Lower`), or a custom name/
  condition → `UniqueConstraint` in `Meta`.

---

## 4. Constraints run in the DB → migrations can FAIL on bad data

Because constraints are enforced by the database, adding one runs against
**existing rows** at `migrate` time. If any row violates it, `migrate` aborts
with an `IntegrityError` and rolls back.

Before adding a unique constraint, check for offenders first:

```python
from django.db.models import Count

# duplicate (user, restaurant) pairs that would break the unique rating rule
RatingModel.objects.values('user', 'restaurant') \
    .annotate(n=Count('id')).filter(n__gt=1)
```

Clean up duplicates (or fix out-of-range values for a CheckConstraint) before
running `migrate`.

---

## 5. Validators vs Constraints — use both

| | Validators (note 03) | Constraints (this note) |
|---|---|---|
| Runs where | Python, in `full_clean()` | Database engine |
| Bypassable? | Yes — `.save()` skips them | No — always enforced |
| Good for | friendly form errors | data integrity guarantee |
| SQLite support | n/a (Python) | CheckConstraint works; some DBs vary |

They complement each other: validators give nice messages in forms;
constraints are the hard backstop so bad data can never land, even from a
shell or another service.

---

## 6. Workflow when adding a constraint

```bash
# 1. add the constraint to Meta.constraints
# 2. create the migration
python manage.py makemigrations
# 3. apply it — fails here if existing rows violate it
python manage.py migrate
# 4. if it fails: find & fix the offending rows, then migrate again
```

---

## 7. Cheat sheet

```python
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

class Meta:
    constraints = [
        # value rule
        models.CheckConstraint(
            name='rating_range',
            condition=Q(rating__range=(1, 5)),               # 5.1+: condition, NOT check
            violation_error_message='Rating must be 1-5',    # NOT message=
        ),
        # multi-column uniqueness
        models.UniqueConstraint(
            fields=['user', 'restaurant'],
            name='unique_rating_per_user_per_restaurant',
        ),
        # case-insensitive uniqueness
        models.UniqueConstraint(
            Lower('name'),
            name='unique_name_ci',
        ),
    ]
```

---

## Mental model

- **Validator** = polite bouncer who checks IDs at the form door (skippable).
- **Constraint** = the locked vault door in the database (never skippable).
- `CheckConstraint` guards **values**; `UniqueConstraint` guards
  **uniqueness**.
- Adding one runs against existing data — clean the data first or the
  migration fails.
