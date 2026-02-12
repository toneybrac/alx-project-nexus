"""Business logic and utility services for polls app."""


def get_voter_identifier(request):
    """
    Get a unique identifier for the voter from the request.

    Priority:
    1. User ID if authenticated
    2. IP address from request headers
    3. Session key as fallback

    Args:
        request: Django request object

    Returns:
        str: Unique voter identifier
    """
    # If user is authenticated, use user ID
    if request.user.is_authenticated:
        return f"user_{request.user.id}"

    # Try to get IP address
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Get the first IP in the chain (client IP)
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')

    # Use IP if available
    if ip:
        return f"ip_{ip}"

    # Fallback to session key
    if not request.session.session_key:
        request.session.create()

    return f"session_{request.session.session_key}"
