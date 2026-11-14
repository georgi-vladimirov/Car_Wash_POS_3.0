from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class HtmxLoginRedirectMiddlewareTests(TestCase):
    def setUp(self):
        self.url = reverse("core:home")
        self.login_url = reverse("login")

    def test_regular_request_gets_normal_redirect(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response["Location"], f"{self.login_url}?next={self.url}")

    def test_htmx_request_gets_client_redirect_to_current_page(self):
        response = self.client.get(
            self.url,
            headers={
                "HX-Request": "true",
                "HX-Current-URL": "http://testserver/some/page/?day=1",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["HX-Redirect"],
            f"{self.login_url}?next=/some/page/%3Fday%3D1",
        )

    def test_authenticated_htmx_request_is_not_redirected(self):
        user = get_user_model().objects.create_user(
            username="owner", password="test-pass-123", role="owner"
        )
        self.client.force_login(user)

        response = self.client.get(self.url, headers={"HX-Request": "true"})

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("HX-Redirect", response)
