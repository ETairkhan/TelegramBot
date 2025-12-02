from django.urls import path
from . import views
from .views import api_token_login

urlpatterns = [
    path('api/users/', views.UserList.as_view(), name='user_list'),
    path('api/user/<int:pk>/', views.UserDetail.as_view(), name='user_detail'),
    path('api/user/create/', views.UserCreate.as_view(), name='user_create'),
    path('api/user/<int:pk>/edit/', views.UserUpdate.as_view(), name='user_update'),
    path('api/user/<int:pk>/delete/', views.UserDelete.as_view(), name='user_delete'),

    path('api/items/', views.ItemList.as_view(), name='item_list'),
    path('api/items/<int:pk>/', views.ItemDetail.as_view(), name='item_detail'),
    path('api/items/create/', views.ItemCreate.as_view(), name='item_create'),
    path('api/items/<int:pk>/edit/', views.ItemUpdate.as_view(), name='item_update'),
    path('api/items/<int:pk>/delete/', views.ItemDelete.as_view(), name="item_delete"),

    path('api/token-login/', api_token_login, name='api_token_login'),

    # Category URLs
    path('api/categories/', views.CategoryList.as_view(), name='category_list'),
    path('api/categories/create/', views.CategoryCreate.as_view(), name='category_create'),
    
    # Order URLs
    path('api/orders/', views.OrderList.as_view(), name='order_list'),
    path('api/orders/create/', views.OrderCreate.as_view(), name='order_create'),
    path('api/orders/<int:pk>/', views.OrderDetail.as_view(), name='order_detail'),
]
