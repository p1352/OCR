from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

User = get_user_model()


def make_user(username, role=User.Role.USER, password="Str0ng!Pass"):
    return User.objects.create_user(
        username=username, email=f"{username}@example.com",
        password=password, role=role,
    )


class AuthTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.user = make_user("alice")

    def test_login_returns_tokens_and_profile(self):
        resp = self.api.post("/api/auth/token/", {
            "username": "alice", "password": "Str0ng!Pass",
        })
        self.assertEqual(resp.status_code, 200)
        self.assertIn("access", resp.data)
        self.assertIn("refresh", resp.data)
        self.assertEqual(resp.data["user"]["username"], "alice")

    def test_me_requires_auth(self):
        self.assertEqual(self.api.get("/api/auth/me/").status_code, 401)
        self.api.force_authenticate(self.user)
        resp = self.api.get("/api/auth/me/")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.data["role"], "user")

    def test_change_password(self):
        self.api.force_authenticate(self.user)
        resp = self.api.post("/api/auth/change-password/", {
            "old_password": "Str0ng!Pass", "new_password": "An0ther!Pass99",
        })
        self.assertEqual(resp.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("An0ther!Pass99"))


class UserAdminTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.admin = make_user("root", role=User.Role.ADMIN)
        self.user = make_user("bob")

    def test_user_list_requires_admin(self):
        self.api.force_authenticate(self.user)
        self.assertEqual(self.api.get("/api/users/").status_code, 403)
        self.api.force_authenticate(self.admin)
        self.assertEqual(self.api.get("/api/users/").status_code, 200)

    def test_admin_can_create_user(self):
        self.api.force_authenticate(self.admin)
        resp = self.api.post("/api/users/", {
            "username": "carol", "email": "carol@example.com",
            "password": "Str0ng!Pass", "role": "user",
        })
        self.assertEqual(resp.status_code, 201)
        self.assertTrue(User.objects.filter(username="carol").exists())

    def test_delete_disables_instead_of_removing(self):
        self.api.force_authenticate(self.admin)
        resp = self.api.delete(f"/api/users/{self.user.pk}/")
        self.assertEqual(resp.status_code, 204)
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)

    def test_admin_cannot_disable_self(self):
        self.api.force_authenticate(self.admin)
        resp = self.api.delete(f"/api/users/{self.admin.pk}/")
        self.assertEqual(resp.status_code, 400)
