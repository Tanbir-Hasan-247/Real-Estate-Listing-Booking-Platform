import builtins
from django.db import models
from django.contrib.auth import get_user_model
from django.templatetags.static import static
from cloudinary.models import CloudinaryField

# Create your models here.
User = get_user_model()

FALLBACK_ARCH_IMAGES = (
    "assets/menu-0.avif",
    "assets/menu-1.avif",
    "assets/menu-2.avif",
    "assets/menu-3.avif",
    "assets/menu-4.avif",
    "assets/menu-5.avif",
)


def is_placeholder_image(field_value):
    """Return True if a CloudinaryField value is missing or the dead seeded default.png placeholder."""
    if not field_value:
        return True
    raw = str(getattr(field_value, "public_id", None) or field_value or "")
    return (not raw.strip()) or raw.strip().endswith("default.png") or raw.strip().endswith("/default")

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

    @property
    def primary_image_url(self):
        """Return the first real image URL or a curated local architectural fallback."""
        for img in self.images.all():
            if not is_placeholder_image(img.image):
                try:
                    return img.image.url
                except Exception:
                    pass
        idx = (self.id or 0) % len(FALLBACK_ARCH_IMAGES)
        return static(FALLBACK_ARCH_IMAGES[idx])
    
    
class PropertyImage(models.Model):
    property = models.ForeignKey(Property, on_delete=models.CASCADE, related_name='images')
    image = CloudinaryField('Image', folder='property_images')
    
    def __str__(self):
        return f"Image for {self.property.title}"

    @builtins.property
    def safe_url(self):
        """Return uploaded Cloudinary image URL unless placeholder default.png, else architectural fallback."""
        if not is_placeholder_image(self.image):
            try:
                return self.image.url
            except Exception:
                pass
        idx = ((self.property_id or 0) + (self.id or 0)) % len(FALLBACK_ARCH_IMAGES)
        return static(FALLBACK_ARCH_IMAGES[idx])
    
    
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


class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=30, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    property = models.ForeignKey(
        Property,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inquiries',
    )
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='inquiries',
    )
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.subject} — {self.name}"
