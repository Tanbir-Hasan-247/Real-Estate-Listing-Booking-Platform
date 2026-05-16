from django.contrib import admin
from .models import PropertyType, Property, PropertyImage, TourBooking, SavedProperty
# Register your models here.
admin.site.site_header = "Real Estate Admin"
admin.site.site_title = "Real Estate Admin Portal" 

admin.site.register(PropertyType)
admin.site.register(Property)
admin.site.register(PropertyImage)
admin.site.register(TourBooking)
admin.site.register(SavedProperty)