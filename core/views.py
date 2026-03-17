from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views import View
from django.contrib import messages
from django.http import HttpResponse
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth.models import User
from .forms import UserSignupForm, UserLoginForm, CarForm
from .models import Car
from .models import SavedCar,TestDrive
import os
from django.db.models import Q
from .models import Conversation, Message, Car


def send_brochure_email(user):
    if not user.email:
        return

    subject = "✅ Car Scout Welcome + PDF Brochure Attached"
    from_email = settings.EMAIL_HOST_USER
    to_email = [user.email]

    html_content = render_to_string("email/car_scout_email.html", {"user": user})
    text_content = f"Welcome to Car Scout, {user.username}! Your brochure is attached."

    email = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=from_email,
        to=to_email
    )
    email.attach_alternative(html_content, "text/html")

    pdf_path = os.path.join(settings.BASE_DIR, "media", "brochure", "Car Scout Brochure.pdf")

    if os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            email.attach("Car-Scout-Brochure.pdf", f.read(), "application/pdf")

    email.send()


def signup_view(request):
    form = UserSignupForm()

    if request.method == "POST":
        form = UserSignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            send_brochure_email(user)
            messages.success(request, "Successfully Signed Up! Please login.")
            return redirect("login")

    return render(request, "core/signup.html", {"form": form})


def login_view(request):
    form = UserLoginForm()

    if request.method == "POST":
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect("home")

    return render(request, "core/login.html", {"form": form})


def logout_view(request):
    logout(request)
    return redirect("login")


class HomeView(View):
    def get(self, request):
        if request.user.is_authenticated:
            role = request.user.profile.role

            if role == "buyer":
                return redirect("buyer_dashboard")
            elif role == "seller":
                return redirect("seller_dashboard")

        return redirect("login")


@login_required
def buyer_dashboard(request):
    if request.user.profile.role != "buyer":
        messages.error(request, "Only buyers can access buyer dashboard.")
        return redirect("home")

    luxury_cars = Car.objects.filter(category="luxury").order_by("-id")[:4]
    sports_cars = Car.objects.filter(category="sports").order_by("-id")[:4]
    electric_cars = Car.objects.filter(category="electric").order_by("-id")[:4]

    saved_ids = list(
        SavedCar.objects.filter(user=request.user).values_list("car_id", flat=True)
    )

    context = {
        "luxury_cars": luxury_cars,
        "sports_cars": sports_cars,
        "electric_cars": electric_cars,
        "saved_count": len(saved_ids),
        "appointment_count": 2,
        "offers_count": 3,
        "saved_ids": saved_ids,
    }

    return render(request, "core/buyer_dashboard.html", context)


@login_required
def seller_dashboard(request):
    if request.user.profile.role != "seller":
        messages.error(request, "Only sellers can access seller dashboard.")
        return redirect("home")

    seller_cars = Car.objects.filter(seller=request.user).order_by("-id")[:6]

    context = {
        "seller_cars": seller_cars,
        "total_listings": seller_cars.count(),
        "total_views": 124,
        "total_messages": 8,
    }
    return render(request, "core/seller_dashboard.html", context)


@login_required
def add_car(request):
    if request.user.profile.role != "seller":
        messages.error(request, "Only sellers can add cars.")
        return redirect("home")

    form = CarForm()

    if request.method == "POST":
        form = CarForm(request.POST, request.FILES)
        if form.is_valid():
            car = form.save(commit=False)
            car.seller = request.user
            car.save()
            messages.success(request, "Car added successfully!")
            return redirect("seller_dashboard")

    return render(request, "core/add_car.html", {"form": form})


@login_required
def edit_car(request, pk):
    car = get_object_or_404(Car, pk=pk, seller=request.user)

    form = CarForm(instance=car)

    if request.method == "POST":
        form = CarForm(request.POST, request.FILES, instance=car)
        if form.is_valid():
            updated_car = form.save(commit=False)
            updated_car.seller = request.user
            updated_car.save()
            messages.success(request, "Car updated successfully!")
            return redirect("seller_dashboard")

    return render(request, "core/edit_car.html", {"form": form, "car": car})


@login_required
def delete_car(request, pk):
    car = get_object_or_404(Car, pk=pk, seller=request.user)

    if request.method == "POST":
        car.delete()
        messages.success(request, "Car deleted successfully!")
        return redirect("seller_dashboard")

    return render(request, "core/delete_car.html", {"car": car})


def car_detail(request, pk):
    car = get_object_or_404(Car, pk=pk)
    return render(request, "core/car_detail.html", {"car": car})

@login_required
def save_car(request, car_id):
    car = get_object_or_404(Car, id=car_id)
    SavedCar.objects.get_or_create(user=request.user,car=car)
    return redirect("buyer_dashboard")

@login_required
def unsave_car(request, car_id):
    car = get_object_or_404(Car, id=car_id)
    SavedCar.objects.filter(user=request.user, car=car).delete()
    return redirect("saved_cars")

@login_required
def saved_cars(request):
    saved = SavedCar.objects.filter(user=request.user).select_related("car").order_by("-saved_at")
    return render(request, "core/saved_cars.html", {"saved_cars": saved})

@login_required
def book_test_drive(request, car_id):

    car = get_object_or_404(Car, id=car_id)

    if request.method == "POST":

        date = request.POST.get("date")
        time = request.POST.get("time")

        TestDrive.objects.create(user=request.user,car=car,date=date,time=time)

        return redirect("buyer_dashboard")

    return render(request, "core/book_test_drive.html", {"car":car})

@login_required
def start_chat(request, car_id):
    car = get_object_or_404(Car, id=car_id)

    # buyer cannot chat with self if seller owns this car
    if car.seller == request.user:
        messages.error(request, "You cannot chat about your own car.")
        return redirect("car_detail", pk=car.id)

    conversation, created = Conversation.objects.get_or_create(buyer=request.user,seller=car.seller,car=car)

    return redirect("chat_detail", conversation_id=conversation.id)


@login_required
def inbox(request):
    conversations = Conversation.objects.filter(
        Q(buyer=request.user) | Q(seller=request.user)
    ).order_by("-created_at")

    return render(request, "core/inbox.html", {"conversations": conversations})


@login_required
def chat_detail(request, conversation_id):
    conversation = get_object_or_404(Conversation, id=conversation_id)

    if request.user != conversation.buyer and request.user != conversation.seller:
        messages.error(request, "You are not allowed to view this chat.")
        return redirect("home")

    if request.method == "POST":
        text = request.POST.get("text")
        if text:
            Message.objects.create(
                conversation=conversation,
                sender=request.user,
                text=text
            )
            return redirect("chat_detail", conversation_id=conversation.id)

    chat_messages = conversation.messages.all().order_by("timestamp")

    context = {
        "conversation": conversation,
        "chat_messages": chat_messages,
    }
    return render(request, "core/chat_detail.html", context)

@login_required
def book_test_drive(request, car_id):
    car = get_object_or_404(Car, id=car_id)

    if request.method == "POST":
        date = request.POST.get("date")
        time = request.POST.get("time")

        TestDrive.objects.create(
            user=request.user,
            car=car,
            date=date,
            time=time
        )

        messages.success(request, "Test drive booked successfully!")
        return redirect("buyer_dashboard")

    return render(request, "core/book_test_drive.html", {"car": car})

@login_required
def test_drive_cars(request):
    if request.user.profile.role != "buyer":
        messages.error(request, "Only buyers can access this page.")
        return redirect("home")

    cars = Car.objects.all().order_by("-id")

    return render(request, "core/test_drive_cars.html", {"cars": cars})