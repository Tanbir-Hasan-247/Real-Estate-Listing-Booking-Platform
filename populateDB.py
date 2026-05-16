import os
import random
from decimal import Decimal

import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Real_Estate.settings')
django.setup()

from users.models import CustomUser
from property.models import PropertyType, Property, PropertyImage

# --------------------------------------------------
# CREATE PROPERTY TYPES
# --------------------------------------------------

property_types_data = [
    'apartment',
    'house',
    'villa',
    'land',
    'shop',
    'office',
]

property_types = {}

for pt in property_types_data:
    obj, created = PropertyType.objects.get_or_create(name=pt)
    property_types[pt] = obj

print("Property types populated.")

# --------------------------------------------------
# CREATE AGENTS
# --------------------------------------------------

agents = []

for i in range(1, 6):
    username = f'agent{i}'

    agent, created = CustomUser.objects.get_or_create(
        username=username,
        defaults={
            'email': f'agent{i}@example.com',
            'role': 'agent',
            'phone': f'0170000000{i}',
            'bio': f'I am professional real estate agent {i}.'
        }
    )

    if created:
        agent.set_password('Agent123!')
        agent.save()

    agents.append(agent)

print("Agents populated.")

# --------------------------------------------------
# SAMPLE DATA
# --------------------------------------------------

titles = [
    "Luxury Apartment in Dhaka",
    "Modern Family House",
    "Beautiful Villa with Garden",
    "Commercial Office Space",
    "Affordable Shop for Business",
    "Premium Land Plot",
    "City View Apartment",
    "Duplex House",
    "Lake Side Villa",
    "Corporate Office",
    "Small Retail Shop",
    "Residential Land",
    "Penthouse Apartment",
    "Classic House",
    "Private Villa",
    "Business Office",
    "Mini Shopping Space",
    "Large Land Area",
    "Stylish Apartment",
    "Dream Family Home",
]

cities = [
    "Dhaka",
    "Chattogram",
    "Sylhet",
    "Khulna",
    "Rajshahi",
]

states = [
    "Dhaka",
    "Chattogram",
    "Sylhet",
]

locations = [
    "Banani",
    "Gulshan",
    "Dhanmondi",
    "Uttara",
    "Mirpur",
    "Bashundhara",
    "Mohammadpur",
]

descriptions = [
    "Beautiful property with modern facilities.",
    "Excellent location and environment.",
    "Perfect for family living.",
    "Suitable for business purposes.",
    "Prime investment opportunity.",
]

listing_types = ['sale', 'rent']
statuses = ['available', 'sold', 'rented']

# --------------------------------------------------
# CREATE 20 PROPERTIES
# --------------------------------------------------

for i in range(20):

    property_type_key = random.choice(property_types_data)

    property_obj = Property.objects.create(
        title=titles[i],
        description=random.choice(descriptions),
        price=Decimal(random.randint(50000, 5000000)),
        area_sqft=random.randint(600, 5000),

        bedrooms=random.randint(1, 6),
        bathrooms=random.randint(1, 5),

        listing_type=random.choice(listing_types),
        status=random.choice(statuses),

        location=random.choice(locations),
        city=random.choice(cities),
        state=random.choice(states),

        latitude=Decimal("23.810331"),
        longitude=Decimal("90.412521"),

        agent=random.choice(agents),
        property_type=property_types[property_type_key],

        is_featured=random.choice([True, False]),
    )

    # Optional image placeholder rows
    for j in range(random.randint(1, 3)):
        PropertyImage.objects.create(
            property=property_obj,
            image='property_images/default.png'
        )

print("20 properties populated successfully!")