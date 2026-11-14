import csv

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.paginator import Paginator
from django.db.models import Avg, Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST
from django.views.generic import DetailView, ListView

from users.demo_accounts import DEMO_PROTECTED_USERNAMES
from users.forms import AdminCreateUserForm

from .forms import PropertyForm, PropertyReviewForm, PropertyTypeForm, TourBookingForm
from .models import (
    AMENITY_CHOICES,
    ContactMessage,
    Notification,
    Property,
    PropertyImage,
    PropertyReview,
    PropertyType,
    SavedProperty,
    TourBooking,
)

User = get_user_model()

CITY_COORDS = {
    "dhaka": (23.7937, 90.4066),
    "chattogram": (22.3569, 91.7832),
    "rajshahi": (24.3745, 88.6042),
    "khulna": (22.8456, 89.5403),
    "sylhet": (24.8949, 91.8687),
}


def _is_admin(user):
    return bool(user and user.is_authenticated and (user.is_superuser or getattr(user, "role", None) == "admin"))


def _is_agent(user):
    return bool(user and user.is_authenticated and getattr(user, "role", None) == "agent")


def _can_manage_property(user, prop):
    return _is_admin(user) or (user.is_authenticated and prop.agent_id == user.id)


def _safe_redirect(request, candidate_url, fallback_name, **fallback_kwargs):
    if candidate_url and url_has_allowed_host_and_scheme(
        candidate_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(candidate_url)
    return redirect(fallback_name, **fallback_kwargs)


@login_required
def PropertyCreateView(request):
    if not (_is_agent(request.user) or _is_admin(request.user)):
        messages.error(request, "Only agents or administrators can create property listings.")
        return redirect("home")

    form = PropertyForm(user=request.user)
    if request.method == "POST":
        form = PropertyForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            prop = form.save(commit=False)
            assigned_agent = form.cleaned_data.get("assigned_agent")
            prop.agent = assigned_agent or request.user
            prop.status = form.cleaned_data.get("status") or "available"
            prop.state = form.cleaned_data.get("state") or "Dhaka"
            prop.save()

            for image in form.cleaned_data.get("images") or []:
                PropertyImage.objects.create(property=prop, image=image)

            messages.success(request, f"Listing '{prop.title}' published successfully.")
            return redirect("admin_property_list" if _is_admin(request.user) else "agent_property_list")
        messages.error(request, "Please correct the highlighted fields before publishing.")

    return render(
        request,
        "agent/add_property.html",
        {
            "form": form,
            "is_admin_context": _is_admin(request.user),
            "base_template": "admin/admin_base.html" if _is_admin(request.user) else "agent/agent_base.html",
        },
    )


@login_required
def PropertyEditView(request, pk):
    prop = get_object_or_404(Property.objects.prefetch_related("images"), pk=pk)
    if not _can_manage_property(request.user, prop):
        messages.error(request, "You do not have permission to edit this property.")
        return redirect("home")

    form = PropertyForm(instance=prop, user=request.user)
    if request.method == "POST":
        form = PropertyForm(request.POST, request.FILES, instance=prop, user=request.user)
        if form.is_valid():
            updated = form.save(commit=False)
            assigned_agent = form.cleaned_data.get("assigned_agent")
            if _is_admin(request.user) and assigned_agent:
                updated.agent = assigned_agent
            updated.save()

            for image in form.cleaned_data.get("images") or []:
                PropertyImage.objects.create(property=updated, image=image)

            messages.success(request, f"Listing '{updated.title}' updated successfully.")
            return redirect("admin_property_list" if _is_admin(request.user) else "agent_property_list")
        messages.error(request, "Please review the highlighted fields.")

    return render(
        request,
        "agent/add_property.html",
        {
            "form": form,
            "property": prop,
            "is_admin_context": _is_admin(request.user),
            "base_template": "admin/admin_base.html" if _is_admin(request.user) else "agent/agent_base.html",
        },
    )


@login_required
def PropertyDeleteView(request, pk):
    prop = get_object_or_404(Property, pk=pk)
    if not _can_manage_property(request.user, prop):
        messages.error(request, "You do not have permission to delete this property.")
        return redirect("home")

    target_redirect = "admin_property_list" if _is_admin(request.user) else "agent_property_list"
    if request.method != "POST":
        messages.warning(request, "Use the confirmation button to delete a property listing.")
        return redirect(target_redirect)

    title = prop.title
    prop.delete()
    messages.success(request, f"Listing '{title}' has been deleted.")
    return redirect(target_redirect)


@login_required
def DeletePropertyImageView(request, pk):
    image_obj = get_object_or_404(PropertyImage.objects.select_related("property"), pk=pk)
    prop = image_obj.property
    if not _can_manage_property(request.user, prop):
        messages.error(request, "You do not have permission to remove this image.")
        return redirect("home")

    if request.method == "POST":
        image_obj.delete()
        messages.success(request, "Property photo removed.")
    return redirect("edit_property", pk=prop.pk)


class AgentDashboardView(LoginRequiredMixin, UserPassesTestMixin, ListView):
    model = Property
    template_name = "agent/dashboard.html"
    context_object_name = "properties"
    login_url = "login"

    def test_func(self):
        return _is_agent(self.request.user) or _is_admin(self.request.user)

    def handle_no_permission(self):
        if not self.request.user.is_authenticated:
            return super().handle_no_permission()
        messages.error(self.request, "Access restricted to registered agents.")
        return redirect("home")

    def get_queryset(self):
        queryset = (
            Property.objects.select_related("property_type", "agent")
            .prefetch_related("images")
            .filter(agent=self.request.user)
            .order_by("-created_at")
        )
        filter_type = self.request.GET.get("filter", "all")
        if filter_type in {"available", "sold", "rented"}:
            queryset = queryset.filter(status=filter_type)

        props = list(queryset)
        for prop in props:
            imgs = list(prop.images.all())
            prop.first_image = imgs[0] if imgs else None
        return props

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_agent_props = Property.objects.filter(agent=self.request.user)
        tour_bookings = (
            TourBooking.objects.select_related("property", "buyer")
            .filter(property__agent=self.request.user)
            .order_by("-created_at")
        )
        context["property_count"] = all_agent_props.count()
        context["active_count"] = all_agent_props.filter(status="available").count()
        context["closed_count"] = all_agent_props.filter(status__in=["sold", "rented"]).count()
        context["tour_bookings"] = tour_bookings[:8]
        context["tour_bookings_count"] = tour_bookings.filter(status="Pending").count()
        context["saved_leads_count"] = SavedProperty.objects.filter(property__agent=self.request.user).count()
        review_stats = PropertyReview.objects.filter(property__agent=self.request.user).aggregate(
            avg=Avg("rating"), total=Count("id")
        )
        context["agent_avg_rating"] = round(float(review_stats["avg"]), 1) if review_stats["avg"] else None
        context["agent_reviews_count"] = review_stats["total"] or 0
        context["current_filter"] = self.request.GET.get("filter", "all")
        return context


@login_required
def AgentPropertyListView(request):
    if not (_is_agent(request.user) or _is_admin(request.user)):
        messages.error(request, "Access restricted to agents.")
        return redirect("home")

    qs = (
        Property.objects.select_related("property_type", "agent")
        .prefetch_related("images")
        .filter(agent=request.user)
        .order_by("-created_at")
    )

    search_query = (request.GET.get("search") or "").strip()
    status_filter = (request.GET.get("status") or "").strip()
    listing_filter = (request.GET.get("listing_type") or "").strip()

    if search_query:
        qs = qs.filter(
            Q(title__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(location__icontains=search_query)
            | Q(city__icontains=search_query)
        )
    if status_filter:
        qs = qs.filter(status=status_filter)
    if listing_filter:
        qs = qs.filter(listing_type=listing_filter)

    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))
    for prop in page_obj:
        imgs = list(prop.images.all())
        prop.first_image = imgs[0] if imgs else None

    return render(
        request,
        "agent/agent_properties.html",
        {
            "properties": page_obj,
            "page_obj": page_obj,
            "search_query": search_query,
            "status_filter": status_filter,
            "listing_filter": listing_filter,
        },
    )


