from django import forms
from .models import Listing
class ListingForm(forms.ModelForm):
    class Meta:
        model = Listing
        fields = ['title','description','price','exchange','tags','image','category']
