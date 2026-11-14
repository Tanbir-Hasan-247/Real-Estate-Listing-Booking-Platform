from django.contrib import admin
from .models import (
    ContactMessage,
    Notification,
    Property,
    PropertyImage,
    PropertyReview,
    PropertyType,
    SavedProperty,
    TourBooking,
)

admin.site.site_header = "PropNest Architectural Admin"
admin.site.site_title = "PropNest Admin Portal"

admin.site.register(PropertyType)
admin.site.register(Property)
admin.site.register(PropertyImage)
admin.site.register(TourBooking)
admin.site.register(SavedProperty)
admin.site.register(ContactMessage)
admin.site.register(PropertyReview)
admin.site.register(Notification)