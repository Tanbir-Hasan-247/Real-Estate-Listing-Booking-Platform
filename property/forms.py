from datetime import date

from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import AMENITY_CHOICES, ContactMessage, Property, PropertyReview, PropertyType, TourBooking

User = get_user_model()


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if not data:
            return []
        if isinstance(data, (list, tuple)):
            return [single_file_clean(d, initial) for d in data if d]
        return [single_file_clean(data, initial)]


class PropertyForm(forms.ModelForm):
    images = MultipleFileField(
        required=False,
        label="Property Gallery Images",
    )
    amenities = forms.MultipleChoiceField(
        choices=AMENITY_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        label="Architectural Amenities",
    )

    class Meta:
        model = Property
        fields = [
            "title",
            "description",
            "property_type",
            "listing_type",
            "status",
            "price",
            "bedrooms",
            "bathrooms",
            "area_sqft",
            "location",
            "city",
            "state",
            "latitude",
            "longitude",
            "amenities",
            "is_featured",
        ]
        widgets = {
            "title": forms.TextInput(attrs={"placeholder": "e.g. Lakefront Sky Villa in Gulshan"}),
            "description": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Describe architectural highlights, lighting, finishes, and neighborhood connectivity...",
                }
            ),
            "price": forms.NumberInput(attrs={"step": "0.01", "min": "0", "placeholder": "e.g. 285000"}),
            "bedrooms": forms.NumberInput(attrs={"min": "0", "placeholder": "e.g. 4"}),
            "bathrooms": forms.NumberInput(attrs={"min": "0", "placeholder": "e.g. 3"}),
            "area_sqft": forms.NumberInput(attrs={"min": "1", "placeholder": "e.g. 2400"}),
            "location": forms.TextInput(attrs={"placeholder": "e.g. Road 74, Gulshan-2"}),
            "city": forms.TextInput(attrs={"placeholder": "e.g. Dhaka"}),
            "state": forms.TextInput(attrs={"placeholder": "e.g. Dhaka Division"}),
            "latitude": forms.NumberInput(attrs={"step": "0.000001", "placeholder": "e.g. 23.793700"}),
            "longitude": forms.NumberInput(attrs={"step": "0.000001", "placeholder": "e.g. 90.406600"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

        self.fields["status"].required = False
        self.fields["state"].required = False
        self.fields["latitude"].required = False
        self.fields["longitude"].required = False
        self.fields["bedrooms"].required = False
        self.fields["bathrooms"].required = False
        self.fields["is_featured"].required = False

        if not self.instance.pk:
            self.fields["status"].initial = "available"
            self.fields["state"].initial = "Dhaka Division"

        if user and (user.is_superuser or getattr(user, "role", None) == "admin"):
            self.fields["assigned_agent"] = forms.ModelChoiceField(
                queryset=User.objects.filter(role="agent").order_by("first_name", "username"),
                required=False,
                label="Assigned Agent",
                initial=self.instance.agent_id if self.instance.pk else None,
            )

        for field_name, field in self.fields.items():
            if field_name == "images":
                field.widget.attrs.update({"class": "pn-input", "multiple": True, "accept": "image/*"})
            elif isinstance(field.widget, forms.CheckboxSelectMultiple):
                field.widget.attrs.update({"class": "pn-amenity-check-input"})
            elif isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs.update({"class": "pn-checkbox"})
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs.update({"class": "pn-select"})
            elif isinstance(field.widget, forms.Textarea):
                field.widget.attrs.update({"class": "pn-textarea"})
            else:
                field.widget.attrs.update({"class": "pn-input"})

    def clean_amenities(self):
        return list(self.cleaned_data.get("amenities") or [])

    def clean_status(self):
        return self.cleaned_data.get("status") or (self.instance.status if self.instance.pk else "available")

    def clean_state(self):
        return (self.cleaned_data.get("state") or "").strip() or (
            self.instance.state if self.instance.pk and self.instance.state else "Dhaka"
        )


class TourBookingForm(forms.ModelForm):
    class Meta:
        model = TourBooking
        fields = ["scheduled_date", "scheduled_time", "message"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        today = date.today().strftime("%Y-%m-%d")
        self.fields["scheduled_date"].widget = forms.DateInput(
            attrs={"class": "pn-input", "type": "date", "min": today}
        )
        self.fields["scheduled_time"].widget = forms.TimeInput(
            attrs={"class": "pn-input", "type": "time"}
        )
        self.fields["message"].widget = forms.Textarea(
            attrs={
                "class": "pn-textarea",
                "rows": 3,
                "placeholder": "Share your preferred viewing focus, parking needs, or questions...",
            }
        )

    def clean_scheduled_date(self):
        scheduled = self.cleaned_data.get("scheduled_date")
        if scheduled and scheduled < date.today():
            raise forms.ValidationError("Please choose today or a future date for your private tour.")
        return scheduled

    def clean(self):
        cleaned = super().clean()
        scheduled_date = cleaned.get("scheduled_date")
        scheduled_time = cleaned.get("scheduled_time")
        if scheduled_date and scheduled_time and scheduled_date == timezone.localdate():
            if scheduled_time <= timezone.localtime().time():
                self.add_error(
                    "scheduled_time",
                    "Please choose a future time slot when booking a tour for today.",
                )
        return cleaned


class PropertyReviewForm(forms.ModelForm):
    rating = forms.ChoiceField(
        choices=[(str(i), f"{i} ★") for i in range(5, 0, -1)],
        widget=forms.RadioSelect,
        label="Overall Rating",
    )

    class Meta:
        model = PropertyReview
        fields = ["rating", "comment"]
        widgets = {
            "comment": forms.Textarea(
                attrs={
                    "class": "pn-textarea",
                    "rows": 3,
                    "placeholder": "Share impressions from your walkthrough: natural light, finish quality, noise isolation, or advisor briefing...",
                }
            )
        }

    def clean_rating(self):
        try:
            val = int(self.cleaned_data["rating"])
        except (TypeError, ValueError):
            raise forms.ValidationError("Select a rating from 1 to 5 stars.")
        if not 1 <= val <= 5:
            raise forms.ValidationError("Rating must be between 1 and 5.")
        return val


class PropertyTypeForm(forms.ModelForm):
    class Meta:
        model = PropertyType
        fields = ["name"]
        widgets = {
            "name": forms.Select(attrs={"class": "pn-select"}),
        }


class ContactForm(forms.ModelForm):
    website = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={"tabindex": "-1", "aria-hidden": "true", "autocomplete": "off"}),
    )

    class Meta:
        model = ContactMessage
        fields = ["name", "email", "phone", "subject", "property", "message"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "pn-input", "autocomplete": "name", "placeholder": "Your full name"}),
            "email": forms.EmailInput(attrs={"class": "pn-input", "autocomplete": "email", "placeholder": "you@example.com"}),
            "phone": forms.TextInput(attrs={"class": "pn-input", "autocomplete": "tel", "placeholder": "+880 1700-000000 (optional)"}),
            "subject": forms.TextInput(attrs={"class": "pn-input", "placeholder": "e.g. Private viewing or advisory request"}),
            "property": forms.Select(attrs={"class": "pn-select"}),
            "message": forms.Textarea(
                attrs={
                    "class": "pn-textarea",
                    "rows": 5,
                    "placeholder": "Tell us which residence, neighborhood, budget, or timeline you have in mind...",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["property"].required = False
        self.fields["property"].empty_label = "General Architectural Inquiry (No specific property)"
        self.fields["property"].queryset = Property.objects.filter(status="available").order_by("title")
