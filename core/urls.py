from django.urls import path
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views
from . import views
from .views import HomeView

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('signup/', views.signup_view, name='signup'),
    path('login/', views.login_view, name='login'),
    path("logout/", views.logout_view, name="logout"),
    path("buyer-dashboard/", TemplateView.as_view(template_name="core/buyer_dashboard.html"), name="buyer_dashboard"),
    path("seller-dashboard/", TemplateView.as_view(template_name="core/seller_dashboard.html"), name="seller_dashboard"),
    path('send-emails/<int:car_id>/', views.send_car_brochure_email, name='send_emails'),
]