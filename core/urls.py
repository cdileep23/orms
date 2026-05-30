"""
URL routes for the core app.
"""
from django.urls import path
from core import views

urlpatterns = [
    # path('', views.index, name='index'),   # re-enable when an index view exists in core/views.py
    path('order/', views.order_product, name='order_product'),
]
