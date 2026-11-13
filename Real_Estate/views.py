import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models import Count, Q
from django.shortcuts import redirect, render
from django.templatetags.static import static
from django.urls import reverse
from django.views import View
from django.views.generic import ListView

from property.forms import ContactForm
from property.models import Property, PropertyType, SavedProperty, TourBooking, is_placeholder_image

User = get_user_model()
logger = logging.getLogger(__name__)

DEFAULT_DHAKA_ZONES = [
    (23.7388125, 90.3780625),   # Dhanmondi / West
    (23.7719375, 90.4036875),   # Tejgaon / Central
    (23.8076875, 90.4576875),   # Bashundhara / Northeast
    (23.8165375, 90.498703125), # Jolshiri / East
]

HERO_SHOWCASE_BACKDROPS = [
    {
        "sm": "https://www.golpoholdings.com/golpo/golpo-aleya/phone/golpo-aleya-phone-hero.avif",
        "lg": "https://www.golpoholdings.com/golpo/golpo-aleya/golpo-aleya-exterior-dusk.avif",
        "card": "https://www.golpoholdings.com/golpo/golpo-aleya/golpo-aleya-exterior-dusk.m.avif",
    },
    {
        "sm": "https://www.golpoholdings.com/golpo/golpo-dar-e-salam/phone/golpo-dar-e-salam-phone-hero.avif",
        "lg": "https://www.golpoholdings.com/golpo/golpo-dar-e-salam/exterior-hero.avif",
        "card": "https://www.golpoholdings.com/golpo/golpo-dar-e-salam/exterior-hero.m.avif",
    },
]


def _property_image_url(prop, idx=0):
    imgs = list(prop.images.all())
    for img in imgs:
        if not is_placeholder_image(img.image):
            return img.image.url
    fallback_idx = idx % 6
    return static(f"assets/menu-{fallback_idx}.avif")


def _hero_image_pair(prop, idx=0):
    imgs = list(prop.images.all())
    for img in imgs:
        if not is_placeholder_image(img.image):
            u = img.image.url
            return {"sm": u, "lg": u, "card": u}
    return HERO_SHOWCASE_BACKDROPS[idx % len(HERO_SHOWCASE_BACKDROPS)]


