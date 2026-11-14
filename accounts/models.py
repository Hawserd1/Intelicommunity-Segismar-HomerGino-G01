from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):
    class Role(models.TextChoices):
        STANDARD_USER = 'STANDARD_USER', 'Standard User'
        MODERATOR = 'MODERATOR', 'Moderator'
        ADMINISTRATOR = 'ADMINISTRATOR', 'Administrator'

    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=24,
        choices=Role.choices,
        default=Role.STANDARD_USER,
    )
    contact_number = models.CharField(max_length=30, blank=True)
    expertise = models.CharField(max_length=100, blank=True)
    bio = models.TextField(blank=True)

    def __str__(self):
        return self.username