def AgentProperty(request, pk):
    agent = get_object_or_404(User, pk=pk, role="agent")
    properties = list(
        Property.objects.select_related("property_type", "agent")
        .prefetch_related("images")
        .filter(agent=agent, status="available")
        .order_by("-is_featured", "-created_at")
    )
    for prop in properties:
        imgs = list(prop.images.all())
        prop.first_image = imgs[0] if imgs else None

    completed_deals = Property.objects.filter(agent=agent, status__in=["sold", "rented"]).count()
    return render(
        request,
        "agent_profile.html",
        {
            "agent": agent,
            "properties": properties,
            "completed_deals": completed_deals,
        },
    )


@login_required
def AgentTourRequestsView(request):
    if not (_is_agent(request.user) or _is_admin(request.user)):
        messages.error(request, "Access restricted to agents.")
        return redirect("home")

    bookings = (
        TourBooking.objects.select_related("property", "buyer")
        .prefetch_related("property__images")
        .filter(property__agent=request.user)
        .order_by("-created_at")
    )
    status_filter = (request.GET.get("status") or "all").strip()
    if status_filter and status_filter.lower() != "all":
        bookings = bookings.filter(status__iexact=status_filter)

    paginator = Paginator(bookings, 12)
    page_obj = paginator.get_page(request.GET.get("page"))
    for booking in page_obj:
        imgs = list(booking.property.images.all())
        booking.property.first_image = imgs[0] if imgs else None

    return render(
        request,
        "agent/agent_tour_requests.html",
        {
            "bookings": page_obj,
            "page_obj": page_obj,
            "status_filter": status_filter,
        },
    )