class HomeView(View):
    def get(self, request):
        available_qs = (
            Property.objects.select_related("property_type", "agent")
            .prefetch_related("images")
            .filter(status="available")
            .order_by("-is_featured", "-created_at")
        )
        all_props = list(available_qs[:8])
        for idx, prop in enumerate(all_props):
            imgs = list(prop.images.all())
            prop.first_image = imgs[0] if imgs else None
            prop.display_img_url = _property_image_url(prop, idx)

        hero_props = all_props[:2]
        dhaka_props = [p for p in available_qs if (p.city or "").strip().lower() == "dhaka"]
        if len(dhaka_props) >= 4:
            map_props = dhaka_props[:4]
        else:
            seen_ids = {p.id for p in dhaka_props}
            map_props = list(dhaka_props) + [p for p in all_props if p.id not in seen_ids]
            map_props = map_props[:4]

        # Build Hero Carousel JSON payload
        hero_slides = []
        for idx, prop in enumerate(hero_props):
            pair = _hero_image_pair(prop, idx)
            prop.hero_sm_url = pair["sm"]
            prop.hero_lg_url = pair["lg"]
            prop.hero_card_url = pair["card"]
            words = (prop.title or "PropNest Residence").split()
            mid = max(1, len(words) // 2)
            line1 = " ".join(words[:mid])
            line2 = " ".join(words[mid:]) or prop.city
            hero_slides.append(
                {
                    "lines": [line1, line2],
                    "statusLabel": prop.get_listing_type_display().upper(),
                    "heroWord": prop.city or "Dhaka",
                    "href": reverse("property_detail", kwargs={"id": prop.id}),
                    "cardTitle": prop.title,
                    "cardLoc": (prop.city or prop.location or "DHAKA").upper(),
                    "cardImg": pair["card"],
                    "num": f"{idx + 1:02d}",
                }
            )

        # Build Interactive Map Pins payload (ensure pins in DB without distinct Dhaka spread don't stack on 1px)
        seen_coords = set()
        map_pins = []
        map_items = []
        for idx, prop in enumerate(map_props):
            lat = float(prop.latitude) if prop.latitude is not None else None
            lng = float(prop.longitude) if prop.longitude is not None else None
            coord_key = (round(lat, 4), round(lng, 4)) if (lat is not None and lng is not None) else None
            if coord_key is None or coord_key in seen_coords or (23.70 <= lat <= 23.86 and 90.35 <= lng <= 90.52 and len(seen_coords) > 0 and coord_key == (23.8103, 90.4125)):
                lat, lng = DEFAULT_DHAKA_ZONES[idx % len(DEFAULT_DHAKA_ZONES)]
            else:
                seen_coords.add(coord_key)
                # Keep overview focused on Dhaka if property is inside Dhaka metro; else blend showcase coords
                if not (23.65 <= lat <= 23.95 and 90.30 <= lng <= 90.56):
                    lat, lng = DEFAULT_DHAKA_ZONES[idx % len(DEFAULT_DHAKA_ZONES)]

            pin_key = f"prop-{prop.id}"
            detail_url = reverse("property_detail", kwargs={"id": prop.id})
            map_pins.append(
                {
                    "key": pin_key,
                    "lat": lat,
                    "lng": lng,
                    "title": prop.title,
                    "city": prop.city,
                    "href": detail_url,
                }
            )
            map_items.append(
                {
                    "key": pin_key,
                    "property": prop,
                    "url": detail_url,
                }
            )

        total_properties = Property.objects.count()
        available_count = Property.objects.filter(status="available").count()
        total_agents = User.objects.filter(role=User.AGENT).count()
        cities_count = Property.objects.values("city").distinct().count()
        total_tours = TourBooking.objects.count()

        home_json_data = {
            "heroSlides": hero_slides,
            "mapPins": map_pins,
            "towerTargets": [
                max(total_properties, 1),
                max(available_count, 1),
                max(cities_count, 1),
                max(total_agents, 1),
            ],
        }

        context = {
            "properties": all_props,
            "hero_props": hero_props,
            "map_items": map_items,
            "total_properties": total_properties,
            "available_count": available_count,
            "total_agents": total_agents,
            "cities_count": cities_count,
            "total_tours": total_tours,
            "property_types": PropertyType.objects.all().order_by("name"),
            "home_json_data": home_json_data,
        }
        return render(request, "home.html", context)


class PropertyListView(ListView):
    model = Property
    template_name = "property_list.html"
    context_object_name = "properties"
    paginate_by = 9

    def get_queryset(self):
        queryset = (
            Property.objects.select_related("property_type", "agent")
            .prefetch_related("images")
            .filter(status="available")
        )
        search_query = (self.request.GET.get("search") or "").strip()
        listing_type = (self.request.GET.get("listing_type") or "").strip()
        property_type = (self.request.GET.get("property_type") or "").strip()
        city = (self.request.GET.get("city") or "").strip()
        bedrooms = (self.request.GET.get("bedrooms") or "").strip()
        min_price = (self.request.GET.get("min_price") or "").strip()
        max_price = (self.request.GET.get("max_price") or "").strip()
        sort_by = (self.request.GET.get("sort") or "").strip()

        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query)
                | Q(location__icontains=search_query)
                | Q(city__icontains=search_query)
                | Q(description__icontains=search_query)
            )
        if listing_type in {"sale", "rent"}:
            queryset = queryset.filter(listing_type=listing_type)
        if property_type:
            queryset = queryset.filter(property_type__name__iexact=property_type)
        if city:
            queryset = queryset.filter(city__iexact=city)
        if bedrooms and bedrooms.isdigit():
            queryset = queryset.filter(bedrooms__gte=int(bedrooms))
        if min_price:
            try:
                queryset = queryset.filter(price__gte=float(min_price))
            except ValueError:
                pass
        if max_price:
            try:
                queryset = queryset.filter(price__lte=float(max_price))
            except ValueError:
                pass

        if sort_by == "price_asc":
            queryset = queryset.order_by("price")
        elif sort_by == "price_desc":
            queryset = queryset.order_by("-price")
        elif sort_by == "area_desc":
            queryset = queryset.order_by("-area_sqft")
        else:
            queryset = queryset.order_by("-is_featured", "-created_at")

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        for idx, prop in enumerate(context["properties"]):
            imgs = list(prop.images.all())
            prop.first_image = imgs[0] if imgs else None
            prop.display_img_url = _property_image_url(prop, idx)

        saved_ids = set()
        if self.request.user.is_authenticated:
            saved_ids = set(
                SavedProperty.objects.filter(user=self.request.user).values_list("property_id", flat=True)
            )

        query_params = self.request.GET.copy()
        query_params.pop("page", None)

        context["saved_ids"] = saved_ids
        context["property_types"] = PropertyType.objects.all().order_by("name")
        context["cities"] = (
            Property.objects.filter(status="available")
            .values_list("city", flat=True)
            .distinct()
            .order_by("city")
        )
        context["querystring"] = query_params.urlencode()
        context["selected_filters"] = {
            "search": self.request.GET.get("search", ""),
            "listing_type": self.request.GET.get("listing_type", ""),
            "property_type": self.request.GET.get("property_type", ""),
            "city": self.request.GET.get("city", ""),
            "bedrooms": self.request.GET.get("bedrooms", ""),
            "min_price": self.request.GET.get("min_price", ""),
            "max_price": self.request.GET.get("max_price", ""),
            "sort": self.request.GET.get("sort", ""),
        }
        return context


