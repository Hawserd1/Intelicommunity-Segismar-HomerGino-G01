from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Tag(models.Model):
    name = models.CharField(max_length=30, unique=True)

    class Meta:
        ordering = ('name',)

    def __str__(self):
        return self.name


class CommunitySection(models.Model):
    name = models.CharField(max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True, blank=True)
    description = models.TextField()
    followers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='followed_sections',
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('name',)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('community:section_detail', kwargs={'slug': self.slug})

    def __str__(self):
        return self.name


class Discussion(models.Model):
    section = models.ForeignKey(
        CommunitySection,
        on_delete=models.PROTECT,
        related_name='discussions',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='discussions',
    )
    title = models.CharField(max_length=200)
    body = models.TextField()
    tags = models.ManyToManyField(Tag, related_name='discussions', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-created_at',)

    def get_absolute_url(self):
        return reverse('community:discussion_detail', kwargs={'pk': self.pk})

    def __str__(self):
        return self.title


class Reply(models.Model):
    discussion = models.ForeignKey(
        Discussion,
        on_delete=models.CASCADE,
        related_name='replies',
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='discussion_replies',
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('created_at',)

    def __str__(self):
        return f'Reply by {self.author} on {self.discussion}'


class Vote(models.Model):
    class Value(models.TextChoices):
        UP = 'up', 'Upvote'
        DOWN = 'down', 'Downvote'

    discussion = models.ForeignKey(
        Discussion,
        on_delete=models.CASCADE,
        related_name='votes',
        null=True,
        blank=True,
    )
    reply = models.ForeignKey(
        Reply,
        on_delete=models.CASCADE,
        related_name='votes',
        null=True,
        blank=True,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='discussion_votes',
    )
    value = models.CharField(max_length=4, choices=Value.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=('discussion', 'user'),
                condition=models.Q(discussion__isnull=False),
                name='unique_user_discussion_vote',
            ),
            models.UniqueConstraint(
                fields=('reply', 'user'),
                condition=models.Q(reply__isnull=False),
                name='unique_user_reply_vote',
            ),
            models.CheckConstraint(
                condition=(
                    models.Q(discussion__isnull=False, reply__isnull=True)
                    | models.Q(discussion__isnull=True, reply__isnull=False)
                ),
                name='vote_has_one_target',
            ),
            models.CheckConstraint(
                condition=models.Q(value__in=('up', 'down')),
                name='vote_value_must_be_up_or_down',
            ),
        ]

    def __str__(self):
        target = self.discussion or self.reply
        return f'{self.get_value_display()} by {self.user} on {target}'


class ContentReport(models.Model):
    class Reason(models.TextChoices):
        SPAM = 'spam', 'Spam'
        HARASSMENT = 'harassment', 'Harassment or abuse'
        MISINFORMATION = 'misinformation', 'Misleading information'
        OTHER = 'other', 'Other'

    class Status(models.TextChoices):
        PENDING = 'pending', 'Pending review'
        REVIEWED = 'reviewed', 'Reviewed'
        DISMISSED = 'dismissed', 'Dismissed'

    reported_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='content_reports',
    )
    discussion = models.ForeignKey(
        Discussion,
        on_delete=models.CASCADE,
        related_name='content_reports',
        null=True,
        blank=True,
    )
    reply = models.ForeignKey(
        Reply,
        on_delete=models.CASCADE,
        related_name='content_reports',
        null=True,
        blank=True,
    )
    reason = models.CharField(max_length=20, choices=Reason.choices)
    details = models.TextField(blank=True, max_length=1000)
    status = models.CharField(
        max_length=10,
        choices=Status.choices,
        default=Status.PENDING,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='reviewed_content_reports',
        null=True,
        blank=True,
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ('-created_at',)
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(discussion__isnull=False, reply__isnull=True)
                    | models.Q(discussion__isnull=True, reply__isnull=False)
                ),
                name='content_report_has_one_target',
            ),
            models.UniqueConstraint(
                fields=('reported_by', 'discussion'),
                condition=models.Q(discussion__isnull=False),
                name='unique_reporter_discussion_report',
            ),
            models.UniqueConstraint(
                fields=('reported_by', 'reply'),
                condition=models.Q(reply__isnull=False),
                name='unique_reporter_reply_report',
            ),
        ]

    def __str__(self):
        target = self.discussion or self.reply
        return f'Report by {self.reported_by} on {target}'
