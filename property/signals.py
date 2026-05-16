from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import TourBooking 

@receiver(post_save, sender=TourBooking)
def send_tour_status_email(sender, instance, created, **kwargs):
    if not created:
        
        subject = f"Tour Update: {instance.property.title} - {instance.status}"
        
        if instance.agent_message:
            message = (
                f"Hello {instance.buyer.first_name or instance.buyer.username},\n\n"
                f"The status of your tour request for '{instance.property.title}' has been updated to: {instance.status.upper()}.\n\n"
                f"Message from the Agent/Admin:\n"
                f"\"{instance.agent_message}\"\n\n"
                f"Scheduled Date: {instance.scheduled_date}\n"
                f"Scheduled Time: {instance.scheduled_time}\n\n"
                f"Thank you,\nPropNest Team"
            )
        else:
            message = (
                f"Hello {instance.buyer.first_name or instance.buyer.username},\n\n"
                f"The status of your tour request for '{instance.property.title}' has been updated to: {instance.status.upper()}.\n\n"
                f"Scheduled Date: {instance.scheduled_date}\n"
                f"Scheduled Time: {instance.scheduled_time}\n\n"
                f"Thank you,\nPropNest Team"
            )

        recipient_list = [instance.buyer.email] 

        try:
            send_mail(
                subject, 
                message,
                settings.EMAIL_HOST_USER, 
                recipient_list,
                fail_silently=False 
            )
            print(f"Status update email sent to {instance.buyer.email}")
        except Exception as e:
            print(f"Failed to send email to {instance.buyer.email}: {str(e)}")