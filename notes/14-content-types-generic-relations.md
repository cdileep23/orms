# 14 — ContentTypes & Generic Relations (`GenericForeignKey`, `GenericRelation`)

A normal `ForeignKey` can point to **one** model. But sometimes you want a
model that can attach to **many different** models — comments, likes, tags,
attachments. A `CommentModel` should be able to live on a `RestaurantModel`,
a `ProductModel`, a `RatingModel`, etc.

Generic relations solve this with two pieces of stored info:

| Field | Question it answers | Example |
|---|---|---|
| `content_type` | *Which model?* | `restaurantmodel` |
| `object_id` | *Which row's id?* | `5` |

Together they're like an address: "the Restaurant with id 5." Django wraps
that pair in a `GenericForeignKey` so you can read/write the real object
naturally.

Everything here lives in `django.contrib.contenttypes` (already in
`INSTALLED_APPS` by default).

---

## 1. The `ContentType` table

Django keeps a small table, `django_content_type`, with **one row per model**
in the whole project. It's a registry the generic relation picks from.

```python
from django.contrib.contenttypes.models import ContentType

# list every model in the 'core' app
ContentType.objects.filter(app_label='core')
# [<ContentType: restaurant model>, <ContentType: product model>, ...]
```

**Gotcha — `model` is stored lowercased.** The class is `RestaurantModel`
but the `model` column holds `restaurantmodel`:

```python
ContentType.objects.get(app_label='core', model='restaurantmodel')   # works
ContentType.objects.get(app_label='core', model='RestaurantModel')   # DoesNotExist!
```

### Handy ContentType methods

```python
ct = ContentType.objects.get_for_model(RatingModel)   # row for a given model
ct.model_class()                                       # -> <class RatingModel>  (record -> class)
ct.get_object_for_this_type(pk=5)                      # -> the RatingModel with id=5
```

`get_for_model` is the preferred lookup — it caches results, so it's faster
than building a `get(app_label=..., model=...)` query yourself.

---

## 2. The model setup

Two sides to wire up.

### Side A — the model that *can attach anywhere* (`GenericForeignKey`)

```python
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

class CommentModel(models.Model):
    text = models.TextField()
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)  # which model
    object_id = models.PositiveIntegerField()                                # which row id
    content_object = GenericForeignKey('content_type', 'object_id')          # the glue
```

- `content_type` + `object_id` are **real DB columns**.
- `content_object` is **not** a column — it's a virtual accessor that reads
  those two columns and fetches the object (or, when you assign to it, fills
  those two columns in for you).
