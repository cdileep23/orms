# 08 — Aggregation & Annotation

Two different verbs in the ORM, two different result shapes.

> **`.aggregate()`** collapses the whole queryset into **one summary dict**.
> **`.annotate()`** adds a **computed column to each row** and gives back a queryset.

## The two-line answer

```
.aggregate()                       .annotate()

  Row 1                              Row 1 → adds new column
  Row 2                              Row 2 → adds new column
  Row 3   →  {single dict}           Row 3 → adds new column
  ...                                ...
  Row N                              Row N → adds new column
```

`aggregate` = **vertical** collapse (whole table to one summary).
`annotate` = **horizontal** addition (each row gets extra info).

## Aggregates available

All live in `django.db.models`:

| Class | SQL function |
|---|---|
| `Count` | `COUNT(...)` |
| `Sum`   | `SUM(...)` |
| `Avg`   | `AVG(...)` |
| `Min`   | `MIN(...)` |
| `Max`   | `MAX(...)` |
| `StdDev`| `STDDEV(...)` |
| `Variance` | `VARIANCE(...)` |

Don't confuse with `django.db.models.functions` — that's where things
like `Upper`, `Lower`, `Length`, `Concat` live. Aggregates are top-level.

## `.aggregate()` — collapse to one summary

```python
RestaurantModel.objects.count()
# → 14                       (special shortcut)

RestaurantModel.objects.aggregate(c=Count('id'))
# → {'c': 14}                (dict, general aggregate)

SaleModel.objects.aggregate(
    min=Min('income'),
    max=Max('income'),
    avg=Avg('income'),
    sum=Sum('income'),
)
# → {'min': 1200, 'max': 9800, 'avg': 4500.5, 'sum': 22500}
```

- Returns a `dict`, never a queryset.
- Computes ALL the aggregates in a SINGLE SQL query — cheap.
- You can rename the dict key with `key=Agg(...)`. Default key is
  `'<field>__<aggregate-lowercase>'`, e.g. `'rating__avg'`.

### Filter THEN aggregate

```python
month_ago = timezone.now() - timezone.timedelta(days=30)
SaleModel.objects.filter(datetime__gte=month_ago).aggregate(sum=Sum('income'))
# → SUM over the last 30 days only
```

The `.filter()` narrows rows first; the `.aggregate()` sums what's left.

## `.annotate()` — add a column per row

```python
RestaurantModel.objects.annotate(num=Count('ratings'))
# → <QuerySet [
#     <RestaurantModel: Mario's>,   r.num = 3
#     <RestaurantModel: Luigi's>,   r.num = 2
#     <RestaurantModel: Tony's>,    r.num = 0
#   ]>
```

- Returns a `QuerySet` — still chainable.
- Each instance gets a NEW attribute (`r.num`) on the Python side.
- The chainability is huge — you can filter / order by the computed value:

```python
RestaurantModel.objects.annotate(
    avg=Avg('ratings__rating'),
).filter(avg__gte=4.5).order_by('-avg')
```

You **cannot** do this with `.aggregate()` — `aggregate` is the end of
the line.

### Annotate doesn't have to be an aggregate

You can annotate with any expression — Upper, Lower, Concat, F(),
case/when, etc. — to compute a per-row value:

```python
from django.db.models.functions import Upper
RestaurantModel.objects.annotate(upper_name=Upper('name'))
# → each row now has r.upper_name = 'MARIO'S', etc.
```

No GROUP BY in this case (see below).

## When does GROUP BY happen?

The single rule:

> GROUP BY appears whenever you ask for **"one aggregate value PER row of something"** — and that "something" is whatever rows you want to keep distinct.

Concrete table:

| Query | Rows out | GROUP BY? |
|---|---|---|
| `.aggregate(Avg('rating'))`                              | 1                  | No |
| `.annotate(avg=Avg('ratings__rating'))`                  | N (per restaurant) | Yes — by source PK |
| `.annotate(upper=Upper('name'))`                         | N (per restaurant) | No — not an aggregate |
| `.values('type').annotate(c=Count('id'))`                | M (per type)       | Yes — by `type` |

### Why does `.annotate(aggregate)` need GROUP BY?

Because the JOIN to the related table **duplicates** parent rows.

