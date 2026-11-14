from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

DEMO_ACCOUNTS = [
    {
        "key": "admin",
        "short_role": "Admin",
        "label": "Admin",
        "badge": "Platform Admin",
        "username": "demo_admin",
        "password": "Admin@2026",
        "role": "admin",
        "first_name": "Aarif",
        "last_name": "Mahmood",
        "email": "demo.admin@propnest.com",
        "phone": "+880 1711-800101",
        "bio": "Operations administrator overseeing verified holdings, advisor onboarding, and marketplace reports.",
        "summary": "Executive console, users, CSV reports & listings",
    },
    {
        "key": "agent",
        "short_role": "Agent",
        "label": "Advisor / Agent",
        "badge": "Licensed Advisor",
        "username": "demo_agent",
        "password": "Agent@2026",
        "role": "agent",
        "first_name": "Nadia",
        "last_name": "Rahman",
        "email": "demo.agent@propnest.com",
        "phone": "+880 1711-002233",
        "bio": "Senior architectural property advisor specializing in Gulshan, Banani, and curated urban residences.",
        "summary": "Advisor studio, listings CRUD & tour approvals",
    },
    {
        "key": "client",
        "short_role": "Client",
        "label": "Client / Buyer",
        "badge": "Verified Client",
        "username": "demo_client",
        "password": "Client@2026",
        "role": "buyer",
        "first_name": "Farhan",
        "last_name": "Ahmed",
        "email": "demo.client@propnest.com",
        "phone": "+880 1819-445566",
        "bio": "Exploring sunlit corner residences, modern workspaces, and verified private tours across Bangladesh.",
        "summary": "Saved residences, wishlist & private tour bookings",
    },
]

DEMO_PROTECTED_USERNAMES = frozenset(spec["username"] for spec in DEMO_ACCOUNTS)


def ensure_demo_accounts(seed_activity=False):
    """Ensure the 3 showcase demo accounts exist, stay active, and have realistic workspace data."""
    User = get_user_model()
    accounts_by_key = {}

    with transaction.atomic():
        for spec in DEMO_ACCOUNTS:
            user, created = User.objects.get_or_create(
                username=spec["username"],
                defaults={
                    "email": spec["email"],
                    "first_name": spec["first_name"],
                    "last_name": spec["last_name"],
                    "role": spec["role"],
                    "phone": spec["phone"],
                    "bio": spec["bio"],
                    "is_active": True,
                    "is_staff": False,
                    "is_superuser": False,
                },
            )
            changed_fields = []
            if not user.is_active:
                user.is_active = True
                changed_fields.append("is_active")
            if user.role != spec["role"]:
                user.role = spec["role"]
                changed_fields.append("role")
            if not user.email:
                user.email = spec["email"]
                changed_fields.append("email")
            if not user.first_name:
                user.first_name = spec["first_name"]
                changed_fields.append("first_name")
            if not user.last_name:
                user.last_name = spec["last_name"]
                changed_fields.append("last_name")
            if not user.phone:
                user.phone = spec["phone"]
                changed_fields.append("phone")
            if not user.bio:
                user.bio = spec["bio"]
                changed_fields.append("bio")
            if created or not user.check_password(spec["password"]):
                user.set_password(spec["password"])
                changed_fields.append("password")

            if changed_fields:
                user.save(update_fields=changed_fields)
            accounts_by_key[spec["key"]] = user

        if seed_activity:
            _seed_demo_activity(
                demo_agent=accounts_by_key["agent"],
                demo_client=accounts_by_key["client"],
            )

    return accounts_by_key


