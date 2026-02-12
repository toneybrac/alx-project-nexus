from django.contrib import admin
from .models import Poll, Option, Vote


class OptionInline(admin.TabularInline):
    """Inline admin for poll options."""
    model = Option
    extra = 2
    fields = ('text', 'order')


@admin.register(Poll)
class PollAdmin(admin.ModelAdmin):
    """Admin configuration for Poll model."""
    list_display = ('title', 'created_at', 'expires_at', 'is_active', 'is_expired')
    list_filter = ('is_active', 'created_at')
    search_fields = ('title', 'description')
    date_hierarchy = 'created_at'
    inlines = [OptionInline]

    def is_expired(self, obj):
        """Display expiration status."""
        return obj.is_expired
    is_expired.boolean = True
    is_expired.short_description = 'Expired'


@admin.register(Option)
class OptionAdmin(admin.ModelAdmin):
    """Admin configuration for Option model."""
    list_display = ('text', 'poll', 'order', 'vote_count')
    list_filter = ('poll',)
    search_fields = ('text', 'poll__title')
    ordering = ('poll', 'order')


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    """Admin configuration for Vote model."""
    list_display = ('poll', 'option', 'voter_identifier', 'voted_at')
    list_filter = ('poll', 'voted_at')
    search_fields = ('voter_identifier', 'poll__title')
    date_hierarchy = 'voted_at'
    readonly_fields = ('voted_at',)
