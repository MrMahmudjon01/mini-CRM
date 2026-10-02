from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from .models import Lead

User = get_user_model()
URL = "/api/leads/"


class AuthTests(APITestCase):
    def test_register_login_me_logout(self):
        r = self.client.post("/api/auth/register/", {"username": "ali", "password": "S3cure-pass-77"})
        self.assertEqual(r.status_code, 201)
        r = self.client.post("/api/auth/login/", {"username": "ali", "password": "S3cure-pass-77"})
        self.assertEqual(r.status_code, 200)
        token = r.data["token"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token}")
        self.assertEqual(self.client.get("/api/auth/me/").data["username"], "ali")
        self.assertEqual(self.client.post("/api/auth/logout/").status_code, 204)
        self.assertEqual(self.client.get("/api/auth/me/").status_code, 401)

    def test_weak_password_rejected(self):
        r = self.client.post("/api/auth/register/", {"username": "bob", "password": "123"})
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.data["error"]["code"], "validation_error")

    def test_wrong_credentials(self):
        User.objects.create_user("ali", password="S3cure-pass-77")
        r = self.client.post("/api/auth/login/", {"username": "ali", "password": "nope"})
        self.assertEqual(r.status_code, 400)

    def test_leads_require_auth(self):
        r = self.client.get(URL)
        self.assertEqual(r.status_code, 401)
        self.assertEqual(r.data["error"]["status"], 401)


class LeadTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user("ali", password="S3cure-pass-77")
        self.other = User.objects.create_user("vali", password="S3cure-pass-77")
        self.client.force_authenticate(self.user)

    def make(self, n=1, **kw):
        for i in range(n):
            Lead.objects.create(owner=kw.pop("owner", self.user), name=kw.get("name", f"Lead {i}"),
                                phone="+998901234567", **{k: v for k, v in kw.items() if k != "name"})

    # create / validation
    def test_create_lead_and_activity(self):
        r = self.client.post(URL, {"name": "Aziz", "phone": "+998 90 123 45 67", "source": "telegram"})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["status"], "new")
        acts = self.client.get(f"{URL}{r.data['id']}/activities/").data
        self.assertEqual(acts[0]["action"], "created")

    def test_requires_phone_or_email(self):
        r = self.client.post(URL, {"name": "Aziz"})
        self.assertEqual(r.status_code, 400)
        self.assertIn("non_field_errors", r.data["error"]["details"])

    def test_invalid_phone_email_status(self):
        r = self.client.post(URL, {"name": "A", "phone": "abc", "email": "bad", "source": "x"})
        self.assertEqual(r.status_code, 400)
        d = r.data["error"]["details"]
        for field in ("name", "phone", "email", "source"):
            self.assertIn(field, d)

    def test_email_only_is_ok(self):
        r = self.client.post(URL, {"name": "Aziz", "email": "Aziz@Example.com"})
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.data["email"], "aziz@example.com")

    # detail / update / delete
    def test_retrieve_update_delete(self):
        lead_id = self.client.post(URL, {"name": "Aziz", "phone": "+998901234567"}).data["id"]
        self.assertEqual(self.client.get(f"{URL}{lead_id}/").status_code, 200)
        r = self.client.patch(f"{URL}{lead_id}/", {"note": "call tomorrow"})
        self.assertEqual(r.data["note"], "call tomorrow")
        r = self.client.put(f"{URL}{lead_id}/", {"name": "Aziz K", "phone": "+998901234567", "source": "website"})
        self.assertEqual(r.data["source"], "website")
        self.assertEqual(self.client.delete(f"{URL}{lead_id}/").status_code, 204)
        self.assertEqual(self.client.get(f"{URL}{lead_id}/").status_code, 404)

    def test_patch_cannot_remove_last_contact(self):
        lead_id = self.client.post(URL, {"name": "Aziz", "phone": "+998901234567"}).data["id"]
        r = self.client.patch(f"{URL}{lead_id}/", {"phone": ""})
        self.assertEqual(r.status_code, 400)

    def test_not_found_format(self):
        r = self.client.get(f"{URL}9999/")
        self.assertEqual(r.status_code, 404)
        self.assertEqual(r.data["error"]["status"], 404)

    # status
    def test_status_change_logged(self):
        lead_id = self.client.post(URL, {"name": "Aziz", "phone": "+998901234567"}).data["id"]
        r = self.client.post(f"{URL}{lead_id}/status/", {"status": "qualified"})
        self.assertEqual(r.data["status"], "qualified")
        acts = self.client.get(f"{URL}{lead_id}/activities/").data
        self.assertEqual(acts[0]["action"], "status_changed")
        self.assertIn("New to Qualified", acts[0]["message"])

    def test_invalid_status_rejected(self):
        lead_id = self.client.post(URL, {"name": "Aziz", "phone": "+998901234567"}).data["id"]
        self.assertEqual(self.client.post(f"{URL}{lead_id}/status/", {"status": "bogus"}).status_code, 400)

    def test_status_via_patch_logged(self):
        lead_id = self.client.post(URL, {"name": "Aziz", "phone": "+998901234567"}).data["id"]
        self.client.patch(f"{URL}{lead_id}/", {"status": "won", "note": "signed"})
        actions = {a["action"] for a in self.client.get(f"{URL}{lead_id}/activities/").data}
        self.assertEqual(actions, {"created", "status_changed", "updated"})

    # list: pagination / filter / search / sort
    def test_pagination(self):
        self.make(25)
        r = self.client.get(URL)
        self.assertEqual(r.data["count"], 25)
        self.assertEqual(len(r.data["results"]), 10)
        r = self.client.get(URL, {"page": 3})
        self.assertEqual(len(r.data["results"]), 5)
        r = self.client.get(URL, {"page_size": 100})
        self.assertEqual(len(r.data["results"]), 25)
        self.assertEqual(self.client.get(URL, {"page": 99}).status_code, 404)

    def test_filter_by_status_and_source(self):
        self.make(2, status="won", source="website")
        self.make(3, status="lost", source="telegram")
        self.assertEqual(self.client.get(URL, {"status": "won"}).data["count"], 2)
        self.assertEqual(self.client.get(URL, {"status": "lost", "source": "telegram"}).data["count"], 3)
        self.assertEqual(self.client.get(URL, {"status": "nope"}).status_code, 400)

    def test_search(self):
        Lead.objects.create(owner=self.user, name="Dilnoza Rahimova", phone="+998901111111")
        Lead.objects.create(owner=self.user, name="Jasur", email="jasur@acme.uz")
        self.assertEqual(self.client.get(URL, {"search": "dilnoza"}).data["count"], 1)
        self.assertEqual(self.client.get(URL, {"search": "acme"}).data["count"], 1)
        self.assertEqual(self.client.get(URL, {"search": "+99890111"}).data["count"], 1)

    def test_ordering(self):
        Lead.objects.create(owner=self.user, name="Bbb", phone="+998901111111")
        Lead.objects.create(owner=self.user, name="Aaa", phone="+998901111111")
        names = [x["name"] for x in self.client.get(URL, {"ordering": "name"}).data["results"]]
        self.assertEqual(names, ["Aaa", "Bbb"])

    # isolation
    def test_users_cannot_see_each_others_leads(self):
        lead = Lead.objects.create(owner=self.other, name="Secret", phone="+998901111111")
        self.assertEqual(self.client.get(URL).data["count"], 0)
        self.assertEqual(self.client.get(f"{URL}{lead.id}/").status_code, 404)
        self.assertEqual(self.client.delete(f"{URL}{lead.id}/").status_code, 404)
        self.assertEqual(self.client.post(f"{URL}{lead.id}/status/", {"status": "won"}).status_code, 404)

    # stats
    def test_stats(self):
        self.make(2, status="won")
        self.make(2, status="new")
        s = self.client.get(f"{URL}stats/").data
        self.assertEqual(s["total"], 4)
        self.assertEqual(s["by_status"]["won"], 2)
        self.assertEqual(s["conversion_rate"], 50.0)
        self.assertEqual(s["new_last_7_days"], 4)
