from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from .demo_accounts import DEMO_ACCOUNTS

User = get_user_model()


class UserAuthAndProfileTests(TestCase):
    def test_registration_buyer_and_agent_sends_activation_email(self):
        mail.outbox.clear()
        res = self.client.post(
            reverse("register"),
            {
                "account_role": "agent",
                "first_name": "Elena",
                "last_name": "Rostova",
                "username": "elena_agent",
                "email": "Elena@Example.com",
                "phone": "+8801711000111",
                "password": "StrongPass!2026",
                "confirm_password": "StrongPass!2026",
            },
        )
        self.assertRedirects(res, reverse("login"))
        user = User.objects.get(username="elena_agent")
        self.assertEqual(user.role, User.AGENT)
        self.assertEqual(user.email, "elena@example.com")
        self.assertFalse(user.is_active)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Activate Your PropNest Architectural Account", mail.outbox[0].subject)

    def test_activation_token_flow(self):
        user = User.objects.create_user(
            username="pending_buyer",
            email="pending@example.com",
            password="StrongPass!2026",
            is_active=False,
        )
        token = default_token_generator.make_token(user)

        bad_res = self.client.get(reverse("activate_user", kwargs={"user_id": user.id, "token": "bad-token"}))
        self.assertEqual(bad_res.status_code, 400)

        good_res = self.client.get(reverse("activate_user", kwargs={"user_id": user.id, "token": token}))
        self.assertRedirects(good_res, reverse("login"))
        user.refresh_from_db()
        self.assertTrue(user.is_active)

    def test_resend_activation_email(self):
        User.objects.create_user(
            username="inactive_u",
            email="inactive@example.com",
            password="StrongPass!2026",
            is_active=False,
        )
        mail.outbox.clear()
        res = self.client.post(reverse("resend_activation"), {"email": "inactive@example.com"})
        self.assertRedirects(res, reverse("login"))
        self.assertEqual(len(mail.outbox), 1)

    def test_role_based_login_redirects(self):
        User.objects.create_user(username="buyer1", email="b1@example.com", password="StrongPass!2026", role=User.BUYER, is_active=True)
        User.objects.create_user(username="agent1", email="a1@example.com", password="StrongPass!2026", role=User.AGENT, is_active=True)
        User.objects.create_user(username="admin1", email="ad@example.com", password="StrongPass!2026", role=User.ADMIN, is_active=True)

        r_buyer = self.client.post(reverse("login"), {"username": "buyer1", "password": "StrongPass!2026"})
        self.assertRedirects(r_buyer, reverse("home"))
        self.client.post(reverse("logout"))

        r_agent = self.client.post(reverse("login"), {"username": "agent1", "password": "StrongPass!2026"})
        self.assertRedirects(r_agent, reverse("agent_dashboard"))
        self.client.post(reverse("logout"))

        r_admin = self.client.post(reverse("login"), {"username": "admin1", "password": "StrongPass!2026"})
        self.assertRedirects(r_admin, reverse("admin_dashboard"))

    def test_profile_update_password_change_and_account_deletion(self):
        user = User.objects.create_user(
            username="member1",
            email="m1@example.com",
            password="OldPassword!2026",
            role=User.BUYER,
            is_active=True,
        )
        self.client.force_login(user)

        # Update profile fields (phone & bio)
        res = self.client.post(
            reverse("profile"),
            {
                "first_name": "Tariq",
                "last_name": "Mahmud",
                "email": "m1@example.com",
                "phone": "+8801900112233",
                "bio": "Seeking sunlit Gulshan apartments.",
            },
        )
        self.assertRedirects(res, reverse("profile"))
        user.refresh_from_db()
        self.assertEqual(user.phone, "+8801900112233")
        self.assertEqual(user.first_name, "Tariq")

        # Change password
        pw_res = self.client.post(
            reverse("change_password"),
            {
                "old_password": "OldPassword!2026",
                "new_password1": "NewPassword!9988",
                "new_password2": "NewPassword!9988",
            },
        )
        self.assertRedirects(pw_res, reverse("profile"))
        user.refresh_from_db()
        self.assertTrue(user.check_password("NewPassword!9988"))

        # Wrong password does NOT delete account
        bad_del = self.client.post(reverse("delete_account"), {"confirm_password": "wrong"})
        self.assertRedirects(bad_del, reverse("profile"))
        self.assertTrue(User.objects.filter(pk=user.pk).exists())

        # Correct password deletes account cleanly
        ok_del = self.client.post(reverse("delete_account"), {"confirm_password": "NewPassword!9988"})
        self.assertRedirects(ok_del, reverse("home"))
        self.assertFalse(User.objects.filter(pk=user.pk).exists())

    def test_demo_accounts_seed_login_and_admin_protection(self):
        call_command("seed_demo_accounts")
        login_res = self.client.get(reverse("login"))
        self.assertEqual(login_res.status_code, 200)
        for spec in DEMO_ACCOUNTS:
            self.assertContains(login_res, spec["username"])
            self.assertContains(login_res, spec["password"])

        expected_targets = {
            "admin": reverse("admin_dashboard"),
            "agent": reverse("agent_dashboard"),
            "client": reverse("home"),
        }
        for spec in DEMO_ACCOUNTS:
            res = self.client.post(
                reverse("login"),
                {"username": spec["username"], "password": spec["password"]},
            )
            self.assertRedirects(res, expected_targets[spec["key"]], fetch_redirect_response=False)
            self.client.post(reverse("logout"))

        # Email login resolution works too
        email_res = self.client.post(
            reverse("login"),
            {"username": "demo.admin@propnest.com", "password": DEMO_ACCOUNTS[0]["password"]},
        )
        self.assertRedirects(email_res, reverse("admin_dashboard"), fetch_redirect_response=False)

        # Demo admin cannot deactivate/demote/delete another demo account
        demo_client = User.objects.get(username="demo_client")
        self.client.post(reverse("admin_toggle_user_active", args=[demo_client.pk]))
        self.client.post(reverse("admin_update_user_role", args=[demo_client.pk]), {"role": User.AGENT})
        self.client.post(reverse("admin_delete_user", args=[demo_client.pk]))
        demo_client.refresh_from_db()
        self.assertTrue(demo_client.is_active)
        self.assertEqual(demo_client.role, User.BUYER)
