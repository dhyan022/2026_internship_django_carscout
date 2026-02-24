from django.contrib.auth.forms import UserCreationForm
from .models import User
from django import forms

class UserSignupForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['email','role','password1','password2']
        widgets = {
            'email': forms.EmailInput(attrs={
                'class': 'input-field',
                'placeholder': 'Enter your email'
            }),
            'role': forms.Select(attrs={
                'class': 'input-field'
            }),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields['password1'].widget.attrs.update({
            'class': 'input-field',
            'placeholder': 'Enter password'
        })

        self.fields['password2'].widget.attrs.update({
            'class': 'input-field',
            'placeholder': 'Confirm password'
        })