from django.shortcuts import render, redirect,get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.views import View
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponseBadRequest, HttpResponse
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives
from django.contrib.auth.models import User
from .forms import UserSignupForm, UserLoginForm, CarForm
from .models import (Car, SavedCar, TestDrive, Payment, Review, Notification,CarInspectionReport, CarComparison, UserPreference )
from django.db.models import Avg, Count, Sum
from .models import Car, Coupon, AppliedCoupon
from .models import Conversation, Message, Car
from django.core.mail import send_mail
from django.contrib import messages
from django.utils import timezone
from .models import Car, Payment
from django.db.models import Q
from decimal import Decimal
import razorpay
import random
import os

def landing_page(request):
    featured_cars = Car.objects.filter(approved=True, status='available').order_by('-created_at')[:6]
    verified_cars = Car.objects.filter(approved=True, verified=True, status='available')[:6]
    latest_reviews = Review.objects.select_related('car', 'user').order_by('-created_at')[:5]

    context = {
        'featured_cars': featured_cars,
        'verified_cars': verified_cars,
        'latest_reviews': latest_reviews,
    }
    return render(request, 'core/landing_page.html', context)

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
            otp = str(random.randint(100000, 999999))

            request.session["signup_data"] = {
                "username": form.cleaned_data["username"],
                "email": form.cleaned_data["email"],
                "password1": form.cleaned_data["password1"],
                "password2": form.cleaned_data["password2"],
                "role": form.cleaned_data["role"],
            }

            request.session["signup_otp"] = otp

            send_mail(
                subject="CarScout OTP Verification",
                message=f"Your CarScout OTP is: {otp}",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[form.cleaned_data["email"]],
                fail_silently=False,
            )

            messages.success(request, "OTP sent to your email.")
            return redirect("verify_otp")

    return render(request, "core/signup.html", {"form": form})

def verify_otp(request):
    if request.method == "POST":
        entered_otp = request.POST.get("otp")
        saved_otp = request.session.get("signup_otp")
        signup_data = request.session.get("signup_data")

        if not signup_data:
            messages.error(request, "Signup session expired. Please sign up again.")
            return redirect("signup")

        if entered_otp == saved_otp:
            form = UserSignupForm(signup_data)

            if form.is_valid():
                user = form.save()

                # optional welcome/brochure email
                send_brochure_email(user)

                request.session.pop("signup_data", None)
                request.session.pop("signup_otp", None)

                messages.success(request, "Account verified successfully. Please login.")
                return redirect("login")
            else:
                messages.error(request, "Something went wrong. Please sign up again.")
                return redirect("signup")
        else:
            messages.error(request, "Invalid OTP. Please try again.")

    return render(request, "core/verify_otp.html")

def login_view(request):
    form = UserLoginForm()

    if request.method == "POST":
        form = UserLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)

            if user.profile.role == "buyer":
                return redirect("buyer_dashboard")
            elif user.profile.role == "seller":
                return redirect("seller_dashboard")

    return render(request, "core/login.html", {"form": form})

@login_required
def add_review(request, car_id):
    car = get_object_or_404(Car, id=car_id)

    if request.method == "POST":
        rating = int(request.POST.get("rating"))
        comment = request.POST.get("comment")

        review, created = Review.objects.update_or_create(
            user=request.user,
            car=car,
            defaults={
                'rating': rating,
                'comment': comment,
            }
        )

        Notification.objects.create(
            user=car.seller,
            message=f"{request.user.username} reviewed your car: {car.title}",
            link=f"/car/{car.id}/"
        )

        messages.success(request, "Your review was submitted.")
    return redirect('car_detail', pk=car.id)

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

        return redirect("signup")


