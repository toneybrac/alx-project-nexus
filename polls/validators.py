"""Custom validators for input validation and sanitization."""

import re
from django.core.exceptions import ValidationError
from django.utils.html import strip_tags


def validate_no_html(value):
    """
    Validate that the input doesn't contain HTML tags.

    Prevents XSS attacks by rejecting inputs with HTML.
    """
    if value != strip_tags(value):
        raise ValidationError(
            'HTML tags are not allowed in this field.',
            code='html_not_allowed'
        )
    return value


def validate_no_script_tags(value):
    """
    Validate that the input doesn't contain script tags.

    Additional protection against XSS attacks.
    """
    script_pattern = re.compile(r'<script[\s\S]*?>[\s\S]*?</script>', re.IGNORECASE)
    if script_pattern.search(value):
        raise ValidationError(
            'Script tags are not allowed.',
            code='script_not_allowed'
        )
    return value


def validate_safe_characters(value):
    """
    Validate that the input contains only safe characters.

    Allows: alphanumeric, spaces, and common punctuation.
    Prevents: potentially dangerous characters used in injections.
    """
    # Allow letters, numbers, spaces, and basic punctuation
    safe_pattern = re.compile(r'^[a-zA-Z0-9\s\.\,\?\!\-\_\'\"\(\)\:]+$')

    if not safe_pattern.match(value):
        raise ValidationError(
            'Input contains invalid characters. Only letters, numbers, and basic punctuation are allowed.',
            code='unsafe_characters'
        )
    return value


def validate_poll_active(poll):
    """Validate that a poll is active."""
    if not poll.is_active:
        raise ValidationError(
            'This poll is not active.',
            code='poll_inactive'
        )


def validate_poll_not_expired(poll):
    """Validate that a poll has not expired."""
    if poll.is_expired:
        raise ValidationError(
            'This poll has expired.',
            code='poll_expired'
        )


def validate_minimum_options(options):
    """
    Validate that a poll has at least 2 options.

    A meaningful poll requires at least two choices.
    """
    if len(options) < 2:
        raise ValidationError(
            'A poll must have at least 2 options.',
            code='insufficient_options'
        )
    return options


def validate_max_title_length(value, max_length=200):
    """
    Validate title length to prevent abuse.

    Args:
        value: The title string
        max_length: Maximum allowed length (default: 200)
    """
    if len(value) > max_length:
        raise ValidationError(
            f'Title must not exceed {max_length} characters.',
            code='title_too_long'
        )
    return value


def validate_max_description_length(value, max_length=1000):
    """
    Validate description length to prevent abuse.

    Args:
        value: The description string
        max_length: Maximum allowed length (default: 1000)
    """
    if len(value) > max_length:
        raise ValidationError(
            f'Description must not exceed {max_length} characters.',
            code='description_too_long'
        )
    return value
