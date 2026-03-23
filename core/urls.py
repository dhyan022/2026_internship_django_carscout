from django.urls import path
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views
from . import views
from .views import HomeView

urlpatterns = [
    path('', views.signup_view, name='home'),
    path('signup/', views.signup_view, name='signup'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('login/', views.login_view, name='login'),
    path("logout/", views.logout_view, name="logout"),
    path("saved-cars/", views.saved_cars, name="saved_cars"),
    path("unsave-car/<int:car_id>/", views.unsave_car, name="unsave_car"),

    path('buyer-dashboard/', views.buyer_dashboard, name='buyer_dashboard'),
    path('seller-dashboard/', views.seller_dashboard, name='seller_dashboard'),
    path('add-car/', views.add_car, name='add_car'),

    path('car/<int:pk>/', views.car_detail, name='car_detail'),
    path('car/<int:pk>/edit/', views.edit_car, name='edit_car'),
    path('car/<int:pk>/delete/', views.delete_car, name='delete_car'),
    path("save-car/<int:car_id>/", views.save_car, name="save_car"),
    path("test-drive/<int:car_id>/", views.book_test_drive, name="book_test_drive"),
    path("test-drive-cars/", views.test_drive_cars, name="test_drive_cars"),
    path("my-listings/", views.my_listings, name="my_listings"),

    path("inbox/", views.inbox, name="inbox"),
    path("chat/start/<int:car_id>/", views.start_chat, name="start_chat"),
    path("chat/<int:conversation_id>/", views.chat_detail, name="chat_detail"),
    path('send-emails/<int:car_id>/', views.send_brochure_email, name='send_emails'),

    path("payment/<int:car_id>/", views.start_payment, name="start_payment"),
    path("verify-payment/", views.verify_payment, name="verify_payment"),

    path("payment/full/<int:car_id>/", views.start_full_payment, name="start_full_payment"),
    path("payment/test-drive/<int:car_id>/", views.start_test_drive_payment, name="start_test_drive_payment"),
    path("verify-payment/", views.verify_payment, name="verify_payment"),

    path("car/<int:car_id>/apply-offer/", views.apply_default_offer, name="apply_default_offer"),
    path("car/<int:car_id>/apply-coupon/", views.apply_coupon_code, name="apply_coupon_code"),

    path('', views.landing_page, name='landing_page'),
    path('car/<int:car_id>/review/', views.add_review, name='add_review'),
    path('car/<int:car_id>/compare/', views.add_to_compare, name='add_to_compare'),
    path('compare-cars/', views.compare_cars, name='compare_cars'),
    path('compare/remove/<int:car_id>/', views.remove_from_compare, name='remove_from_compare'),
    path('notifications/', views.notifications_view, name='notifications'),
    path('notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
    path('toggle-dark-mode/', views.toggle_dark_mode, name='toggle_dark_mode'),
    path('seller-analytics/', views.seller_analytics, name='seller_analytics'),
]