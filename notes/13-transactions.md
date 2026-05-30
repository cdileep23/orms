# 13 — Transactions (`atomic`, `select_for_update`, `on_commit`)

A **transaction** is a group of DB operations that all succeed together,
or all roll back together. Django gives you three tools to use them well:

| Tool | Purpose |
|---|---|
| `transaction.atomic()` | Wrap a block so writes commit or rollback as one unit |
| `select_for_update()` | Lock specific rows so concurrent writers wait until you're done |
| `transaction.on_commit(fn)` | Defer a side effect until the transaction successfully commits |

All three live in `django.db.transaction` (except `select_for_update`,
which is a queryset method).

Examples use the project's `ProductModel` (with `number_in_stock`) and
`OrderModel` from the order-product flow.

---

## 1. Why transactions

A single SQL statement is already atomic. Transactions matter when **a
business action spans multiple statements** and partial completion would
leave the database in a bad state.

The classic Django example — placing an order:

```python
order = OrderModel.objects.create(product=p, no_of_items=3)   # row 1
p.number_in_stock -= 3
p.save()                                                       # row 2
```

If the process crashes between the two saves, we've created an order
without decrementing stock — we'll happily oversell. A transaction
makes both happen together, or neither:

```python
with transaction.atomic():
    order = OrderModel.objects.create(product=p, no_of_items=3)
    p.number_in_stock -= 3
    p.save()
```

---

## 2. `transaction.atomic()` — three ways to use it

### As a context manager (most common)

```python
from django.db import transaction

with transaction.atomic():
    do_thing_1()
    do_thing_2()
```

- Opens a transaction at `with`.
- Commits when the block exits normally.
- **Rolls back if any exception escapes the block** — including
  exceptions you raise yourself.

### As a decorator on a function

```python
@transaction.atomic
def place_order(user, product, qty):
    ...
```

The whole function body is one transaction.

### `ATOMIC_REQUESTS` — wrap every view in a transaction

In `settings.py`:

```python
DATABASES = {
    'default': {
        ...
        'ATOMIC_REQUESTS': True,
    }
}
```

Every HTTP request becomes one transaction. If the view raises, all
writes roll back automatically. Simple, but blunt — every request opens
a transaction even when it does no writes, and long-running views hold
the transaction open the whole time. Most projects prefer explicit
`atomic()` only around the parts that need it.

---

## 3. How rollback works

Inside `atomic()`, Django commits **only if the block exits cleanly**.
Any uncaught exception triggers a rollback:

```python
with transaction.atomic():
    OrderModel.objects.create(product=p, no_of_items=999)   # written
    raise ValueError("nope")                                # bombs out
# -> entire transaction rolled back; the order row never existed
```

### Gotcha — catching an exception INSIDE atomic()

If you catch the exception, the DB never sees it and **the transaction
will try to commit**:

```python
with transaction.atomic():
    bad_thing()         # raises
    # except: pass      # <- if you swallow here, atomic() commits
```

Worse, if a query inside `atomic()` raised an `IntegrityError` and you
swallowed it, the transaction is in a broken state — every subsequent
query in the same block will raise `TransactionManagementError`. Either:

- Let the exception propagate (preferred), or
- Use a **nested `atomic()`** (savepoint) so you can catch errors from
  the inner block without poisoning the outer one.

### Nested `atomic()` = savepoints

```python
with transaction.atomic():            # outer transaction
    do_safe_thing()

    try:
        with transaction.atomic():    # SAVEPOINT
            do_risky_thing()          # if this raises...
    except IntegrityError:
        log_and_continue()            # ...only the savepoint rolls back

    do_more_safe_things()             # outer txn keeps going, commits at end
```

Inner `atomic()` blocks create a **savepoint**, not a new transaction.
They let you roll back just part of a larger transaction.

---

## 4. `select_for_update()` — locking rows

A transaction alone doesn't protect you from **another** transaction
reading the same row and racing you to UPDATE it. Example without lock:

```python
# Two requests both want to order from a product with 10 in stock.
with transaction.atomic():
    p = ProductModel.objects.get(pk=1)   # both read number_in_stock = 10
    p.number_in_stock -= 3               # both compute 7
    p.save()                             # last writer wins -> stock = 7
# Real stock should be 4; you've oversold.
```

`select_for_update()` adds `FOR UPDATE` to the SELECT, which places a
**row-level write lock** on the matched rows for the rest of the
transaction:

```python
with transaction.atomic():
    p = ProductModel.objects.select_for_update().get(pk=1)
    # Another txn calling .select_for_update().get(pk=1) now BLOCKS
    # until our transaction commits or rolls back.
    p.number_in_stock -= 3
    p.save()
```

SQL produced:

```sql
SELECT ... FROM product WHERE id = 1 FOR UPDATE;
```

### Requirements

- **Must be inside `atomic()`**. Outside a transaction it raises
  `TransactionManagementError`.
- Database support — Postgres yes, MySQL/InnoDB yes, **SQLite IGNORES it
  silently**. Use Postgres if you want to test locking behaviour.

### Variants worth knowing

