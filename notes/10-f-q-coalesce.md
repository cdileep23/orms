# 10 — `F()`, `Q()`, `Coalesce()`

Three small helpers, one big idea: **push work into the database** instead of
pulling rows into Python, mutating them, and writing them back.

| Helper | Lives in | Used for |
|---|---|---|
| `F('field')` | `django.db.models` | Reference a column's current DB value inside a query |
| `Q(...)` | `django.db.models` | Combine filter conditions with `OR`, `NOT`, grouped `AND/OR` |
| `Coalesce(a, b)` | `django.db.models.functions` | Replace `NULL` with a fallback |

Examples use my restaurant project: `RestaurantModel`, `RatingModel`
(FK to restaurant via `related_name='ratings'`) and `SaleModel`
(FK to restaurant via `related_name='sales'`, has `income` and `expenditure`).

---

## 1. `F()` — reference a column inside a query

`F('income')` means *"the current value of the income column, in the database"*.
Whatever you build with it (`F('income') * 2`, `F('income') - F('expenditure')`)
gets translated to SQL and runs **inside the DB**.

### Why not just do it in Python?

```python
rating = RatingModel.objects.get(pk=1)
rating.rating += 1          # <- BAD
rating.save()
```

That code does **three** things:

1. `SELECT rating FROM ratingmodel WHERE id = 1` → into Python (`rating = 3`)
2. Python adds 1 → `4`
3. `UPDATE ratingmodel SET rating = 4 WHERE id = 1`

Between step 1 and step 3, another request can change the row. Your write
silently overwrites it. This is the classic **race condition**.

With `F()`:

```python
rating.rating = F('rating') + 1
rating.save()
# → UPDATE ratingmodel SET rating = rating + 1 WHERE id = 1;
```

One atomic SQL statement. No race. No round-trip to read the old value.

### The three places you use `F()`

**a. In `.update()` — bulk math across rows**
```python
SaleModel.objects.update(expenditure=F('income') * 0.5)
# every row's expenditure becomes half of its own income, in one query
```

**b. In `.filter()` — compare two columns**
```python
SaleModel.objects.filter(expenditure__gt=F('income'))
# rows where expenditure > income (a column-to-column comparison)
```
You can't write this with normal kwargs — `filter(expenditure__gt='income')`
would compare to the string `'income'`.

**c. In `.annotate()` — derived columns**
```python
SaleModel.objects.annotate(profit=F('income') - F('expenditure'))
# every row now has .profit, computed by the DB
```

### Gotcha: stale Python attribute after save

```python
rating.rating = F('rating') + 1
rating.save()
print(rating.rating)   # <- prints the F() expression object, NOT the number!
```
The DB has the new value; the Python attribute is still the unresolved
expression. To see the real value:
```python
rating.refresh_from_db()
print(rating.rating)   # now the actual number
```

### `F()` in `order_by` — controlling where `NULL`s land

```python
RestaurantModel.objects.order_by('capacity')        # ASC, plain string field
RestaurantModel.objects.order_by('-capacity')       # DESC, leading minus
```

For nullable columns, the position of `NULL` rows depends on the DB backend
(Postgres puts them last in ASC; SQLite/MySQL put them first). When that
matters — e.g. you don't want "no rating" restaurants at the top of a
"best rated" page — use `F()` and be explicit:

```python
RestaurantModel.objects.order_by(F('capacity').desc(nulls_last=True))
RestaurantModel.objects.order_by(F('capacity').asc(nulls_first=True))
```

The `F` form unlocks `.asc(...)` / `.desc(...)` with `nulls_first` /
`nulls_last`, which the bare string form doesn't support.

---

## 2. `Q()` — `OR`, `NOT`, and grouped conditions in filters

Normal keyword filters are **always combined with `AND`**:

```python
RatingModel.objects.filter(rating=5, user_id=1)
# WHERE rating = 5 AND user_id = 1
```

There is no way with kwargs alone to say *"rating = 5 **OR** user_id = 1"*.
That's what `Q` is for.

### The operators

| Operator | Meaning |
|---|---|
| `Q(a) \| Q(b)` | OR |
| `Q(a) & Q(b)` | AND (same as passing both as kwargs) |
| `~Q(a)` | NOT |

### Examples

**OR:**
```python
RatingModel.objects.filter(Q(rating=5) | Q(rating=1))
# WHERE rating = 5 OR rating = 1
```

**NOT (same as `.exclude`):**
```python
RatingModel.objects.filter(~Q(rating=3))
# WHERE NOT (rating = 3)
```

