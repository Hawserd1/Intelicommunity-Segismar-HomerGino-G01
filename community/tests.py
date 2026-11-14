from django.contrib.auth import get_user_model
from django.db.models.deletion import ProtectedError
from django.test import TestCase
from django.urls import reverse

from .forms import DiscussionForm
from .models import CommunitySection, Discussion, Reply, Tag

User = get_user_model()


class CommunityFeatureTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.member = User.objects.create_user(
            username='member',
            email='member@example.com',
            password='Safe-password-872!',
        )
        cls.other_member = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='Safe-password-872!',
        )
        cls.moderator = User.objects.create_user(
            username='moderator',
            email='moderator@example.com',
            password='Safe-password-872!',
            role=User.Role.MODERATOR,
        )
        cls.section, _created = CommunitySection.objects.get_or_create(
            name='Programming',
            defaults={
                'description': 'Questions and ideas about programming.',
            },
        )
        cls.discussion = Discussion.objects.create(
            section=cls.section,
            author=cls.member,
            title='How do Django migrations work?',
            body='I would like to understand how migrations update the database.',
        )

    def test_section_slug_is_generated_and_sections_are_listed(self):
        response = self.client.get(reverse('community:section_list'))

        self.assertEqual(self.section.slug, 'programming')
        self.assertContains(response, 'Programming')
        self.assertContains(response, reverse('community:section_detail', args=('programming',)))

    def test_starter_community_sections_are_available(self):
        names = set(
            CommunitySection.objects.filter(
                name__in=('Programming', 'Engineering', 'Cooking', 'Music', 'Language')
            ).values_list('name', flat=True)
        )

        self.assertEqual(
            names,
            {'Programming', 'Engineering', 'Cooking', 'Music', 'Language'},
        )

    def test_section_page_lists_its_discussions_and_post_link(self):
        self.client.force_login(self.member)
        response = self.client.get(self.section.get_absolute_url())

        self.assertContains(response, self.discussion.title)
        self.assertContains(
            response,
            reverse('community:section_discussion_create', args=(self.section.slug,)),
        )

    def test_users_can_follow_and_unfollow_a_section_with_post_requests(self):
        self.client.force_login(self.member)
        follow_url = reverse('community:toggle_follow', args=(self.section.slug,))

        response = self.client.post(follow_url)
        self.assertRedirects(response, self.section.get_absolute_url())
        self.assertTrue(self.section.followers.filter(pk=self.member.pk).exists())

        response = self.client.post(follow_url)
        self.assertRedirects(response, self.section.get_absolute_url())
        self.assertFalse(self.section.followers.filter(pk=self.member.pk).exists())

    def test_follow_requires_login_and_rejects_get(self):
        follow_url = reverse('community:toggle_follow', args=(self.section.slug,))
        response = self.client.post(follow_url)
        self.assertRedirects(
            response,
            f'{reverse("accounts:login")}?next={follow_url}',
        )

        self.client.force_login(self.member)
        self.assertEqual(self.client.get(follow_url).status_code, 405)

    def test_member_can_create_discussion_in_a_section(self):
        self.client.force_login(self.member)
        url = reverse('community:section_discussion_create', args=(self.section.slug,))

        response = self.client.post(
            url,
            {
                'title': 'A new programming question',
                'body': 'Here are the details of my question.',
            },
        )

        created = Discussion.objects.get(title='A new programming question')
        self.assertRedirects(response, created.get_absolute_url())
        self.assertEqual(created.author, self.member)
        self.assertEqual(created.section, self.section)

    def test_member_can_create_discussion_with_section_selector(self):
        self.client.force_login(self.member)
        response = self.client.post(
            reverse('community:discussion_create'),
            {
                'section': self.section.pk,
                'title': 'Choosing a section',
                'body': 'This discussion uses the section selector.',
            },
        )

        created = Discussion.objects.get(title='Choosing a section')
        self.assertRedirects(response, created.get_absolute_url())
        self.assertEqual(created.section, self.section)

    def test_discussion_creation_requires_login(self):
        url = reverse('community:discussion_create')
        response = self.client.get(url)

        self.assertRedirects(
            response,
            f'{reverse("accounts:login")}?next={url}',
        )

    def test_member_can_view_and_reply_to_discussion(self):
        self.client.force_login(self.other_member)
        detail_url = self.discussion.get_absolute_url()
        self.assertContains(self.client.get(detail_url), self.discussion.title)

        response = self.client.post(
            reverse('community:reply_create', args=(self.discussion.pk,)),
            {'body': 'A helpful answer with more detail.'},
        )

        reply = Reply.objects.get(discussion=self.discussion)
        self.assertRedirects(response, detail_url)
        self.assertEqual(reply.author, self.other_member)
        self.assertContains(self.client.get(detail_url), 'A helpful answer with more detail.')

    def test_anonymous_users_can_read_discussions_but_cannot_reply(self):
        self.assertEqual(self.client.get(self.discussion.get_absolute_url()).status_code, 200)

        reply_url = reverse('community:reply_create', args=(self.discussion.pk,))
        response = self.client.post(reply_url, {'body': 'A reply'})
        self.assertRedirects(
            response,
            f'{reverse("accounts:login")}?next={reply_url}',
        )

    def test_author_can_update_and_delete_their_discussion(self):
        self.client.force_login(self.member)
        edit_url = reverse('community:discussion_update', args=(self.discussion.pk,))
        response = self.client.post(
            edit_url,
            {
                'section': self.section.pk,
                'title': 'Updated discussion title',
                'body': 'Updated discussion details.',
            },
        )

        self.assertRedirects(response, self.discussion.get_absolute_url())
        self.discussion.refresh_from_db()
        self.assertEqual(self.discussion.title, 'Updated discussion title')

        response = self.client.post(
            reverse('community:discussion_delete', args=(self.discussion.pk,))
        )
        self.assertRedirects(response, reverse('community:discussion_list'))
        self.assertFalse(Discussion.objects.filter(pk=self.discussion.pk).exists())

    def test_discussion_tags_are_created_normalized_and_reused(self):
        self.client.force_login(self.member)
        create_url = reverse('community:discussion_create')
        first_response = self.client.post(
            create_url,
            {
                'section': self.section.pk,
                'title': 'First tagged discussion',
                'body': 'Discussion with tags.',
                'tags': ' Python, Django, python ',
            },
        )
        first = Discussion.objects.get(title='First tagged discussion')
        self.assertRedirects(first_response, first.get_absolute_url())
        self.assertEqual(
            list(first.tags.values_list('name', flat=True)),
            ['django', 'python'],
        )
        self.assertEqual(Tag.objects.filter(name='python').count(), 1)

        self.client.post(
            create_url,
            {
                'section': self.section.pk,
                'title': 'Second tagged discussion',
                'body': 'It reuses the same tag.',
                'tags': 'PYTHON',
            },
        )
        second = Discussion.objects.get(title='Second tagged discussion')
        self.assertEqual(Tag.objects.filter(name='python').count(), 1)
        self.assertTrue(second.tags.filter(name='python').exists())

    def test_editing_discussion_replaces_its_tags(self):
        old_tag = Tag.objects.create(name='old-tag')
        self.discussion.tags.add(old_tag)
        self.client.force_login(self.member)

        response = self.client.post(
            reverse('community:discussion_update', args=(self.discussion.pk,)),
            {
                'section': self.section.pk,
                'title': self.discussion.title,
                'body': self.discussion.body,
                'tags': 'Django, testing',
            },
        )

        self.assertRedirects(response, self.discussion.get_absolute_url())
        self.assertEqual(
            set(self.discussion.tags.values_list('name', flat=True)),
            {'django', 'testing'},
        )

    def test_discussion_form_rejects_more_than_five_or_invalid_tags(self):
        too_many_tags = DiscussionForm(
            data={
                'section': self.section.pk,
                'title': 'Too many tags',
                'body': 'This form should be invalid.',
                'tags': 'one, two, three, four, five, six',
            }
        )
        invalid_tag = DiscussionForm(
            data={
                'section': self.section.pk,
                'title': 'Invalid tag',
                'body': 'This form should be invalid.',
                'tags': 'not a valid tag',
            }
        )

        self.assertFalse(too_many_tags.is_valid())
        self.assertIn('no more than 5 tags', str(too_many_tags.errors))
        self.assertFalse(invalid_tag.is_valid())
        self.assertIn('Tags must start', str(invalid_tag.errors))

    def test_tags_are_displayed_and_link_to_matching_discussions(self):
        self.client.force_login(self.member)
        form = DiscussionForm(
            data={
                'section': self.section.pk,
                'title': 'Tagged discussion for display',
                'body': 'The tag appears on the post.',
                'tags': 'django',
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        discussion = form.save(commit=False)
        discussion.author = self.member
        discussion.save()
        form.save()
        tag = discussion.tags.get(name='django')

        detail_response = self.client.get(discussion.get_absolute_url())
        self.assertContains(detail_response, 'django')
        self.assertContains(
            detail_response,
            reverse('community:tag_detail', args=(tag.pk,)),
        )

        tag_response = self.client.get(
            reverse('community:tag_detail', args=(tag.pk,))
        )
        self.assertContains(tag_response, discussion.title)
    def test_other_member_cannot_edit_or_delete_discussion(self):
        self.client.force_login(self.other_member)

        edit_response = self.client.get(
            reverse('community:discussion_update', args=(self.discussion.pk,))
        )
        delete_response = self.client.get(
            reverse('community:discussion_delete', args=(self.discussion.pk,))
        )

        self.assertEqual(edit_response.status_code, 403)
        self.assertEqual(delete_response.status_code, 403)

    def test_moderator_can_manage_discussions_without_becoming_django_staff(self):
        self.client.force_login(self.moderator)
        response = self.client.get(
            reverse('community:discussion_update', args=(self.discussion.pk,))
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.moderator.is_staff)

    def test_deleting_a_section_with_discussions_is_protected(self):
        with self.assertRaises(ProtectedError):
            self.section.delete()
