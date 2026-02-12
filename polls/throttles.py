"""Custom throttle classes for rate limiting specific actions."""

from rest_framework.throttling import UserRateThrottle, AnonRateThrottle


class VoteRateThrottle(AnonRateThrottle):
    """
    Throttle for voting endpoint.

    Limits voting to prevent abuse while allowing legitimate users
    to participate in multiple polls.

    Rate: 10 votes per hour for anonymous users
    """
    scope = 'vote'


class CreatePollRateThrottle(UserRateThrottle):
    """
    Throttle for poll creation endpoint.

    Limits poll creation to prevent spam.

    Rate: 20 poll creations per hour
    """
    scope = 'create_poll'
