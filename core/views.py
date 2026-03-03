from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views import View
from django.contrib import messages
from django.http import HttpResponse
from django.conf import settings

from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth.models import User

from .forms import UserSignupForm, UserLoginForm

import os


# =========================
# Helper: Send Welcome HTML + PDF Attachment
# =========================
def send_brochure_email(user):
    # Safety: skip if user has no email
    if not user.email:
        return

    subject = "✅ Welcome To Car Scout"
    from_email = settings.EMAIL_HOST_USER
    to_email = [user.email]

    # HTML template
    html_content = render_to_string("email/car_scout_email.html", {"user": user})

    # Plain text fallback
    text_content = f"Welcome to Car Scout, {user.username}! Your brochure is attached."

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=from_email,
        to=to_email
    )
    email.attach_alternative(html_content, "text/html")

    # PDF path (matches your screenshot)
    pdf_path = os.path.join(settings.BASE_DIR, "media", "brochures", "carscout_brochure.pdf")
    # Debug prints (you can remove later)
    print("PDF PATH =", pdf_path)
    print("EXISTS?  =", os.path.exists(pdf_path))

    if os.path.exists(pdf_path):
        print("SIZE    =", os.path.getsize(pdf_path), "bytes")
        with open(pdf_path, "rb") as f:
            # Attach as bytes = most reliable
            email.attach("Car-Scout-Brochure.pdf", f.read(), "application/pdf")
        print("✅ PDF attached")
    else:
        print("❌ PDF NOT FOUND - check folder/file name")

    email.send()


# =========================
# Signup
# =========================
def signup_view(request):
    form = UserSignupForm()

    if request.method == "POST":
        form = UserSignupForm(request.POST)
        if form.is_valid():
            user = form.save()

            # ✅ Send single email with HTML + PDF
            send_brochure_email(user)

            messages.success(request, "Successfully Signed Up! Please login.")
            return redirect("login")

    return render(request, "core/signup.html", {"form": form})


# =========================
# Login
# =========================
def login_view(request):
    form = UserLoginForm()

    if request.method == "POST":
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            # If you want to redirect to home logic:
            return redirect("home")

    return render(request, "core/login.html", {"form": form})


# =========================
# Logout
# =========================
def logout_view(request):
    logout(request)
    return redirect("login")


# =========================
# Home Redirect by Role
# =========================
class HomeView(View):
    def get(self, request):
        if request.user.is_authenticated:
            role = request.user.profile.role

            if role == "buyer":
                return redirect("buyer_dashboard")
            elif role == "seller":
                return redirect("seller_dashboard")

        return redirect("login")


# =========================
# Buyer Dashboard
# =========================
@login_required
def buyer_dashboard(request):
    return render(request, "core/buyer_dashboard.html")


# =========================
# Seller Dashboard
# =========================
@login_required
def seller_dashboard(request):
    return render(request, "core/seller_dashboard.html")


# =========================
# Optional: Send brochure to ALL users (admin/testing)
# URL: /core/send-emails/<car_id>/
# car_id not used here; kept only to match your urls.py
# =========================
def send_car_brochure_email(request, car_id):
    users = User.objects.filter(is_active=True).exclude(email="")

    sent = 0
    for user in users:
        send_brochure_email(user)
        sent += 1

    return HttpResponse(f"Emails sent successfully to {sent} users.")