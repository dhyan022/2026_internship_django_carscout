from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from django import forms
from .models import Profile


# ---------------- SIGNUP FORM ----------------
class UserSignupForm(UserCreationForm):

    ROLE_CHOICES = (
        ('buyer', 'Buyer'),
        ('seller', 'Seller'),
    )

    email = forms.EmailField()
    role = forms.ChoiceField(choices=ROLE_CHOICES)

    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2']

    def save(self, commit=True):
        user = super().save(commit)
        role = self.cleaned_data.get('role')
        Profile.objects.create(user=user, role=role)
        return user


# ---------------- LOGIN FORM ----------------
class UserLoginForm(AuthenticationForm):
    pass