@login_required
def UpdateTourStatusView(request, booking_id, new_status):
    fallback_url = "admin_tour_requests" if _is_admin(request.user) else "agent_tour_requests"
    next_url = request.POST.get("next") or request.META.get("HTTP_REFERER") or fallback_url

    if request.method == "POST":
        booking = get_object_or_404(TourBooking.objects.select_related("property"), id=booking_id)
        if booking.property.agent_id != request.user.id and not _is_admin(request.user):
            messages.error(request, "You do not have permission to update this booking.")
            return redirect(fallback_url)

        valid_statuses = {"Pending", "Confirmed", "Cancelled", "Completed"}
        if new_status in valid_statuses:
            booking.status = new_status
            agent_msg = (request.POST.get("agent_message") or "").strip()
            if agent_msg:
                booking.agent_message = agent_msg
            booking.save()
            messages.success(request, f"Tour status updated to {new_status}.")
        else:
            messages.error(request, "Invalid status update.")

    return _safe_redirect(request, next_url, fallback_url)


@login_required
def MyTourBookingsView(request):
    bookings = (
        TourBooking.objects.select_related("property", "property__agent", "property__property_type")
        .prefetch_related("property__images")
        .filter(buyer=request.user)
        .order_by("-created_at")
    )
    for booking in bookings:
        imgs = list(booking.property.images.all())
        booking.property.first_image = imgs[0] if imgs else None
    return render(request, "my_tours.html", {"bookings": bookings})


@login_required
def CancelMyTourView(request, booking_id):
    if request.method == "POST":
        booking = get_object_or_404(TourBooking, id=booking_id, buyer=request.user)
        if booking.status in {"Pending", "Confirmed"}:
            booking.status = "Cancelled"
            booking.save()
            messages.success(request, f"Tour request for '{booking.property.title}' was cancelled.")
        else:
            messages.info(request, "This tour cannot be cancelled in its current status.")
    return redirect("my_tours")


# =========================================================================
# ADMIN MANAGEMENT PANEL
# =========================================================================