**Grouped: `(A AND B) OR C`** — parentheses matter, just like SQL:
```python
SaleModel.objects.filter(
    (Q(income__gt=1000) & Q(expenditure__lt=500)) | Q(restaurant__name='Mario')
)
```

### Mixing `Q` with regular kwargs

`Q` objects come **first**, kwargs after. Everything is `AND`-ed together:

```python
RatingModel.objects.filter(Q(rating=5) | Q(rating=1), user_id=1)
# WHERE (rating = 5 OR rating = 1) AND user_id = 1
```

This is the most common real-world shape: *"rows for this user, where the
rating is one of these extreme values."*

### Store `Q` in a variable — compose readable filters

A `Q` is just a value. Name it, reuse it, combine it later:

```python
recently_opened     = Q(date_opened__gte=timezone.now() - timezone.timedelta(days=4))
not_recently_opened = ~Q(date_opened__gte=timezone.now() - timezone.timedelta(days=4))
it_or_mx            = Q(name__icontains='italian') | Q(name__icontains='mexican')

# "Italian/Mexican places, OR anything open for more than 4 days"
RestaurantModel.objects.filter(it_or_mx | not_recently_opened)
```

This is the readability win — instead of one giant chained expression, each
piece of business logic gets a name. Combine them with `|`, `&`, `~` later.

### `Q` can walk relationships (FK traversal)

The `__` double-underscore works inside `Q` just like in `.filter()`. You can
filter on a related model's column:

```python
# Sales whose RESTAURANT's name contains a digit
Q(restaurant__name__regex=r'[0-9]+')
```

Used in a queryset:
```python
name_has_num = Q(restaurant__name__regex=r'[0-9]+')
is_profit    = Q(income__gt=F('expenditure'))
SaleModel.objects.filter(name_has_num | is_profit)
```

Because the filter crosses the FK (`restaurant__name`), Django **automatically
adds a JOIN** to `core_restaurantmodel` — you don't need `select_related` to
make the filter work. (`select_related` is only for *accessing* `.restaurant`
afterward in Python without extra queries — see notes file 09.)

### Useful field lookups that pair well with `Q`

Lookups are the `__something` suffixes. The case-insensitive ones (`i` prefix)
are usually what you want for user-typed search:

| Lookup | SQL | Use case |
|---|---|---|
| `__exact` | `=` | exact match (default if no `__`) |
| `__iexact` | case-insensitive `=` | "matches regardless of case" |
| `__contains` / `__icontains` | `LIKE '%x%'` | substring search |
| `__startswith` / `__istartswith` | `LIKE 'x%'` | prefix search |
| `__endswith` / `__iendswith` | `LIKE '%x'` | suffix search |
| `__in` | `IN (...)` | "is one of these values" |
| `__gt` / `__gte` / `__lt` / `__lte` | `>`, `>=`, `<`, `<=` | comparisons |
| `__range` | `BETWEEN a AND b` | inclusive range |
| `__regex` / `__iregex` | regex match | when LIKE isn't enough |
| `__isnull` | `IS NULL` / `IS NOT NULL` | `__isnull=True/False` |
| `__date`, `__year`, `__month`, `__week_day` | DB date funcs | date-part filtering |

All of these work inside `Q(...)`:
```python
Q(name__icontains='pizza') | Q(restaurant_type__in=['IT', 'MX'])
```

### `Q` + `F` — combine them

```python
SaleModel.objects.filter(
    Q(income__gt=F('expenditure') * 2) | Q(income=0)
)
# either income is more than double expenditure, OR income is exactly zero
```

### `Q` inside `Count` / `Sum` for conditional aggregates

This is where `Q` really shines:

```python
SaleModel.objects.aggregate(
    profit_rows=Count('id', filter=Q(income__gt=F('expenditure'))),
    loss_rows  =Count('id', filter=Q(income__lt=F('expenditure'))),
)
# → {'profit_rows': 12, 'loss_rows': 4}
```
Two conditional counts, **one query**. No Python looping.

---

## 3. `Coalesce()` — replace `NULL` with a fallback

`Coalesce(a, b, c, ...)` returns the **first non-NULL** value. Direct
translation of SQL's `COALESCE()`.

```python
from django.db.models.functions import Coalesce
```

### Argument order — preferred first, safe fallback last

> **Mental rule:** put the *preferred / optional* value first, the
> *guaranteed-not-NULL* value last.

It should read as: *"use **this** if you have it, otherwise **this**, otherwise **this**…"*

```python
Coalesce(F('nickname'), F('name'))         # nickname if set, else real name
Coalesce(Sum('income'), 0)                 # sum if any rows, else 0
Coalesce(F('updated_at'), F('created_at')) # "last touched" timestamp
Coalesce(F('preferred_email'), F('email'), Value(''))   # chain of fallbacks
```

