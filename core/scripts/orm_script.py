from core.models import RestaurantModel, RatingModel,SaleModel
from django.utils import timezone
from django.db import connection
from django.contrib.auth.models import User
from django.db.models.functions import Lower


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

    sales=SaleModel.objects.filter(restaurant__name__startswith="CH")
    print(sales)
    print(connection.queries)



    
