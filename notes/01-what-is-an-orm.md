# 01 — What is an ORM

## The one-line definition

**ORM = Object-Relational Mapper.** It lets you work with your database
using Python objects instead of writing raw SQL.

## The core mapping

A relational database stores data in **tables** (rows and columns).
Python thinks in **classes** and **objects**. The ORM bridges the two:

| Database concept | Python concept (Django ORM) |
|------------------|-----------------------------|
| Table            | A model class               |
| Column           | A field (class attribute)   |
| Row              | An instance of the model    |
| Cell value       | An attribute on the instance |

So in my project, the `RestaurantModel` **class** becomes a **table**, and
every restaurant I save becomes one **row** in that table.

## Why use an ORM instead of SQL?

1. **Write Python, not SQL.** Two languages become one.
2. **Database-agnostic.** The same code works on SQLite, PostgreSQL, MySQL.
   I'm on SQLite now (`db.sqlite3`); switching later needs no model changes.
3. **Safe by default.** The ORM escapes values for me, so I don't open up
   SQL-injection holes.
4. **Less boilerplate.** Creating, reading, updating, deleting rows is a
   method call, not a hand-written query.

## SQL vs ORM — same result, two styles

```sql
-- Raw SQL
SELECT * FROM core_restaurantmodel WHERE restaurant_type = 'IN';
```

```python
# Django ORM
RestaurantModel.objects.filter(restaurant_type='IN')
```

The ORM still runs SQL under the hood — it just writes it for me.

## The trade-off (good to know early)

The ORM hides SQL, which is great until a query is slow. Then you need to
know what SQL it generated. That's what topic 08 (query optimization) is
about. For now: convenience first, understand the cost later.

## Mental model to keep

> A model class is a **table blueprint**.
> An instance is **one row**.
> `.objects` is the **doorway** to all the rows already in the table.

Next: [02 — Models and Fields](02-models-and-fields.md)
