import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.urls import reverse

from .models import ContactMessage, Notification, PropertyReview, TourBooking

logger = logging.getLogger(__name__)
User = get_user_model()


@receiver(pre_save, sender=TourBooking)
def capture_previous_tour_status(sender, instance, **kwargs):
    if instance.pk:
        previous = TourBooking.objects.filter(pk=instance.pk).values("status").first()
        instance._previous_status = previous["status"] if previous else None
    else:
        instance._previous_status = None


@receiver(post_save, sender=TourBooking)
def handle_tour_booking_notifications(sender, instance, created, **kwargs):
    buyer_name = instance.buyer.get_full_name() or instance.buyer.username
    prev_status = getattr(instance, "_previous_status", None)

    if created:
        Notification.objects.create(
            recipient=instance.property.agent,
            actor=instance.buyer,
            category="tour",
            title=f"New Tour Request: {instance.property.title}",
            message=(
                f"{buyer_name} requested a private walkthrough on "
                f"{instance.scheduled_date} at {instance.scheduled_time}."
            ),
            link=reverse("agent_tour_requests"),
        )
        return

    # Notify recipient cleanly when status changes
    if prev_status != instance.status:
        if instance.status == "Cancelled":
            Notification.objects.create(
                recipient=instance.property.agent,
                actor=instance.buyer,
                category="tour",
                title=f"Tour Cancelled: {instance.property.title}",
                message=(
                    f"The private tour on {instance.scheduled_date} at "
                    f"{instance.scheduled_time} has been cancelled."
                ),
                link=reverse("agent_tour_requests"),
            )
        else:
            Notification.objects.create(
                recipient=instance.buyer,
                actor=instance.property.agent,
                category="tour",
                title=f"Tour {instance.status}: {instance.property.title}",
                message=(
                    instance.agent_message
                    or f"Your walkthrough on {instance.scheduled_date} at {instance.scheduled_time} is now {instance.status}."
                ),
                link=reverse("my_tours"),
            )

    if not instance.buyer.email:
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


@receiver(post_save, sender=PropertyReview)
def notify_agent_on_review(sender, instance, created, **kwargs):
    if not created:
        return
    reviewer_name = instance.reviewer.get_full_name() or instance.reviewer.username
    Notification.objects.create(
        recipient=instance.property.agent,
        actor=instance.reviewer,
        category="review",
        title=f"Verified {instance.rating}★ Review on {instance.property.title}",
        message=f"{reviewer_name}: \"{instance.comment[:160]}\"",
        link=reverse("property_detail", kwargs={"id": instance.property_id}),
    )


@receiver(post_save, sender=ContactMessage)
def notify_admins_on_inquiry(sender, instance, created, **kwargs):
    if not created:
        return
    admins = User.objects.filter(is_active=True, role="admin")
    notifications = [
        Notification(
            recipient=admin_user,
            actor=instance.user,
            category="inquiry",
            title=f"New Inquiry: {instance.subject[:120]}",
            message=f"From {instance.name} ({instance.email}): {instance.message[:160]}",
            link=reverse("admin_inquiries"),
        )
        for admin_user in admins
    ]
    if notifications:
        Notification.objects.bulk_create(notifications)
