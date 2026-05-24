# 07 — Relationships (ForeignKey, ManyToMany, OneToOne)

Three relationship fields. Each describes "how many of *that* belongs to
one of *this*". Examples use my restaurant project.

## ForeignKey (many → one)

"Many ratings belong to **one** restaurant."

```python
class RatingModel(models.Model):
    restaurant = models.ForeignKey(
        RestaurantModel,
        on_delete=models.CASCADE,
        related_name='ratings',
    )
    rating = models.PositiveSmallIntegerField()
```

What Django actually creates in the database:
- Adds a column `restaurant_id` (an integer) to `core_ratingmodel`.
- That's it — **no separate table**. A FK is just a foreign-key column.

### Forward vs reverse access

```python
rating.restaurant            # forward — gives ONE RestaurantModel
restaurant.ratings.all()     # reverse — gives MANY RatingModels
```

| Direction | Goes from → to | Accessor name |
|---|---|---|
| **Forward** | from the model that **declared** the FK | the **field name** (here `restaurant`) |
| **Reverse** | from the target back to the FK's model | `related_name` if set, else `<modelname>_set` |

So if you removed `related_name='ratings'`, you'd write
`restaurant.ratingmodel_set.all()`. The `_set` suffix is Django's hint
that the result is a collection.

### `related_name` rules

- Whatever string you give is the **exact** accessor name — Django does
  **not** append `_set` to it.
- It only affects the **reverse** direction. Forward access always uses
  the field name.
- If two FKs in the same model point to the same target, you're **forced**
  to set distinct `related_name`s to avoid a clash.
- Use `related_name='+'` to disable the reverse accessor entirely (rare).

### `on_delete=` is required

When the parent row is deleted, what happens to the child? You must say:

| Value | Behavior |
|---|---|
| `CASCADE`    | delete the child too |
| `PROTECT`    | raise an error, prevent the parent delete |
| `SET_NULL`   | set the FK column to NULL (needs `null=True`) |
| `SET_DEFAULT`| set it to the field's `default=` |
| `SET(...)`   | set it to a custom value/callable |
| `DO_NOTHING` | leave the FK dangling (database may error later) |

## ManyToMany (many ↔ many)

"A staff member works at many restaurants. A restaurant has many staff."

```python
class StaffModel(models.Model):
    name = models.CharField(max_length=100)
    restaurants = models.ManyToManyField(RestaurantModel, related_name='staff')
```

What Django actually creates:
- A hidden **link table** `core_staffmodel_restaurants(id, staffmodel_id, restaurantmodel_id)`.
- Each row in the link table = one (staff, restaurant) link.

### The M2M manager

`staff.restaurants` is a *manager* that reads/writes the link table:

| Method | What it does |
|---|---|
| `.add(*objs)`        | INSERT links (duplicates are skipped) |
| `.remove(*objs)`     | DELETE specific links (the objects themselves stay) |
| `.clear()`           | DELETE all links for this side |
| `.set(iterable)`     | replace the entire link set (diffs add + remove) |
| `.all()`             | QuerySet of the related objects (uses a JOIN) |
| `.count()`           | COUNT linked rows |
| `.create(**fields)`  | create the related object AND link it |
| `.filter()`, `.exclude()`, `.order_by()`, `.annotate()` | normal QuerySet methods, scoped to the linked set |

```python
staff.restaurants.set(RestaurantModel.objects.all()[:10])
italian = staff.restaurants.filter(restaurant_type='IT')
```

### Custom `through` model — when you want EXTRA columns on the link

If each link needs its own data (e.g. salary per (staff, restaurant)),
declare your own link model and tell M2M to use it with `through=`:

```python
class StaffModel(models.Model):
    name = models.CharField(max_length=100)
    restaurants = models.ManyToManyField(
        RestaurantModel,
        through='StaffRestaurantModel',
    )

class StaffRestaurantModel(models.Model):
    staff = models.ForeignKey(StaffModel, on_delete=models.CASCADE)
    restaurant = models.ForeignKey(RestaurantModel, on_delete=models.CASCADE)
    salary = models.FloatField(null=True)       # the extra column
```

