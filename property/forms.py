from datetime import date

from django import forms
from .models import Property, TourBooking 

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = [single_file_clean(data, initial)]
        return result

class PropertyForm(forms.ModelForm):
    images = MultipleFileField(
        required=False,
        label="Upload Property Images"
    )

    class Meta:
        model = Property
        fields = [
            'title', 'description', 'property_type', 'listing_type',
            'price', 'bedrooms', 'bathrooms', 'area_sqft',
            'location', 'city'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Write a detailed description...'}),
            'title': forms.TextInput(attrs={'placeholder': 'e.g. Modern Apartment with Sea View'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            if field_name != 'images':
                field.widget.attrs.update({
                    'class': 'w-full border border-gray-300 rounded-lg px-4 py-2.5 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 text-sm'
                })
                
    
class TourBookingForm(forms.ModelForm):
    class Meta:
        model = TourBooking
        fields = ['scheduled_date', 'scheduled_time', 'message']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        today = date.today().strftime('%Y-%m-%d')
        
        self.fields['scheduled_date'].widget.attrs.update({
            'class': 'w-full bg-white/80 border border-gray-200 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 text-sm cursor-pointer', 
            'type': 'date',
            'min': today, 
        })
        
        self.fields['scheduled_time'].widget.attrs.update({
            'class': 'w-full bg-white/80 border border-gray-200 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 text-sm cursor-pointer', 
            'type': 'time'
        })
        
        self.fields['message'].widget.attrs.update({
            'class': 'w-full bg-white/80 border border-gray-200 rounded-xl px-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 text-sm', 
            'rows': '2', 
            'placeholder': 'Any specific requests?'
        })