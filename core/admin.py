from django.contrib import admin
from .models  import RestaurantModel,SaleModel,RatingModel,ProductModel,OrderModel,CommentModel
# Register your models here.
from django.contrib.contenttypes.admin import GenericTabularInline

class CommentInLine(GenericTabularInline):
    model = CommentModel
    max_num=1
class RestaurantAdmin(admin.ModelAdmin):
    list_display=['name','id']
    inlines=[CommentInLine]
admin.site.register(RestaurantModel, RestaurantAdmin)
admin.site.register(SaleModel)


class RatingAdminModel(admin.ModelAdmin):
    list_display=['restaurant','rating','id']


admin.site.register(RatingModel,RatingAdminModel)

class CommentAdminModel(admin.ModelAdmin):
    list_display=['text','object_id','content_object','content_type']

   

admin.site.register(CommentModel, CommentAdminModel)
admin.site.register(ProductModel)
admin.site.register(OrderModel)