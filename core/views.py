from django.shortcuts import render
from core.models import RestaurantModel,RatingModel,SaleModel,StaffModel,StaffRestaurantModel
from django.db.models.functions import Lower
from django.db.models import Sum,Prefetch
# Create your views here.
from django.utils import timezone
# def index(request):
#     """
#     Fetch all restaurants + their ratings.
#     Runs 2 SQL queries total:
#       1. SELECT * FROM core_restaurantmodel;
#       2. SELECT * FROM core_ratingmodel WHERE restaurant_id IN (...);
#     Django then groups ratings per restaurant in Python and caches them on
#     each instance under `_prefetched_objects_cache['ratings']`, so accessing
#     `r.ratings.all` in the template hits the cache, not the DB.
#     """
#     # restaurant=RestaurantModel.objects.prefetch_related('ratings')

#     """
#     Same as above, but also prefetch each restaurant's sales.
#     prefetch_related can take multiple relation names; each one fires ONE
#     extra SQL query. Total = 3 queries (restaurants, ratings, sales).
#     Use this when the template touches both `r.ratings.all` and `r.sales.all`.
#     """
#     # restaurant=RestaurantModel.objects.prefetch_related('ratings','sales')

#     """
#     Filter BEFORE prefetching.
#     `filter(name__istartswith='C')` narrows the restaurants to those whose
#     name starts with 'C' (case-insensitive). The follow-up prefetch then
#     only loads ratings/sales for THAT smaller set, because the second
#     query uses `WHERE restaurant_id IN (<filtered ids>)`.
#     Order matters: always `.filter(...).prefetch_related(...)` so the
#     prefetch sees the narrowed PK list, not the full table.
#     """
#     # restaurant=RestaurantModel.objects.filter(name__istartswith='C').prefetch_related('ratings','sales')

#     # context={
#     #     'restaurant':restaurant
#     # }

#     """
#     Query Ratings directly and JOIN the parent restaurant in one SQL query.
#     `select_related('restaurant')` does an INNER JOIN, so `rt.restaurant.name`
#     in the template costs ZERO extra queries.
#     Used when the template iterates ratings (not restaurants).
#     """
#     # ratings=RatingModel.objects.select_related('restaurant')

#     """
#     Same as above, but only pull the columns we actually need.
#     `only('rating','restaurant__name')` tells Django to SELECT just
#     `ratingmodel.rating` and the joined `restaurantmodel.name`, plus the
#     PKs needed to wire them up. Other fields become "deferred" — accessing
#     them later would trigger an extra query per row.
#     Use this when the table is wide and you only render a few columns.
#     """
#     # ratings=RatingModel.objects.only('rating','restaurant__name').select_related('restaurant')

#     # context={
#     #     'ratings':ratings
#     # }

#     """
#     Show restaurants that have at least one 5-star rating, plus a `total`
#     column = lifetime SUM of every sale's income for each restaurant.

#     Breakdown of the chain:
#       .prefetch_related('ratings','sales')
#           - Loads ALL ratings and ALL sales for the matching restaurants
#             in 2 follow-up queries (one per relation). Used by the template
#             so `r.ratings.all` and `r.sales.all` don't trigger N+1.

#       .filter(ratings__rating=5)
#           - INNER JOINs `core_ratingmodel` in the main query just to test
#             existence: keep a restaurant if it has at least one rating=5.
#           - Side effect: a restaurant with N five-star ratings appears N
#             times in the raw join. Add `.distinct()` if you want unique
#             rows. (The annotate below adds a GROUP BY which incidentally
#             dedupes here, but don't rely on that in general.)

#       .annotate(total=Sum('sales__income'))
#           - Adds another LEFT OUTER JOIN to `core_salemodel` in the SAME
#             main query, then SUMs income per restaurant and exposes it as
#             `r.total`. Forces a `GROUP BY core_restaurantmodel.*`.
#           - This SUM is independent of the `sales` prefetch — they're two
#             different SQL paths. So `total` counts ALL sales ever, even
#             if you later swap the prefetch to a filtered one.

#     Query count: 3
#       1. restaurants (INNER JOIN ratings for filter, LEFT JOIN sales for SUM, GROUP BY)
#       2. ratings   WHERE restaurant_id IN (...)
#       3. sales     WHERE restaurant_id IN (...)
#     """
#     # restaurants=RestaurantModel.objects.prefetch_related('ratings','sales')\
#     # .filter(ratings__rating=5)\
#     # .annotate(total=Sum('sales__income'))
    


#     """
#     Show restaurants that have at least one 5-star rating, with:
#       - ALL their ratings prefetched (for display in the template)
#       - ONLY their last-30-days sales prefetched (filtered prefetch)
#       - A total `total` = SUM of ALL their sales income (annotation,
#         not affected by the prefetch filter — these are independent paths).

#     Key idea — `Prefetch(...)` customizes a prefetch_related call:
#       - Plain `'sales'` would prefetch every sale for each restaurant.
#       - `Prefetch('sales', queryset=...)` lets us hand Django a custom
#         queryset, so the second SQL query becomes:
#             SELECT * FROM core_salemodel
#             WHERE restaurant_id IN (...) AND datetime >= <month_ago>;
#         Django still groups results in Python and attaches them to each
#         restaurant's `_prefetched_objects_cache['sales']`, so
#         `r.sales.all` in the template returns only recent sales.

#     Important gotcha — the `.annotate(total=Sum('sales__income'))` uses
#     a SEPARATE JOIN to sales inside the main query. It is NOT influenced
#     by the `Prefetch` filter above. So `total` is the lifetime income,
#     while `r.sales.all` shows only the past 30 days. If you wanted the
#     annotation to also be limited to 30 days, you'd need a conditional
#     Sum with `filter=Q(sales__datetime__gte=month_ago)`.

#     Query count: 3
#       1. restaurants (with INNER JOIN ratings for the filter + JOIN sales for the SUM, grouped)
#       2. ratings   WHERE restaurant_id IN (...)
#       3. sales     WHERE restaurant_id IN (...) AND datetime >= month_ago
#     """
#     month_ago=timezone.now()-timezone.timedelta(days=30)

#     monthly_sales=Prefetch(
#         'sales',queryset=SaleModel.objects.filter(datetime__gte=month_ago)
#     )
#     restaurants=RestaurantModel.objects.prefetch_related('ratings',monthly_sales)\
#     .filter(ratings__rating=5).annotate(total=Sum('sales__income'))

#     context={
#         'restaurants':restaurants
#     }
#     # print(restaurants)
#     return render(request,'index.html',context)


def index(request):
    jobs=StaffRestaurantModel.objects.prefetch_related('restaurant','staff')

    for job in jobs:
        print(job.staff.name)
        print(job.restaurant.name)
        print(job.salary)

    return render(request,'index.html')