@login_required
def buyer_dashboard(request):
    search_query = request.GET.get("search", "")
    all_cars = Car.objects.all()

    if search_query:
        searched_cars = all_cars.filter(
            Q(title__icontains=search_query) |
            Q(category__icontains=search_query)
        )
    else:
        searched_cars = Car.objects.none()

    luxury_cars = all_cars.filter(category__iexact="luxury")
    sports_cars = all_cars.filter(category__iexact="sports")
    electric_cars = all_cars.filter(category__iexact="electric")

    saved_ids = SavedCar.objects.filter(user=request.user).values_list("car_id", flat=True)
    saved_count = SavedCar.objects.filter(user=request.user).count()
    testdrive_count = TestDrive.objects.filter(user=request.user).count()
    offers_count = 0

    pref, created = UserPreference.objects.get_or_create(user=request.user)
    dark_mode = pref.dark_mode

    context = {
        "luxury_cars": luxury_cars,
        "sports_cars": sports_cars,
        "electric_cars": electric_cars,
        "searched_cars": searched_cars,
        "search_query": search_query,
        "saved_ids": saved_ids,
        "saved_count": saved_count,
        "testdrive_count": testdrive_count,
        "offers_count": offers_count,
        "dark_mode": dark_mode
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

def seller_analytics(request):
    cars = Car.objects.filter(seller=request.user)
    total_cars = cars.count()
    total_views = cars.aggregate(total=Sum('views'))['total'] or 0
    approved_cars = cars.filter(approved=True).count()
    sold_cars = cars.filter(status='sold').count()
    reserved_cars = cars.filter(status='reserved').count()
    review_count = Review.objects.filter(car__seller=request.user).count()
    avg_rating = Review.objects.filter(car__seller=request.user).aggregate(avg=Avg('rating'))['avg']
    saved_count = SavedCar.objects.filter(car__seller=request.user).count()
    test_drive_count = TestDrive.objects.filter(car__seller=request.user).count()

    context = {
        'total_cars': total_cars,
        'total_views': total_views,
        'approved_cars': approved_cars,
        'sold_cars': sold_cars,
        'reserved_cars': reserved_cars,
        'review_count': review_count,
        'avg_rating': avg_rating,
        'saved_count': saved_count,
        'test_drive_count': test_drive_count,
        'seller_cars': cars,
    }
    return render(request, 'core/seller_analytics.html', context)

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

    # increase view count
    car.views += 1
    car.save()

    # existing offer logic
    base_discount_percent = Decimal('5')
    base_discount_amount, base_final_price = calculate_discounted_price(car.price, base_discount_percent)

    applied_coupons = []
    extra_discount_amount = Decimal('0')
    final_price = base_final_price

    if request.user.is_authenticated:
        applied_coupons = AppliedCoupon.objects.filter(
            user=request.user,
            car=car
        ).select_related('coupon')

        for item in applied_coupons:
            if item.coupon.code != "AUTO5":
                extra_discount_amount += Decimal(item.discount_amount)

        final_price = base_final_price - extra_discount_amount
        if final_price < 0:
            final_price = Decimal('0')

    # reviews
    reviews = car.reviews.select_related('user').order_by('-created_at')
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg']
    review_count = reviews.count()

    # inspection report
    inspection_report = getattr(car, 'inspection_report', None)

    # compare feature
    is_in_compare = False
    if request.user.is_authenticated:
        is_in_compare = CarComparison.objects.filter(user=request.user, car=car).exists()

    context = {
        'car': car,

        # offer data
        'original_price': Decimal(car.price),
        'base_discount_percent': base_discount_percent,
        'base_discount_amount': base_discount_amount,
        'base_final_price': base_final_price,
        'extra_discount_amount': extra_discount_amount,
        'final_price': final_price,
        'applied_coupons': applied_coupons,

        # new features
        'reviews': reviews,
        'avg_rating': avg_rating,
        'review_count': review_count,
        'inspection_report': inspection_report,
        'is_in_compare': is_in_compare,
    }
    return render(request, 'core/car_detail.html', context)

@login_required
def add_to_compare(request, car_id):
    car = get_object_or_404(Car, id=car_id)

    if CarComparison.objects.filter(user=request.user).count() >= 3:
        messages.error(request, "You can compare maximum 3 cars.")
        return redirect('car_detail', pk=car.id)

    CarComparison.objects.get_or_create(user=request.user, car=car)
    messages.success(request, "Car added to compare list.")
    return redirect('car_detail', pk=car.id)


@login_required
def compare_cars(request):
    compared = CarComparison.objects.filter(user=request.user).select_related('car')
    cars = [item.car for item in compared]
    return render(request, 'core/compare_cars.html', {'cars': cars})


@login_required
def remove_from_compare(request, car_id):
    CarComparison.objects.filter(user=request.user, car_id=car_id).delete()
    messages.info(request, "Car removed from compare list.")
    return redirect('compare_cars')

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

@login_required
def my_listings(request):
    if request.user.profile.role != "seller":
        messages.error(request, "Only sellers can access My Listings.")
        return redirect("home")

    seller_cars = Car.objects.filter(seller=request.user).order_by("-id")

    return render(request, "core/my_listings.html", {
        "seller_cars": seller_cars
    })

@login_required
def start_payment(request, car_id):
    car = get_object_or_404(Car, id=car_id)

    # example: ₹500 booking fee = 50000 paise
    amount = 50000

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    order_data = {
        "amount": amount,
        "currency": "INR",
        "payment_capture": 1
    }
    order = client.order.create(data=order_data)

    payment = Payment.objects.create(
        user=request.user,
        car=car,
        amount=amount,
        razorpay_order_id=order["id"],
        status="created"
    )

    context = {
        "car": car,
        "payment": payment,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "amount": amount,
        "order_id": order["id"],
    }
    return render(request, "core/payment.html", context)

@csrf_exempt
@login_required
def verify_payment(request):
    if request.method == "POST":
        razorpay_payment_id = request.POST.get("razorpay_payment_id")
        razorpay_order_id = request.POST.get("razorpay_order_id")
        razorpay_signature = request.POST.get("razorpay_signature")

        client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

        try:
            client.utility.verify_payment_signature({
                "razorpay_order_id": razorpay_order_id,
                "razorpay_payment_id": razorpay_payment_id,
                "razorpay_signature": razorpay_signature
            })

            payment = Payment.objects.get(razorpay_order_id=razorpay_order_id)
            payment.razorpay_payment_id = razorpay_payment_id
            payment.razorpay_signature = razorpay_signature
            payment.status = "paid"
            payment.save()

            return HttpResponse("Payment verified successfully")

        except:
            return HttpResponseBadRequest("Payment verification failed")
        
@login_required
def start_full_payment(request, car_id):
    car = get_object_or_404(Car, id=car_id)

    display_amount = car.price
    payable_amount = 1000   # test/demo amount

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    order_data = {
        "amount": payable_amount * 100,
        "currency": "INR",
        "receipt": f"fullpayment_{request.user.id}_{car.id}",
        "notes": {
            "car_id": str(car.id),
            "user_id": str(request.user.id),
            "payment_type": "full_payment",
        }
    }

    order = client.order.create(data=order_data)

    payment = Payment.objects.create(
        user=request.user,
        car=car,
        payment_type="full_payment",
        amount=payable_amount,
        razorpay_order_id=order["id"],
        status="created",
    )

    context = {
        "car": car,
        "payment": payment,
        "display_amount": display_amount,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "amount_paise": payable_amount * 100,
        "order_id": order["id"],
        "button_text": f"Pay Now ₹{payable_amount}",
        "payment_title": "Buy Now",
    }

    return render(request, "core/payment_page.html", context)


@login_required
def start_test_drive_payment(request, car_id):
    car = get_object_or_404(Car, id=car_id)

    if request.method != "POST":
        return redirect("car_detail", pk=car.id)

    drive_date = request.POST.get("drive_date")
    test_drive_fee = 500

    test_drive = TestDrive.objects.create(
        user=request.user,
        car=car,
        drive_date=drive_date,
        fee_paid=False,
        fee_amount=test_drive_fee,
        status="pending_payment",
    )

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    order_data = {
        "amount": test_drive_fee * 100,
        "currency": "INR",
        "receipt": f"testdrive_{request.user.id}_{car.id}_{test_drive.id}",
        "notes": {
            "car_id": str(car.id),
            "user_id": str(request.user.id),
            "payment_type": "test_drive",
            "test_drive_id": str(test_drive.id),
        }
    }

    order = client.order.create(data=order_data)

    payment = Payment.objects.create(
        user=request.user,
        car=car,
        test_drive=test_drive,
        payment_type="test_drive",
        amount=test_drive_fee,
        razorpay_order_id=order["id"],
        status="created",
    )

    context = {
        "car": car,
        "payment": payment,
        "razorpay_key_id": settings.RAZORPAY_KEY_ID,
        "amount_paise": test_drive_fee * 100,
        "order_id": order["id"],
        "button_text": "Pay ₹500 & Confirm",
        "payment_title": "Test Drive Payment",
    }
    return render(request, "core/payment_page.html", context)


@login_required
def verify_payment(request):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid request")

    razorpay_order_id = request.POST.get("razorpay_order_id")
    razorpay_payment_id = request.POST.get("razorpay_payment_id")
    razorpay_signature = request.POST.get("razorpay_signature")

    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))

    try:
        client.utility.verify_payment_signature({
            "razorpay_order_id": razorpay_order_id,
            "razorpay_payment_id": razorpay_payment_id,
            "razorpay_signature": razorpay_signature,
        })
    except Exception:
        payment = Payment.objects.filter(razorpay_order_id=razorpay_order_id).first()
        if payment:
            payment.status = "failed"
            payment.save()
        return render(request, "core/payment_failed.html")

    payment = get_object_or_404(Payment, razorpay_order_id=razorpay_order_id)
    payment.razorpay_payment_id = razorpay_payment_id
    payment.razorpay_signature = razorpay_signature
    payment.status = "paid"
    payment.save()

    if payment.payment_type == "test_drive" and payment.test_drive:
        payment.test_drive.fee_paid = True
        payment.test_drive.status = "confirmed"
        payment.test_drive.save()

    return render(request, "core/payment_success.html", {"payment": payment})

