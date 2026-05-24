from core.models import RestaurantModel, RatingModel,SaleModel,StaffModel,StaffRestaurantModel
from django.utils import timezone
from django.db import connection

from django.utils import timezone
from random import randint
from django.db.models.functions import Upper,Lower,Length,Concat

from django.db.models import Count,Avg,Min,Max,Sum,StdDev,Variance,CharField,Value

def run():
    """
    ==================== CREATING OBJECTS ====================
    """

    """
    .create(...) -> builds the object AND saves it to the DB in ONE step.
    Returns the saved object. Runs a single SQL INSERT.
    """

    """
    ============================================================
    HOW TO RUN THIS SCRIPT
    ============================================================
    'runscript' is NOT a built-in Django command - it comes from the
    third-party package 'django-extensions'.

    ONE-TIME SETUP:
      1. Install the package into the virtual environment:
             pip install django-extensions
      2. Register it in orms/settings.py -> INSTALLED_APPS:
             'django_extensions',

    THIS SCRIPT FILE MUST:
      - live in a 'scripts/' folder inside an app  (here: core/scripts/)
      - that 'scripts/' folder must contain an __init__.py file
      - define a function named run()
        -> runscript calls run(); any code outside run() is ignored

    RUN IT (pass the MODULE name, with NO '.py' extension):
             python manage.py runscript orm_script
    ============================================================
    """
    # restaurant = RestaurantModel.objects.create(
    #     name='Pappas Pizza',
    #     latitude=40.7128,
    #     longitude=-74.0060,
    #     date_opened=timezone.now(),
    # )

    """
    Manual way: make an empty instance, set fields, then call .save().
    Nothing hits the DB until .save() runs. Two steps instead of one.
    """
    # restaurant = RestaurantModel()
    # restaurant.name = "Burger King"
    # restaurant.latitude = "123"
    # restaurant.longitude = "456"
    # restaurant.date_opened = timezone.now()
    # restaurant.save()                 # <- THIS line runs the INSERT

    """
    ==================== READING / RETRIEVING ====================
    """

    """
    .all() -> every row in the table, as a QuerySet (a lazy collection).
    """
    # restaurants = RestaurantModel.objects.all()

    """
    [0] -> index/slice a QuerySet to pull one object (here, the 1st row).
    Raises IndexError if the table is empty.
    """
    # restaurants = RestaurantModel.objects.all()[0]

    """
    .first() -> the first row, or None if the table is empty (no error).
    """
    # restaurants = RestaurantModel.objects.first()

    """
    .count() -> how many rows, as an int. Uses SQL COUNT(*) (fast).
    """
    # restaurants = RestaurantModel.objects.count()

    """
    .last() -> the last row, or None if the table is empty.
    """
    # restaurants = RestaurantModel.objects.last()

    # print(restaurants)

    """
    connection.queries -> list of every SQL statement Django ran this run.
    Best tool for seeing what the ORM actually does under the hood.
    """
    # print(connection.queries)

    """
    ==================== CREATING A RELATED OBJECT ====================
    """

    # restaurant = RestaurantModel.objects.last()
    # user = User.objects.first()

    """
    .create() with ForeignKey fields -> pass the related OBJECTS directly
    (user=..., restaurant=...), not their ids.
    """
    # RatingModel.objects.create(user=user, restaurant=restaurant, rating=3)

    """
    ==================== FILTERING ====================
    """

    """
    .filter(field=value) -> all rows that MATCH the condition.
    Returns a QuerySet (could be 0, 1, or many rows).
    """
    # print(RatingModel.objects.filter(rating=5))

    """
    __lte -> a "field lookup" meaning "less than or equal to".
    Family: __lt, __lte, __gt, __gte, __contains, __in, ...
    """
    # print(RatingModel.objects.filter(rating__lte=5))

    """
    .exclude(field=value) -> the opposite of .filter():
    rows that do NOT match the condition.
    """
    # print(RatingModel.objects.exclude(rating=5))

    """
    ==================== UPDATING ====================
    """

    """
    Update = fetch a row, change an attribute, then .save() it again.
    Calling .save() on a row that already exists runs an UPDATE, not INSERT.
    """
    # restaurant = RestaurantModel.objects.all()[1]
    # restaurant.name = '99999'
    # restaurant.save()

    """
    ==================== FOLLOWING RELATIONSHIPS ====================
    """

    """
    FORWARD access: from the "many" side to the "one" side.
    rating.restaurant -> the single RestaurantModel this rating points to.
    """
    # rating = RatingModel.objects.first()
    # print(rating.restaurant)
    # print(connection.queries)

    # restaurant = RestaurantModel.objects.first()

    """
    REVERSE access WITHOUT related_name:
    Django's default reverse accessor is <modelname>_set, e.g. ratingmodel_set.
    (A ForeignKey is just a column - it does NOT create a separate table.)
    This line no longer works, because RatingModel now sets related_name.
    """
    # print(restaurant.ratingmodel_set.all())

    """
    REVERSE access WITH related_name='ratings' on RatingModel.restaurant:
    restaurant.ratings -> all RatingModel rows that point to this restaurant.
    """
    # print(restaurant.ratings.all())

    """
    CREATING SALES
    .objects.create() builds AND saves each row in one step (SQL INSERT).
    The ForeignKey MUST be passed by keyword: restaurant=restaurant
    (passing it positionally would land on the 'id' field instead).
    """
    # SaleModel.objects.create(restaurant=restaurant, datetime=timezone.now(), income=1000)
    # SaleModel.objects.create(restaurant=restaurant, datetime=timezone.now(), income=3000)
    # SaleModel.objects.create(restaurant=restaurant, datetime=timezone.now(), income=4000)

    """
    ==================== GET OR CREATE ====================
    """

    """
    First fetch the related objects we want to look up / link.
    .first() -> the first row of each table, or None if empty.
    """
    # user = User.objects.first()
    # restaurant = RestaurantModel.objects.first()

    """
    .get_or_create() -> tries to GET a row matching ALL the given fields.
    - If a matching row exists  -> returns it (no INSERT runs).
    - If no match is found      -> CREATES a new row.
    It returns a TUPLE: (object, created)
        created = True  -> a brand-new row was inserted
        created = False -> an existing row was found and returned
    Use it to avoid inserting duplicate rows.
    (Tip: a 'defaults={...}' argument sets values used ONLY on creation,
     keeping them out of the lookup.)
    """
    # print(RatingModel.objects.get_or_create(user=user, restaurant=restaurant, rating=3))

    """
    ==================== VALIDATION (full_clean) ====================
    """

    """
    KEY POINT: .save() does NOT run validation.
    It writes straight to the database and IGNORES the field validators
    (here: MinValueValidator(1) / MaxValueValidator(5) on rating).
    So 'rating=9' WOULD be saved silently, even though the model says 1-5.
    That is why "creating the object works" when you skip full_clean().

    .full_clean() is what actually validates. It runs:
      - the validators=[...] list on each field
      - field rules (max_length, choices, null, blank, ...)
      - the model's own clean() method
    If anything is invalid it raises a ValidationError BEFORE the save.

    Correct order: call .full_clean() FIRST, then .save() only if it passed.

    Why doesn't .save() validate on its own?
      - .save() is meant to be a direct, fast DB write - nothing more.
      - Validation is a separate step. Django ModelForms and DRF
        serializers call .full_clean() FOR you - that is why web forms
        reject bad input automatically. A plain script has no form,
        so YOU must call .full_clean() yourself.

    NOTE: rating=9 below breaks MaxValueValidator(5), so .full_clean()
    will raise a ValidationError here on purpose - that is the demo.
    """
    # Rating=RatingModel(user=user,restaurant=restaurant,rating=9)
    # Rating.full_clean()
    # Rating.save()

    # print(restaurant.name)
    # restaurant.name="New Restaurant 1"
    """ 
    This is like put kind of operation where all the fields are updated
    """

    #  restaurant.save()

    """
    This is like PATCH kind of operation where only the fields are updated
    """
    # restaurant.save(update_fields=['name'])

   
    # print(connection.queries)