If you reverse the order, the fallback never fires. In our model `name` is
non-nullable, so `Coalesce(F('name'), F('nickname'))` **always picks name**
— the nickname branch is dead code.

### Why you need it: `NULL` is contagious

Two places this bites you constantly:

**a. `Sum` on an empty queryset returns `None`, not `0`:**
```python
SaleModel.objects.filter(restaurant_id=999).aggregate(t=Sum('income'))
# → {'t': None}                         <- not 0!
```
Then `total + 10` blows up with `TypeError: unsupported operand type(s) for +: 'NoneType' and 'int'`.

Fix:
```python
SaleModel.objects.filter(restaurant_id=999).aggregate(
    t=Coalesce(Sum('income'), 0)
)
# → {'t': 0}                           <- safe
```

**b. Nullable columns in arithmetic:**
```python
# expenditure is nullable in our SaleModel
SaleModel.objects.annotate(profit=F('income') - F('expenditure'))
# rows where expenditure IS NULL → profit is NULL (not income!)
```
Because in SQL, `5 - NULL = NULL`. One `NULL` poisons the whole expression.

Fix:
```python
SaleModel.objects.annotate(
    profit=F('income') - Coalesce(F('expenditure'), 0)
)
# treat NULL expenditure as 0 for the math
```

### Coalesce with multiple fallbacks

```python
Coalesce('nickname', 'first_name', Value('Anonymous'))
# first non-NULL of: nickname, first_name, the string 'Anonymous'
```
Wrap raw literals in `Value(...)` so Django knows it's a constant, not a
column name.

### `output_field` when types are mixed

If Django can't infer the result type (e.g. mixing a Decimal column with an
integer literal), pass `output_field`:
```python
from django.db.models import DecimalField
Coalesce(Sum('income'), 0, output_field=DecimalField())
```

---

## Putting all three together

A realistic "restaurant scoreboard" query:

```python
RestaurantModel.objects.annotate(
    total_income     = Coalesce(Sum('sales__income'), 0),
    total_expenditure= Coalesce(Sum('sales__expenditure'), 0),
    profit           = F('total_income') - F('total_expenditure'),
).filter(
    Q(profit__gt=0) | Q(total_income__gte=10000)
).values('name', 'total_income', 'total_expenditure', 'profit')
```

- `Coalesce` keeps restaurants with no sales from getting `NULL` totals.
- `F` does the subtraction in SQL.
- `Q` expresses the "profitable OR high-revenue" OR condition.

One query. Zero Python loops.

---

## Try it (Django shell)

```bash
python manage.py shell
```

```python
from django.db.models import F, Q, Sum, Count
from django.db.models.functions import Coalesce
from core.models import RestaurantModel, RatingModel, SaleModel

# 1. F: increment every rating by 1, atomically
RatingModel.objects.update(rating=F('rating') + 1)

# 2. Q: ratings that are extreme (1 or 5) AND belong to user 1
RatingModel.objects.filter(Q(rating=1) | Q(rating=5), user_id=1)

# 3. Coalesce: total income per restaurant, 0 if no sales
RestaurantModel.objects.annotate(
    total=Coalesce(Sum('sales__income'), 0)
).values('name', 'total')
```

---

## Common gotchas

- **`F()` value is not refreshed after `.save()`** → call `.refresh_from_db()`.
- **`Q` objects must come BEFORE kwargs** in `.filter(...)`.
- **`Sum`/`Avg` of an empty queryset returns `None`** → wrap in `Coalesce(..., 0)`.
- **`NULL` in arithmetic gives `NULL`** → `Coalesce(F('field'), 0)` before doing math.
- **String literals in `Coalesce`** need `Value('...')`, otherwise Django thinks
  it's a column name.
- **`~Q(x)` is not exactly the same as `.exclude(x)`** when nulls are involved —
  SQL's three-valued logic treats `NOT NULL` as unknown, not true. For most
  cases they match; for nullable columns, prefer `.exclude(...)`.
- **Annotated columns are invisible in `print(queryset)`** — `__str__` shows
  only normal fields. Use `.values('name', 'annotated_col')` or iterate and
  print `obj.annotated_col` explicitly.
- **Reversing Coalesce args silently breaks the fallback** — if the first arg
  is a non-nullable column, every other arg is dead code. Always: preferred
  first, safe fallback last.
- **`order_by(F(field).desc(nulls_last=True))`** — needed when NULL position
  matters; the bare string form (`'-field'`) gives backend-dependent ordering
  for NULLs.
