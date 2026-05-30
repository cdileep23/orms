from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator,MaxValueValidator
from django.core.exceptions import ValidationError
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey,GenericRelation
from django.db.models import Q,CheckConstraint,UniqueConstraint
from django.db.models.functions import Lower
"""
Models required for the project

Restaurant 
User
Rating


"""

def validate_restaurant_name(value):
    if value.startswith('Z'):
        raise ValidationError('Cannot start with Z')

class RestaurantModel(models.Model):
    class TypeChoices(models.TextChoices):
        INDIAN='IN', 'Indian'
        CHINESE='CH', 'Chinese'
        ITALIAN='IT', 'Italian'
        GREEK='GR', 'Greek'
        MEXICAN='MX', 'Mexican'
        OTHER='OT', 'Other'
    restaurant_type=models.CharField(max_length=2,choices=TypeChoices.choices,default=TypeChoices.INDIAN)
    name=models.CharField(max_length=100,validators=[validate_restaurant_name])
    website=models.URLField(default='')
    date_opened=models.DateField()
    latitude=models.FloatField(validators=[MinValueValidator(-90),MaxValueValidator(90)])
    longitude=models.FloatField(validators=[MinValueValidator(-180),MaxValueValidator(180)])
    capacity=models.PositiveSmallIntegerField(null=True,blank=True)
    nickname=models.CharField(max_length=100, null=True, blank=True)
    comments=GenericRelation('core.CommentModel',related_query_name='restaurant')
    class Meta():
        ordering=['date_opened']
        get_latest_by = 'date_opened'
        constraints=[
          models.CheckConstraint(  name='latitude_range',
            condition=Q(latitude__range=(-90,90)),
            violation_error_message="Latitude should be between -90 and 90"
            ),
          models.CheckConstraint(  name='longitude_range',
            condition=Q(longitude__range=(-180,180)),
            violation_error_message="Longitude should be between -180 and 180"
            ),
            models.UniqueConstraint(
                Lower('name'),
                name='check_name_unique_constraints'
            )


        ]
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        print(self._state)
        super().save(*args, **kwargs)


class StaffModel(models.Model):

    name=models.CharField(max_length=100)
    restaurants=models.ManyToManyField(RestaurantModel,through='StaffRestaurantModel')
    def __str__(self):
        return self.name
    

class StaffRestaurantModel(models.Model):
    staff=models.ForeignKey(StaffModel, on_delete=models.CASCADE)
    restaurant=models.ForeignKey(RestaurantModel, on_delete=models.CASCADE)
    salary=models.FloatField(null=True)

    def __str__(self):
        return f"{self.staff} {self.restaurant}"
    
class RatingModel(models.Model):
    user=models.ForeignKey(User,on_delete=models.CASCADE)
    # to reverse relationship we need to pass related name
    restaurant=models.ForeignKey(RestaurantModel, on_delete=models.CASCADE,related_name='ratings')
    rating=models.PositiveSmallIntegerField(validators=[MinValueValidator(1),MaxValueValidator(5)])
    comments=GenericRelation('core.CommentModel')

    def __str__(self):
        return f"Rating {self.rating}"
    
    class Meta:
        constraints=[
            models.CheckConstraint(
                name='rating_range',
                condition=Q(rating__range=(1,5)),
                violation_error_message='Rating should be between 1 and 5'
            ),
            models.UniqueConstraint(
                fields=['user', 'restaurant'],
                name='unique_rating_per_user_per_restaurant'
            )
        ]
    

class SaleModel(models.Model):
    restaurant=models.ForeignKey(RestaurantModel, on_delete=models.CASCADE,null=True,related_name='sales')
    datetime=models.DateTimeField()
    expenditure=models.DecimalField(max_digits=8,decimal_places=2,null=True)
    income=models.DecimalField(max_digits=8,decimal_places=2,default=0)

    def __str__(self):
        return f"Sale {self.income}"
    
class ProductModel(models.Model):
    name=models.CharField(max_length=100)
    number_in_stock=models.PositiveIntegerField()
    def __str__(self):
        return f"{self.name} ({self.number_in_stock} in stock)"
    
class OrderModel(models.Model):
    product=models.ForeignKey(ProductModel, on_delete=models.CASCADE)
    no_of_items=models.PositiveSmallIntegerField()

    def __str__(self):
        return f"{self.product.name} X {self.no_of_items}"
    
class CommentModel(models.Model):
    text=models.TextField()
    content_type=models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id=models.PositiveIntegerField()
    content_object=GenericForeignKey('content_type','object_id')



