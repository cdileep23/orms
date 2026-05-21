# 05 — CRUD: Create, Read, Update, Delete

CRUD = the four basic things you do with data. Everything in a backend is
some mix of these. Examples use my restaurant project and my `orm_script.py`.

## The big picture

| Letter | Operation | Main ORM tools | SQL it runs |
|--------|-----------|----------------|-------------|
| **C** | Create | `.create()`, `Model()` + `.save()` | `INSERT` |
| **R** | Read   | `.all()`, `.get()`, `.filter()`, `.first()` | `SELECT` |
| **U** | Update | `.save()` (again), `QuerySet.update()` | `UPDATE` |
| **D** | Delete | `.delete()` | `DELETE` |

Key thing to notice: **Create and Update use the SAME method — `.save()`.**
More on that below.

## C — CREATE

Two ways, both seen in my script:

```python
# Way 1: .create() -> builds AND saves in ONE step. Returns the object.
SaleModel.objects.create(restaurant=restaurant, datetime=timezone.now(), income=1000)

# Way 2: build in memory, then .save(). Two steps. Nothing hits the DB
# until .save() runs.
r = RestaurantModel()
r.name = "Burger King"
r.save()                      # <- the INSERT happens here
```

Both run an `INSERT`. Other create helpers:

- `get_or_create(...)` — create only if no matching row exists; returns
  `(object, created)`.
- `bulk_create([obj1, obj2, ...])` — insert many rows in one query (fast).

## R — READ

Reading never changes the database — it only runs `SELECT`.

| Call | Returns | If nothing matches |
|------|---------|--------------------|
| `.all()` | QuerySet of every row | empty QuerySet |
| `.filter(**kw)` | QuerySet of matching rows | empty QuerySet |
| `.exclude(**kw)` | QuerySet of non-matching rows | empty QuerySet |
| `.get(**kw)` | exactly ONE object | raises `DoesNotExist` |
| `.first()` / `.last()` | one object | `None` |
| `.count()` | an int | `0` |
| `.exists()` | a bool | `False` |
| `qs[0]` / `qs[:5]` | object / sliced QuerySet | `IndexError` for `[0]` |

`.get()` is strict — it expects **one** row:

```python
RestaurantModel.objects.get(id=1)     # exactly one -> the object
# 0 matches -> RestaurantModel.DoesNotExist
# 2+ matches -> RestaurantModel.MultipleObjectsReturned
```

Use `.get()` when you expect one specific row; use `.filter()` when you
expect a set (0, 1, or many).

## U — UPDATE

### Updating one object — fetch, change, save

```python
restaurant = RestaurantModel.objects.first()   # 1. fetch
restaurant.name = "New Restaurant 1"           # 2. change in memory
restaurant.save()                              # 3. save -> runs UPDATE
```

`.save()` is smart: if the object **already exists** (has a primary key
from the DB), it runs `UPDATE`, not `INSERT`. Same method, different SQL —
that is why Create and Update share `.save()`.

### `update_fields` — a narrower UPDATE

```python
restaurant.save(update_fields=['name'])
```

This writes **only** the `name` column instead of all of them. The SQL
becomes `UPDATE ... SET "name" = ...` — smaller and faster.

### Bulk update — `QuerySet.update()`

To change **many rows at once**, call `.update()` on a QuerySet:

```python
RestaurantModel.objects.filter(restaurant_type='IN').update(website='')
```

One `UPDATE` statement hits every matching row. Very fast.

### ⚠️ Instance `.save()` vs QuerySet `.update()`

| | `obj.save()` | `QuerySet.update()` |
|--|--------------|---------------------|
| Rows affected | one | many |
| Runs my overridden `save()`? | ✅ yes | ❌ no |
| Runs validators / `full_clean`? | ❌ no (never auto) | ❌ no |
| Fires signals | ✅ yes | ❌ no |

Bulk `.update()` is fast but **skips my custom `save()` logic**. Know which
one you need.

## D — DELETE

### Deleting one object

