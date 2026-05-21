# 03 — Validation

How Django checks that data is acceptable **before** it goes into the
database. Examples use my own models (`RatingModel`, `RestaurantModel`).

## The big idea

A field type says *what kind* of data a column holds. **Validation** says
*which values are allowed*. My `rating` column is an integer — but a rating
of `9` or `-3` makes no sense. Validation is the rule "rating must be 1–5".

## ⚠️ The #1 gotcha — `.save()` does NOT validate

This is the most important thing on this page.

```python
rating = RatingModel(user=user, restaurant=restaurant, rating=9)
rating.save()          # ← NO error. Row with rating=9 goes into the DB.
```

`.save()` writes straight to the database and **ignores every validator**.
It does *not* raise an error for bad data. Validation is a **separate,
explicit step** — you have to ask for it:

```python
rating = RatingModel(user=user, restaurant=restaurant, rating=9)
rating.full_clean()    # ← raises ValidationError: rating must be <= 5
rating.save()          # ← only reached if full_clean() passed
```

**Correct order: `full_clean()` first, then `save()`.**

### Why doesn't `.save()` validate automatically?

By design. `.save()` is meant to be a fast, direct DB write — nothing more.
Validation is the job of `full_clean()`. In normal Django web code you
rarely call it yourself because **ModelForms and DRF serializers call
`full_clean()` for you** — that's why web forms reject bad input. A plain
script (like `orm_script.py`) has no form, so *I* must call it.

## Where validators live — the `validators=[...]` option

A validator is attached to a field via the `validators` keyword argument.
From my `core/models.py`:

```python
from django.core.validators import MinValueValidator, MaxValueValidator

rating = models.PositiveSmallIntegerField(
    validators=[MinValueValidator(1), MaxValueValidator(5)]
)
latitude  = models.FloatField(validators=[MinValueValidator(-90),  MaxValueValidator(90)])
longitude = models.FloatField(validators=[MinValueValidator(-180), MaxValueValidator(180)])
```

A validator is just a callable that receives the value and raises
`ValidationError` if it's bad. The list can hold as many as I want.

Docs: https://docs.djangoproject.com/en/stable/ref/models/fields/#validators

## Built-in validators

Django ships these in `django.core.validators`:

| Validator | Checks |
|-----------|--------|
| `MinValueValidator(n)` | value ≥ n |
| `MaxValueValidator(n)` | value ≤ n |
| `MinLengthValidator(n)` | text length ≥ n |
| `MaxLengthValidator(n)` | text length ≤ n |
| `RegexValidator(regex)` | value matches a regular expression |
| `EmailValidator` | value is a valid email |
| `URLValidator` | value is a valid URL |
| `validate_slug` | value is a valid slug (letters, numbers, `-`, `_`) |

Docs: https://docs.djangoproject.com/en/stable/ref/validators/

## The validation methods

Called on a model **instance**:

| Method | What it does |
|--------|--------------|
| `full_clean()` | Runs the whole validation suite (the one I normally call). |
| `clean_fields()` | Validates each field: field rules + the `validators=[...]` list. |
| `clean()` | My own model-wide / cross-field checks (I override this). |
| `validate_unique()` | Checks `unique=True` / `unique_together` rules. |
| `validate_constraints()` | Checks `Meta.constraints`. |

`full_clean()` calls the other four for me. So I almost always just call
`full_clean()`.

Docs: https://docs.djangoproject.com/en/stable/ref/models/instances/#validating-objects

## What `full_clean()` runs, in order

1. `clean_fields()` — every field's type rules (`max_length`, `choices`,
   `null`…) **and** its `validators=[...]` list.
2. `clean()` — my custom cross-field logic (does nothing unless I override it).
3. `validate_unique()` — uniqueness rules.
4. `validate_constraints()` — `Meta.constraints`.

If any step finds problems, it collects them and raises **one**
`ValidationError` at the end.

## `ValidationError` — the shape of the error

When validation fails I get a `ValidationError` whose data is a **dict**:

```python
{'rating': ['Ensure this value is less than or equal to 5.']}
#  field      list of human-readable messages for that field
```

`{field_name: [messages]}`. That structure is exactly what forms use to
show each error next to the right input box.

To handle it gracefully instead of crashing:

```python
from django.core.exceptions import ValidationError

try:
    rating.full_clean()
    rating.save()
except ValidationError as e:
    print(e.message_dict)   # {'rating': ['Ensure this value ...']}
```

## Custom validation

### A custom validator function

A validator is any function that raises `ValidationError` on bad input:

