import django
from django.db import models
from django.contrib.auth.models import AbstractUser
from cloudinary.models import CloudinaryField

# Create your models here.

class CustomUser(AbstractUser):
    ADMIN = 'admin'
    AGENT = 'agent'
    BUYER = 'buyer'
    
    USER_TYPE_CHOICES = [
        (ADMIN, 'Admin'),
        (AGENT, 'Agent'),
        (BUYER, 'Buyer'),
    ]
    
    role = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default=BUYER)
    profile = CloudinaryField('Profile Image', folder='profile_pics', null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    bio = models.TextField(null=True, blank=True)
    
    def __str__(self):
        return self.username


