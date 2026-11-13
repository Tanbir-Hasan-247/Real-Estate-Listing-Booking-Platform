from property.models import ContactMessage, Property, SavedProperty, TourBooking


def propnest_context(request):
    """Global architectural navigation badges and featured residence showcase."""
    ctx = {
        "pending_agent_tours_count": 0,
        "pending_admin_tours_count": 0,
        "unresolved_inquiries_count": 0,
        "saved_properties_count": 0,
    }
    try:
        ctx["nav_featured_properties"] = (
            Property.objects.filter(status="available")
            .only("id", "title", "city", "listing_type", "price")
            .order_by("-is_featured", "-created_at")[:4]
        )
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            ctx["saved_properties_count"] = SavedProperty.objects.filter(user=user).count()
            if getattr(user, "role", None) == "agent":
                ctx["pending_agent_tours_count"] = TourBooking.objects.filter(
                    property__agent=user, status="Pending"
                ).count()
            if getattr(user, "role", None) == "admin" or user.is_superuser:
                ctx["pending_admin_tours_count"] = TourBooking.objects.filter(
                    status="Pending"
                ).count()
                ctx["unresolved_inquiries_count"] = ContactMessage.objects.filter(
                    is_resolved=False
                ).count()
    except Exception:
        # During initial migrations before tables exist, fail safely without crashing templates
        ctx["nav_featured_properties"] = []
    return ctx
