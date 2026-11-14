import datetime
import tempfile

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

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

User = get_user_model()

ONE_BY_ONE_GIF = (
    b"GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff"
    b"\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00"
    b"\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
)


class PropNestPlatformTests(TestCase):
    def setUp(self):
        self.buyer = User.objects.create_user(
            username="buyer_demo",
            email="buyer@example.com",
            password="StrongPass!2026",
            role=User.BUYER,
            first_name="Amina",
            last_name="Rahman",
            is_active=True,
        )
        self.agent = User.objects.create_user(
            username="agent_demo",
            email="agent@example.com",
            password="StrongPass!2026",
            role=User.AGENT,
            first_name="Zayan",
            last_name="Karim",
            is_active=True,
        )
        self.other_agent = User.objects.create_user(
            username="agent_two",
            email="agent2@example.com",
            password="StrongPass!2026",
            role=User.AGENT,
            is_active=True,
        )
        self.admin = User.objects.create_user(
            username="admin_demo",
            email="admin@example.com",
            password="StrongPass!2026",
            role=User.ADMIN,
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )

        self.ptype_apt = PropertyType.objects.create(name="apartment")
        self.ptype_villa = PropertyType.objects.create(name="villa")

        self.prop1 = Property.objects.create(
            title="Golpo Aleya Sky Residence",
            description="Dual-aspect architectural residence overlooking Gulshan Lake.",
            property_type=self.ptype_apt,
            listing_type="sale",
            status="available",
            price=450000,
            bedrooms=4,
            bathrooms=4,
            area_sqft=3200,
            location="Road 74, Gulshan-2",
            city="Dhaka",
            state="Dhaka Division",
            latitude=23.7937,
            longitude=90.4066,
            is_featured=True,
            agent=self.agent,
        )
        self.prop2 = Property.objects.create(
            title="Banani Courtyard Villa",
            description="Private garden residence in quiet Banani sector.",
            property_type=self.ptype_villa,
            listing_type="rent",
            status="available",
            price=3500,
            bedrooms=3,
            bathrooms=3,
            area_sqft=2400,
            location="Road 11, Banani",
            city="Dhaka",
            state="Dhaka Division",
            agent=self.other_agent,
        )

    def test_public_pages_render_with_design_system_and_no_dead_links(self):
        urls = [
            reverse("home"),
            reverse("property_list"),
            reverse("agent_list"),
            reverse("about"),
            reverse("contact"),
            reverse("property_detail", kwargs={"id": self.prop1.id}),
            reverse("properties_by_agent", kwargs={"pk": self.agent.id}),
            reverse("login"),
            reverse("register"),
            reverse("resend_activation"),
            reverse("password_reset"),
        ]
        for url in urls:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 200, f"Failed on {url}")
            html = res.content.decode("utf-8")
            self.assertIn("golpo-design.css", html)
            self.assertIn("propnest-app.css", html)
            self.assertIn("propnest-engine.js", html)
            self.assertIn('name="color-scheme"', html)
            self.assertNotIn('href="#"', html)

        # Verify HomeView JSON script block & Authenticated user/agent routes
        home_res = self.client.get(reverse("home"))
        self.assertIn('id="propnest-home-data"', home_res.content.decode("utf-8"))
        self.assertIn("heroSlides", home_res.content.decode("utf-8"))

        self.client.force_login(self.buyer)
        for u_url in [reverse("profile"), reverse("saved_properties"), reverse("my_tours")]:
            r = self.client.get(u_url)
            self.assertEqual(r.status_code, 200, f"Buyer route failed: {u_url}")
            self.assertNotIn('href="#"', r.content.decode("utf-8"))

        self.client.force_login(self.agent)
        for a_url in [reverse("agent_dashboard"), reverse("agent_property_list"), reverse("add_property"), reverse("agent_tour_requests")]:
            r = self.client.get(a_url)
            self.assertEqual(r.status_code, 200, f"Agent route failed: {a_url}")
            self.assertNotIn('href="#"', r.content.decode("utf-8"))

    def test_property_filtering_and_sorting(self):
        res = self.client.get(
            reverse("property_list"),
            {"search": "Aleya", "listing_type": "sale", "bedrooms": "3", "sort": "price_desc"},
        )
        self.assertEqual(res.status_code, 200)
        filtered = list(res.context["properties"])
        self.assertEqual([p.id for p in filtered], [self.prop1.id])

        res_city = self.client.get(reverse("property_list"), {"city": "Dhaka", "sort": "area_desc"})
        self.assertEqual(res_city.status_code, 200)
        props = list(res_city.context["properties"])
        self.assertEqual(props[0].id, self.prop1.id)

    def test_wishlist_toggle_ajax_and_saved_page(self):
        self.client.force_login(self.buyer)
        save_url = reverse("save_property", kwargs={"id": self.prop1.id})
        res = self.client.post(save_url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(res.status_code, 200)
        payload = res.json()
        self.assertTrue(payload["saved"])
        self.assertEqual(payload["saved_count"], 1)

        saved_page = self.client.get(reverse("saved_properties"))
        self.assertEqual(saved_page.status_code, 200)
        self.assertContains(saved_page, self.prop1.title)

        # Toggle off
        res2 = self.client.post(save_url, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertFalse(res2.json()["saved"])
        self.assertEqual(SavedProperty.objects.filter(user=self.buyer).count(), 0)

    def test_tour_booking_signals_and_cancellation(self):
        self.client.force_login(self.buyer)
        detail_url = reverse("property_detail", kwargs={"id": self.prop1.id})

        # Past date rejected
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
        bad_tour = self.client.post(
            detail_url,
            {"scheduled_date": yesterday, "scheduled_time": "11:00", "message": "Early"},
        )
        self.assertEqual(bad_tour.status_code, 200)
        self.assertEqual(TourBooking.objects.count(), 0)

        # Valid future date succeeds and triggers email notification
        future = (datetime.date.today() + datetime.timedelta(days=3)).isoformat()
        mail.outbox.clear()
        ok_tour = self.client.post(
            detail_url,
            {"scheduled_date": future, "scheduled_time": "15:30", "message": "Sunlit balcony view please"},
        )
        self.assertRedirects(ok_tour, detail_url)
        booking = TourBooking.objects.get(buyer=self.buyer, property=self.prop1)
        self.assertEqual(booking.status, "Pending")

        # Agent updates tour status -> triggers status email
        self.client.force_login(self.agent)
        mail.outbox.clear()
        upd_res = self.client.post(
            reverse("update_tour_status", kwargs={"booking_id": booking.id, "new_status": "Confirmed"}),
            {"agent_message": "Meet at lobby reception."},
        )
        self.assertEqual(upd_res.status_code, 302)
        booking.refresh_from_db()
        self.assertEqual(booking.status, "Confirmed")
        self.assertEqual(booking.agent_message, "Meet at lobby reception.")

        # Buyer cancels tour
        self.client.force_login(self.buyer)
        cancel_res = self.client.post(reverse("cancel_my_tour", kwargs={"booking_id": booking.id}))
        self.assertRedirects(cancel_res, reverse("my_tours"))
        booking.refresh_from_db()
        self.assertEqual(booking.status, "Cancelled")

    def test_role_access_guards_and_ownership(self):
        # Buyer cannot access agent or admin portals
        self.client.force_login(self.buyer)
        self.assertRedirects(self.client.get(reverse("agent_dashboard")), reverse("home"))
        self.assertRedirects(self.client.get(reverse("add_property")), reverse("home"))
        self.assertRedirects(self.client.get(reverse("admin_dashboard")), reverse("home"))
        self.assertRedirects(self.client.get(reverse("admin_export_report")), reverse("home"))

        # Other agent cannot edit/delete prop1 owned by self.agent
        self.client.force_login(self.other_agent)
        self.assertRedirects(self.client.get(reverse("edit_property", kwargs={"pk": self.prop1.id})), reverse("home"))
        self.client.post(reverse("delete_property", kwargs={"pk": self.prop1.id}))
        self.assertTrue(Property.objects.filter(pk=self.prop1.id).exists())

        # Admin CAN edit any property
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("edit_property", kwargs={"pk": self.prop1.id})).status_code, 200)

    def test_agent_create_edit_image_delete_and_dashboard(self):
        self.client.force_login(self.agent)
        dash = self.client.get(reverse("agent_dashboard"))
        self.assertEqual(dash.status_code, 200)
        self.assertEqual(self.client.get(reverse("agent_property_list")).status_code, 200)
        self.assertEqual(self.client.get(reverse("agent_tour_requests")).status_code, 200)

        with tempfile.TemporaryDirectory() as tmp_media:
            with override_settings(MEDIA_ROOT=tmp_media):
                img_file = SimpleUploadedFile("facade.gif", ONE_BY_ONE_GIF, content_type="image/gif")
                create_res = self.client.post(
                    reverse("add_property"),
                    {
                        "title": "Baridhara Minimalist Loft",
                        "description": "Double-height architectural loft with tranquil courtyard.",
                        "property_type": self.ptype_apt.id,
                        "listing_type": "sale",
                        "status": "available",
                        "price": "380000",
                        "bedrooms": "3",
                        "bathrooms": "3",
                        "area_sqft": "2250",
                        "location": "Park Road, Baridhara",
                        "city": "Dhaka",
                        "state": "Dhaka Division",
                        "is_featured": "on",
                        "images": [img_file],
                    },
                )
                created = Property.objects.get(title="Baridhara Minimalist Loft")
                self.assertRedirects(create_res, reverse("agent_property_list"))
                self.assertEqual(created.images.count(), 1)
                img_obj = created.images.first()

                # Delete image via POST
                del_img = self.client.post(reverse("delete_property_image", kwargs={"pk": img_obj.id}))
                self.assertRedirects(del_img, reverse("edit_property", kwargs={"pk": created.id}))
                self.assertFalse(PropertyImage.objects.filter(pk=img_obj.id).exists())

                # Delete property via POST only (GET should not delete)
                self.client.get(reverse("delete_property", kwargs={"pk": created.id}))
                self.assertTrue(Property.objects.filter(pk=created.id).exists())
                self.client.post(reverse("delete_property", kwargs={"pk": created.id}))
                self.assertFalse(Property.objects.filter(pk=created.id).exists())

    def test_contact_inquiry_and_honeypot(self):
        # Legitimate inquiry saved
        res = self.client.post(
            reverse("contact"),
            {
                "name": "Nadia Islam",
                "email": "nadia@example.com",
                "phone": "+8801712345678",
                "subject": "Penthouse Viewing",
                "property": self.prop1.id,
                "message": "Interested in touring next Friday morning.",
            },
        )
        self.assertRedirects(res, reverse("contact"))
        self.assertEqual(ContactMessage.objects.count(), 1)

        # Honeypot catches bot silently without saving
        bot_res = self.client.post(
            reverse("contact"),
            {
                "name": "Bot",
                "email": "bot@spam.example.com",
                "subject": "Spam",
                "message": "Buy links",
                "website": "https://spam.example.com",
            },
        )
        self.assertRedirects(bot_res, reverse("contact"))
        self.assertEqual(ContactMessage.objects.count(), 1)

    def test_admin_operations_and_csv_export(self):
        self.client.force_login(self.admin)
        for url in [
            reverse("admin_dashboard"),
            reverse("admin_property_list"),
            reverse("admin_property_types"),
            reverse("admin_user_list"),
            reverse("admin_agent_list"),
            reverse("admin_tour_requests"),
            reverse("admin_inquiries"),
        ]:
            self.assertEqual(self.client.get(url).status_code, 200, f"Admin GET failed: {url}")

        # Add & delete property type (must match PropertyType.CHOICE)
        self.client.post(reverse("admin_property_types"), {"name": "office"})
        office_type = PropertyType.objects.get(name="office")
        self.client.post(reverse("admin_delete_property_type", kwargs={"pk": office_type.id}))
        self.assertFalse(PropertyType.objects.filter(name="office").exists())

        # Create new user via admin
        self.client.post(
            reverse("admin_user_list"),
            {
                "username": "new_vip_buyer",
                "first_name": "Rafiq",
                "last_name": "Hasan",
                "email": "rafiq@example.com",
                "role": "buyer",
                "phone": "01700000000",
                "bio": "Collector",
                "is_active": "on",
                "password": "StrongPass!2026",
            },
        )
        new_u = User.objects.get(username="new_vip_buyer")
        self.client.post(reverse("admin_update_user_role", kwargs={"pk": new_u.id}), {"role": "agent"})
        new_u.refresh_from_db()
        self.assertEqual(new_u.role, User.AGENT)

        self.client.post(reverse("admin_toggle_user_active", kwargs={"pk": new_u.id}))
        new_u.refresh_from_db()
        self.assertFalse(new_u.is_active)

        # Inquiry resolution toggle
        inq = ContactMessage.objects.create(name="Client", email="c@example.com", subject="Question", message="Hi")
        self.client.post(reverse("admin_toggle_inquiry", kwargs={"pk": inq.id}))
        inq.refresh_from_db()
        self.assertTrue(inq.is_resolved)

        # CSV export
        csv_res = self.client.get(reverse("admin_export_report"))
        self.assertEqual(csv_res.status_code, 200)
        self.assertIn("text/csv", csv_res["Content-Type"])
        csv_text = csv_res.content.decode("utf-8")
        self.assertIn("Golpo Aleya Sky Residence", csv_text)
        self.assertIn("Dhaka", csv_text)

    def test_security_guards_post_save_open_redirect_and_seo_routes(self):
        self.client.force_login(self.buyer)
        save_url = reverse("save_property", kwargs={"id": self.prop1.id})

        # GET on state-mutating save endpoint must be rejected (405 Method Not Allowed)
        self.assertEqual(self.client.get(save_url).status_code, 405)

        # Open redirect attempt via next/Referer must not leave site
        res = self.client.post(save_url, {"next": "https://evil.example/phish"})
        self.assertEqual(res.status_code, 302)
        self.assertNotIn("evil.example", res["Location"])

        # SEO, favicon & 404 routes
        fav_res = self.client.get("/favicon.ico")
        self.assertEqual(fav_res.status_code, 301)

        robots_res = self.client.get(reverse("robots_txt"))
        self.assertEqual(robots_res.status_code, 200)
        self.assertIn("Sitemap:", robots_res.content.decode("utf-8"))

        sitemap_res = self.client.get(reverse("sitemap_xml"))
        self.assertEqual(sitemap_res.status_code, 200)
        self.assertIn(f"/property/{self.prop1.id}/", sitemap_res.content.decode("utf-8"))

        with override_settings(DEBUG=False):
            missing_res = self.client.get("/nonexistent-residence-route/")
            self.assertEqual(missing_res.status_code, 404)
            self.assertIn("architectural record could not be located", missing_res.content.decode("utf-8"))

    def test_property_type_id_and_amenity_filtering_and_comparison(self):
        self.prop1.amenities = ["elevator", "rooftop"]
        self.prop1.save(update_fields=["amenities"])
        self.prop2.amenities = ["security"]
        self.prop2.save(update_fields=["amenities"])

        # Integer property_type filter (previously broken dropdown value)
        res_id = self.client.get(reverse("property_list"), {"property_type": str(self.ptype_apt.id)})
        self.assertEqual(res_id.status_code, 200)
        self.assertEqual([p.id for p in res_id.context["properties"]], [self.prop1.id])

        # Amenity filter
        res_am = self.client.get(reverse("property_list"), {"amenity": "rooftop"})
        self.assertEqual(res_am.status_code, 200)
        self.assertEqual([p.id for p in res_am.context["properties"]], [self.prop1.id])

        # Side-by-side compare page
        cmp_res = self.client.get(reverse("compare_properties"), {"ids": f"{self.prop1.id},{self.prop2.id}"})
        self.assertEqual(cmp_res.status_code, 200)
        self.assertContains(cmp_res, self.prop1.title)
        self.assertContains(cmp_res, self.prop2.title)
        self.assertContains(cmp_res, "Private Elevator")

    def test_booking_availability_duplicate_and_slot_collision_guards(self):
        future = (datetime.date.today() + datetime.timedelta(days=4)).isoformat()
        detail_url = reverse("property_detail", kwargs={"id": self.prop1.id})

        # Non-available property rejects bookings
        self.prop1.status = "sold"
        self.prop1.save(update_fields=["status"])
        self.client.force_login(self.buyer)
        self.client.post(detail_url, {"scheduled_date": future, "scheduled_time": "12:00", "message": "Try"})
        self.assertEqual(TourBooking.objects.count(), 0)

        self.prop1.status = "available"
        self.prop1.save(update_fields=["status"])

        # First booking creates Pending request; duplicate Pending by same buyer is blocked
        self.client.post(detail_url, {"scheduled_date": future, "scheduled_time": "12:00", "message": "First"})
        self.client.post(detail_url, {"scheduled_date": future, "scheduled_time": "14:00", "message": "Duplicate"})
        self.assertEqual(TourBooking.objects.filter(property=self.prop1, buyer=self.buyer).count(), 1)

        # Confirmed time slot collision across another buyer is rejected
        booking = TourBooking.objects.get(property=self.prop1, buyer=self.buyer)
        booking.status = "Confirmed"
        booking.save()

        buyer2 = User.objects.create_user(
            username="buyer_two",
            email="buyer2@example.com",
            password="StrongPass!2026",
            role=User.BUYER,
            is_active=True,
        )
        self.client.force_login(buyer2)
        self.client.post(detail_url, {"scheduled_date": future, "scheduled_time": "12:00", "message": "Collision"})
        self.assertEqual(TourBooking.objects.filter(property=self.prop1, buyer=buyer2).count(), 0)

    def test_notifications_and_verified_buyer_reviews(self):
        future = datetime.date.today() + datetime.timedelta(days=2)
        booking = TourBooking.objects.create(
            property=self.prop1,
            buyer=self.buyer,
            scheduled_date=future,
            scheduled_time="11:30:00",
            status="Pending",
        )
        # Agent received notification for newly created tour request
        self.assertTrue(Notification.objects.filter(recipient=self.agent, category="tour").exists())

        # Uncompleted tour cannot submit verified review
        self.client.force_login(self.buyer)
        review_url = reverse("submit_property_review", kwargs={"id": self.prop1.id})
        self.client.post(review_url, {"rating": "5", "comment": "Premature review"})
        self.assertEqual(PropertyReview.objects.count(), 0)

        # Complete tour -> buyer gets notification & review unlocks
        booking.status = "Completed"
        booking.save()
        self.assertTrue(Notification.objects.filter(recipient=self.buyer, category="tour").exists())

        self.client.post(review_url, {"rating": "5", "comment": "Brilliant daylight and calm courtyard."})
        self.assertEqual(PropertyReview.objects.filter(property=self.prop1, reviewer=self.buyer).count(), 1)
        self.assertTrue(Notification.objects.filter(recipient=self.agent, category="review").exists())

        # Property detail renders verified review and rating
        detail_res = self.client.get(reverse("property_detail", kwargs={"id": self.prop1.id}))
        self.assertContains(detail_res, "Brilliant daylight and calm courtyard.")
        self.assertContains(detail_res, "5.0 / 5.0 Average")

        # Mark all notifications read
        self.client.post(reverse("mark_all_notifications_read"))
        self.assertEqual(Notification.objects.filter(recipient=self.buyer, is_read=False).count(), 0)