```python
.select_for_update(skip_locked=True)   # skip rows already locked (no wait)
.select_for_update(nowait=True)        # raise immediately if row is locked
.select_for_update(of=('self',))       # lock only THIS table in a JOIN, not joined ones
```

`skip_locked` is great for job queues — many workers `SELECT FOR UPDATE
SKIP LOCKED LIMIT 1` to grab the next un-claimed job atomically.

### Demo (run with Postgres)

Open two `python manage.py shell` sessions.

**Session A:**

```python
import time
from django.db import transaction
from core.models import ProductModel

with transaction.atomic():
    p = ProductModel.objects.select_for_update().get(name='Book')
    time.sleep(15)   # hold the lock for 15 seconds
```

**Session B (within those 15 seconds):**

```python
from django.db import transaction
from core.models import ProductModel

with transaction.atomic():
    p = ProductModel.objects.select_for_update().get(name='Book')
    print('got it!')
```

Session B blocks until Session A's transaction exits.

---

## 5. `transaction.on_commit()` — defer side effects

The order-placed email shouldn't go out if the transaction rolls back.
But you also can't email AFTER the `with` block, because by then
exceptions and rollbacks have already happened.

Solution: register the side effect with `on_commit` INSIDE the
transaction. Django runs it **only after a successful commit**.

```python
from django.db import transaction
from functools import partial

def email_user(name):
    print(f"order placed: {name}")

with transaction.atomic():
    order = OrderModel.objects.create(product=p, no_of_items=3)
    transaction.on_commit(partial(email_user, order.product.name))
    # ... if anything below raises, the callback never runs
```

`on_commit` takes a **zero-argument callable**. To pass arguments, wrap
with `functools.partial` (or a lambda).

Use it for any side effect that must NOT happen on rollback:

- Sending emails
- Enqueuing a Celery / RQ task (don't let a worker process an order that
  doesn't exist yet)
- Calling an external API
- Cache invalidation

### Gotcha — outside `atomic()`, it fires immediately

If you call `transaction.on_commit(fn)` while no transaction is open,
the callback runs **right away** (because there's nothing to wait for).
Usually harmless, but easy to be surprised by in tests.

---

## 6. Real example — the order_product view

The full pattern, putting all three tools together:

```python
def order_product(request):
    if request.method == 'POST':
        form = ProductOrderForm(request.POST)

        if form.is_valid():
            with transaction.atomic():                       # 1. all-or-nothing
                order = form.save()

                product = (                                  # 2. lock the row
                    ProductModel.objects
                    .select_for_update()
                    .get(pk=order.product_id)
                )
                product.number_in_stock -= order.no_of_items
                product.save()

                transaction.on_commit(                       # 3. side effect
                    partial(email_user, product.name)
                )

            return redirect('order_product')
    else:
        form = ProductOrderForm()

    return render(request, 'order_product.html', {'form': form})
```

What each piece prevents:

| Risk | Protection |
|---|---|
| Order saved but stock not decremented (crash mid-flow) | `transaction.atomic()` — both or neither |
| Two concurrent orders both reading "10 in stock" and overselling | `select_for_update()` — one transaction waits for the other |
| Email sent for an order whose transaction rolled back | `transaction.on_commit()` — fires only after successful commit |

---

## 7. Common pitfalls

- **Not wrapping `select_for_update` in `atomic()`** → `TransactionManagementError`.
- **Catching exceptions inside `atomic()` and continuing** → broken transaction state, every later query raises `TransactionManagementError`. Use nested `atomic()` (savepoint) if you must catch.
- **Calling `on_commit` outside a transaction** → callback fires immediately.
- **Long-running work inside `atomic()`** (HTTP calls, sleep, large loops) → holds the lock for that whole time, blocks every other writer.
- **Locking rows you don't need to update** → unnecessary blocking. Lock only the rows you'll write to.
- **`select_for_update` on SQLite** → silently does nothing. Test concurrency with Postgres.
- **Reading the row BEFORE opening `atomic()`** → no lock. Always re-fetch with `select_for_update()` inside the transaction.

---

## 8. Cheat sheet

```python
from django.db import transaction
from functools import partial

# 1. Wrap writes in a transaction
with transaction.atomic():
    ...

# 2. Lock rows you're about to update
with transaction.atomic():
    p = ProductModel.objects.select_for_update().get(pk=1)
    p.number_in_stock -= qty
    p.save()

# 3. Defer side effects until commit
with transaction.atomic():
    order = OrderModel.objects.create(...)
    transaction.on_commit(partial(send_email, order.id))

# 4. Nested savepoint — catch inner errors without poisoning outer txn
with transaction.atomic():
    try:
        with transaction.atomic():
            risky()
    except IntegrityError:
        recover()
    safe_stuff()

# 5. Job queue pattern — workers don't trip over each other
job = (
    JobModel.objects
    .select_for_update(skip_locked=True)
    .filter(status='pending')
    .first()
)
```

---

## Mental model

- **`atomic`** answers *"do these writes commit together?"*
- **`select_for_update`** answers *"who gets to write this row first?"*
- **`on_commit`** answers *"when is it safe to do the side effect?"*

Use all three together whenever a write affects a shared resource and
has external consequences (emails, billing, queues).
