# 11 — `Subquery`, `OuterRef`, `Exists`

How to ask questions like:

- *"Each restaurant + the income of its most recent sale."*
- *"Restaurants that have at least one sale over 85."*
- *"Restaurants with NO sales in the last 5 days."*

These need an **inner query that depends on the outer row**. Plain `.filter()`
with JOINs can't do this cleanly — that's where `Subquery`, `Exists`, and
`OuterRef` come in.

| Helper | Lives in | Used for |
|---|---|---|
| `Subquery(qs)` | `django.db.models` | Embed an inner queryset as a **scalar value** in the outer query |
| `Exists(qs)` | `django.db.models` | Embed an inner queryset as a **boolean** (does any row exist?) |
| `OuterRef('field')` | `django.db.models` | Placeholder — *"plug in this field from the OUTER row here"* |

Examples use my restaurant project: `RestaurantModel`, `SaleModel`
(FK to restaurant, has `income`, `expenditure`, `datetime`).

---

## 1. The big idea — correlated vs uncorrelated subqueries

A **subquery** is a SELECT inside another SELECT. Two flavours:

### Uncorrelated — inner runs ONCE

```sql
SELECT * FROM restaurant
WHERE id IN (
    SELECT restaurant_id FROM sale WHERE income > 85
);
```

The inner query has no link to the outer. It produces a fixed list of ids,
the outer filters by membership. Django ORM:

```python
RestaurantModel.objects.filter(
    id__in=SaleModel.objects.filter(income__gt=85).values('restaurant')
)
```

### Correlated — inner runs PER OUTER ROW

```sql
SELECT * FROM restaurant
WHERE EXISTS (
    SELECT 1 FROM sale
    WHERE sale.restaurant_id = restaurant.id   -- ← outer reference
      AND sale.income > 85
);
```

The inner query references the outer row (`restaurant.id`). It is
re-evaluated for every outer row, plugging in that row's value each time.
Django ORM needs `OuterRef` for this:

```python
RestaurantModel.objects.filter(
    Exists(SaleModel.objects.filter(
        restaurant=OuterRef('pk'),
        income__gt=85,
    ))
)
```

**`OuterRef` is the piece that makes a subquery correlated.** Without it,
the inner query asks one global question; with it, the inner query asks
the same question per outer row.

---

## 2. `OuterRef` — the placeholder

`OuterRef('pk')` = *"the primary key of the current OUTER row"*.

It's a **placeholder**, not a runnable value. Resolved by Django at SQL
generation time, substituted into the inner query for each outer row.

A queryset that uses `OuterRef` **cannot run on its own**:

```python
sale = SaleModel.objects.filter(restaurant=OuterRef('pk'))
list(sale)
# ValueError: This queryset contains a reference to an outer query
#             and may only be used in a subquery.
```

It only becomes runnable when wrapped in `Subquery(...)` or `Exists(...)`
inside another queryset.

### Not just `'pk'`

`OuterRef` can reference any field of the outer query:

```python
OuterRef('pk')                  # outer row's primary key (most common)
OuterRef('restaurant_type')     # outer row's type column
OuterRef('opening_date')        # outer row's date column
```

---

## 3. `Exists` — "does any row exist?"

`Exists(qs)` wraps a queryset and returns a **boolean** in SQL:

- `TRUE` if the inner query finds at least one row
- `FALSE` otherwise

Maps to SQL `EXISTS (...)`. Short-circuits — the DB stops at the first match.

### Filter restaurants that have a sale > 85

```python
RestaurantModel.objects.filter(
    Exists(SaleModel.objects.filter(
        restaurant=OuterRef('pk'),
        income__gt=85,
    ))
)
```

SQL:

```sql
SELECT * FROM restaurant
WHERE EXISTS (
    SELECT 1 FROM sale
    WHERE sale.restaurant_id = restaurant.id
      AND sale.income > 85
);
```

### Negate with `~Exists` — "restaurants with NO recent sales"

```python
five_days_ago = timezone.now() - timezone.timedelta(days=5)

RestaurantModel.objects.filter(
    ~Exists(SaleModel.objects.filter(
        restaurant=OuterRef('pk'),
        datetime__gte=five_days_ago,
    ))
)
```

Reads as: `WHERE NOT EXISTS (...)`. Perfect for "find rows that **lack**
a related thing" — users with no orders, restaurants with no ratings, etc.

### Common mistake — forgetting `OuterRef`

```python
# WRONG — no link to the outer row
RestaurantModel.objects.filter(
    Exists(SaleModel.objects.filter(income__gt=85))
)
```

The inner query runs once globally. It asks *"does any sale > 85 exist
**anywhere**?"*. Result: either ALL restaurants or NONE — not what you
want.

Mental check whenever you write `Exists(...)`:
> *"Does my inner query reference the outer row via `OuterRef`?"*
> If no → it's almost certainly a bug.

---

## 4. `Subquery` — "give me a VALUE per outer row"

`Exists` only answers yes/no. To pull an actual **value** out of the inner
query, use `Subquery`.

A `Subquery` used as a scalar must return:

- Exactly **one column** → use `.values('col')`
- At most **one row** → use `[:1]` (LIMIT 1)

### Each restaurant + income of its LATEST sale

```python
sale = (
    SaleModel.objects
        .filter(restaurant=OuterRef('pk'))
        .order_by('-datetime')                # newest first
)

restaurants = RestaurantModel.objects.annotate(
    last_sale_income=Subquery(sale.values('income')[:1]),
)
```

