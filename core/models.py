from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator,MaxValueValidator
from django.core.exceptions import ValidationError

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
    class Meta():
        ordering=['date_opened']
        get_latest_by = 'date_opened'
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

    def __str__(self):
        return f"Rating {self.rating}"
    

class SaleModel(models.Model):
    restaurant=models.ForeignKey(RestaurantModel, on_delete=models.CASCADE,null=True,related_name='sales')
    datetime=models.DateTimeField()
    expenditure=models.DecimalField(max_digits=8,decimal_places=2,null=True)
    income=models.DecimalField(max_digits=8,decimal_places=2,default=0)

    def __str__(self):
        return f"Sale {self.income}"
    
class ProductModel(models.Model):
    name=models.CharField(max_length=100)
    number_in_stock=models.PositiveIntegerField(    )
    def __str__(self):
        return f"{self.name} {self.price}"
    
class OrderModel(models.Model):
    product=models.ForeignKey(ProductModel, on_delete=models.CASCADE)
    no_of_items=models.PositiveSmallIntegerField()

    def __str__(self):
        return f"{self.product.name} X {self.no_of_items}"
    



