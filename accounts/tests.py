from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class AccountFeatureTests(TestCase):
    def test_registration_creates_hashed_password_and_standard_role(self):
        response = self.client.post(
            reverse('accounts:register'),
            {
                'username': 'newmember',
                'email': 'newmember@example.com',
                'first_name': 'New',
                'last_name': 'Member',
                'role': User.Role.ADMINISTRATOR,
                'password1': 'Safe-password-872!',
                'password2': 'Safe-password-872!',
            },
        )

        self.assertRedirects(response, reverse('accounts:login'))
        user = User.objects.get(username='newmember')
        self.assertTrue(user.check_password('Safe-password-872!'))
        self.assertNotEqual(user.password, 'Safe-password-872!')
        self.assertEqual(user.role, User.Role.STANDARD_USER)

    def test_expertise_is_not_a_privileged_role(self):
        labels = {value for value, _label in User.Role.choices}

        self.assertEqual(labels, {'STANDARD_USER', 'MODERATOR', 'ADMINISTRATOR'})

    def test_registration_rejects_duplicate_email_case_insensitively(self):
        User.objects.create_user(
            username='existing',
            email='person@example.com',
            password='Safe-password-872!',
        )

        response = self.client.post(
            reverse('accounts:register'),
            {
                'username': 'another',
                'email': 'PERSON@example.com',
                'password1': 'Safe-password-872!',
                'password2': 'Safe-password-872!',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'already exists')
        self.assertFalse(User.objects.filter(username='another').exists())

    def test_registration_requires_valid_email_and_matching_passwords(self):
        response = self.client.post(
            reverse('accounts:register'),
            {
                'username': 'newmember',
                'email': '',
                'password1': 'Safe-password-872!',
                'password2': 'Different-password-872!',
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='newmember').exists())
        self.assertContains(response, 'This field is required')

    def test_login_and_logout(self):
        user = User.objects.create_user(
            username='member',
            email='member@example.com',
            password='Safe-password-872!',
        )
        response = self.client.post(
            reverse('accounts:login'),
            {'username': user.username, 'password': 'wrong-password'},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please enter a correct username and password')

        response = self.client.post(
            reverse('accounts:login'),
            {'username': user.username, 'password': 'Safe-password-872!'},
        )
        self.assertRedirects(response, reverse('dashboard:member'))
        self.assertTrue('_auth_user_id' in self.client.session)

        response = self.client.post(reverse('accounts:logout'))
        self.assertRedirects(response, reverse('accounts:login'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('dashboard:home'))
        self.assertRedirects(
            response,
            f'{reverse("accounts:login")}?next={reverse("dashboard:home")}',
        )

    def test_profile_requires_login_and_only_edits_current_user(self):
        profile_url = reverse('accounts:profile')
        response = self.client.get(profile_url)
        self.assertRedirects(response, f'{reverse("accounts:login")}?next={profile_url}')

        user = User.objects.create_user(
            username='member',
            email='member@example.com',
            password='Safe-password-872!',
        )
        other_user = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='Safe-password-872!',
        )
        self.client.force_login(user)

        response = self.client.post(
            profile_url,
            {
                'first_name': 'Updated',
                'last_name': '',
                'email': user.email,
                'contact_number': '',
                'expertise': '',
                'bio': '',
            },
        )

        self.assertRedirects(response, profile_url)
        user.refresh_from_db()
        other_user.refresh_from_db()
        self.assertEqual(user.first_name, 'Updated')
        self.assertEqual(other_user.first_name, '')
        self.assertEqual(user.role, User.Role.STANDARD_USER)