SQL:

```sql
SELECT
    restaurant.*,
    (
        SELECT sale.income
        FROM sale
        WHERE sale.restaurant_id = restaurant.id
        ORDER BY sale.datetime DESC
        LIMIT 1
    ) AS last_sale_income
FROM restaurant;
```

### Reuse the template for multiple annotations

The inner queryset is just a Python variable — reuse it for more
subqueries, then do math with `F`:

```python
restaurants = RestaurantModel.objects.annotate(
    last_sale_income=Subquery(sale.values('income')[:1]),
    last_sale_expenditure=Subquery(sale.values('expenditure')[:1]),
    profit=F('last_sale_income') - F('last_sale_expenditure'),
)
```

One template, three virtual columns, all computed in the DB.

---

## 5. `Exists` vs `Subquery` — when to pick which

Both are correlated-subquery wrappers, but they answer different questions.

| You want… | Use |
|---|---|
| A yes/no check ("does any related row exist?") | **`Exists`** |
| A yes/no check, negated ("does NO related row exist?") | **`~Exists`** |
| A value from the related table (income, date, name…) | **`Subquery`** |
| Math on related values (e.g. profit = income − expenditure) | **`Subquery`** + `F` |

You can't replace `Subquery` with `Exists` when you need a value — `Exists`
only returns booleans, and `F('x') - F('y')` needs numbers.

---

## 6. `__in=Subquery(...)` — the uncorrelated alternative

When the question is just *"is the outer row's id in some set?"*, you don't
need `OuterRef`. An uncorrelated `__in` subquery works:

```python
# Restaurants that have ANY sale over 85
RestaurantModel.objects.filter(
    id__in=SaleModel.objects.filter(income__gt=85).values('restaurant')
)
```

Equivalent in result to the `Exists` version above. Differences:

| | `Exists + OuterRef` | `id__in=Subquery(...)` |
|---|---|---|
| Correlation | Per outer row | Inner runs once |
| Short-circuits | Yes (DB stops at first match per row) | No (materializes id list) |
| Negation | `~Exists(...)` — clean | `exclude(id__in=...)` — clunkier |
| Reads as | "for each outer row, check…" | "is outer id in this list?" |

For simple membership filters, both are fine. `Exists` is usually
faster and easier to negate.

---

## 7. When `OuterRef` is mandatory

`OuterRef` becomes **non-negotiable** the moment your inner query needs
something specific from each outer row beyond just an id check. Examples:

### Inner query depends on multiple outer fields

> *"Sales whose income beats the average for that same restaurant type."*

The inner query's WHERE changes per outer row's `restaurant_type` — can't
flatten this into a single precomputed list.

### Inner query returns a per-row value

> *"Each restaurant + the date of its most recent sale."*

There's a different date per restaurant. `__in=` doesn't help — that's a
set test, not a value lookup.

### Inner query has complex per-row conditions

> *"Restaurants where the LATEST sale (specifically) was profitable."*

You need "latest" computed per restaurant. Different latest sale per
outer row → correlated subquery required.

---

## 8. Cheat sheet

```python
# 1. Boolean: "any related row exists?"
RestaurantModel.objects.filter(
    Exists(SaleModel.objects.filter(restaurant=OuterRef('pk'), income__gt=85))
)

# 2. Boolean negated: "no related row exists"
RestaurantModel.objects.filter(
    ~Exists(SaleModel.objects.filter(restaurant=OuterRef('pk')))
)

# 3. Scalar value: "give me one field from the related row"
sale = SaleModel.objects.filter(restaurant=OuterRef('pk')).order_by('-datetime')
RestaurantModel.objects.annotate(
    last_sale_income=Subquery(sale.values('income')[:1]),
)

# 4. Multiple scalars + math
RestaurantModel.objects.annotate(
    last_sale_income=Subquery(sale.values('income')[:1]),
    last_sale_expenditure=Subquery(sale.values('expenditure')[:1]),
    profit=F('last_sale_income') - F('last_sale_expenditure'),
)

# 5. Membership (uncorrelated, no OuterRef)
RestaurantModel.objects.filter(
    id__in=SaleModel.objects.filter(income__gt=85).values('restaurant')
)
```

---

## Try it

```bash
python manage.py shell
```

```python
from django.utils import timezone
from django.db.models import Subquery, OuterRef, Exists, F
from core.models import RestaurantModel, SaleModel

# Restaurants with at least one sale in the last 5 days
five_days_ago = timezone.now() - timezone.timedelta(days=5)
RestaurantModel.objects.filter(
    Exists(SaleModel.objects.filter(
        restaurant=OuterRef('pk'),
        datetime__gte=five_days_ago,
    ))
)

# Latest sale income per restaurant
sale = SaleModel.objects.filter(restaurant=OuterRef('pk')).order_by('-datetime')
RestaurantModel.objects.annotate(
    last_sale_income=Subquery(sale.values('income')[:1]),
).values('name', 'last_sale_income')
```

---

## Mental model — one line each

- **`OuterRef('field')`** → *"plug in this field of the CURRENT outer row here"*
- **`Exists(qs)`** → *"does any inner row exist?"* (boolean)
- **`Subquery(qs.values('col')[:1])`** → *"give me this value from one inner row"* (scalar)
- **Correlated** = inner query references outer row → re-runs per outer row
- **Uncorrelated** = inner query has no outer reference → runs once globally