```
restaurants JOIN ratings →

  restaurant.id  name      rating.id  rating.rating
  ─────────────  ────────  ─────────  ──────────────
  1              Mario's   10         5
  1              Mario's   11         3              ← Mario duplicated
  1              Mario's   12         4              ← Mario duplicated
  2              Luigi's   13         5
  2              Luigi's   14         2              ← Luigi duplicated
  3              Tony's    NULL       NULL           ← LEFT JOIN keeps Tony
```

To get **one row per restaurant** with one aggregate beside it, the DB
must `GROUP BY restaurant.id` to fold the duplicated rows back.

### The classic SQL "GROUP BY column" pattern

Put `.values()` **before** `.annotate()` to group by a column instead of
the PK:

```python
RestaurantModel.objects.values('restaurant_type').annotate(c=Count('id'))
# → [{'restaurant_type': 'IT', 'c': 5},
#    {'restaurant_type': 'IN', 'c': 3},
#    {'restaurant_type': 'CH', 'c': 6}]
```

SQL:
```sql
SELECT restaurant_type, COUNT(id) AS c
FROM   core_restaurantmodel
GROUP BY restaurant_type;
```

> Rule: `.values(...).annotate(...)` → GROUP BY whatever columns are in
> `.values()`. `.annotate(...)` alone → GROUP BY the source PK.

## INNER JOIN vs LEFT OUTER JOIN inside annotations

Django picks the JOIN type based on whether the related row is guaranteed
to exist:

| Situation | JOIN type |
|---|---|
| Forward FK, `null=False` (default) | INNER JOIN |
| Forward FK, `null=True` | LEFT OUTER JOIN |
| Reverse FK / M2M (the "many" side) | LEFT OUTER JOIN |
| Inside `.filter(rel__x=...)` | INNER JOIN (filter implies existence) |

So `RestaurantModel.objects.annotate(avg=Avg('ratings__rating'))` uses
LEFT OUTER JOIN — restaurants with **zero** ratings are kept in the
result with `avg = None`. If Django had used INNER JOIN, those
restaurants would silently disappear.

## Combining aggregate and annotate

You can pipe them — annotate per row, then aggregate over those:

```python
RestaurantModel.objects.annotate(
    rating_count=Count('ratings'),
).aggregate(
    busiest=Max('rating_count'),
    total_ratings=Sum('rating_count'),
)
# → {'busiest': 12, 'total_ratings': 47}
```

annotate adds `rating_count` to each restaurant; aggregate then
summarises those per-row counts into one dict.

## Filtering aggregates (`Sum(... , filter=Q(...))`)

To aggregate only **some** of the related rows, pass a `filter=Q(...)`:

```python
from django.db.models import Q

month_ago = timezone.now() - timezone.timedelta(days=30)

RestaurantModel.objects.annotate(
    recent_income=Sum('sales__income', filter=Q(sales__datetime__gte=month_ago)),
)
```

This way you don't have to use a separate `Prefetch` — the SUM itself is
restricted to recent sales. (`Prefetch` and `annotate` are independent
SQL paths — one filtering the other doesn't carry over.)

## Cheat-sheet

| | `.aggregate()` | `.annotate()` |
|---|---|---|
| Returns                  | a `dict`             | a `QuerySet` |
| One value, or per row?   | one for whole table  | one per row |
| Chainable?               | No (ends the QS)     | Yes (`.filter(annotated__gte=...)`) |
| Loop over it?            | No                   | Yes |
| Question it answers      | "What's the total/avg across X?" | "What's the total/avg **for each** X?" |
| SQL shape                | `SELECT AGG(...) FROM ...` | `SELECT *, AGG(...) FROM ... GROUP BY ...` |

## Mental hooks

> **"aggreg-ATE"** — eats the table down to one summary.
> **"anno-TATE"** — attaches notes (extra columns) to each row.

Or:

> A single number? → `.aggregate()`.
> One number per row? → `.annotate()`.
> One number per category? → `.values('category').annotate()`.

## Try it (Django shell)

```bash
python manage.py shell
```

```python
from django.db.models import Count, Avg, Sum, Max
from core.models import RestaurantModel, RatingModel

# 1) aggregate — one dict
RatingModel.objects.aggregate(avg=Avg('rating'))

# 2) annotate — one row per restaurant
list(RestaurantModel.objects.annotate(n=Count('ratings')).values('name', 'n'))

# 3) values + annotate — GROUP BY column
list(RestaurantModel.objects.values('restaurant_type').annotate(c=Count('id')))

# Confirm the SQL each one generates
from django.db import connection
print(connection.queries[-1]['sql'])
```
