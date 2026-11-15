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
                name='unique_vote_per_user_discussion',
            ),
            models.CheckConstraint(
                condition=models.Q(value__in=('up', 'down')),
                name='vote_value_must_be_up_or_down',
            ),
        ]

    def __str__(self):
        return f'{self.get_value_display()} by {self.user} on {self.discussion}'
