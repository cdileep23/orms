from core.models import RestaurantModel,SaleModel,RatingModel,ProductModel,OrderModel
from django.db.models import Q,F,Sum,Avg,Case,When,Count,Value,Subquery,OuterRef,Exists
from django.db.models.functions import Coalesce
from django.db import connection
from django.utils import timezone
from django.db import transaction
import time
def run():
    """
    ==================== Q() — COMBINING FILTERS WITH OR / NOT ====================

    Plain .filter(a=1, b=2) joins conditions with AND.
    To express OR / NOT / grouped (AND/OR) logic, wrap the conditions in Q():
        Q(a=1) | Q(b=2)      -> a=1 OR  b=2
        Q(a=1) & Q(b=2)      -> a=1 AND b=2   (same as kwargs)
        ~Q(a=1)              -> NOT (a=1)     (same as .exclude(a=1))
    """

    """
    Pull two values out of the TextChoices enum on RestaurantModel.
    These are the short DB codes: 'IT' and 'MX'.
    """
    # it=RestaurantModel.TypeChoices.ITALIAN
    # mx=RestaurantModel.TypeChoices.MEXICAN

    """
    OR with Q: restaurants whose restaurant_type is ITALIAN *or* MEXICAN.
    SQL: WHERE restaurant_type = 'IT' OR restaurant_type = 'MX'

    .values() makes the queryset return dicts (raw column data) instead of
    RestaurantModel instances. Useful here just for quick printing.
    """
    # restaurants=RestaurantModel.objects.filter(
    #     Q(restaurant_type=it) | Q(restaurant_type=mx)
    # ).values()

    # print(restaurants)

    """
    ==================== FIELD LOOKUPS RECAP ====================
    __endswith / __startswith / __contains -> case-SENSITIVE
    __iendswith / __istartswith / __icontains -> case-INSENSITIVE
    """

    """
    Names ending in the digit '1'. SQL: WHERE name LIKE '%1'
    """
    # print(RestaurantModel.objects.filter(name__endswith='1').values())

    """
    OR across two case-insensitive substring matches.
    SQL: WHERE LOWER(name) LIKE '%italian%' OR LOWER(name) LIKE '%mexican%'
    """
    # print(RestaurantModel.objects.filter(Q(name__icontains='Italian')  | Q(name__icontains="Mexican")).values())

    """
    ==================== STORING Q OBJECTS IN VARIABLES ====================
    A Q is just a value - you can name it, reuse it, combine it later.
    This makes complex filters readable instead of one giant expression.
    """
    # recently_opened=Q(date_opened__gte=timezone.now() - timezone.timedelta(days=4))
    # not_recently_opened=~Q(date_opened__gte=timezone.now() - timezone.timedelta(days=4))
    # it_or_mx=Q(name__icontains='Italian') | Q(name__icontains="Mexican")

    """
    Compose the named Q objects with | (OR).
    SQL: WHERE (name ILIKE '%italian%' OR name ILIKE '%mexican%')
            OR NOT (date_opened >= <4 days ago>)

    Translation: "Italian or Mexican places, OR anything that's been open
    for more than 4 days."
    """
    # print(RestaurantModel.objects.filter(it_or_mx | not_recently_opened).values())

    """
    ==================== Q + F TOGETHER (CROSS-TABLE + COLUMN COMPARE) ====================

    Q(restaurant__name__regex="[0-9]+")
        - The 'restaurant__' part walks the ForeignKey from SaleModel -> RestaurantModel.
        - __regex is a regular-expression match on the restaurant's name.
        - Because we filter on a related field, Django MUST JOIN to
          core_restaurantmodel automatically.

    Q(income__gt=F('expenditure'))
        - F('expenditure') refers to the expenditure COLUMN on the same row.
        - Lets us compare two columns: "income > expenditure" (profitable sale).
        - You can't do this with normal kwargs - filter(income__gt='expenditure')
          would compare to the literal string 'expenditure'.
    """
    # name_has_num=Q(restaurant__name__regex="[0-9]+")
    # is_profit=Q(income__gt=F('expenditure'))

    """
    select_related('restaurant')
        - Tells Django to JOIN core_restaurantmodel in the SAME query so
          accessing .restaurant later doesn't fire extra queries (N+1 fix).
        - HERE it's actually dead weight:
            1. The filter already crosses the FK (restaurant__name__regex),
               so Django was going to JOIN anyway.
            2. .values() returns dicts, not SaleModel instances - there is
               no .restaurant attribute to access later, so eager-loading
               the restaurant gains nothing.
          Drop the .values() and loop over instances to see the benefit.

    connection.queries
        - List of every SQL statement Django ran this request.
        - Use it to confirm how many queries fired and what they look like.
    """
    # s=SaleModel.objects.select_related('restaurant').filter(name_has_num|is_profit).values()
    # s=SaleModel.objects.select_related('restaurant').filter(name_has_num|is_profit).values()
    # print(s)
    # print(connection.queries)

    """
    ==================== ORDERING (.order_by) AND NULL HANDLING ====================

    .order_by('field')        -> ORDER BY field ASC
    .order_by('-field')       -> ORDER BY field DESC   (leading minus = DESC)

    Default behaviour for NULLs depends on the DB backend:
      - Postgres:  NULLs come LAST  in ASC, FIRST in DESC
      - SQLite/MySQL: NULLs come FIRST in ASC, LAST  in DESC
    If you care, be explicit using an F() expression with nulls_first / nulls_last.
    """
    # print(
    #     RestaurantModel.objects.order_by('capacity').values('name', 'capacity')
    # )

    """
    F('capacity').desc(nulls_last=True)
        - Order by capacity DESC, with NULL capacities at the END of the list.
        - Use F(...).asc(nulls_first=True) / .desc(nulls_last=True) whenever
          the position of NULL rows matters in the UI (e.g. don't show "no
          rating" restaurants at the top of a "best rated" page).
    """
    # print(
    #     RestaurantModel.objects.order_by(F('capacity').desc(nulls_last=True)).values('name', 'capacity')
    # )

    """
    Wipes every restaurant's capacity to NULL - used once to set up the
    Coalesce demo below. Leave it commented out so it doesn't run again.
    """
    # RestaurantModel.objects.update(capacity=None)

    """
    ==================== Coalesce — NULL FALLBACK ====================

    Coalesce(a, b, ...) -> first non-NULL value. Maps to SQL COALESCE().
    Mental rule: put the PREFERRED value first, the safe fallback last.

    Two classic uses:
      1. Aggregates on empty querysets (Sum/Avg/Max return None, not 0).
      2. "Show this if set, otherwise that" pattern on nullable columns.
    """

    """
    Case 1 — protecting an aggregate from None.

    aggregate(total=Coalesce(Sum('capacity'), 0))
        - If every capacity is NULL (or the queryset is empty),
          Sum('capacity') returns None.
        - Coalesce(..., 0) turns the None into 0 so `total + 10` won't crash.
    """
    # print(RestaurantModel.objects.aggregate(total=Coalesce(Sum('capacity'),0)))

    """
    Same pattern with Avg on a deliberately empty queryset
    (no rating is less than 0 - it's a PositiveSmallIntegerField).
    Without Coalesce, Avg returns None; with Coalesce we get 0.
    """
    # print(RatingModel.objects.filter(rating__lt=0).aggregate(total=Coalesce(Avg('rating'),0)))

    """
    Case 2 — "display name" pattern with annotate().

    Coalesce(F('nickname'), F('name'))
        - If nickname IS NOT NULL, use it.
        - Otherwise fall back to name (which is non-nullable, so this never
          collapses to NULL).

    Why .values('name','nickname','name_value') is needed:
        .annotate(name_value=...) computes name_value in SQL, but printing
        the queryset shows model __str__ output (just self.name). To see
        the annotated column you must either:
          - call .values(...) so each row becomes a dict, OR
          - iterate and print r.name_value for each row.
    """
    # print(
    #     RestaurantModel.objects
    #     .annotate(name_value=Coalesce(F('nickname'), F('name')))
    #     .values('name', 'nickname', 'name_value')
    # )

    """
    Inspect every SQL statement Django ran during this run() call.
    Great for confirming that .filter(...).aggregate(...) is one query,
    not N+1.
    """
    # print(connection.queries)

    # restaurants=RestaurantModel.objects.annotate(
    #     is_italian=Case(When(restaurant_type='IT', then=True), default=False),
    # ).values()
    # res=RestaurantModel.objects.annotate(nsales=Count('sales'))
    # res=res.annotate(is_popular=Case(
    #     When(nsales__gte=10, then=True),
    #     default=False
    # ))
    
    # print(res.values())

    # res=RestaurantModel.objects.annotate(
    #     avg=Avg('ratings__rating'),
       
    #     num_ratings=Count('ratings'),

    # )
    # res = res.annotate(
    #     rating_bucket=Case(
    #         When(avg__gte=4, then=Value('highly_rated')),
    #         When(avg__range=(2.5, 3.5), then=Value('Average Rating')),
    #         default=Value('not_highly_rated'),
           
    #     )
    # )


    # print(res.values())
    # print(connection.queries)

    """
    Approach 1: JOIN (via FK lookup `restaurant__restaurant_type`)

    Django builds ONE SQL query with an INNER JOIN:

        SELECT sale.* FROM sale
        INNER JOIN restaurant ON sale.restaurant_id = restaurant.id
        WHERE restaurant.restaurant_type IN ('IT','CH');

    - Walks the FK by joining the two tables.
    - Can produce duplicates if the joined side has multiple matching
      rows (use .distinct() to dedupe).
    - Idiomatic Django — preferred for simple FK filters, and when you
      also need fields from the related table.
    """
    # sales=SaleModel.objects.filter(restaurant__restaurant_type__in=['IT','CH'])
    # print(sales.values_list('restaurant__restaurant_type').distinct())

    """
    Approach 2: Subquery (via `restaurant__in=Subquery(...)`)

    Django builds a NESTED SQL query (no JOIN):

        SELECT sale.* FROM sale
        WHERE sale.restaurant_id IN (
            SELECT restaurant.id FROM restaurant
            WHERE restaurant.restaurant_type IN ('IT','CH')
        );

    - Inner query returns a list of restaurant ids; outer query filters
      sales by membership in that list.
    - Set-based IN, so no duplicate rows from the relationship.
    - Use when:
        * A JOIN would create duplicates (many-to-many / reverse FK).
        * You need correlation with OuterRef (e.g. "sales where amount >
          average for that restaurant").
        * The inner query is reusable or logically independent.

    Same result as Approach 1, different SQL shape.
    """
    # restaurants=RestaurantModel.objects.filter(restaurant_type__in=['IT','CH'])
    # sales=SaleModel.objects.filter(restaurant__in=Subquery(restaurants.values('id')))

    """
    ==================== CORRELATED SUBQUERY with OuterRef ====================

    Goal: for each restaurant, attach data from its MOST RECENT sale
    (last_sale_income, last_sale_expenditure) and compute profit from those.

    A plain JOIN can't do this on its own — it would give every sale per
    restaurant, not just the latest one. We need a subquery that returns
    exactly one row per outer restaurant.
    """

    """
    OUTER query — the rows we want to annotate.
    Each restaurant row will eventually get extra virtual columns
    (last_sale_income, last_sale_expenditure, profit) filled in by
    the subquery below.
    """
    # restaurants=RestaurantModel.objects.all()

    """
    INNER query TEMPLATE (a blueprint, not a runnable query).

    OuterRef('pk')
        - Placeholder for "the pk of the current OUTER row".
        - Resolved at SQL generation time to the outer restaurant's id.
        - Because of this placeholder, `sale` cannot be evaluated on its
          own — it only works wrapped in Subquery(...).

    .filter(restaurant=OuterRef('pk'))
        - WHERE sale.restaurant_id = <current restaurant.id>
        - Picks the sales belonging to the current outer restaurant.

    .order_by('-datetime')
        - Newest sale first, so combined with LIMIT 1 we get the LATEST sale.
    """
    # sale=SaleModel.objects.filter(restaurant=OuterRef('pk')).order_by('-datetime')

    """
    Activate the template by plugging it into the outer query via .annotate().

    Subquery(sale.values('income')[:1])
        - .values('income')  -> SELECT only the income column (Subquery must
                                 return exactly ONE column).
        - [:1]               -> LIMIT 1 (Subquery must return at most ONE row).
        - Combined with the ORDER BY in the template: "income of the most
          recent sale for this restaurant".

    Same trick reused for expenditure — one template, two scalar subqueries.

    profit=F('last_sale_income') - F('last_sale_expenditure')
        - F() references the annotated columns themselves (column-vs-column
          math, computed in SQL — not in Python).
        - Result: profit of that latest sale, exposed as another virtual column.
    """
    # restaurants=restaurants.annotate(
    #     last_sale_income=Subquery(sale.values('income')[:1]),
    #     last_sale_expenditure=Subquery(sale.values('expenditure')[:1]),
    #     profit=F('last_sale_income')-F('last_sale_expenditure')
    # )
  

    """
    Iterate to print the annotated values.

    Each `res` is a RestaurantModel instance with the extra attributes
    (last_sale_income, last_sale_expenditure, profit) attached because
    of the .annotate() above. They are not real model fields — they
    only exist on this queryset.
    """
    # for res in restaurants:
    #     print(res.last_sale_income)

    """
    connection.queries
        - Inspect the actual SQL Django ran.
        - You should see ONE outer SELECT on restaurant with the
          subqueries nested inline (not N+1 separate queries) — that's
          the whole point of doing this with Subquery instead of looping
          in Python.
    """
    # print(connection.queries)

    """
    ==================== Exists() — CORRELATED YES/NO SUBQUERY ====================

    Exists(qs) wraps a queryset and asks the database a BOOLEAN question:
        "Does the inner query find at least one row?"
            - TRUE  -> keep this outer row
            - FALSE -> drop it

    Maps to SQL EXISTS (...). The DB short-circuits — as soon as it finds
    ONE matching inner row, it returns TRUE and moves on.

    Exists vs Subquery — different jobs:
        Exists(qs)                       -> boolean       (does it exist?)
        Subquery(qs.values('col')[:1])   -> scalar value  (what's the value?)

    OuterRef is what makes Exists CORRELATED (per outer row). Without it,
    the inner query runs once globally — almost always a bug.
    """

    """
    Example A — "restaurants that have ANY sale with income > 85".

    OuterRef('pk') = current restaurant's id.
    Inner asks: "any sale belonging to THIS restaurant with income > 85?"
    Outer keeps the restaurant if YES.

    SQL:
        SELECT * FROM restaurant
        WHERE EXISTS (
            SELECT 1 FROM sale
            WHERE sale.restaurant_id = restaurant.id
              AND sale.income > 85
        );

    No .distinct() needed — Exists is a boolean per outer row, never
    duplicates rows the way a JOIN would.
    """
    # restaurants=RestaurantModel.objects.filter(
    #     Exists(SaleModel.objects.filter(restaurant=OuterRef('pk'),income__gt=85)
    #     )
    # )

    # print(restaurants)

    """
    Example B — "restaurants that had ANY sale in the last 5 days".

    Same pattern, different inner WHERE clause:
        - restaurant = OuterRef('pk')        -> link to outer row
        - datetime__gte = five_days_ago      -> recency filter

    SQL:
        SELECT * FROM restaurant
        WHERE EXISTS (
            SELECT 1 FROM sale
            WHERE sale.restaurant_id = restaurant.id
              AND sale.datetime >= <5 days ago>
        );

    To flip the question to "restaurants with NO sales in the last 5 days",
    just negate with ~Exists(...) -> WHERE NOT EXISTS (...).
    """
    # five_days_ago=timezone.now()-timezone.timedelta(days=5)
    # restaurants=RestaurantModel.objects.filter(
    #     Exists(SaleModel.objects.filter(restaurant=OuterRef('pk'),datetime__gte=five_days_ago)
    #     )
    # )

    # print(restaurants)

    """
    ==================== select_for_update() — ROW-LEVEL LOCKING ====================

    SQL:  SELECT ... FROM product WHERE name = 'Book' FOR UPDATE;

    While THIS transaction is open, Postgres places a write lock on the
    matching product row. Any OTHER transaction that tries to:
        - SELECT ... FOR UPDATE on the same row, or
        - UPDATE / DELETE the same row,
    will BLOCK and wait until we either COMMIT or ROLLBACK.

    Requires an open transaction — that's why it must be inside
    `with transaction.atomic():`. Outside a transaction, Django raises
    TransactionManagementError.

    How to SEE the lock in action:
        Open TWO `python manage.py shell` sessions.
        In session A, run this script (the sleep keeps the txn open 1s).
        Inside that 1s window, in session B run:
            from core.models import ProductModel
            ProductModel.objects.filter(name='Book').update(number_in_stock=99)
        Session B will block until session A's `with` block exits.

    Notes:
        - SQLite IGNORES select_for_update silently. Use Postgres for real demos.
        - Use sparingly — locks reduce concurrency. Only lock the rows you
          actually need to update.
    """
    with transaction.atomic():
        book=ProductModel.objects.select_for_update().get(name="Book")
        time.sleep(1)
