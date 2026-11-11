from django.contrib import admin
from .models import ShortURL


@admin.register(ShortURL)
class ShortURLAdmin(admin.ModelAdmin):
    list_display = (
        'short_code',
        'original_url',
        'clicks',
        'created_at',
        'expires_at',
        'is_active'
    )

    search_fields = ('short_code', 'original_url')
    list_filter = ('is_active', 'created_at')
from .models import ClickEvent


@admin.register(ClickEvent)
class ClickEventAdmin(admin.ModelAdmin):
    list_display = (
        'short_url',
        'clicked_at',
        'device',
        'browser',
        'operating_system',
        'country'
    )

    list_filter = (
        'device',
        'browser',
        'operating_system',
        'clicked_at'
    )

    search_fields = ('short_url__short_code', 'ip_address')