@login_required
def AdminDashboardView(request):
    if not _is_admin(request.user):
        messages.error(request, "Administrator access required.")
        return redirect("home")

    all_props = (
        Property.objects.select_related("property_type", "agent")
        .prefetch_related("images")
        .order_by("-created_at")
    )
    property_count = all_props.count()
    active_count = all_props.filter(status="available").count()
    sold_count = all_props.filter(status__in=["sold", "rented"]).count()
    total_users = User.objects.count()
    total_agents = User.objects.filter(role="agent").count()
    pending_tours_count = TourBooking.objects.filter(status="Pending").count()
    unresolved_inquiries_count = ContactMessage.objects.filter(is_resolved=False).count()

    filter_type = request.GET.get("filter", "all")
    filtered_props = all_props.filter(status=filter_type) if filter_type in {"available", "sold", "rented"} else all_props
    recent_props = list(filtered_props[:8])
    for prop in recent_props:
        imgs = list(prop.images.all())
        prop.first_image = imgs[0] if imgs else None

    tour_bookings = (
        TourBooking.objects.select_related("property", "buyer", "property__agent", "property__property_type")
        .prefetch_related("property__images")
        .order_by("-created_at")[:8]
    )
    recent_inquiries = ContactMessage.objects.select_related("property").order_by("-created_at")[:5]

    return render(
        request,
        "admin/admin_dashboard.html",
        {
            "properties": recent_props,
            "property_count": property_count,
            "active_count": active_count,
            "sold_count": sold_count,
            "total_users": total_users,
            "total_agents": total_agents,
            "tour_bookings": tour_bookings,
            "pending_tours_count": pending_tours_count,
            "unresolved_inquiries_count": unresolved_inquiries_count,
            "recent_inquiries": recent_inquiries,
            "current_filter": filter_type,
        },
    )


