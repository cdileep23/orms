# 06 — Filtering & Field Lookups

This is the heart of "reading" data: asking the database for **only the rows
you want**. Examples use my restaurant project and the filtering blocks I've
been practising in `orm_script.py`.

## Recap: `.filter()` and `.exclude()`

Both take conditions as keyword arguments and return a **QuerySet**
(0, 1, or many rows — never an error if nothing matches).

```python
RestaurantModel.objects.filter(restaurant_type='CH')    # rows that MATCH
RestaurantModel.objects.exclude(restaurant_type='CH')   # rows that DON'T
```

`.filter()` is `WHERE ...`, `.exclude()` is `WHERE NOT ...` in SQL.

## What a "field lookup" is

A plain `field=value` only checks **equality**. To ask other questions —
"greater than", "contains", "starts with" — you add a **lookup suffix** with
a **double underscore**:

```
field__lookup=value
        ^^
   two underscores
```

```python
RatingModel.objects.filter(rating=5)        # rating EQUALS 5
RatingModel.objects.filter(rating__gte=5)   # rating >= 5
RatingModel.objects.filter(rating__lt=3)    # rating < 3
```

> ⚠️ It is **two underscores** (`__`), not one. `rating_gte` (one underscore)
> would be read as a field *named* `rating_gte`, and Django would error
> because no such field exists.

## Comparison lookups (numbers, dates)

| Lookup | Means | SQL |
|--------|-------|-----|
| `__gt` | greater than | `>` |
| `__gte` | greater than or equal | `>=` |
| `__lt` | less than | `<` |
| `__lte` | less than or equal | `<=` |

```python
RatingModel.objects.filter(rating__gte=4)              # 4 and 5 star
SaleModel.objects.filter(income__lt=1000)              # small sales
RestaurantModel.objects.filter(date_opened__gt='2000-01-01')
```

## Text lookups

| Lookup | Matches when the text... | Case-insensitive twin |
|--------|--------------------------|------------------------|
| `__contains` | contains the substring | `__icontains` |
| `__startswith` | starts with it | `__istartswith` |
| `__endswith` | ends with it | `__iendswith` |
| `__exact` | equals it exactly | `__iexact` |

```python
RestaurantModel.objects.filter(name__startswith='Chinese')
RestaurantModel.objects.filter(name__icontains='pizza')   # Pizza, PIZZA, pizza
```

### The `i` prefix = case-**i**nsensitive

Any lookup starting with `i` ignores upper/lower case. `name__exact='bk'`
matches only `bk`; `name__iexact='bk'` also matches `BK`, `Bk`, `bK`.

> Note: `field=value` is the same as `field__exact=value` — `exact` is the
> default lookup you get when you write no suffix at all.

## Membership: `__in`

`__in` checks "is the value **one of** these?" — pass a list/tuple/QuerySet.

```python
check_types = [
    RestaurantModel.TypeChoices.CHINESE,
    RestaurantModel.TypeChoices.INDIAN,
    RestaurantModel.TypeChoices.ITALIAN,
]
RestaurantModel.objects.filter(restaurant_type__in=check_types)
```

This is one `WHERE restaurant_type IN (...)` query — much better than
running a separate query per type.

## Range: `__range`

`__range` is "between two values, **inclusive**" — like SQL `BETWEEN`.

```python
SaleModel.objects.filter(income__range=(1000, 5000))     # 1000 <= income <= 5000
RatingModel.objects.filter(rating__range=(3, 5))
```

## NULL check: `__isnull`

Tests whether a column is empty (`NULL`). `SaleModel.restaurant` allows
`null=True`, so this matters there:

```python
SaleModel.objects.filter(restaurant__isnull=True)    # sales with no restaurant
SaleModel.objects.filter(restaurant__isnull=False)   # sales that have one
```

## Date / datetime lookups

On `DateField` / `DateTimeField` you can dig into parts of the date:

| Lookup | Example |
|--------|---------|
| `__year` | `date_opened__year=2020` |
| `__month` | `date_opened__month=12` |
| `__day` | `date_opened__day=1` |
| `__date` | `datetime__date='2024-05-01'` (date part of a datetime) |
| `__gte` etc. | `date_opened__gte='2010-01-01'` |

```python
RestaurantModel.objects.filter(date_opened__year=2020)
SaleModel.objects.filter(datetime__month=1)        # all January sales
```

## Combining conditions

### AND — multiple arguments or chained `.filter()`

Several conditions in one `.filter()` are joined with **AND** — every one
must be true:

```python
RestaurantModel.objects.filter(
    restaurant_type=RestaurantModel.TypeChoices.CHINESE,
    name__startswith='Chinese',
)
```

