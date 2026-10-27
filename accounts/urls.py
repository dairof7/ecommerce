from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.UserCreate.as_view(), name='register'),
    path('profile/', views.UserProfileRetrieveUpdate.as_view(), name='profile'),
    path('user-search/', views.UserSearchView.as_view(), name='user-search'),
    path('pos-create-user/', views.POSCustomerCreateView.as_view(), name='pos-create-user'),
]