```python
from django.core.exceptions import ValidationError

def validate_positive_income(value):
    if value <= 0:
        raise ValidationError(f"Income must be positive, got {value}.")

# use it like any built-in validator:
income = models.DecimalField(
    max_digits=8, decimal_places=2,
    validators=[validate_positive_income],
)
```

### Overriding `clean()` for cross-field rules

`validators=[...]` only sees **one field's** value. When a rule depends on
the **whole object** (or several fields together), override `clean()`:

```python
from django.core.exceptions import ValidationError
from django.utils import timezone

class RestaurantModel(models.Model):
    ...
    def clean(self):
        if self.date_opened and self.date_opened > timezone.now().date():
            raise ValidationError("date_opened cannot be in the future.")
```

`clean()` runs as part of `full_clean()` — so it only fires when I call
`full_clean()`, same rule as everything else.

Docs: https://docs.djangoproject.com/en/stable/ref/models/instances/#django.db.models.Model.clean

## Three layers of data rules (important!)

There isn't one "validation" — there are three layers, enforced at
different times:

| Layer | Examples | Enforced by | When it fires | Error |
|-------|----------|-------------|---------------|-------|
| **Field rules** | `max_length`, `choices`, `blank` | `clean_fields()` | only on `full_clean()` | `ValidationError` |
| **Validators** | `MinValueValidator`, custom funcs | `clean_fields()` | only on `full_clean()` | `ValidationError` |
| **DB constraints** | `null=False`→`NOT NULL`, `unique=True`→`UNIQUE` | the **database** | always, even on plain `.save()` | `IntegrityError` |

Key takeaway:
- **Validators are Python-level.** They run *only* when I call
  `full_clean()`. The database knows nothing about them — it would happily
  store `rating=9`.
- **DB constraints are database-level.** They're always enforced. A
  `.save()` that violates `NOT NULL` or `UNIQUE` raises `IntegrityError`
  even if I never call `full_clean()`.

So `MinValueValidator(1)`/`MaxValueValidator(5)` on `rating` give me **no**
database guarantee. If I want the database *itself* to reject a rating of
9, I need a real DB constraint via `Meta.constraints`:

```python
from django.db.models import CheckConstraint, Q

class RatingModel(models.Model):
    ...
    class Meta:
        constraints = [
            CheckConstraint(check=Q(rating__gte=1) & Q(rating__lte=5),
                            name='rating_between_1_and_5'),
        ]
```

That adds a SQL `CHECK` constraint — enforced on every write, no
`full_clean()` required. (Advanced; revisit later.)

Docs: https://docs.djangoproject.com/en/stable/ref/models/constraints/

## The practical pattern

```python
from django.core.exceptions import ValidationError

obj = RatingModel(user=user, restaurant=restaurant, rating=4)
try:
    obj.full_clean()     # 1. validate
    obj.save()           # 2. save only if valid
except ValidationError as e:
    print("Invalid:", e.message_dict)
```

In web code I usually don't write this — a ModelForm or DRF serializer
does it for me. In scripts and the shell, I do.

## Try it (Django shell)

```bash
python manage.py shell
```

```python
from core.models import RatingModel
from django.contrib.auth.models import User
from core.models import RestaurantModel

r = RatingModel(user=User.objects.first(),
                restaurant=RestaurantModel.objects.first(),
                rating=99)
r.full_clean()   # watch it raise ValidationError
```

## What I should remember

1. `.save()` **never validates** — it writes straight to the DB.
2. `full_clean()` is what runs validation. Call it **before** `save()`.
3. Validators go in the field's `validators=[...]` list.
4. `ValidationError` carries a `{field: [messages]}` dict (`.message_dict`).
5. Override `clean()` for rules that span multiple fields.
6. Validators = Python-level (need `full_clean()`).
   DB constraints = database-level (always enforced, raise `IntegrityError`).
7. ModelForms / DRF serializers call `full_clean()` for me — scripts don't.

## Official docs — bookmark these

- Validators reference: https://docs.djangoproject.com/en/stable/ref/validators/
- Validating objects (`full_clean`, `clean`): https://docs.djangoproject.com/en/stable/ref/models/instances/#validating-objects
- `validators` field option: https://docs.djangoproject.com/en/stable/ref/models/fields/#validators
- Model constraints: https://docs.djangoproject.com/en/stable/ref/models/constraints/
- Form & field validation (how it's normally triggered): https://docs.djangoproject.com/en/stable/ref/forms/validation/

Next: [04 — Migrations](04-migrations.md)
