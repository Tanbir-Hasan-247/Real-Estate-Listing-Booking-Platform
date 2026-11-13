import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm

from .models import CustomUser


class CustomUserCreationForm(forms.ModelForm):
    ROLE_CHOICES = [
        (CustomUser.BUYER, "Resident / Buyer"),
        (CustomUser.AGENT, "Property Advisor / Agent"),
    ]

    account_role = forms.ChoiceField(
        choices=ROLE_CHOICES,
        initial=CustomUser.BUYER,
        required=False,
        label="Account Type",
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "pn-input",
                "autocomplete": "new-password",
                "placeholder": "Create a strong password",
            }
        ),
    )
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "pn-input",
                "autocomplete": "new-password",
                "placeholder": "Repeat your password",
            }
        ),
    )

    class Meta:
        model = CustomUser
        fields = ["first_name", "last_name", "username", "email", "phone", "profile"]

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            raise forms.ValidationError("Please enter a valid email address.")
        if CustomUser.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email address is already registered.")
        return email

    def clean_password(self):
        password = self.cleaned_data.get("password") or ""
        errors = []
        if len(password) < 8:
            errors.append("Password must be at least 8 characters long.")
        if not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter.")
        if not re.search(r"[0-9]", password):
            errors.append("Password must contain at least one number.")
        if not re.search(r'[!@#$%^&*(),.?":{}|<>\-_=+\[\]\\/;`~]', password):
            errors.append("Password must contain at least one special character.")
        if errors:
            raise forms.ValidationError(errors)
        return password

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if phone and not re.match(r"^\+?[\d\s\-()]{9,20}$", phone):
            raise forms.ValidationError(
                "Enter a valid phone number (9-15 digits, e.g. +880 1700-000000)."
            )
        return phone

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password and confirm_password and password != confirm_password:
            self.add_error("confirm_password", "Passwords do not match.")
        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        selected_role = self.cleaned_data.get("account_role") or CustomUser.BUYER
        user.role = selected_role if selected_role in {CustomUser.BUYER, CustomUser.AGENT} else CustomUser.BUYER
        user.set_password(self.cleaned_data["password"])
        user.is_active = False
        if commit:
            user.save()
        return user

    def __init__(self, *args, **kwargs):
        initial_role = kwargs.pop("initial_role", None)
        super().__init__(*args, **kwargs)
        if initial_role in {CustomUser.BUYER, CustomUser.AGENT}:
            self.fields["account_role"].initial = initial_role

        self.fields["first_name"].required = False
        self.fields["last_name"].required = False
        self.fields["first_name"].widget.attrs.update(
            {"class": "pn-input", "autocomplete": "given-name", "placeholder": "e.g. Tariq"}
        )
        self.fields["last_name"].widget.attrs.update(
            {"class": "pn-input", "autocomplete": "family-name", "placeholder": "e.g. Chowdhury"}
        )
        self.fields["username"].widget.attrs.update(
            {
                "class": "pn-input",
                "autocomplete": "username",
                "autocorrect": "off",
                "autocapitalize": "none",
                "spellcheck": "false",
                "placeholder": "Choose a username",
            }
        )
        self.fields["email"].widget.attrs.update(
            {
                "class": "pn-input",
                "autocomplete": "email",
                "placeholder": "you@example.com",
            }
        )
        self.fields["phone"].widget.attrs.update(
            {
                "class": "pn-input",
                "autocomplete": "tel",
                "placeholder": "+880 1700-000000",
            }
        )
        self.fields["profile"].widget.attrs.update({"class": "pn-input"})
        self.fields["account_role"].widget.attrs.update({"class": "pn-select"})
        for fname in ["username", "email", "password", "confirm_password"]:
            self.fields[fname].help_text = None


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Username or Email",
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "pn-input",
                "autocomplete": "username",
                "autocorrect": "off",
                "autocapitalize": "none",
                "spellcheck": "false",
                "enterkeyhint": "next",
                "placeholder": "Enter your username or email",
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "pn-input",
                "autocomplete": "current-password",
                "enterkeyhint": "done",
                "placeholder": "Enter your password",
            }
        ),
    )

    def clean_username(self):
        identifier = (self.cleaned_data.get("username") or "").strip()
        if "@" in identifier and not CustomUser.objects.filter(username=identifier).exists():
            matched = CustomUser.objects.filter(email__iexact=identifier).first()
            if matched:
                return matched.username
        return identifier


class ProfileUpdateForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ["first_name", "last_name", "email", "phone", "bio", "profile"]
        widgets = {
            "first_name": forms.TextInput(attrs={"class": "pn-input", "autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"class": "pn-input", "autocomplete": "family-name"}),
            "email": forms.EmailInput(attrs={"class": "pn-input", "autocomplete": "email"}),
            "phone": forms.TextInput(attrs={"class": "pn-input", "autocomplete": "tel"}),
            "bio": forms.Textarea(
                attrs={
                    "class": "pn-textarea",
                    "rows": 4,
                    "placeholder": "Share your architectural interests, portfolio background, or preferences...",
                }
            ),
            "profile": forms.ClearableFileInput(attrs={"class": "pn-input"}),
        }

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            return self.instance.email
        qs = CustomUser.objects.filter(email__iexact=email).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Another account is already using this email.")
        return email


class StyledPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["old_password"].widget.attrs.update(
            {"class": "pn-input", "autocomplete": "current-password", "placeholder": "Current password"}
        )
        self.fields["new_password1"].widget.attrs.update(
            {"class": "pn-input", "autocomplete": "new-password", "placeholder": "New strong password"}
        )
        self.fields["new_password2"].widget.attrs.update(
            {"class": "pn-input", "autocomplete": "new-password", "placeholder": "Confirm new password"}
        )
        for f in self.fields.values():
            f.help_text = None


class AdminCreateUserForm(forms.ModelForm):
    password = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={"class": "pn-input", "placeholder": "Initial password (min 8 chars)"}),
    )

    class Meta:
        model = CustomUser
        fields = ["username", "first_name", "last_name", "email", "role", "phone", "bio", "is_active"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "pn-input"}),
            "first_name": forms.TextInput(attrs={"class": "pn-input"}),
            "last_name": forms.TextInput(attrs={"class": "pn-input"}),
            "email": forms.EmailInput(attrs={"class": "pn-input"}),
            "role": forms.Select(attrs={"class": "pn-select"}),
            "phone": forms.TextInput(attrs={"class": "pn-input"}),
            "bio": forms.Textarea(attrs={"class": "pn-textarea", "rows": 2}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user