Chaining `.filter()` calls does the same thing:

```python
RestaurantModel.objects.filter(restaurant_type='CH').filter(name__startswith='Chinese')
```

Both produce ONE SQL query with `WHERE ... AND ...` (QuerySets are lazy —
see topic 05).

### OR — `Q` objects

Keyword arguments can only do AND. For **OR**, import `Q` and combine with
the `|` operator:

```python
from django.db.models import Q

RestaurantModel.objects.filter(
    Q(restaurant_type='CH') | Q(restaurant_type='IT')   # Chinese OR Italian
)
```

`&` is AND, `|` is OR, `~` is NOT. (`Q` gets covered properly later — for
now just know OR needs it.)

## Spanning relationships — `__` follows a ForeignKey

The double underscore also **jumps across a ForeignKey** into the related
table. Django turns this into a SQL **JOIN** automatically.

```python
# Ratings whose restaurant's name starts with "Ch"
RatingModel.objects.filter(restaurant__name__startswith='Ch')

# Sales whose restaurant's name starts with "Ch"
SaleModel.objects.filter(restaurant__name__startswith='Ch')
```

Read `restaurant__name__startswith` left to right:
**`restaurant`** (follow the FK) → **`name`** (a field on that restaurant) →
**`startswith`** (the lookup). You can chain as deep as the relationships go.

It also works in the **reverse** direction, using the `related_name`.
`RatingModel.restaurant` has `related_name='ratings'`, so:

```python
# Restaurants that have at least one 5-star rating
RestaurantModel.objects.filter(ratings__rating=5)
```

## `exclude()` = NOT

`.exclude()` keeps every row that does **not** match — the "NOT" of a query:

```python
chinese = RestaurantModel.TypeChoices.CHINESE
RestaurantModel.objects.exclude(restaurant_type=chinese)   # everything except Chinese
```

It accepts the exact same lookups as `.filter()`.

## Bonus: ordering the results

Filtering picks *which* rows; ordering picks *what order* they come back in.

```python
RestaurantModel.objects.order_by('name')        # A -> Z
RestaurantModel.objects.order_by('-name')       # Z -> A   (minus = descending)
RestaurantModel.objects.order_by('name').reverse()   # flips the order
```

Case-insensitive sort with the `Lower` function:

```python
from django.db.models.functions import Lower
RestaurantModel.objects.order_by(Lower('name'))   # 'apple' and 'Apple' sort together
```

`earliest()` / `latest()` grab the single oldest/newest row by a date field:

```python
RestaurantModel.objects.earliest('date_opened')   # oldest restaurant
RestaurantModel.objects.latest('date_opened')     # newest restaurant
```

(My `RestaurantModel.Meta` sets `ordering=['date_opened']` and
`get_latest_by='date_opened'`, so it already has a default order.)

Slicing a QuerySet becomes `LIMIT` / `OFFSET` — it does **not** load
everything then cut:

```python
RestaurantModel.objects.order_by('date_opened')[2:5]   # 3rd, 4th, 5th rows
```

## Try it (Django shell)

```bash
python manage.py shell
```

```python
from core.models import RestaurantModel, RatingModel
from django.db import connection

qs = RestaurantModel.objects.filter(name__icontains='a', date_opened__year__gte=2000)
print(qs)
print(connection.queries[-1]['sql'])   # see the WHERE clause Django built
```

## What I should remember

1. `.filter()` = `WHERE`, `.exclude()` = `WHERE NOT`. Both return QuerySets.
2. A field lookup is `field__lookup=value` — **two** underscores.
3. `field=value` is just shorthand for `field__exact=value`.
4. Comparisons: `gt gte lt lte`. Text: `contains startswith endswith`.
5. An `i` prefix (`icontains`, `iexact`, ...) makes it case-insensitive.
6. `__in` = "one of a list"; `__range` = "between, inclusive"; `__isnull` = NULL check.
7. Multiple args / chained `.filter()` = **AND**. For **OR**, use `Q(...) | Q(...)`.
8. `__` also crosses a ForeignKey — that's a SQL JOIN done for you.

## Official docs

- Field lookups reference: https://docs.djangoproject.com/en/stable/ref/models/querysets/#field-lookups
- Making queries — retrieving objects: https://docs.djangoproject.com/en/stable/topics/db/queries/#retrieving-objects
- Lookups that span relationships: https://docs.djangoproject.com/en/stable/topics/db/queries/#lookups-that-span-relationships
- Complex lookups with `Q`: https://docs.djangoproject.com/en/stable/topics/db/queries/#complex-lookups-with-q-objects

Next: [07 — Relationships (ForeignKey, ManyToMany, OneToOne)](07-relationships.md)