Once you use `through=`, Django **disables** the convenient writer
methods unless you provide extras via `through_defaults={...}`:

```python
# WORKS — insert through-row directly:
StaffRestaurantModel.objects.create(staff=s, restaurant=r, salary=50000)

# WORKS in modern Django — use through_defaults to fill required extras:
staff.restaurants.add(r, through_defaults={'salary': 50000})
staff.restaurants.set(qs, through_defaults={'salary': 50000})
```

> ⚠️ `.add()` is **idempotent**. If (staff, restaurant) already exists
> in the through table, `.add()` does nothing — and `through_defaults`
> is **ignored**, so it won't update `salary`. To "create or update",
> use `StaffRestaurantModel.objects.update_or_create(...)`.

### Add a uniqueness constraint when needed

The through table has no unique constraint by default — meaning duplicate
(staff, restaurant) rows are allowed. To prevent that:

```python
class StaffRestaurantModel(models.Model):
    staff = models.ForeignKey(StaffModel, on_delete=models.CASCADE)
    restaurant = models.ForeignKey(RestaurantModel, on_delete=models.CASCADE)
    salary = models.FloatField(null=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['staff', 'restaurant'],
                name='unique_staff_restaurant',
            ),
        ]
```

## OneToOne (one ↔ one)

"One Profile per User."

```python
class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
```

What Django creates:
- A FK column with a **UNIQUE** constraint on it.

### Reverse is singular

Because only one match is possible, the reverse accessor doesn't have
`_set` and doesn't need `.all()`:

```python
user.profile          # → ONE Profile, or DoesNotExist
```

That's the only relation type where reverse gives back a single object
directly.

## Cheat-sheet — field name vs reverse accessor

For all three relation types, the rule is the same:

```
Forward (out of the model that DECLARED the field): use the FIELD NAME
Reverse (into that model from the other side):      use related_name,
                                                    else <modelname>_set
                                                    (OneToOne: no _set)
```

Concrete examples from this project:

| From → To | Direction | Accessor |
|---|---|---|
| `rating.restaurant`  | forward FK | field name `restaurant` |
| `restaurant.ratings` | reverse FK | `related_name='ratings'` |
| `sale.restaurant`    | forward FK | field name `restaurant` |
| `restaurant.sales`   | reverse FK | `related_name='sales'` |
| `staff.restaurants`  | forward M2M | field name `restaurants` |
| `restaurant.staff`   | reverse M2M | `related_name='staff'` |
| `job.staff`          | forward FK (in through model) | field name `staff` |
| `job.restaurant`     | forward FK (in through model) | field name `restaurant` |

## Querying across relations with `__`

`__` follows a relation in any of `.filter()`, `.values()`, `.order_by()`,
`.select_related()`, `.prefetch_related()`, `.annotate()`:

```python
# "ratings on restaurants whose name starts with C"
RatingModel.objects.filter(restaurant__name__istartswith='C')

# "restaurants that have at least one 5-star rating"
RestaurantModel.objects.filter(ratings__rating=5)

# "names of restaurants tied to ratings, distinct"
RatingModel.objects.values_list('restaurant__name', flat=True).distinct()
```

> Single underscore = field on this model. Double underscore = follow a
> relation. `restaurant_name` ≠ `restaurant__name`.

## Mental model

> A relationship in Django is **two-way by default**.
> The field declared on one side gives you the forward accessor;
> Django auto-creates the reverse accessor on the other side, named
> after `related_name` (or `<modelname>_set`).
>
> ForeignKey = a column.
> ManyToMany = a hidden link table (or a `through` model you control).
> OneToOne = a unique column.

Whenever you're stuck, ask:
- **Which side declared the field?** That side uses the field name.
- **Going to the other side?** That's reverse → use `related_name` (or
  the default `_set` name).
