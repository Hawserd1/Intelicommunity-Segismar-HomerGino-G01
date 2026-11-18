from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from community.models import CommunitySection, ContentReport, Discussion, Reply

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

    def test_standard_user_dashboard_shows_followed_sections_and_their_discussions(self):
        user = self.make_user(User.Role.STANDARD_USER)
        followed = CommunitySection.objects.create(
            name='Dashboard Programming',
            description='Programming conversations for the dashboard.',
        )
        not_followed = CommunitySection.objects.create(
            name='Dashboard Cooking',
            description='Cooking conversations not followed by this user.',
        )
        followed.followers.add(user)
        Discussion.objects.create(
            section=followed,
            author=user,
            title='A discussion from my followed section',
            body='This should appear in my dashboard community activity.',
        )
        Discussion.objects.create(
            section=not_followed,
            author=user,
            title='A discussion from a section I do not follow',
            body='This should not appear in my dashboard community activity.',
        )
        self.client.force_login(user)

        response = self.client.get(reverse('dashboard:member'))

        self.assertContains(response, followed.name)
        self.assertContains(response, 'A discussion from my followed section')
        self.assertNotContains(response, not_followed.name)
        self.assertNotContains(response, 'A discussion from a section I do not follow')

    def test_moderator_and_administrator_dashboards_show_followed_communities(self):
        section = CommunitySection.objects.create(
            name='Role dashboard community',
            description='A followed community for staff dashboards.',
        )
        discussion = Discussion.objects.create(
            section=section,
            author=self.make_user(User.Role.STANDARD_USER),
            title='Recent followed community discussion',
            body='This should appear on both staff dashboards.',
        )

        for role, dashboard_name in (
            (User.Role.MODERATOR, 'dashboard:moderator'),
            (User.Role.ADMINISTRATOR, 'dashboard:administrator'),
        ):
            with self.subTest(role=role):
                user = self.make_user(role)
                section.followers.add(user)
                self.client.force_login(user)

                response = self.client.get(reverse(dashboard_name))

                self.assertContains(response, section.name)
                self.assertContains(response, discussion.title)

    def test_moderator_dashboard_shows_pending_report_snapshot(self):
        moderator = self.make_user(User.Role.MODERATOR)
        reporter = self.make_user(User.Role.STANDARD_USER)
        section = CommunitySection.objects.create(
            name='Moderation snapshot community',
            description='Section for the moderator dashboard test.',
        )
        discussion = Discussion.objects.create(
            section=section,
            author=reporter,
            title='Discussion awaiting moderation',
            body='Reported content.',
        )
        ContentReport.objects.create(
            reported_by=moderator,
            discussion=discussion,
            reason=ContentReport.Reason.SPAM,
        )
        self.client.force_login(moderator)

        response = self.client.get(reverse('dashboard:moderator'))

        self.assertContains(response, 'Moderation queue')
        self.assertContains(response, '1 report pending review')
        self.assertContains(response, discussion.title)
        self.assertContains(response, reverse('dashboard:reported_content'))

    def test_administrator_dashboard_shows_platform_snapshot(self):
        administrator = self.make_user(User.Role.ADMINISTRATOR)
        self.make_user(User.Role.STANDARD_USER)
        self.make_user(User.Role.MODERATOR)
        self.client.force_login(administrator)

        response = self.client.get(reverse('dashboard:administrator'))

        self.assertContains(response, 'Platform overview')
        self.assertContains(response, 'Standard users')
        self.assertContains(response, 'Moderators')
        self.assertContains(response, 'Administrators')
        self.assertEqual(response.context['user_counts_by_role'][User.Role.ADMINISTRATOR], 1)
        self.assertEqual(response.context['user_counts_by_role'][User.Role.MODERATOR], 1)
        self.assertEqual(response.context['user_counts_by_role'][User.Role.STANDARD_USER], 1)

    def test_standard_user_dashboard_shows_explore_prompt_when_no_sections_followed(self):
        self.client.force_login(self.make_user(User.Role.STANDARD_USER))

        response = self.client.get(reverse('dashboard:member'))

        self.assertContains(response, "You haven't followed a section yet.")
        self.assertContains(
            response,
            reverse('community:section_list'),
        )

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
            reverse('dashboard:coming_soon', args=('bookmarks',))
        )

        self.assertEqual(response.status_code, 501)
        self.assertContains(response, 'Saved Discussions', status_code=501)
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

    def test_application_administrator_can_manage_roles_without_django_staff_access(self):
        administrator = self.make_user(User.Role.ADMINISTRATOR)
        member = self.make_user(User.Role.STANDARD_USER)
        self.client.force_login(administrator)

        response = self.client.get(reverse('dashboard:user_management'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, member.username)
        self.assertContains(response, 'Standard User')
        self.assertContains(response, 'Moderator')
        self.assertContains(response, 'Administrator')

        response = self.client.post(
            reverse('dashboard:update_user_role', args=(member.pk,)),
            {'role': User.Role.MODERATOR},
        )

        self.assertRedirects(response, reverse('dashboard:user_management'))
        member.refresh_from_db()
        self.assertEqual(member.role, User.Role.MODERATOR)
        self.assertFalse(member.is_staff)

    def test_non_administrators_cannot_view_or_change_user_roles(self):
        target = self.make_user(User.Role.STANDARD_USER)
        role_url = reverse('dashboard:update_user_role', args=(target.pk,))

        for role in (User.Role.STANDARD_USER, User.Role.MODERATOR):
            with self.subTest(role=role):
                actor = User.objects.create_user(
                    username=f'role-check-{role.lower()}',
                    email=f'role-check-{role.lower()}@example.com',
                    password='Safe-password-872!',
                    role=role,
                )
                self.client.force_login(actor)
                self.assertEqual(
                    self.client.get(reverse('dashboard:user_management')).status_code,
                    403,
                )
                self.assertEqual(
                    self.client.post(
                        role_url,
                        {'role': User.Role.ADMINISTRATOR},
                    ).status_code,
                    403,
                )

        target.refresh_from_db()
        self.assertEqual(target.role, User.Role.STANDARD_USER)

    def test_administrator_cannot_change_their_own_role(self):
        administrator = self.make_user(User.Role.ADMINISTRATOR)
        self.client.force_login(administrator)
        role_url = reverse('dashboard:update_user_role', args=(administrator.pk,))

        self.assertEqual(self.client.post(role_url, {'role': User.Role.STANDARD_USER}).status_code, 404)
        administrator.refresh_from_db()
        self.assertEqual(administrator.role, User.Role.ADMINISTRATOR)

    def test_role_assignment_requires_post_and_valid_role(self):
        administrator = self.make_user(User.Role.ADMINISTRATOR)
        member = self.make_user(User.Role.STANDARD_USER)
        self.client.force_login(administrator)
        role_url = reverse('dashboard:update_user_role', args=(member.pk,))

        self.assertEqual(self.client.get(role_url).status_code, 405)
        response = self.client.post(role_url, {'role': 'INVALID'})
        self.assertEqual(response.status_code, 400)
        self.assertContains(response, 'Select a valid choice', status_code=400)
        member.refresh_from_db()
        self.assertEqual(member.role, User.Role.STANDARD_USER)

    def test_moderators_can_review_and_dismiss_content_reports(self):
        moderator = self.make_user(User.Role.MODERATOR)
        reporter = self.make_user(User.Role.STANDARD_USER)
        author = self.make_user(User.Role.ADMINISTRATOR)
        section = CommunitySection.objects.create(
            name='Report review section',
            description='A section used to test report review.',
        )
        discussion = Discussion.objects.create(
            section=section,
            author=author,
            title='A reported discussion',
            body='Discussion content under review.',
        )
        report = ContentReport.objects.create(
            reported_by=reporter,
            discussion=discussion,
            reason=ContentReport.Reason.SPAM,
            details='Please review this discussion.',
        )
        self.client.force_login(moderator)

        response = self.client.get(reverse('dashboard:reported_content'))
        self.assertContains(response, 'A reported discussion')
        self.assertContains(response, 'Please review this discussion.')
        self.assertContains(response, reverse('dashboard:activity_reports'))

        review_url = reverse('dashboard:review_report', args=(report.pk,))
        self.assertEqual(self.client.get(review_url).status_code, 405)
        response = self.client.post(review_url, {'status': ContentReport.Status.REVIEWED})
        self.assertRedirects(response, reverse('dashboard:reported_content'))
        report.refresh_from_db()
        self.assertEqual(report.status, ContentReport.Status.REVIEWED)
        self.assertEqual(report.reviewed_by, moderator)
        self.assertIsNotNone(report.reviewed_at)

        self.client.post(review_url, {'status': ContentReport.Status.DISMISSED})
        report.refresh_from_db()
        self.assertEqual(report.status, ContentReport.Status.DISMISSED)

        self.client.force_login(reporter)
        self.assertEqual(
            self.client.get(reverse('dashboard:reported_content')).status_code,
            403,
        )

    def test_activity_report_summarizes_reported_users_and_section_discussions(self):
        moderator = self.make_user(User.Role.MODERATOR)
        reporter_one = User.objects.create_user(
            username='reporter-one',
            email='reporter-one@example.com',
            password='Safe-password-872!',
        )
        reporter_two = User.objects.create_user(
            username='reporter-two',
            email='reporter-two@example.com',
            password='Safe-password-872!',
        )
        reported_user = User.objects.create_user(
            username='frequently-reported',
            email='frequently-reported@example.com',
            password='Safe-password-872!',
        )
        section = CommunitySection.objects.create(
            name='Activity summary section',
            description='A section used to test activity reporting.',
        )
        discussion = Discussion.objects.create(
            section=section,
            author=reported_user,
            title='Reported discussion for summary',
            body='This report should count toward its author.',
        )
        reply = Reply.objects.create(
            discussion=discussion,
            author=reported_user,
            body='Reported reply for summary.',
        )
        ContentReport.objects.create(
            reported_by=reporter_one,
            discussion=discussion,
            reason=ContentReport.Reason.OTHER,
        )
        ContentReport.objects.create(
            reported_by=reporter_two,
            reply=reply,
            reason=ContentReport.Reason.HARASSMENT,
            status=ContentReport.Status.REVIEWED,
            reviewed_by=moderator,
        )
        self.client.force_login(moderator)

        response = self.client.get(reverse('dashboard:activity_reports'))

        self.assertContains(response, 'frequently-reported')
        self.assertEqual(response.context['total_reports'], 2)
        self.assertEqual(response.context['pending_count'], 1)
        self.assertEqual(response.context['reviewed_count'], 1)
        self.assertEqual(response.context['dismissed_count'], 0)
        self.assertEqual(
            response.context['most_reported_users'][0],
            {'username': 'frequently-reported', 'report_count': 2},
        )
        section_summary = next(
            item
            for item in response.context['section_discussions']
            if item.pk == section.pk
        )
        self.assertEqual(section_summary.discussion_count, 1)

        administrator = self.make_user(User.Role.ADMINISTRATOR)
        self.client.force_login(administrator)
        self.assertEqual(
            self.client.get(reverse('dashboard:activity_reports')).status_code,
            200,
        )
