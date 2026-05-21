from django.contrib import admin
from .models  import RestaurantModel,SaleModel,RatingModel
# Register your models here.
admin.site.register(RestaurantModel)
admin.site.register(SaleModel)
admin.site.register(RatingModel)