from django.db import models
from django.contrib.auth import get_user_model

# Create your models here.
User = get_user_model()

class PropertyType(models.Model):
    CHOICE = [
        ('apartment', 'Apartment'),
        ('house', 'House'),
        ('villa', 'Villa'),
        ('land', 'Land'),
        ("shop", "Shop"),
        ("office", "Office"),
    ]
    name = models.CharField(max_length=20, choices=CHOICE, unique=True)
    
    def __str__(self):
        return self.name
    
class Property(models.Model):
    LISTIONG_CHOICE = [
        ('sale', 'For Sale'),
        ('rent', 'For Rent'),
    ]
    STATUS_CHOICE = [
        ('available', 'Available'),
        ('sold', 'Sold'),
        ('rented', 'Rented'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=12, decimal_places=2)
    area_sqft = models.PositiveBigIntegerField()
    
    bedrooms = models.PositiveIntegerField(null=True, blank=True)
    bathrooms = models.PositiveIntegerField(null=True, blank=True)
    
    listing_type = models.CharField(max_length=10, choices=LISTIONG_CHOICE)
    status = models.CharField(max_length=10, choices=STATUS_CHOICE, default='available')
    
    location = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    
    agent = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role': 'agent'})
    property_type = models.ForeignKey(PropertyType, on_delete=models.SET_NULL, null=True, related_name='properties')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_featured = models.BooleanField(default=False)
    
    def __str__(self):
        return self.title
    
    
class PropertyImage(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='property_images/')
    
    def __str__(self):
        return f"Image for {self.property.title}"
    
    
class TourBooking(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Cancelled', 'Cancelled'),
        ('Completed', 'Completed'),
    )

    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='tour_bookings')
    buyer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tour_bookings')
    
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField()
    message = models.TextField(blank=True, null=True)
    agent_message = models.TextField(blank=True, null=True, help_text="Message from agent regarding status update") 
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at'] 

    def __str__(self):
        return f"Tour for {self.property.title} by {self.buyer.username}"


class SavedProperty(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_properties')
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='saved_by_users')
    saved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'property')
        ordering = ['-saved_at']

    def __str__(self):
        return f"{self.user.username} saved {self.property.title}"