```python
restaurant = RestaurantModel.objects.first()
restaurant.delete()                 # runs a DELETE for this row
```

### Bulk delete

```python
SaleModel.objects.all().delete()                  # delete every sale
RatingModel.objects.filter(rating=1).delete()     # delete a subset
```

### CASCADE — deletes can spread

My ForeignKeys use `on_delete=models.CASCADE`. So deleting a restaurant
**also deletes every RatingModel and SaleModel that points to it** — the
database removes the children so no row is left "pointing at nothing".

```python
RestaurantModel.objects.get(id=1).delete()
# -> also deletes that restaurant's ratings AND sales
```

(`on_delete` options: `CASCADE`, `PROTECT`, `SET_NULL`, `SET_DEFAULT`,
`DO_NOTHING` — covered with relationships in topic 07.)

Like bulk update, `QuerySet.delete()` does **not** call a custom
`delete()` method you wrote on the model.

## Overriding `save()` and `delete()`

This is how Update and Delete connect to custom code.

`models.Model` already provides `save()` and `delete()`. Defining your own
**overrides** them — yours runs instead.

### Why override `save()`?

`.save()` is the one chokepoint **every write** (create *and* update)
passes through. Override it to run logic automatically on every save:
auto-fill a field, normalise data, log, force `full_clean()`, etc.

```python
class RestaurantModel(models.Model):
    ...
    def save(self, *args, **kwargs):
        print(self._state)                 # my custom logic
        super().save(*args, **kwargs)      # MUST call the real save
```

### `save()` covers BOTH create and update

There is no separate `create()`/`update()` method to override — just
`save()`. To tell which one is happening, check inside:

```python
def save(self, *args, **kwargs):
    if self._state.adding:        # True  -> not in DB yet  -> INSERT (create)
        print("creating")
    else:                         # False -> already in DB  -> UPDATE
        print("updating")
    super().save(*args, **kwargs)
```

(`self.pk is None` works as a check too.)

### Overriding `delete()`

Same idea, its own method:

```python
def delete(self, *args, **kwargs):
    print("about to delete", self)
    super().delete(*args, **kwargs)
```

Classic use: **soft delete** — set an `is_deleted = True` flag instead of
really removing the row, so data stays recoverable.

### ⚠️ The rule you must never break

Always call `super().save(...)` / `super().delete(...)` inside the
override. Forget it and your method *replaces* Django's — the override
runs but **nothing happens in the database**.

(Reminder: `super()` WITH parentheses. `super.save()` fails with
`AttributeError: type object 'super' has no attribute 'save'`.)

## Bonus: QuerySets are lazy

A read like `RestaurantModel.objects.filter(...)` does **not** hit the DB
right away. The `SELECT` runs only when you actually *use* the result —
loop over it, `print()` it, index it, call `list()`. This lets Django
chain `.filter().exclude().order_by()` into ONE efficient query.

## What I should remember

1. CRUD = Create, Read, Update, Delete — the four data operations.
2. **Create and Update share `.save()`** — new object → INSERT, existing → UPDATE.
3. `.get()` expects exactly one row (errors otherwise); `.filter()` returns a set.
4. `save(update_fields=[...])` writes only some columns.
5. `QuerySet.update()` / `.delete()` are bulk + fast, but **skip** overridden `save()`/`delete()`, validators, and (for update) signals.
6. `on_delete=CASCADE` means deleting a parent deletes its children.
7. Override `save()`/`delete()` for custom write logic — and ALWAYS call `super()`.

## Official docs

- Creating / saving objects: https://docs.djangoproject.com/en/stable/ref/models/instances/#saving-objects
- Making queries (full CRUD walkthrough): https://docs.djangoproject.com/en/stable/topics/db/queries/
- QuerySet API (`.filter`, `.update`, `.delete`, ...): https://docs.djangoproject.com/en/stable/ref/models/querysets/
- Overriding model methods: https://docs.djangoproject.com/en/stable/topics/db/models/#overriding-model-methods

Next: [06 — Filtering & field lookups](06-filtering.md)
