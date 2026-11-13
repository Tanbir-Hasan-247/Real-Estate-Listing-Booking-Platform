from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.views import LoginView, LogoutView
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.generic import CreateView

from property.models import SavedProperty, TourBooking

from .demo_accounts import DEMO_ACCOUNTS, DEMO_PROTECTED_USERNAMES, ensure_demo_accounts
from .forms import (
    CustomUserCreationForm,
    LoginForm,
    ProfileUpdateForm,
    StyledPasswordChangeForm,
)
from .signals import send_user_activation_email

User = get_user_model()


def _role_dashboard_url(user):
    if user.is_superuser or getattr(user, "role", None) == "admin":
        return reverse_lazy("admin_dashboard")
    if getattr(user, "role", None) == "agent":
        return reverse_lazy("agent_dashboard")
    return reverse_lazy("home")


class UserRegistrationView(CreateView):
    model = User
    form_class = CustomUserCreationForm
    template_name = "users/register.html"
    success_url = reverse_lazy("login")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(_role_dashboard_url(request.user))
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        requested_role = self.request.GET.get("role")
        if requested_role in {"buyer", "agent"}:
            kwargs["initial_role"] = requested_role
        return kwargs

    def form_valid(self, form):
        form.instance._defer_activation_email = True
        response = super().form_valid(form)
        activation_url = send_user_activation_email(
            self.object,
            base_url=self.request.build_absolute_uri("/").rstrip("/"),
        )
        if settings.DEBUG:
            messages.info(
                self.request,
                f"Account created! Check your email ({self.object.email}) to activate. "
                f"Dev activation link logged cleanly.",
            )
            print(f"[PropNest Dev Activation Link for {self.object.username}]: {activation_url}")
        else:
            messages.success(
                self.request,
                f"Account created! We sent an activation link to {self.object.email}. Please verify before signing in.",
            )
        return response


class UserLoginView(LoginView):
    form_class = LoginForm
    template_name = "users/login.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(_role_dashboard_url(request.user))
        if not settings.TESTING:
            try:
                active_demo_count = User.objects.filter(
                    username__in=DEMO_PROTECTED_USERNAMES,
                    is_active=True,
                ).count()
                if active_demo_count < len(DEMO_ACCOUNTS):
                    ensure_demo_accounts(seed_activity=True)
            except Exception:
                pass
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["demo_accounts"] = DEMO_ACCOUNTS
        return context

    def form_invalid(self, form):
        identifier = (self.request.POST.get("username") or "").strip()
        if identifier:
            candidate = User.objects.filter(Q(username=identifier) | Q(email__iexact=identifier)).first()
            if candidate and not candidate.is_active:
                messages.warning(
                    self.request,
                    "This account has not been activated yet. Check your email or resend your activation link below.",
                )
        return super().form_invalid(form)

    def get_success_url(self):
        next_url = self.get_redirect_url()
        if next_url:
            return next_url
        return _role_dashboard_url(self.request.user)


class UserLogoutView(LogoutView):
    next_page = "home"


@login_required
def ProfileView(request):
    user = request.user
    profile_form = ProfileUpdateForm(instance=user)
    password_form = StyledPasswordChangeForm(user)

    if request.method == "POST":
        profile_form = ProfileUpdateForm(request.POST, request.FILES, instance=user)
        if profile_form.is_valid():
            profile_form.save()
            messages.success(request, "Your profile has been updated successfully.")
            return redirect("profile")
        messages.error(request, "Please correct the highlighted errors in your profile.")

    saved_count = SavedProperty.objects.filter(user=user).count()
    my_tours_count = TourBooking.objects.filter(buyer=user).count()

    return render(
        request,
        "user_profile.html",
        {
            "profile_form": profile_form,
            "password_form": password_form,
            "saved_count": saved_count,
            "my_tours_count": my_tours_count,
        },
    )


@login_required
def ChangePasswordView(request):
    if request.method != "POST":
        return redirect("profile")

    form = StyledPasswordChangeForm(request.user, request.POST)
    if form.is_valid():
        user = form.save()
        update_session_auth_hash(request, user)
        messages.success(request, "Your password has been updated securely.")
    else:
        for field_errors in form.errors.values():
            for err in field_errors:
                messages.error(request, err)
    return redirect("profile")


@login_required
def DeleteAccountView(request):
    if request.method != "POST":
        return redirect("profile")

    password = request.POST.get("confirm_password", "")
    if not request.user.check_password(password):
        messages.error(request, "Incorrect password. Account deletion cancelled.")
        return redirect("profile")

    user = request.user
    logout(request)
    user.delete()
    messages.success(request, "Your PropNest account has been permanently removed.")
    return redirect("home")


def activate_user(request, user_id, token):
    try:
        user = User.objects.get(id=user_id)
        if user.is_active:
            messages.info(request, "Your account is already active. Please sign in.")
            return redirect("login")
        if default_token_generator.check_token(user, token):
            user.is_active = True
            user.save(update_fields=["is_active"])
            messages.success(request, "Your account is now activated! You can sign in.")
            return redirect("login")
        messages.error(request, "This activation link is invalid or has expired.")
        return render(
            request,
            "users/activation_status.html",
            {"activated": False, "reason": "Invalid or expired activation token."},
            status=400,
        )
    except User.DoesNotExist:
        messages.error(request, "Account not found.")
        return render(
            request,
            "users/activation_status.html",
            {"activated": False, "reason": "User account not found."},
            status=404,
        )


def resend_activation_view(request):
    if request.method == "POST":
        email_or_user = (request.POST.get("identifier") or request.POST.get("email") or "").strip()
        user = (
            User.objects.filter(email__iexact=email_or_user).first()
            or User.objects.filter(username=email_or_user).first()
        )
        if user and not user.is_active:
            activation_url = send_user_activation_email(
                user,
                base_url=request.build_absolute_uri("/").rstrip("/"),
            )
            if settings.DEBUG:
                print(f"[PropNest Resend Activation for {user.username}]: {activation_url}")
        messages.success(
            request,
            "If an unactivated account matches your entry, a fresh activation link has been dispatched.",
        )
        return redirect("login")
    return render(request, "users/resend_activation.html")
