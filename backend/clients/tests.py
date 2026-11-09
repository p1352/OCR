from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Client

User = get_user_model()


class ClientTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.user = User.objects.create_user(
            username="u", email="u@example.com", password="Str0ng!Pass"
        )
        self.api.force_authenticate(self.user)

    def test_crud_and_archive(self):
        resp = self.api.post("/api/clients/", {"name": "ACME"})
        self.assertEqual(resp.status_code, 201)
        cid = resp.data["id"]

        resp = self.api.get(f"/api/clients/{cid}/")
        self.assertEqual(resp.data["name"], "ACME")

        resp = self.api.post(f"/api/clients/{cid}/archive/")
        self.assertEqual(resp.data["status"], "archived")

        resp = self.api.post(f"/api/clients/{cid}/restore/")
        self.assertEqual(resp.data["status"], "active")

    def test_search(self):
        Client.objects.create(name="Alpha Corp", created_by=self.user)
        Client.objects.create(name="Beta LLC", created_by=self.user)
        resp = self.api.get("/api/clients/?search=alpha")
        self.assertEqual(resp.data["count"], 1)

    def test_unauthenticated_denied(self):
        self.api.force_authenticate(user=None)
        self.assertEqual(self.api.get("/api/clients/").status_code, 401)