- The arg names `'content_type', 'object_id'` must match the field names above.
  (They're the default, so `GenericForeignKey()` with no args also works.)

### Side B — the parent model that *owns* them (`GenericRelation`)

This is optional but gives you the reverse lookup (`restaurant.comments`).

```python
from django.contrib.contenttypes.fields import GenericRelation

class RestaurantModel(models.Model):
    name = models.CharField(max_length=100)
    # ...
    comments = GenericRelation('core.CommentModel')
```

| Field | Lives on | Direction | Gives you |
|---|---|---|---|
| `GenericForeignKey` | `CommentModel` | comment → object | `comment.content_object` |
| `GenericRelation` | `RestaurantModel` | object → comments | `restaurant.comments.all()` |

Without the `GenericRelation`, `restaurant.comments` doesn't exist and you'd
get an `AttributeError`.

---

## 3. Writing — attach a comment to an object

### Easiest way — assign `content_object`

```python
res = RestaurantModel.objects.first()

CommentModel.objects.create(
    text='Great tacos!',
    content_object=res,    # Django fills in content_type + object_id automatically
)
```

You never touch `content_type` / `object_id` directly — assigning the object
sets both behind the scenes. Check with `comment.__dict__` to see the raw
`content_type_id` and `object_id` Django stored.

### Via the reverse manager — `.create()` (cleanest)

If you have the `GenericRelation`, the parent knows who it is, so you don't
even pass `content_object`:

```python
res.comments.create(text='Great tacos!')
```

### `.add()` — the bulk gotcha

```python
res.comments.add(comment)              # works only if `comment` is ALREADY saved
res.comments.add(CommentModel(...))    # ValueError: instance isn't saved
res.comments.add(CommentModel(...), bulk=False)   # fix: bulk=False saves it first
```

`.add()` defaults to `bulk=True`, a fast single `UPDATE` that re-points
existing rows — so it can't insert a brand-new unsaved object. `bulk=False`
switches it to call `.save()` on each object (slower, but handles unsaved
ones). **For new objects, prefer `.create()` — no gotcha.**

---

## 4. Reading — from a comment back to its object

```python
comment = CommentModel.objects.first()

comment.content_object        # <RestaurantModel: Taco Bell>  (the easy shortcut)

# the manual way (useful when you want the model CLASS, not just the object):
ctype = comment.content_type            # the ContentType row
ctype.model_class()                     # <class RestaurantModel>
ctype.get_object_for_this_type(pk=comment.object_id)   # <RestaurantModel: Taco Bell>
```

99% of the time `comment.content_object` is all you need. Drop to
`content_type` + `object_id` only when you need the class itself or are
filtering by type.

---

## 5. Reverse lookups & filtering (needs `GenericRelation`)

```python
res = RestaurantModel.objects.get(id=2)

res.comments.all()        # every comment on this restaurant
res.comments.last()       # most recent
res.comments.count()
```

### `.remove()` DELETES, it doesn't unlink

```python
res.comments.remove(some_comment)   # deletes the comment ROW from the DB
```

Because `content_type` and `object_id` are **not nullable**, there's no way to
leave a comment "floating" with no owner. So `.remove()` has no choice but to
delete the row. For generic relations these two are equivalent:

```python
res.comments.remove(c)
c.delete()
```

### N+1 warning

```python
for r in RestaurantModel.objects.all():
    print(r.comments.all())          # one extra query PER restaurant (N+1)

# fix — fetch all comments in one extra query:
for r in RestaurantModel.objects.prefetch_related('comments'):
    print(r.comments.all())
```

`prefetch_related` works on `GenericRelation` just like any reverse FK.

---

## 6. Admin — editing comments inline

You can edit an object's comments **right on its admin page** using a
generic inline.

```python
from django.contrib.contenttypes.admin import GenericTabularInline

class CommentInline(GenericTabularInline):
    model = CommentModel
    max_num = 1                 # show at most 1 comment form (omit for many)

class RestaurantAdmin(admin.ModelAdmin):
    list_display = ['name', 'id']
    inlines = [CommentInline]   # <- this is what actually shows the inline

admin.site.register(RestaurantModel, RestaurantAdmin)
```

- Use **`GenericTabularInline`** (or `GenericStackedInline`) — the plain
  `TabularInline` only works with regular foreign keys.
- Defining the inline class does nothing until you add it to a parent admin's
  `inlines` list.
- `max_num=1` limits how many forms appear; leave it out to add many.

---

## 7. Common pitfalls

- **Querying `model='RestaurantModel'`** → `DoesNotExist`. The `model` column
  is lowercased: use `'restaurantmodel'`.
- **`.add(unsaved_obj)`** → `ValueError: instance isn't saved`. Use
  `bulk=False`, or just `.create()`.
- **Forgetting `GenericRelation`** → `restaurant.comments` raises
  `AttributeError`. Add it to the parent for reverse access.
- **Expecting `.remove()` to unlink** → it DELETES (non-nullable columns).
- **N+1 in loops** → use `prefetch_related('comments')`.
- **Plain `TabularInline` for a generic relation** → won't work; use
  `GenericTabularInline`.

---

## 8. Cheat sheet

```python
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey, GenericRelation

# --- model setup ---
class CommentModel(models.Model):
    text = models.TextField()
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

class RestaurantModel(models.Model):
    comments = GenericRelation('core.CommentModel')   # reverse access

# --- write ---
res.comments.create(text='hi')                        # cleanest
CommentModel.objects.create(text='hi', content_object=res)

# --- read (comment -> object) ---
comment.content_object                                # the object
comment.content_type.model_class()                    # the class

# --- read (object -> comments) ---
res.comments.all()
RestaurantModel.objects.prefetch_related('comments')  # avoid N+1

# --- contenttype helpers ---
ContentType.objects.get_for_model(RatingModel)
ct.model_class()
ct.get_object_for_this_type(pk=5)

# --- delete ---
res.comments.remove(c)                                # deletes the row
```

---

## Mental model

- **`ContentType`** = a registry with one row per model (the menu).
- **`GenericForeignKey`** = "which menu item + which row" stored as
  `content_type` + `object_id`, exposed as `content_object`.
- **`GenericRelation`** = the reverse view, so the parent can list its
  attached objects.

Reach for generic relations when **one model needs to attach to many
different models**. If it only ever attaches to one, a plain `ForeignKey`
is simpler and faster — don't over-generalize.
