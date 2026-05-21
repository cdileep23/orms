# 02 — Models and Fields

This is where I am right now. Everything here uses my own `core/models.py`.

## What a model is

A **model** is a Python class that inherits from `django.db.models.Model`.
Each model becomes one database table.

```python
from django.db import models

class RestaurantModel(models.Model):
    name = models.CharField(max_length=100)
    ...
```

- `models.Model` is the base class — it gives me `.objects`, `.save()`,
  `.delete()`, etc. for free.
- The table name Django generates is `appname_modelname` in lowercase,
  e.g. `core_restaurantmodel`.

## A field = a column

Every class attribute set to a `models.SomethingField(...)` becomes a
**column** in the table. The **field type** decides what kind of data the
column holds and how Django validates it.

### Field types I'm using

| Field | What it stores | In my project |
|-------|----------------|---------------|
| `CharField` | Short text (needs `max_length`) | `name`, `restaurant_type` |
| `URLField` | A URL (a CharField that validates URLs) | `website` |
| `DateField` | A date (no time) | `date_opened` |
| `DateTimeField` | A date **and** time | `SaleModel.datetime` |
| `FloatField` | A floating-point number | `latitude`, `longitude` |
| `DecimalField` | Exact decimal — use for money | `SaleModel.income` |
| `PositiveSmallIntegerField` | A small non-negative integer | `RatingModel.rating` |
| `ForeignKey` | A link to another table's row | `restaurant`, `user` |

### Why `DecimalField` for money, not `FloatField`?

`FloatField` is approximate — `0.1 + 0.2` is famously not `0.3` in floating
point. Money must be exact, so `income` uses `DecimalField`:

```python
income = models.DecimalField(max_digits=8, decimal_places=2)
```

- `decimal_places=2` → two digits after the point (cents).
- `max_digits=8` → 8 digits total, so the biggest value is `999999.99`.

## Field options (the keyword arguments)

Options tune how a column behaves. The ones in my models:

| Option | Meaning |
|--------|---------|
| `max_length=100` | Max characters (required on `CharField`). |
| `default=''` | Value used when none is given. `website` defaults to empty. |
| `null=True` | The **database** column may be empty (`NULL`). On `SaleModel.restaurant`. |
| `choices=...` | Restricts the value to a fixed set (see below). |
| `on_delete=models.CASCADE` | What to do when the linked row is deleted (topic 06). |

### `null` vs `blank` (common beginner trap)

- `null=True` — about the **database**: the column can store `NULL`.
- `blank=True` — about **forms/validation**: the field can be left empty.
- They are independent. For text fields Django convention is to use
  `blank=True` and *not* `null=True` (empty string instead of `NULL`).

## The hidden primary key

I never declared an `id`, but every model has one. Django auto-adds:

```python
id = models.BigAutoField(primary_key=True)  # added for me
```

It's a unique, auto-incrementing number for each row. That's how the ORM
tells rows apart. I can read `restaurant.id` after saving.

## Choices — a fixed set of values

`RestaurantModel` uses `TextChoices` to limit `restaurant_type`:

```python
class TypeChoices(models.TextChoices):
    INDIAN  = 'IN', 'Indian'
    CHINESE = 'CH', 'Chinese'
    ...

restaurant_type = models.CharField(
    max_length=2,
    choices=TypeChoices.choices,
    default=TypeChoices.INDIAN,
)
```

- Each line is `NAME = stored_value, human_label`.
- `'IN'` is what's saved in the database (compact).
- `'Indian'` is what's shown to people (in the admin, forms).
- Django gives a free helper: `restaurant.get_restaurant_type_display()`
  returns `'Indian'` instead of `'IN'`.

## The `__str__` method

```python
def __str__(self):
    return self.name
```

`__str__` controls how an object looks when printed — in the shell, in the
admin list. Without it I'd see `RestaurantModel object (1)`, which is
useless. Always add one.

> ⚠️ Bug in my current code: `SaleModel.__str__` returns
> `f"Sale {self.sale}"` but there is no `sale` field. It should be a real
> field like `self.income` or `self.id`, or it crashes when displayed.

## Each model is its own table — recap of my 3 models

- `RestaurantModel` → table of restaurants.
- `RatingModel` → table of ratings; each row links to a `User` and a
  restaurant (topic 06 covers these links).
- `SaleModel` → table of sales; each row links to a restaurant.

## Try it (Django shell)

```bash
python manage.py shell
```

```python
from core.models import RestaurantModel
# inspect the table's columns the ORM knows about
for f in RestaurantModel._meta.get_fields():
    print(f.name, "->", f.get_internal_type())
```

## What I should remember

1. Model class → table. Field → column. Instance → row.
2. Pick the field type by the *kind* of data (money = `DecimalField`).
3. `null` is database-level; `blank` is form-level. Not the same.
4. An `id` primary key is created automatically.
5. `choices` stores a short code but shows a friendly label.
6. Always write `__str__`.

Next: [03 — Validation](03-validation.md)
