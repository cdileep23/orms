# 09 — Query Optimization (`select_related`, `prefetch_related`, N+1)

This is what you reach for **after** the ORM works but is slow.
The Django debug toolbar will tell you a page made 32 queries — this file
is about getting that number down without changing what the page shows.

Examples use my restaurant project: `RestaurantModel`, `RatingModel` (FK to
restaurant via `related_name='ratings'`) and `SaleModel` (FK to restaurant
via `related_name='sales'`).

## 1. QuerySets are LAZY (the root cause)

When you write:

```python
restaurants = RestaurantModel.objects.all()
```

**Zero SQL has run yet.** `restaurants` is a "promise" — it knows how to
fetch the rows but hasn't. SQL only runs when you *touch* the queryset:

- `for r in restaurants:`
- `list(restaurants)`
- `len(restaurants)`, `bool(restaurants)`
- slicing `restaurants[:5]`
- rendering it in a template

> A QuerySet is a recipe for SQL, not the data itself.

## 2. The N+1 problem

Classic trap. View:

```python
def index(request):
    restaurants = RestaurantModel.objects.all()        # 1 query (lazy → on render)
    return render(request, 'index.html', {'restaurant': restaurants})
```

Template:

```django
{% for r in restaurant %}
    {{ r.name }}
    {% for rt in r.ratings.all %}
        {{ rt.user.username }} — {{ rt.rating }}/5
    {% endfor %}
{% endfor %}
```

Looks innocent. But for each restaurant the template calls `r.ratings.all`,
which is a **reverse manager still connected to the DB**. Result:

| Step | Queries |
|------|---------|
| Restaurants | 1 |
| Ratings (per restaurant) | N |
| User (per rating, because `rt.user.username` is an FK access) | M |

If you have 10 restaurants with ~4 ratings each: **1 + 10 + 40 = 51 queries**.
That is "N+1" — one base query plus a new one per row.

## 3. `select_related` — SQL JOIN

Use when going to the related model gives you **one** object:
ForeignKey or OneToOne, **forward** direction.

```python
ratings = RatingModel.objects.select_related('restaurant', 'user')
```

SQL produced — **1 query** with JOINs:

```sql
SELECT rating.*, restaurant.*, user.*
FROM core_ratingmodel rating
INNER JOIN core_restaurantmodel restaurant ON rating.restaurant_id = restaurant.id
INNER JOIN auth_user user ON rating.user_id = user.id;
```

The DB does the join; Python just hydrates the objects with the joined data
already attached. `rt.restaurant.name` and `rt.user.username` cost **zero**
extra queries.

## 4. `prefetch_related` — 2nd query + Python grouping

Use when going to the related model gives you **many** objects:
reverse ForeignKey or ManyToMany.

```python
restaurants = RestaurantModel.objects.prefetch_related('ratings', 'sales')
```

SQL produced — **3 queries**:

```sql
-- 1
SELECT * FROM core_restaurantmodel;

-- 2 (uses PKs from query 1)
SELECT * FROM core_ratingmodel WHERE restaurant_id IN (...);

-- 3
SELECT * FROM core_salemodel   WHERE restaurant_id IN (...);
```

Then Django **groups results in Python** (one bucket per restaurant id) and
attaches each bucket to the matching restaurant under
`_prefetched_objects_cache['ratings']` / `['sales']`.

When the template does `r.ratings.all`, the reverse manager checks the
cache first → returns the list, no DB hit.

### Why not just JOIN everything?

A restaurant with 4 ratings and 10 sales joined together = 40 rows
(4 × 10 Cartesian product). With many relations it explodes.
So Django splits "many" relations into **one extra query per relation**.

## 5. Chaining lookups across relations

Use `__` to follow relations deeper.

```python
RestaurantModel.objects.prefetch_related('ratings__user')
```

→ prefetch ratings, AND for those ratings, also prefetch each rating's user.
3 queries: restaurants, ratings, users.

You can also combine the two strategies:

```python
RestaurantModel.objects.prefetch_related(
    Prefetch('ratings', queryset=RatingModel.objects.select_related('user'))
)
```

→ 2 queries total: restaurants + (ratings JOIN users).

## 6. `Prefetch(...)` — filter the prefetched set

By default `prefetch_related('sales')` loads **all** sales. To filter:

