import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import TourBooking

logger = logging.getLogger(__name__)


@receiver(post_save, sender=TourBooking)
def send_tour_status_email(sender, instance, created, **kwargs):
    if created or not instance.buyer.email:
        return

    subject = f"Tour Update: {instance.property.title} — {instance.status}"
    greeting = instance.buyer.first_name or instance.buyer.username

    if instance.agent_message:
        message = (
            f"Hello {greeting},\n\n"
            f"The status of your private tour request for '{instance.property.title}' "
            f"has been updated to: {instance.status.upper()}.\n\n"
            f"Note from Advisor:\n\"{instance.agent_message}\"\n\n"
            f"Scheduled Date: {instance.scheduled_date}\n"
            f"Scheduled Time: {instance.scheduled_time}\n\n"
            f"Thank you,\nPropNest Real Estate"
        )
    else:
        message = (
            f"Hello {greeting},\n\n"
            f"The status of your private tour request for '{instance.property.title}' "
            f"has been updated to: {instance.status.upper()}.\n\n"
            f"Scheduled Date: {instance.scheduled_date}\n"
            f"Scheduled Time: {instance.scheduled_time}\n\n"
            f"Thank you,\nPropNest Real Estate"
        )

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [instance.buyer.email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.warning("Failed to send tour status email to %s: %s", instance.buyer.email, exc)
