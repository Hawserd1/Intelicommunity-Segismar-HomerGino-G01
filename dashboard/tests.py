from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class RoleDashboardTests(TestCase):
    def make_user(self, role, **kwargs):
        return User.objects.create_user(
            username=f'user-{role.lower()}',
            email=f'{role.lower()}@example.com',
            password='Safe-password-872!',
            role=role,
            **kwargs,
        )

    def test_dashboard_landing_redirects_each_role_to_its_own_dashboard(self):
        role_urls = (
            (User.Role.STANDARD_USER, 'dashboard:member'),
            (User.Role.MODERATOR, 'dashboard:moderator'),
            (User.Role.ADMINISTRATOR, 'dashboard:administrator'),
        )

        for role, dashboard_name in role_urls:
            with self.subTest(role=role):
                self.client.force_login(self.make_user(role))
                response = self.client.get(reverse('dashboard:home'))
                self.assertRedirects(response, reverse(dashboard_name))

    def test_users_cannot_open_another_roles_dashboard(self):
        dashboard_names = {
            User.Role.STANDARD_USER: 'dashboard:member',
            User.Role.MODERATOR: 'dashboard:moderator',
            User.Role.ADMINISTRATOR: 'dashboard:administrator',
        }

        for user_role in dashboard_names:
            self.client.force_login(self.make_user(user_role))
            for page_role, dashboard_name in dashboard_names.items():
                with self.subTest(user_role=user_role, page_role=page_role):
                    response = self.client.get(reverse(dashboard_name))
                    self.assertEqual(
                        response.status_code,
                        200 if user_role == page_role else 403,
                    )

    def test_dashboard_pages_show_role_specific_content(self):
        content = (
            (User.Role.STANDARD_USER, 'dashboard:member', 'Explore communities'),
            (User.Role.MODERATOR, 'dashboard:moderator', 'Reported content'),
            (User.Role.ADMINISTRATOR, 'dashboard:administrator', 'User management'),
        )

        for role, dashboard_name, expected_text in content:
            with self.subTest(role=role):
                self.client.force_login(self.make_user(role))
                response = self.client.get(reverse(dashboard_name))
                self.assertContains(response, expected_text)
                self.assertContains(response, 'dashboard/site.css')

    def test_role_dashboards_require_login(self):
        for dashboard_name in (
            'dashboard:member',
            'dashboard:moderator',
            'dashboard:administrator',
        ):
            with self.subTest(dashboard=dashboard_name):
                url = reverse(dashboard_name)
                response = self.client.get(url)
                self.assertRedirects(
                    response,
                    f'{reverse("accounts:login")}?next={url}',
                )

    def test_coming_soon_pages_explain_feature_and_return_501(self):
        self.client.force_login(self.make_user(User.Role.STANDARD_USER))
        response = self.client.get(
            reverse('dashboard:coming_soon', args=('communities',))
        )

        self.assertEqual(response.status_code, 501)
        self.assertContains(response, 'Community Sections', status_code=501)
        self.assertContains(response, 'HTTP 501', status_code=501)

    def test_unknown_placeholder_feature_returns_404(self):
        self.client.force_login(self.make_user(User.Role.STANDARD_USER))

        response = self.client.get(
            reverse('dashboard:coming_soon', args=('not-a-feature',))
        )

        self.assertEqual(response.status_code, 404)

    def test_application_administrator_role_does_not_grant_django_admin_access(self):
        self.client.force_login(self.make_user(User.Role.ADMINISTRATOR))

        response = self.client.get('/admin/')

        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/login/', response['Location'])

    def test_django_staff_permission_is_independent_of_application_role(self):
        staff_member = self.make_user(User.Role.STANDARD_USER, is_staff=True)
        self.client.force_login(staff_member)

        response = self.client.get('/admin/')

        self.assertEqual(response.status_code, 200)

    def test_application_administrator_without_staff_access_cannot_use_user_management(self):
        self.client.force_login(self.make_user(User.Role.ADMINISTRATOR))

        response = self.client.get(reverse('dashboard:user_management'))

        self.assertEqual(response.status_code, 403)
