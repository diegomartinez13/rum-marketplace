from django import forms
from django.contrib.auth import authenticate
from .models import User

class SignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    class Meta:
        model = User
        fields = ['username','email','password']

class LoginForm(forms.Form):
    username = forms.CharField()
    password = forms.CharField(widget=forms.PasswordInput)
    def clean(self):
        u = self.cleaned_data.get('username')
        p = self.cleaned_data.get('password')
        user = authenticate(username=u, password=p)
        if not user:
            raise forms.ValidationError("Invalid credentials")
        self.user = user
        return self.cleaned_data