def _seed_demo_activity(demo_agent, demo_client):
    """Give the demo agent listings/leads and the demo client saved properties, amenities, tours & reviews without clobbering existing data."""
    from django.db.models import Count
    from django.urls import reverse
    from property.models import (
        AMENITY_CHOICES,
        ContactMessage,
        Notification,
        Property,
        PropertyReview,
        SavedProperty,
        TourBooking,
    )

    agent_owned_count = Property.objects.filter(agent=demo_agent).count()
    if agent_owned_count < 3 and Property.objects.exists():
        needed = 3 - agent_owned_count
        donor_agents = (
            Property.objects.values("agent_id")
            .annotate(total=Count("id"))
            .filter(total__gt=3)
            .exclude(agent_id=demo_agent.id)
            .order_by("-total")
        )
        for donor in donor_agents:
            if needed <= 0:
                break
            spare = max(0, donor["total"] - 3)
            if not spare:
                continue
            take = min(needed, spare)
            props_to_assign = list(
                Property.objects.filter(agent_id=donor["agent_id"])
                .order_by("-is_featured", "-id")[:take]
            )
            if props_to_assign:
                Property.objects.filter(pk__in=[p.pk for p in props_to_assign]).update(agent=demo_agent)
                needed -= len(props_to_assign)

    # Populate curated architectural amenities on existing showcase listings that lack them
    amenity_codes = [code for code, _ in AMENITY_CHOICES]
    props_without_amenities = list(Property.objects.order_by("id"))
    for idx, prop in enumerate(props_without_amenities):
        if not prop.amenities:
            start = idx % len(amenity_codes)
            sample = [amenity_codes[(start + offset) % len(amenity_codes)] for offset in range(4)]
            prop.amenities = sample
            prop.save(update_fields=["amenities"])

    agent_props = list(Property.objects.filter(agent=demo_agent).order_by("-id")[:3])
    all_props = agent_props or list(Property.objects.order_by("-id")[:3])
    if not all_props:
        return

    if SavedProperty.objects.filter(user=demo_client).count() == 0:
        for prop in all_props[:2]:
            SavedProperty.objects.get_or_create(user=demo_client, property=prop)

    first_prop = all_props[0]
    second_prop = all_props[1] if len(all_props) > 1 else first_prop
    third_prop = all_props[2] if len(all_props) > 2 else second_prop
    today = timezone.localdate()

    if TourBooking.objects.filter(buyer=demo_client).count() == 0:
        TourBooking.objects.create(
            property=first_prop,
            buyer=demo_client,
            scheduled_date=today + timedelta(days=3),
            scheduled_time="11:00:00",
            message="Interested in reviewing natural daylight orientation and floorplan dimensions.",
            status="Pending",
        )
        TourBooking.objects.create(
            property=second_prop,
            buyer=demo_client,
            scheduled_date=today + timedelta(days=5),
            scheduled_time="16:30:00",
            message="Requesting private architectural walkthrough with advisor.",
            agent_message="Looking forward to hosting you on site. Courtyard lobby keys reserved.",
            status="Confirmed",
        )

    # Ensure demo_client has at least one Completed walkthrough so verified review workflow is demonstrable immediately
    if not TourBooking.objects.filter(buyer=demo_client, status="Completed").exists():
        TourBooking.objects.create(
            property=third_prop,
            buyer=demo_client,
            scheduled_date=today - timedelta(days=4),
            scheduled_time="14:00:00",
            message="Afternoon solar study & acoustics walkthrough completed.",
            agent_message="Thank you for visiting! Digital dossier & floorplan measurements attached.",
            status="Completed",
        )

    # Seed verified walkthrough review if missing on third_prop
    if third_prop.agent_id != demo_client.id and not PropertyReview.objects.filter(
        property=third_prop, reviewer=demo_client
    ).exists():
        PropertyReview.objects.create(
            property=third_prop,
            reviewer=demo_client,
            rating=5,
            comment="Exceptionally quiet cross-ventilated layout, double-glazed terrace views, and thorough advisor briefing.",
        )

    # Ensure demo_client has an unread welcome/tour notification badge visible
    if Notification.objects.filter(recipient=demo_client).count() == 0:
        Notification.objects.create(
            recipient=demo_client,
            actor=demo_agent,
            category="tour",
            title=f"Tour Confirmed: {second_prop.title}",
            message="Advisor Arfan confirmed your upcoming private walkthrough at 16:30. Lobby pass is ready.",
            link=reverse("my_tours"),
        )
        Notification.objects.create(
            recipient=demo_client,
            actor=demo_agent,
            category="review",
            title=f"Review Unlocked: {third_prop.title}",
            message="Your walkthrough was marked Completed — share your verified buyer impression anytime.",
            link=f"{reverse('property_detail', kwargs={'id': third_prop.id})}#reviews",
        )

    if ContactMessage.objects.count() == 0:
        first_prop = all_props[0]
        ContactMessage.objects.create(
            name="Farhan Ahmed",
            email="demo.client@propnest.com",
            phone="+880 1819-445566",
            subject=f"Floorplan dossier & structural finish specs — {first_prop.title}",
            message="Could your advisory team share the full architectural CAD dimensions, parking allocation, and service charge breakdown ahead of our scheduled walkthrough?",
            property=first_prop,
            user=demo_client,
            is_resolved=False,
        )
        ContactMessage.objects.create(
            name="Samira Kabir",
            email="samira.kabir@example.com",
            phone="+880 1755-889900",
            subject="Corporate relocation portfolio consultation",
            message="Our executive team is evaluating multi-unit leases in Gulshan and Bashundhara for Q4 arrivals. We appreciated yesterday's briefing call.",
            is_resolved=True,
        )
