from django.shortcuts import render, redirect
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views import View
from .forms import UserSignupForm, UserLoginForm


# =========================
# Signup
# =========================
def signup_view(request):
    form = UserSignupForm()

    if request.method == "POST":
        form = UserSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")

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
            return redirect("home")

    return render(request, "core/login.html", {"form": form})

from django.contrib.auth import logout
from django.shortcuts import redirect

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