def calculate_discounted_price(car_price, percent):
    car_price = Decimal(car_price)
    percent = Decimal(percent)
    discount = (car_price * percent) / Decimal(100)
    final_price = car_price - discount
    return discount, final_price

@login_required
def apply_default_offer(request, car_id):
    car = get_object_or_404(Car, id=car_id)

    coupon, created = Coupon.objects.get_or_create(
        code="AUTO5",
        defaults={
            "discount_type": "percent",
            "discount_value": Decimal('5'),
            "is_active": True,
            "is_admin_only": False,
            "usage_limit": 999999,
        }
    )

    already_applied = AppliedCoupon.objects.filter(
        user=request.user,
        car=car,
        coupon=coupon
    ).exists()

    if already_applied:
        messages.info(request, "5% offer already applied on this car.")
        return redirect('car_detail', pk=car.id)

    discount_amount, final_price = calculate_discounted_price(car.price, coupon.discount_value)

    AppliedCoupon.objects.create(
        user=request.user,
        car=car,
        coupon=coupon,
        discount_amount=discount_amount,
        final_price=final_price
    )

    messages.success(request, "5% offer applied successfully.")
    return redirect('car_detail', pk=car.id)


@login_required
def apply_coupon_code(request, car_id):
    car = get_object_or_404(Car, id=car_id)

    if request.method == "POST":
        entered_code = request.POST.get("coupon_code", "").strip().upper()

        try:
            coupon = Coupon.objects.get(code=entered_code, is_active=True)
        except Coupon.DoesNotExist:
            messages.error(request, "Invalid coupon code.")
            return redirect('car_detail', pk=car.id)

        now = timezone.now()

        if coupon.valid_from and coupon.valid_from > now:
            messages.error(request, "This coupon is not active yet.")
            return redirect('car_detail', pk=car.id)

        if coupon.valid_to and coupon.valid_to < now:
            messages.error(request, "This coupon has expired.")
            return redirect('car_detail', pk=car.id)

        if coupon.used_count >= coupon.usage_limit:
            messages.error(request, "This coupon usage limit is finished.")
            return redirect('car_detail', pk=car.id)

        already_applied = AppliedCoupon.objects.filter(
            user=request.user,
            car=car,
            coupon=coupon
        ).exists()

        if already_applied:
            messages.info(request, "This coupon is already applied.")
            return redirect('car_detail', pk=car.id)

        existing_extra_coupon = AppliedCoupon.objects.filter(
            user=request.user,
            car=car
        ).exclude(coupon__code="AUTO5").exists()

        if existing_extra_coupon:
            messages.error(request, "An extra coupon is already applied on this car.")
            return redirect('car_detail', pk=car.id)

        if coupon.discount_type == 'percent':
            discount_amount, _ = calculate_discounted_price(car.price, coupon.discount_value)
        else:
            discount_amount = Decimal(coupon.discount_value)

        auto_coupon = Coupon.objects.filter(code="AUTO5").first()
        auto_discount = Decimal('0')

        if auto_coupon and AppliedCoupon.objects.filter(
            user=request.user,
            car=car,
            coupon=auto_coupon
        ).exists():
            auto_discount, _ = calculate_discounted_price(car.price, Decimal('5'))

        final_price = Decimal(car.price) - auto_discount - discount_amount
        if final_price < 0:
            final_price = Decimal('0')

        AppliedCoupon.objects.create(
            user=request.user,
            car=car,
            coupon=coupon,
            discount_amount=discount_amount,
            final_price=final_price
        )

        coupon.used_count += 1
        coupon.save()

        messages.success(request, f"Coupon {coupon.code} applied successfully.")
        return redirect('car_detail', pk=car.id)

    return redirect('car_detail', pk=car.id)

@login_required
def notifications_view(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'core/notifications.html', {'notifications': notifications})


@login_required
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save()

    if notification.link:
        return redirect(notification.link)
    return redirect('notifications')

@login_required
def toggle_dark_mode(request):
    pref, created = UserPreference.objects.get_or_create(user=request.user)
    pref.dark_mode = not pref.dark_mode
    pref.save()
    return redirect(request.META.get('HTTP_REFERER', 'buyer_dashboard'))