```python
from django.db.models import Prefetch

month_ago = timezone.now() - timezone.timedelta(days=30)

monthly_sales = Prefetch(
    'sales',
    queryset=SaleModel.objects.filter(datetime__gte=month_ago),
)
restaurants = RestaurantModel.objects.prefetch_related('ratings', monthly_sales)
```

Now `r.sales.all` in the template returns **only** sales from the last 30 days.

## 7. `filter` + JOINs and the `.distinct()` trap

```python
RestaurantModel.objects.filter(ratings__rating=5)
```

Means: "restaurants that have **at least one** rating equal to 5".
Mechanically, this does an INNER JOIN to `core_ratingmodel`. So a restaurant
with 3 five-star ratings appears in the raw join **3 times**.

Fix:

```python
RestaurantModel.objects.filter(ratings__rating=5).distinct()
```

Note: `annotate()` adds a GROUP BY which often happens to dedupe — but don't
rely on that as your dedupe mechanism. Be explicit with `.distinct()`.

## 8. `annotate` and the prefetch are SEPARATE paths

This was the surprising one for me:

```python
restaurants = (
    RestaurantModel.objects
    .prefetch_related(Prefetch('sales', queryset=SaleModel.objects.filter(datetime__gte=month_ago)))
    .annotate(total=Sum('sales__income'))
)
```

- The **prefetch** runs as a separate query and is filtered to last 30 days.
  → `r.sales.all` shows only recent sales.
- The **annotate** adds a LEFT JOIN to `core_salemodel` inside the **main**
  query and SUMs across **all** rows (no filter applied).
  → `r.total` is **lifetime** income, not last-30-days income.

These two SQL paths don't know about each other. If you want the SUM also
limited to 30 days, use a conditional sum:

```python
from django.db.models import Q
.annotate(total=Sum('sales__income', filter=Q(sales__datetime__gte=month_ago)))
```

## 9. `only()` — fetch fewer columns

When the table is wide and you render a couple of fields:

```python
RatingModel.objects.only('rating', 'restaurant__name').select_related('restaurant')
```

Django SELECTs only `rating`, `restaurant.name`, plus PKs to wire things up.
Other fields become **deferred** — touching one later triggers a fresh
query per row. Use only when you're sure the template won't read other fields.

## 10. Gotcha: `print(queryset)` runs queries TWICE

```python
restaurants = (...)
print(restaurants)              # runs SELECT ... LIMIT 21 (+ prefetches)
return render(... restaurants)  # runs SELECT ... (no LIMIT) (+ prefetches) AGAIN
```

`print` calls `__repr__`, which evaluates a **slice** (`self[:21]`) for
display — it does **not** populate the original queryset's `_result_cache`.
The template then re-evaluates the full queryset.

Fix:

```python
restaurants = list(RestaurantModel.objects....)   # forces evaluation + caches
print(restaurants)
```

`list(qs)` materializes once; the template iterates the Python list afterwards,
zero extra queries.

## Quick chooser

| You're going from | To one thing | To many things |
|---|---|---|
| ForeignKey forward (`rating.restaurant`) | `select_related('restaurant')` | — |
| OneToOne | `select_related(...)` | — |
| Reverse FK (`restaurant.ratings`) | — | `prefetch_related('ratings')` |
| ManyToMany | — | `prefetch_related(...)` |
| Filter the prefetched set | — | `Prefetch('ratings', queryset=...)` |
| Multiple "many" relations | — | `prefetch_related('a','b','c')` (one query each) |

## Try it (Django shell)

```bash
python manage.py shell
```

```python
from core.models import RestaurantModel, RatingModel
from django.db import connection, reset_queries
from django.conf import settings

# Enable query logging
settings.DEBUG = True
reset_queries()

# BAD — N+1
for r in RestaurantModel.objects.all():
    list(r.ratings.all())
print(len(connection.queries))     # 1 + N

reset_queries()

# GOOD — prefetch
for r in RestaurantModel.objects.prefetch_related('ratings'):
    list(r.ratings.all())
print(len(connection.queries))     # 2
```

## Mental model

1. Querysets are lazy — touching them runs SQL.
2. **One-side** relation → `select_related` (JOIN, 0 extra queries).
3. **Many-side** relation → `prefetch_related` (1 extra query per relation, grouped in Python).
4. `Prefetch(...)` lets you customize the prefetch query.
5. `annotate()` and `prefetch_related()` are independent SQL paths — they don't share filters.
6. Don't `print()` querysets — use the debug toolbar, or `list(qs)` first.