@login_required
def AdminPropertyListView(request):
    if not _is_admin(request.user):
        messages.error(request, "Administrator access required.")
        return redirect("home")

    qs = (
        Property.objects.select_related("property_type", "agent")
        .prefetch_related("images")
        .order_by("-created_at")
    )
    search_query = (request.GET.get("search") or "").strip()
    status_filter = (request.GET.get("status") or "").strip()
    listing_filter = (request.GET.get("listing_type") or "").strip()

    if search_query:
        qs = qs.filter(
            Q(title__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(location__icontains=search_query)
            | Q(city__icontains=search_query)
            | Q(agent__username__icontains=search_query)
        )
    if status_filter:
        qs = qs.filter(status=status_filter)
    if listing_filter:
        qs = qs.filter(listing_type=listing_filter)

    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(request.GET.get("page"))
    for prop in page_obj:
        imgs = list(prop.images.all())
        prop.first_image = imgs[0] if imgs else None

    return render(
        request,
        "admin/all_properties.html",
        {
            "properties": page_obj,
            "page_obj": page_obj,
            "search_query": search_query,
            "status_filter": status_filter,
            "listing_filter": listing_filter,
        },
    )


@login_required
def AdminPropertyTypeListView(request):
    if not _is_admin(request.user):
        messages.error(request, "Administrator access required.")
        return redirect("home")

    form = PropertyTypeForm()
    if request.method == "POST":
        form = PropertyTypeForm(request.POST)
        if form.is_valid():
            ptype = form.save()
            messages.success(request, f"Category '{ptype.get_name_display()}' added.")
            return redirect("admin_property_types")
        messages.error(request, "Category already exists or invalid selection.")

    property_types = (
        PropertyType.objects.prefetch_related("properties")
        .annotate(property_count=Count("properties"))
        .order_by("-property_count", "name")
    )
    return render(
        request,
        "admin/property_types.html",
        {"property_types": property_types, "form": form},
    )


@login_required
def AdminDeletePropertyTypeView(request, pk):
    if not _is_admin(request.user):
        messages.error(request, "Administrator access required.")
        return redirect("home")
    if request.method == "POST":
        ptype = get_object_or_404(PropertyType, pk=pk)
        label = ptype.get_name_display()
        ptype.delete()
        messages.success(request, f"Category '{label}' removed.")
    return redirect("admin_property_types")


@login_required
def AdminUserListView(request):
    if not _is_admin(request.user):
        messages.error(request, "Administrator access required.")
        return redirect("home")

    create_form = AdminCreateUserForm()
    if request.method == "POST":
        create_form = AdminCreateUserForm(request.POST)
        if create_form.is_valid():
            new_user = create_form.save()
            messages.success(request, f"User account '{new_user.username}' created.")
            return redirect("admin_user_list")
        messages.error(request, "Could not create user. Review the form errors.")

    users_qs = User.objects.all().order_by("-date_joined")
    search_query = (request.GET.get("search") or "").strip()
    role_filter = (request.GET.get("role") or "").strip()

    if search_query:
        users_qs = users_qs.filter(
            Q(username__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
        )
    if role_filter:
        users_qs = users_qs.filter(role=role_filter)

    paginator = Paginator(users_qs, 15)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "admin/admin_user_list.html",
        {
            "users": page_obj,
            "page_obj": page_obj,
            "create_form": create_form,
            "search_query": search_query,
            "role_filter": role_filter,
        },
    )


def _guard_demo_account(request, target):
    """Protect the showcase demo accounts from destructive changes during public tours."""
    if target.username in DEMO_PROTECTED_USERNAMES:
        messages.warning(
            request,
            f"Showcase demo account '{target.username}' is locked in its demo state so every visitor can tour it.",
        )
        return True
    return False


@login_required
def AdminUpdateUserRoleView(request, pk):
    if not _is_admin(request.user):
        return redirect("home")
    if request.method == "POST":
        target = get_object_or_404(User, pk=pk)
        if _guard_demo_account(request, target):
            return _safe_redirect(request, request.META.get("HTTP_REFERER"), "admin_user_list")
        new_role = request.POST.get("role")
        if new_role in {User.BUYER, User.AGENT, User.ADMIN}:
            if target.pk == request.user.pk and new_role != User.ADMIN:
                messages.warning(request, "You cannot demote your own administrator role here.")
            else:
                target.role = new_role
                target.save(update_fields=["role"])
                messages.success(request, f"Updated '{target.username}' role to {target.get_role_display()}.")
    return _safe_redirect(request, request.META.get("HTTP_REFERER"), "admin_user_list")


@login_required
def AdminToggleUserActiveView(request, pk):
    if not _is_admin(request.user):
        return redirect("home")
    if request.method == "POST":
        target = get_object_or_404(User, pk=pk)
        if _guard_demo_account(request, target):
            return _safe_redirect(request, request.META.get("HTTP_REFERER"), "admin_user_list")
        if target.pk == request.user.pk:
            messages.warning(request, "You cannot deactivate your own logged-in account.")
        else:
            target.is_active = not target.is_active
            target.save(update_fields=["is_active"])
            state = "activated" if target.is_active else "suspended"
            messages.success(request, f"Account '{target.username}' has been {state}.")
    return _safe_redirect(request, request.META.get("HTTP_REFERER"), "admin_user_list")


@login_required
def AdminDeleteUserView(request, pk):
    if not _is_admin(request.user):
        return redirect("home")
    if request.method == "POST":
        target = get_object_or_404(User, pk=pk)
        if _guard_demo_account(request, target):
            return _safe_redirect(request, request.META.get("HTTP_REFERER"), "admin_user_list")
        if target.pk == request.user.pk:
            messages.error(request, "You cannot delete your own active session account.")
        else:
            uname = target.username
            target.delete()
            messages.success(request, f"User '{uname}' permanently deleted.")
    return _safe_redirect(request, request.META.get("HTTP_REFERER"), "admin_user_list")


@login_required
def AdminAgentListView(request):
    if not _is_admin(request.user):
        messages.error(request, "Administrator access required.")
        return redirect("home")

    create_form = AdminCreateUserForm(initial={"role": User.AGENT, "is_active": True})
    if request.method == "POST":
        post_data = request.POST.copy()
        post_data["role"] = User.AGENT
        create_form = AdminCreateUserForm(post_data)
        if create_form.is_valid():
            agent = create_form.save()
            messages.success(request, f"Partner agent '{agent.username}' registered.")
            return redirect("admin_agent_list")
        messages.error(request, "Could not register agent. Check highlighted fields.")

    agents_qs = (
        User.objects.filter(role="agent")
        .annotate(
            listing_count=Count("property", distinct=True),
            active_listing_count=Count("property", filter=Q(property__status="available"), distinct=True),
        )
        .order_by("-date_joined")
    )
    search_query = (request.GET.get("search") or "").strip()
    if search_query:
        agents_qs = agents_qs.filter(
            Q(username__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
        )

    return render(
        request,
        "admin/admin_agent_list.html",
        {
            "agents": agents_qs,
            "create_form": create_form,
            "search_query": search_query,
        },
    )


@login_required
def AdminTourRequestsView(request):
    if not _is_admin(request.user):
        messages.error(request, "Administrator access required.")
        return redirect("home")

    bookings = (
        TourBooking.objects.select_related("property__agent", "buyer")
        .prefetch_related("property__images")
        .order_by("-created_at")
    )
    status_filter = (request.GET.get("status") or "all").strip()
    if status_filter and status_filter.lower() != "all":
        bookings = bookings.filter(status__iexact=status_filter)

    paginator = Paginator(bookings, 15)
    page_obj = paginator.get_page(request.GET.get("page"))
    for booking in page_obj:
        imgs = list(booking.property.images.all())
        booking.property.first_image = imgs[0] if imgs else None

    return render(
        request,
        "admin/admin_tour_requests.html",
        {
            "bookings": page_obj,
            "page_obj": page_obj,
            "status_filter": status_filter,
        },
    )


@login_required
def AdminInquiryListView(request):
    if not _is_admin(request.user):
        messages.error(request, "Administrator access required.")
        return redirect("home")

    inquiries = ContactMessage.objects.select_related("property", "user").order_by("-created_at")
    filter_status = request.GET.get("status", "all")
    if filter_status == "open":
        inquiries = inquiries.filter(is_resolved=False)
    elif filter_status == "resolved":
        inquiries = inquiries.filter(is_resolved=True)

    return render(
        request,
        "admin/admin_inquiries.html",
        {"inquiries": inquiries, "filter_status": filter_status},
    )


@login_required
def AdminToggleInquiryView(request, pk):
    if not _is_admin(request.user):
        return redirect("home")
    if request.method == "POST":
        inquiry = get_object_or_404(ContactMessage, pk=pk)
        inquiry.is_resolved = not inquiry.is_resolved
        inquiry.save(update_fields=["is_resolved"])
        messages.success(
            request,
            "Inquiry marked as resolved." if inquiry.is_resolved else "Inquiry reopened.",
        )
    return _safe_redirect(request, request.META.get("HTTP_REFERER"), "admin_inquiries")


@login_required
def AdminExportReportView(request):
    if not _is_admin(request.user):
        messages.error(request, "Administrator access required.")
        return redirect("home")

    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="propnest_portfolio_report.csv"'
    response.write("\ufeff")

    writer = csv.writer(response)
    writer.writerow(
        [
            "Property ID",
            "Title",
            "Category",
            "Listing Type",
            "Status",
            "Price (USD)",
            "Area (Sq Ft)",
            "Bedrooms",
            "Bathrooms",
            "City",
            "Location",
            "Agent",
            "Tour Requests",
            "Featured",
            "Created At",
        ]
    )

    properties = (
        Property.objects.select_related("property_type", "agent")
        .annotate(tour_total=Count("tour_bookings"))
        .order_by("-created_at")
    )
    for prop in properties:
        writer.writerow(
            [
                prop.id,
                prop.title,
                prop.property_type.get_name_display() if prop.property_type else "Residence",
                prop.get_listing_type_display(),
                prop.get_status_display(),
                str(prop.price),
                prop.area_sqft,
                prop.bedrooms or "",
                prop.bathrooms or "",
                prop.city,
                prop.location,
                prop.agent.get_full_name() or prop.agent.username,
                prop.tour_total,
                "Yes" if prop.is_featured else "No",
                prop.created_at.strftime("%Y-%m-%d %H:%M"),
            ]
        )

    return response


# =========================================================================
# PUBLIC DETAIL & BUYER SAVED PROPERTIES
# =========================================================================


class PropertyDetailView(DetailView):
    model = Property
    template_name = "property_detail.html"
    context_object_name = "property"
    pk_url_kwarg = "id"

    def get_queryset(self):
        return Property.objects.select_related("agent", "property_type").prefetch_related("images")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        prop = self.get_object()
        images_list = list(prop.images.all())

        is_saved = False
        user_booking = None
        if self.request.user.is_authenticated:
            is_saved = SavedProperty.objects.filter(user=self.request.user, property=prop).exists()
            user_booking = (
                TourBooking.objects.filter(buyer=self.request.user, property=prop)
                .order_by("-created_at")
                .first()
            )

        similar_qs = (
            Property.objects.select_related("property_type", "agent")
            .prefetch_related("images")
            .filter(status="available")
            .exclude(id=prop.id)
        )
        if prop.property_type_id:
            similar_qs = similar_qs.filter(
                Q(property_type=prop.property_type) | Q(city__iexact=prop.city)
            )
        similar_properties = list(similar_qs.order_by("-is_featured", "-created_at")[:3])
        for sp in similar_properties:
            sp_imgs = list(sp.images.all())
            sp.first_image = sp_imgs[0] if sp_imgs else None

        city_key = (prop.city or "dhaka").strip().lower()
        fallback_lat, fallback_lng = CITY_COORDS.get(city_key, (23.7937, 90.4066))

        reviews = list(prop.reviews.select_related("reviewer"))
        review_count = len(reviews)
        review_avg = round(sum(r.rating for r in reviews) / review_count, 1) if review_count else None
        can_review = False
        user_review = None
        if self.request.user.is_authenticated and self.request.user != prop.agent:
            can_review = TourBooking.objects.filter(
                property=prop, buyer=self.request.user, status="Completed"
            ).exists()
            user_review = next((r for r in reviews if r.reviewer_id == self.request.user.id), None)

        context["images_list"] = images_list
        context["is_saved"] = is_saved
        context["user_booking"] = user_booking
        context["can_manage"] = _can_manage_property(self.request.user, prop)
        context["similar_properties"] = similar_properties
        context["map_lat"] = float(prop.latitude) if prop.latitude is not None else fallback_lat
        context["map_lng"] = float(prop.longitude) if prop.longitude is not None else fallback_lng
        context["form"] = kwargs.get("form") or TourBookingForm()
        context["reviews"] = reviews
        context["review_count"] = review_count
        context["review_avg"] = review_avg
        context["can_review"] = can_review
        context["user_review"] = user_review
        context["review_form"] = kwargs.get("review_form") or PropertyReviewForm(instance=user_review)
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()

        if not request.user.is_authenticated:
            messages.error(request, "Please sign in to schedule a private viewing.")
            return redirect(f"/login/?next=/property/{self.object.id}/")

        if request.user == self.object.agent:
            messages.error(request, "You cannot book a viewing on your own property.")
            return redirect("property_detail", id=self.object.id)

        if self.object.status != "available":
            messages.error(
                request,
                f"This residence is currently marked '{self.object.get_status_display()}' and cannot accept new tour bookings.",
            )
            return redirect("property_detail", id=self.object.id)

        if TourBooking.objects.filter(
            property=self.object, buyer=request.user, status__in=["Pending", "Confirmed"]
        ).exists():
            messages.warning(
                request,
                "You already have an active Pending or Confirmed walkthrough for this residence.",
            )
            return redirect("property_detail", id=self.object.id)

        form = TourBookingForm(request.POST)
        if form.is_valid():
            booking = form.save(commit=False)
            if TourBooking.objects.filter(
                property=self.object,
                scheduled_date=booking.scheduled_date,
                scheduled_time=booking.scheduled_time,
                status="Confirmed",
            ).exists():
                form.add_error(
                    "scheduled_time",
                    "Another private tour is already confirmed for this exact date and time. Please choose a different slot.",
                )
            else:
                booking.property = self.object
                booking.buyer = request.user
                booking.save()
                messages.success(request, "Private tour scheduled! The assigned advisor will confirm shortly.")
                return redirect("property_detail", id=self.object.id)

        messages.error(request, "Please fix the scheduling details below.")
        return self.render_to_response(self.get_context_data(form=form))


@login_required
@require_POST
def SubmitPropertyReviewView(request, id):
    prop = get_object_or_404(Property, id=id)
    if request.user == prop.agent:
        messages.error(request, "Property advisors cannot submit reviews for their own listings.")
        return redirect("property_detail", id=prop.id)

    has_completed_tour = TourBooking.objects.filter(
        property=prop, buyer=request.user, status="Completed"
    ).exists()
    if not has_completed_tour:
        messages.error(
            request,
            "Verified buyer reviews are unlocked after completing an on-site walkthrough.",
        )
        return redirect("property_detail", id=prop.id)

    existing = PropertyReview.objects.filter(property=prop, reviewer=request.user).first()
    form = PropertyReviewForm(request.POST, instance=existing)
    if form.is_valid():
        review = form.save(commit=False)
        review.property = prop
        review.reviewer = request.user
        review.save()
        messages.success(
            request,
            "Your verified buyer review has been updated." if existing else "Thank you — your verified review is now published.",
        )
        return redirect(f"{reverse('property_detail', kwargs={'id': prop.id})}#reviews")

    messages.error(request, "Please select a star rating and provide your impressions.")
    return redirect(f"{reverse('property_detail', kwargs={'id': prop.id})}#reviews")


@login_required
@require_POST
def ToggleSavePropertyView(request, id):
    prop = get_object_or_404(Property, id=id)
    saved_item = SavedProperty.objects.filter(user=request.user, property=prop).first()

    if saved_item:
        saved_item.delete()
        is_saved = False
        msg = f"Removed '{prop.title}' from saved residences."
    else:
        SavedProperty.objects.create(user=request.user, property=prop)
        is_saved = True
        msg = f"Saved '{prop.title}' to your wishlist."

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse(
            {
                "saved": is_saved,
                "saved_count": SavedProperty.objects.filter(user=request.user).count(),
                "message": msg,
            }
        )

    messages.success(request, msg)
    fallback = request.POST.get("next") or request.META.get("HTTP_REFERER")
    return _safe_redirect(request, fallback, "property_detail", id=prop.id)


@login_required
def SavedPropertiesView(request):
    saved_items = (
        SavedProperty.objects.filter(user=request.user)
        .select_related("property", "property__property_type", "property__agent")
        .prefetch_related("property__images")
        .order_by("-saved_at")
    )
    for item in saved_items:
        imgs = list(item.property.images.all())
        item.property.first_image = imgs[0] if imgs else None

    return render(request, "saved_properties.html", {"saved_items": saved_items})


def ComparePropertiesView(request):
    raw_ids = request.GET.get("ids", "")
    parsed_ids = []
    for part in raw_ids.split(","):
        cleaned = part.strip()
        if cleaned.isdigit():
            pid = int(cleaned)
            if pid not in parsed_ids:
                parsed_ids.append(pid)
        if len(parsed_ids) >= 4:
            break

    base_qs = (
        Property.objects.select_related("property_type", "agent")
        .prefetch_related("images")
        .annotate(avg_rating=Avg("reviews__rating"), reviews_total=Count("reviews", distinct=True))
    )
    if parsed_ids:
        prop_map = {p.id: p for p in base_qs.filter(id__in=parsed_ids)}
        properties = [prop_map[pid] for pid in parsed_ids if pid in prop_map]
    else:
        properties = list(base_qs.filter(status="available").order_by("-is_featured", "-created_at")[:3])

    for prop in properties:
        imgs = list(prop.images.all())
        prop.first_image = imgs[0] if imgs else None
        prop.price_per_sqft = round(float(prop.price) / prop.area_sqft, 2) if prop.area_sqft else None

    saved_ids = set()
    if request.user.is_authenticated:
        saved_ids = set(
            SavedProperty.objects.filter(user=request.user).values_list("property_id", flat=True)
        )

    amenity_rows = [
        (code, label, [code in (p.amenities or []) for p in properties])
        for code, label in AMENITY_CHOICES
    ]

    return render(
        request,
        "compare_properties.html",
        {
            "properties": properties,
            "is_default_showcase": not bool(parsed_ids),
            "saved_ids": saved_ids,
            "amenity_rows": amenity_rows,
        },
    )


@login_required
def NotificationListView(request):
    qs = Notification.objects.filter(recipient=request.user).select_related("actor")
    paginator = Paginator(qs, 20)
    page_obj = paginator.get_page(request.GET.get("page"))
    unread_count = qs.filter(is_read=False).count()
    return render(
        request,
        "notifications.html",
        {
            "notifications": page_obj,
            "page_obj": page_obj,
            "unread_count": unread_count,
        },
    )


@login_required
@require_POST
def MarkNotificationReadView(request, pk):
    notif = get_object_or_404(Notification, pk=pk, recipient=request.user)
    if not notif.is_read:
        notif.is_read = True
        notif.save(update_fields=["is_read"])

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse(
            {
                "ok": True,
                "unread_count": Notification.objects.filter(recipient=request.user, is_read=False).count(),
            }
        )

    follow_url = request.POST.get("next") or notif.link
    return _safe_redirect(request, follow_url, "notifications")


@login_required
@require_POST
def MarkAllNotificationsReadView(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "unread_count": 0})
    messages.success(request, "All notifications marked as read.")
    return _safe_redirect(request, request.POST.get("next") or request.META.get("HTTP_REFERER"), "notifications")
