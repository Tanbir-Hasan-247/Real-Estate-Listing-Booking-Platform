import logging

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import CustomUser

logger = logging.getLogger(__name__)


def send_user_activation_email(user, base_url=None):
    """Send account activation link using clean formatting and configured frontend URL."""
    token = default_token_generator.make_token(user)
    root = (base_url or settings.FRONTEND_URL or "http://127.0.0.1:8000").rstrip("/")
    activation_url = f"{root}/activate/{user.id}/{token}/"

    subject = "Activate Your PropNest Architectural Account"
    message = (
        f"Hello {user.first_name or user.username},\n\n"
        f"Welcome to PropNest Real Estate. Please activate your account by clicking the link below:\n"
        f"{activation_url}\n\n"
        f"If you did not create this account, you can safely ignore this message.\n\n"
        f"Regards,\nPropNest Concierge"
    )
    recipient_list = [user.email] if user.email else []
    if not recipient_list:
        return activation_url

    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            recipient_list,
            fail_silently=False,
        )
    except Exception as exc:
        logger.warning("Failed to send activation email to %s: %s", user.email, exc)
    return activation_url


@receiver(post_save, sender=CustomUser)
def send_activation_email(sender, instance, created, **kwargs):
    if (
        created
        and not instance.is_active
        and not instance.is_superuser
        and not getattr(instance, "_defer_activation_email", False)
    ):
        send_user_activation_email(instance)
