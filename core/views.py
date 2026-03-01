from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views import View
from django.contrib import messages
from .forms import UserSignupForm, UserLoginForm
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib.auth.models import User
from django.conf import settings
from django.http import HttpResponse
import os
from django.core.mail import EmailMultiAlternatives


# =========================
# Signup
# =========================

def signup_view(request):
    form = UserSignupForm()

    if request.method == "POST":
        form = UserSignupForm(request.POST)
        if form.is_valid():

            user = form.save()

            subject = "Welcome To Car Scout 🚗"
            from_email = settings.EMAIL_HOST_USER
            to_email = [user.email]

            # Render HTML template
            html_content = render_to_string(
                "email/car_scout_email.html",
                {"user": user}
            )
            print("HTML CONTENT:")
            print(html_content)

            # Plain text fallback (important!)
            text_content = f"Welcome to Car Scout, {user.username}"

            email = EmailMultiAlternatives(
                subject,
                text_content,
                from_email,
                to_email
            )

            email.attach_alternative(html_content, "text/html")
            email.send()

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
            return redirect("login")

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

#==========================
#    Email Response
#==========================
def send_car_brochure_email(request, car_id):

    users = User.objects.all()

    for user in users:
        subject = "🚗 Car Scout - Special Update"
        from_email = settings.EMAIL_HOST_USER
        to_email = [user.email]

        # Render HTML
        html_content = render_to_string(
            'email/email.html',
            {'user': user}
        )

        email = EmailMultiAlternatives(
            subject,
            "Your email client does not support HTML",
            from_email,
            to_email
        )

        email.attach_alternative(html_content, "text/html")

        # Attach a file (example: PDF or image)
        file_path = os.path.join(settings.BASE_DIR, 'media/sample.pdf')
        if os.path.exists(file_path):
            email.attach_file(file_path)

        email.send()

    return HttpResponse("Emails Sent Successfully!")