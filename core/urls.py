from django.urls import path
from . import views

urlpatterns = [
    path('signup/', views.userSignupView, name='signup'),
    path('login/', views.userLoginView, name='login'),
]