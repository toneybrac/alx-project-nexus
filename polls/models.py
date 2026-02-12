from django.db import models
from django.utils import timezone


class Poll(models.Model):
    """Model representing a poll with multiple options."""
    title = models.CharField(max_length=200, help_text="Poll title")
    description = models.TextField(blank=True, help_text="Optional poll description")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Poll expiry date/time (optional)"
    )
    is_active = models.BooleanField(default=True, help_text="Whether the poll is active")

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return self.title

    @property
    def is_expired(self):
        """Check if the poll has expired."""
        if self.expires_at is None:
            return False
        return timezone.now() > self.expires_at

    def user_has_voted(self, voter_identifier):
        """Check if a user has already voted in this poll."""
        return self.votes.filter(voter_identifier=voter_identifier).exists()

    def get_results(self):
        """Get vote counts for all options in this poll."""
        from django.db.models import Count
        return self.options.annotate(votes_total=Count('votes')).order_by('order')


class Option(models.Model):
    """Model representing a poll option/choice."""
    poll = models.ForeignKey(
        Poll,
        on_delete=models.CASCADE,
        related_name='options'
    )
    text = models.CharField(max_length=200, help_text="Option text")
    order = models.IntegerField(default=0, help_text="Display order")

    class Meta:
        ordering = ['order', 'id']
        indexes = [
            models.Index(fields=['poll', 'order']),
        ]

    def __str__(self):
        return f"{self.poll.title} - {self.text}"

    @property
    def vote_count(self):
        """Get the number of votes for this option."""
        return self.votes.count()


class Vote(models.Model):
    """Model representing a vote cast for a poll option."""
    poll = models.ForeignKey(
        Poll,
        on_delete=models.CASCADE,
        related_name='votes'
    )
    option = models.ForeignKey(
        Option,
        on_delete=models.CASCADE,
        related_name='votes'
    )
    voter_identifier = models.CharField(
        max_length=255,
        help_text="Unique identifier for the voter (IP, session ID, or user ID)"
    )
    voted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['poll', 'voter_identifier'],
                name='unique_vote_per_poll'
            )
        ]
        indexes = [
            models.Index(fields=['poll']),
            models.Index(fields=['voter_identifier']),
        ]

    def __str__(self):
        return f"Vote for {self.option.text} in {self.poll.title}"
