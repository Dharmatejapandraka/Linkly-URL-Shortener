
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class ShortURL(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="short_urls",
        null=True,
        blank=True
    )

    original_url = models.URLField(max_length=2048)

    short_code = models.CharField(
        max_length=20,
        unique=True
    )

    clicks = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    expires_at = models.DateTimeField(
        null=True,
        blank=True
    )

    is_active = models.BooleanField(default=True)

    def is_expired(self):
        return self.expires_at is not None and timezone.now() >= self.expires_at

    def __str__(self):
        return self.short_code

class ClickEvent(models.Model):
    short_url = models.ForeignKey(
        ShortURL,
        on_delete=models.CASCADE,
        related_name="click_events"
    )

    clicked_at = models.DateTimeField(auto_now_add=True)

    referrer = models.URLField(
        max_length=2048,
        blank=True,
        null=True
    )

    ip_address = models.GenericIPAddressField(
        blank=True,
        null=True
    )

    country = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    city = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    device = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    browser = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    operating_system = models.CharField(
        max_length=100,
        blank=True,
        null=True
    )

    def __str__(self):
        return f"{self.short_url.short_code} - {self.clicked_at}"