class AgentListView(ListView):
    model = User
    template_name = "agent/agent_list.html"
    context_object_name = "agents"

    def get_queryset(self):
        agents = User.objects.filter(role=User.AGENT).annotate(
            property_count=Count("property", filter=Q(property__status="available")),
            total_listings=Count("property"),
        ).order_by("-property_count", "-date_joined")

        search_query = (self.request.GET.get("search") or "").strip()
        if search_query:
            agents = agents.filter(
                Q(first_name__icontains=search_query)
                | Q(last_name__icontains=search_query)
                | Q(username__icontains=search_query)
                | Q(bio__icontains=search_query)
            )
        return agents


class AboutView(View):
    def get(self, request):
        featured_agents = (
            User.objects.filter(role=User.AGENT)
            .annotate(property_count=Count("property", filter=Q(property__status="available")))
            .order_by("-property_count")[:4]
        )
        return render(
            request,
            "about.html",
            {
                "featured_agents": featured_agents,
                "total_properties": Property.objects.count(),
                "total_agents": User.objects.filter(role=User.AGENT).count(),
                "cities_count": Property.objects.values("city").distinct().count(),
            },
        )


class ContactView(View):
    def get(self, request):
        initial = {}
        if request.user.is_authenticated:
            initial["name"] = request.user.get_full_name() or request.user.username
            initial["email"] = request.user.email
            initial["phone"] = request.user.phone or ""
        prop_id = request.GET.get("property")
        if prop_id and prop_id.isdigit():
            initial["property"] = int(prop_id)
            initial["subject"] = "Private Residence Inquiry"
        form = ContactForm(initial=initial)
        return render(request, "contact.html", {"form": form})

    def post(self, request):
        form = ContactForm(request.POST)
        if form.is_valid():
            # Honeypot spam guard
            if form.cleaned_data.get("website"):
                messages.success(request, "Thank you — your message has been received.")
                return redirect("contact")

            inquiry = form.save(commit=False)
            if request.user.is_authenticated:
                inquiry.user = request.user
            inquiry.save()

            try:
                recipient = settings.EMAIL_HOST_USER or settings.DEFAULT_FROM_EMAIL
                if recipient:
                    send_mail(
                        f"[PropNest Inquiry] {inquiry.subject}",
                        f"From: {inquiry.name} ({inquiry.email} / {inquiry.phone})\n\n{inquiry.message}",
                        settings.DEFAULT_FROM_EMAIL,
                        [recipient],
                        fail_silently=True,
                    )
            except Exception as exc:
                logger.warning("Contact notification dispatch failed: %s", exc)

            messages.success(
                request,
                "Your architectural inquiry has been registered. Our senior concierge will respond shortly.",
            )
            return redirect("contact")

        messages.error(request, "Please complete all required fields before submitting.")
        return render(request, "contact.html", {"form": form})