# [{'sql': 'SELECT "core_restaurantmodel"."id", "core_restaurantmodel"."restaurant_type", "core_restaurantmodel"."name", "core_restaurantmodel"."website", "core_restaurantmodel"."date_opened", "core_restaurantmodel"."latitude", "core_restaurantmodel"."longitude" FROM "core_restaurantmodel" ORDER BY "core_restaurantmodel"."id" ASC LIMIT 1', 'time': '0.000'}, {'sql': 'SELECT "core_restaurantmodel"."id", "core_restaurantmodel"."restaurant_type", "core_restaurantmodel"."name", "core_restaurantmodel"."website", "core_restaurantmodel"."date_opened", "core_restaurantmodel"."latitude", "core_restaurantmodel"."longitude" FROM "core_restaurantmodel" ORDER BY "core_restaurantmodel"."id" ASC LIMIT 1', 'time': '0.000'}, {'sql': 'UPDATE "core_restaurantmodel" SET "restaurant_type" = \'IN\', "name" = \'New Restaurant 1\', "website" = \'\', "date_opened" = \'1980-01-01\', "latitude" = 99999.0, "longitude" = -74.006 WHERE "core_restaurantmodel"."id" = 1', 'time': '0.000'}]
# [{'sql': 'SELECT "core_restaurantmodel"."id", "core_restaurantmodel"."restaurant_type", "core_restaurantmodel"."name", "core_restaurantmodel"."website", "core_restaurantmodel"."date_opened", "core_restaurantmodel"."latitude", "core_restaurantmodel"."longitude" FROM "core_restaurantmodel" ORDER BY "core_restaurantmodel"."id" ASC LIMIT 1', 'time': '0.000'}, {'sql': 'SELECT "core_restaurantmodel"."id", "core_restaurantmodel"."restaurant_type", "core_restaurantmodel"."name", "core_restaurantmodel"."website", "core_restaurantmodel"."date_opened", "core_restaurantmodel"."latitude", "core_restaurantmodel"."longitude" FROM "core_restaurantmodel" ORDER BY "core_restaurantmodel"."id" ASC LIMIT 1', 'time': '0.000'}, {'sql': 'UPDATE "core_restaurantmodel" SET "restaurant_type" = \'IN\', "name" = \'New Restaurant 1\', "website" = \'\', "date_opened" = \'1980-01-01\', "latitude" = 99999.0, "longitude" = -74.006 WHERE "core_restaurantmodel"."id" = 1', 'time': '0.000'}]
   
    # print(connection.queries)

    """
    Filter down only chinese restaurants in the database
    """
    # chinese_restaurants=RestaurantModel.objects.filter(name="Pizzeria 1")
    
    # print(chinese_restaurants)
    # print(chinese_restaurants.get())

    """
    exists function django orm
    """

    # italian_restaurants=RestaurantModel.objects.filter(restaurant_type=RestaurantModel.TypeChoices.ITALIAN)
    # print(italian_restaurants.exists())

    """
    multiple conditions in django or using where operation in sql
    """
   
    # chinese_restaurants=RestaurantModel.objects.filter(restaurant_type=RestaurantModel.TypeChoices.CHINESE, name__startswith="Chinese")

    # print(chinese_restaurants)
    # print(connection.queries)

    # chinese=RestaurantModel.TypeChoices.CHINESE
    # indian=RestaurantModel.TypeChoices.INDIAN
    # italian=RestaurantModel.TypeChoices.ITALIAN

    # check_types=[chinese,indian,italian]
    # restaurants=RestaurantModel.objects.filter(restaurant_type__in=check_types)
    # print(restaurants)
    # print(connection.queries)
    

    """
    Not condition in django
    """
    # chinese=RestaurantModel.TypeChoices.CHINESE
    # restaurants=RestaurantModel.objects.exclude(restaurant_type=chinese)
    # print(restaurants)
    # print(connection.queries)

    """
    lt and gt ,lte,gte lookup in django
    """

    # restaurants=RestaurantModel.objects.filter(restaurant_type__lt=RestaurantModel.TypeChoices.CHINESE)
    # print(restaurants)
    # print(connection.queries)


    """
    order_by lookup in django
    """
    # restaurants=RestaurantModel.objects.order_by('name').reverse()
    # restaurants=RestaurantModel.objects.order_by('name')
    # restaurants=RestaurantModel.objects.order_by('-name')
    # print(restaurants)
    # print(connection.queries)
   
    """
    Lower function in django models

    """

    # restaurants=RestaurantModel.objects.order_by(Lower('name'))
    # print(restaurants)
    # print(connection.queries)


    """
    Indexing slicing in django orm
    """

    # restaurants=RestaurantModel.objects.order_by('date_opened')[2:5]
    # print(restaurants)
    # print(connection.queries)

    """
    Earliest & latest in django orm
    """

    # restaurant=RestaurantModel.objects.latest('date_opened')
    # restaurant=RestaurantModel.objects.earliest('date_opened')
    # print(restaurant)
    # print(connection.queries)

    """
    Find all the ratings for a restaurant starts with "CH"

    when we do filter on foreign key django is going to do a join
    """

    # ratings=RatingModel.objects.filter(restaurant__name__startswith="CH")
    # print(ratings)
    # print(connection.queries)

    """
      Find all the sales for a restaurant starts with "CH"

      when we do filter on foreign key django is going to do a join
    """

    # sales=SaleModel.objects.filter(restaurant__name__startswith="CH")
    # print(sales)
    # print(connection.queries)

    """
    Many-to-Many CRUD on `StaffModel.restaurants` (M2M to RestaurantModel,
    reverse name `staff`). With an M2M, Django creates a hidden "through"
    table — e.g. `core_staffmodel_restaurants(id, staffmodel_id, restaurantmodel_id)`
    — and `staff.restaurants` is a *manager* that reads/writes that table.

    Common manager methods on an M2M:
      .add(*objs)        → INSERT links (ignores duplicates)
      .remove(*objs)     → DELETE specific links (objs stay in their own tables)
      .clear()           → DELETE all links for this side
      .set(iterable)     → make the link set equal to iterable (add+remove diff)
      .all()             → QuerySet of the related objects (SELECT via JOIN)
      .count()           → COUNT linked rows (one query, no Python loop)
      .create(**fields)  → create the related object AND link it in one step
      .filter() / .exclude() / .order_by() / .annotate()
                         → behave like any normal QuerySet, just scoped to the linked set
    """

    """
    get_or_create returns (object, created_flag).
      - If a StaffModel with name="John Doe" exists → fetch it, created=False.
      - Else → INSERT a new one, created=True.
    Avoids the "look up first, then insert if missing" race / boilerplate.
    """
    # staff,created=StaffModel.objects.get_or_create(name="John Doe")

    """
    .set(qs) replaces the entire link set for this staff:
      - Diff = (new links to add) + (old links to remove).
      - Issues INSERTs and DELETEs on the through table only — the
        Restaurant rows themselves are never touched.
    Here we link John Doe to the first 10 restaurants (in the model's
    default ordering, which on RestaurantModel is by `date_opened`).
    """
    # staff.restaurants.set(RestaurantModel.objects.all()[:10])

    """
    Filter the M2M like a normal QuerySet — narrowed to restaurants
    linked to THIS staff member. SQL is roughly:
      SELECT restaurant.* FROM core_restaurantmodel restaurant
      INNER JOIN core_staffmodel_restaurants link
          ON link.restaurantmodel_id = restaurant.id
      WHERE link.staffmodel_id = <staff.id>
        AND restaurant.restaurant_type = 'IT';
    So we only get Italian restaurants that John Doe is linked to.
    """
    # r=staff.restaurants.filter(restaurant_type="IT")


    # print(r)

    # restaurant=RestaurantModel.objects.get(pk=22)

    # print(restaurant.staff.all())

    """
    M2M WITH A CUSTOM "THROUGH" MODEL
    ---------------------------------
    StaffModel.restaurants is declared as:
        restaurants = ManyToManyField(RestaurantModel, through='StaffRestaurantModel')

    The `through=` tells Django: "don't auto-create the link table, I want
    my own model so I can store EXTRA columns on the link itself".
    Here the extra column is `salary` — i.e. each (staff, restaurant) link
    also carries how much that staff earns at that restaurant.

    Tables created:
        core_staffmodel              (id, name)
        core_restaurantmodel         (id, name, ...)
        core_staffrestaurantmodel    (id, staff_id, restaurant_id, salary)
                                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                      the "through" / link table — Django
                                      does NOT make a hidden one because
                                      WE provided it explicitly.

    Important consequence of using `through`:
        staff.restaurants.add(r), .remove(r), .set([...]), .create(...)
        are DISABLED (Django can't fill `salary` for you).
        You MUST create the link by inserting a StaffRestaurantModel row
        directly, as we do below.

    .get(name="John Doe")
        Returns the single StaffModel instance. Unlike .filter() (which
        returns a QuerySet), .get() returns the object itself — required
        for FK assignment. Raises DoesNotExist / MultipleObjectsReturned
        if 0 or >1 rows match.
    """
    # staff = StaffModel.objects.get(name="John Doe")
    # restaurant1 = RestaurantModel.objects.first()
    # restaurant2 = RestaurantModel.objects.last()

    """
    Insert TWO rows in the through table — one per (staff, restaurant) link,
    each with its own salary. Each .create() runs an INSERT against
    core_staffrestaurantmodel only; the staff and restaurant rows are
    untouched.
    """
    # res = StaffRestaurantModel.objects.create(staff=staff, restaurant=restaurant1, salary=10000)
    # res2 = StaffRestaurantModel.objects.create(staff=staff, restaurant=restaurant2, salary=40000)
    
    # staff=StaffModel.objects.get(name="John Doe")
    # restaurant=RestaurantModel.objects.get(pk=12)
    # print(restaurant)
    # staff.restaurants.add(restaurant,through_defaults={'salary':58000})



    # staff,created=StaffModel.objects.get_or_create(name="John wick")
    # staff.restaurants.set(RestaurantModel.objects.all()[:10],through_defaults={'salary':randint(22222,33333)})

    """
    .values(...) with a COMPUTED FIELD using a database function (Upper).

    Two things to understand here:

    1) .values() vs normal QuerySet
       - Normal: RestaurantModel.objects.all() -> QuerySet of model INSTANCES
                 (you get RestaurantModel objects with .name, .latitude, etc.)
       - .values(): QuerySet of DICTS, one dict per row.
                 You give it the columns you want; it returns only those.
       Example without args: RestaurantModel.objects.values('id','name')
                 -> [{'id': 1, 'name': 'X'}, {'id': 2, 'name': 'Y'}, ...]

    2) Upper('name') is a "database function" expression
       - Lives in django.db.models.functions (alongside Lower, Length, Concat, ...).
       - Tells the DB to compute SQL: UPPER("core_restaurantmodel"."name")
         and return that value — no Python uppercasing.
       - When passed as a KEYWORD argument to .values() (or .annotate()),
         the keyword becomes the column ALIAS in the resulting dict.

    So `values(name_uper=Upper('name'))` is the same shape as:
         SELECT UPPER("core_restaurantmodel"."name") AS "name_uper"
         FROM   "core_restaurantmodel"
         LIMIT  1;                              -- because of .first()

    Returned object:
         {'name_uper': 'PAPPAS PIZZA'}          # a plain dict, not a model

    .first()  -> takes the first row (or None if the table is empty).
    Note the alias 'name_uper' is missing a 'p' — it's just a label, so
    Django won't complain; you'll just have to spell it the same way later.
    """
    # restaurant=RestaurantModel.objects.values(name_uper=Upper('name'),).first()

    """
    connection.queries -> list of dicts: {'sql': '...', 'time': '...'} for
    every query Django ran this process. Only populated when DEBUG=True.
    Great for confirming the exact SQL Django generated.
    """
    # print(connection.queries)


    """
    .values('rating','restaurant__name') -> QuerySet of DICTS.

    Building blocks:

    1) RestaurantModel.TypeChoices.ITALIAN
       - This is a TextChoices enum on the model. Its `.value` is 'IT'
         (the stored DB code). Using the enum is safer than typing 'IT'
         everywhere — Python yells if you typo the name, not the string.

    2) .filter(restaurant__restaurant_type=IT)
       - `restaurant__restaurant_type` is a "lookup through a relation":
         "follow the FK `restaurant`, then check its `restaurant_type` column".
       - Django turns this into an INNER JOIN to core_restaurantmodel and
         a WHERE clause: WHERE core_restaurantmodel.restaurant_type = 'IT'.

    3) .values('rating', 'restaurant__name')
       - Returns dicts instead of model instances.
       - Each dict has exactly the keys you asked for. The dotted-with-__
         path becomes a flat key in the dict.
       - Example output:
           <QuerySet [
             {'rating': 5, 'restaurant__name': "Mario's"},
             {'rating': 3, 'restaurant__name': "Luigi's"},
             ...
           ]>
       - Why use this? Cheaper than fetching full model instances when
         you only need a few columns; great for JSON responses, CSVs, etc.

    SQL produced (roughly):
        SELECT  "core_ratingmodel"."rating",
                "core_restaurantmodel"."name"
        FROM    "core_ratingmodel"
        INNER JOIN "core_restaurantmodel"
                ON "core_ratingmodel"."restaurant_id" = "core_restaurantmodel"."id"
        WHERE   "core_restaurantmodel"."restaurant_type" = 'IT';
    """
    # IT=RestaurantModel.TypeChoices.ITALIAN
    # ratings=RatingModel.objects.filter(restaurant__restaurant_type=IT).values('rating','restaurant__name')
    # print(ratings)
    # print(connection.queries)

    """
    .values_list('restaurant__name', flat=True) -> QuerySet of plain values.

    Same JOIN + WHERE as above, but the output shape is different:

      .values('restaurant__name')          -> [{'restaurant__name': 'X'}, ...]
      .values_list('restaurant__name')     -> [('X',), ('Y',), ...]     (tuples)
      .values_list('restaurant__name',
                   flat=True)              -> ['X', 'Y', ...]           (plain strings)

    `flat=True` is only allowed when you ask for EXACTLY ONE column —
    Django strips the 1-tuple wrapper so you get bare values.
    Useful when feeding a list of IDs/names into another query
    (e.g. Other.objects.filter(name__in=ratings)).

    Result here:
        <QuerySet ["Mario's", "Luigi's", "Mario's", ...]>
        Duplicates are kept — one row per matching RATING, not per restaurant.
        Add .distinct() if you want unique restaurant names.
    """
    # IT=RestaurantModel.TypeChoices.ITALIAN
    # ratings=RatingModel.objects.filter(restaurant__restaurant_type=IT).values_list('restaurant__name',flat=True)
    # print(ratings)
    # print(connection.queries)

    """
    .count()  -> shortcut that returns the row count as a plain Python int.

    Returns:
        14

    SQL run:
        SELECT COUNT(*) AS "__count"
        FROM   "core_restaurantmodel";

    - COUNT(*) counts every row, including ones with NULLs.
    - Single round-trip to the DB; never loads rows into Python.
    - Use this when you just need "how many?". It's the most concise option.
    """
    # print(RestaurantModel.objects.count())

    """
    .aggregate(Count('id')) -> returns a DICT of aggregate results.

    Returns:
        {'id__count': 14}
        ^^^^^^^^^^         dict key = '<field>__<aggregate-lowercase>'
                           (Django auto-generates this alias.)

    SQL run:
        SELECT COUNT("core_restaurantmodel"."id") AS "id__count"
        FROM   "core_restaurantmodel";

    Differences vs .count():
      - .count() always returns an int.
        .aggregate(...) always returns a dict (so you can compute multiple
        aggregates in one query, each as its own key).
      - .count() does COUNT(*). .aggregate(Count('id')) does COUNT(id),
        which would skip rows where id is NULL — for a PK column this is
        identical to COUNT(*), so no practical difference here.
      - .aggregate() is the general tool: any Count / Sum / Avg / Min / Max
        / StdDev / Variance — and you can combine them:

            RestaurantModel.objects.aggregate(
                total=Count('id'),
                avg_rating=Avg('ratings__rating'),
            )
        -> {'total': 14, 'avg_rating': 4.07}

    Rename the alias yourself with a keyword:
        .aggregate(total=Count('id'))   -> {'total': 14}
    """
    # print(RestaurantModel.objects.aggregate(total=Count('id')))
    # print(connection.queries)


   
    """
    AGGREGATE ACROSS A RELATION + FILTER FIRST

    "Average rating for restaurants whose name starts with 'c'."

    Step-by-step:
      .filter(restaurant__name__startswith='c')
          - Follows the FK `restaurant`, then checks `name LIKE 'c%'`
            (case-sensitive). Translates to an INNER JOIN + WHERE.
            Use `__istartswith` if you want case-insensitive ('c' or 'C').
      .aggregate(avg_rating=Avg('rating'))
          - Computes AVG over the FILTERED rows.
          - Keyword `avg_rating=` renames the dict key (otherwise it
            would be 'rating__avg').

    Returns:
        {'avg_rating': 3.42}     # one dict, not a queryset

    SQL run:
        SELECT AVG("core_ratingmodel"."rating") AS "avg_rating"
        FROM   "core_ratingmodel"
        INNER JOIN "core_restaurantmodel"
                ON "core_ratingmodel"."restaurant_id" = "core_restaurantmodel"."id"
        WHERE  "core_restaurantmodel"."name" LIKE 'c%';
    """
    # r=RatingModel.objects.filter(restaurant__name__startswith='c').aggregate(avg_rating=Avg('rating'))


    """
    MULTIPLE AGGREGATES IN ONE QUERY (entire table)

    .aggregate() accepts many keyword aggregates in a single call — they
    are computed in ONE round-trip to the DB, returning a single dict.

    Returns:
        {'min': 1000.0, 'max': 9999.0, 'avg': 4233.7, 'sum': 59271.0}

    SQL run:
        SELECT MIN("income") AS "min",
               MAX("income") AS "max",
               AVG("income") AS "avg",
               SUM("income") AS "sum"
        FROM   "core_salemodel";
    """
    # print(SaleModel.objects.aggregate(min=Min('income'),max=Max('income'),avg=Avg('income'),sum=Sum('income')))
    # print(connection.queries)

    """
    FILTER THEN AGGREGATE (last 30 days of sales)

    Order matters: .filter() FIRST narrows the rows; .aggregate() AFTER
    sees only those filtered rows. So min/max/avg/sum are computed over
    sales whose datetime is within the last 30 days.

    `timezone.now() - timezone.timedelta(days=30)` is the cutoff datetime
    (timezone-aware because we used django.utils.timezone, not
    datetime.now() — important when USE_TZ=True in settings).

    `datetime__gte=one_month`  -> WHERE datetime >= <cutoff>.

    Returns:
        {'min': 1200.0, 'max': 9800.0, 'avg': 4500.5, 'sum': 22500.0}
        (None for each key if no rows match the filter — be ready for nulls.)

    SQL run:
        SELECT MIN("income") AS "min",
               MAX("income") AS "max",
               AVG("income") AS "avg",
               SUM("income") AS "sum"
        FROM   "core_salemodel"
        WHERE  "datetime" >= '<one_month_ago>';

    Still ONE query — both the WHERE and the four aggregates are in the
    same statement.
    """
    # one_month=timezone.now()-timezone.timedelta(days=30)
    # sale=SaleModel.objects.filter(datetime__gte=one_month)
    # print(sale.aggregate(min=Min('income'),max=Max('income'),avg=Avg('income'),sum=Sum('income')))


    """
    annotation concept
    """

    # restaurants=RestaurantModel.objects.annotate(len_name=Length('name')).values('name','len_name').filter(len_name__gte=10)
    # print(restaurants)

    # concatenation=Concat('name',Value(' [Rating: '),Avg('ratings__rating'),Value(']'),output_field=CharField())
    # restaurants=RestaurantModel.objects.annotate(concatenation=concatenation).values('name','concatenation')
    # for r in restaurants:
    #   print(r)

    # sales1=Concat('name', Value(' [Sales: '),Count('sales'),Value(']'),output_field=CharField())
    # totalsales=RestaurantModel.objects.annotate(a=sales1).values('name','a')
    # for r in totalsales:
    #   print(r)

    # restaurants=RestaurantModel.objects.annotate(sum=Sum('sales__income')).values('name','sum')
    # for r in restaurants:
    #     print(r)
    restaurants=RestaurantModel.objects.annotate(num_ratings=Avg('ratings')).values('name','num_ratings')
    for r in restaurants:
        print(r)
    print(connection.queries)