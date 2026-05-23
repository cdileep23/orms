# Django ORM Notes

My study notes for learning the Django ORM and backend development.
One file per topic. I add to these as I learn.

## Roadmap

| # | Topic | Status |
|---|-------|--------|
| 00 | [Django Project Setup](00-django-project-setup.md) | done |
| 01 | [What is an ORM](01-what-is-an-orm.md) | done |
| 02 | [Models and Fields](02-models-and-fields.md) | done |
| 03 | [Validation (`full_clean`, validators)](03-validation.md) | done |
| 04 | Migrations | not started |
| 05 | [CRUD — Create, Read, Update, Delete](05-crud.md) | done |
| 06 | [Filtering & field lookups (`.filter()`, `__gte`, `__contains`)](06-filtering.md) | done |
| 07 | Relationships (ForeignKey, ManyToMany, OneToOne) | not started |
| 08 | Aggregation & annotation (`Count`, `Avg`, `annotate`) | not started |
| 09 | [Query optimization (`select_related`, `prefetch_related`, N+1)](09-query-optimization.md) | done — *you are here* |

## How I use these notes

- Read top to bottom; each file builds on the previous one.
- Examples use my own restaurant project (`core` app): `RestaurantModel`, `RatingModel`, `SaleModel`.
- "Try it" blocks are things to run in the Django shell: `python manage.py shell`.
