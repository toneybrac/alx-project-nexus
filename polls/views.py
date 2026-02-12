from django.db.models import Count
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiResponse, OpenApiExample

from .models import Poll, Option, Vote
from .serializers import (
    PollListSerializer,
    PollDetailSerializer,
    PollCreateSerializer,
    VoteSerializer,
    PollResultSerializer,
    OptionResultSerializer
)
from .services import get_voter_identifier
from .throttles import VoteRateThrottle, CreatePollRateThrottle


@extend_schema(tags=['Polls'])
class PollViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing polls.

    Provides CRUD operations and custom actions for voting and viewing results.
    """
    queryset = Poll.objects.all()

    def get_serializer_class(self):
        """Return appropriate serializer based on action."""
        if self.action == 'list':
            return PollListSerializer
        elif self.action == 'create':
            return PollCreateSerializer
        elif self.action == 'vote':
            return VoteSerializer
        elif self.action == 'results':
            return PollResultSerializer
        return PollDetailSerializer

    def get_queryset(self):
        """Optimize queryset based on action."""
        queryset = Poll.objects.all()

        if self.action == 'retrieve':
            # Prefetch options for detail view
            queryset = queryset.prefetch_related('options')
        elif self.action == 'list':
            # No need for related data in list view
            pass

        return queryset

    def get_throttles(self):
        """Apply specific throttles based on action."""
        from django.conf import settings

        # Skip throttling during tests
        if getattr(settings, 'TESTING', False):
            return []

        if self.action == 'create':
            return [CreatePollRateThrottle()]
        elif self.action == 'vote':
            return [VoteRateThrottle()]
        return super().get_throttles()

    @extend_schema(
        summary="List all polls",
        description="Get a paginated list of all polls without detailed options.",
        responses={200: PollListSerializer(many=True)}
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @extend_schema(
        summary="Get poll details",
        description="Retrieve detailed information about a specific poll including all options.",
        responses={
            200: PollDetailSerializer,
            404: OpenApiResponse(description="Poll not found")
        }
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @extend_schema(
        summary="Update a poll",
        description="Update an existing poll. Note: This updates the poll metadata, not the options.",
        request=PollDetailSerializer,
        responses={
            200: PollDetailSerializer,
            400: OpenApiResponse(description="Bad request - validation errors"),
            404: OpenApiResponse(description="Poll not found")
        }
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Partially update a poll",
        description="Partially update an existing poll.",
        request=PollDetailSerializer,
        responses={
            200: PollDetailSerializer,
            400: OpenApiResponse(description="Bad request - validation errors"),
            404: OpenApiResponse(description="Poll not found")
        }
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(
        summary="Delete a poll",
        description="Delete a poll and all associated options and votes.",
        responses={
            204: OpenApiResponse(description="Poll deleted successfully"),
            404: OpenApiResponse(description="Poll not found")
        }
    )
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    @extend_schema(
        summary="Create a new poll",
        description="Create a new poll with multiple options. Requires at least 2 options.",
        request=PollCreateSerializer,
        responses={
            201: PollDetailSerializer,
            400: OpenApiResponse(description="Bad request - validation errors"),
        },
        examples=[
            OpenApiExample(
                'Create Poll Example',
                value={
                    "title": "What is your favorite programming language?",
                    "description": "Choose your top pick",
                    "expires_at": "2026-12-31T23:59:59Z",
                    "is_active": True,
                    "options": [
                        {"text": "Python", "order": 1},
                        {"text": "JavaScript", "order": 2},
                        {"text": "Go", "order": 3}
                    ]
                },
                request_only=True
            )
        ]
    )
    def create(self, request, *args, **kwargs):
        """Create a new poll with options."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        poll = serializer.save()

        # Return detailed response with options
        response_serializer = PollDetailSerializer(poll)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Cast a vote",
        description=(
            "Cast a vote for one of the poll's options. "
            "The voter is identified automatically by IP address, session, or user ID. "
            "Duplicate voting is prevented - each voter can only vote once per poll."
        ),
        request=VoteSerializer,
        responses={
            201: OpenApiResponse(
                description="Vote cast successfully",
                response={
                    'type': 'object',
                    'properties': {
                        'message': {'type': 'string'},
                        'poll_id': {'type': 'integer'},
                        'option_id': {'type': 'integer'},
                        'voted_at': {'type': 'string', 'format': 'date-time'}
                    }
                }
            ),
            400: OpenApiResponse(description="Bad request - poll inactive, expired, or already voted"),
            404: OpenApiResponse(description="Poll or option not found")
        },
        examples=[
            OpenApiExample(
                'Cast Vote',
                value={"option_id": 1},
                request_only=True
            ),
            OpenApiExample(
                'Vote Success Response',
                value={
                    "message": "Vote cast successfully",
                    "poll_id": 1,
                    "option_id": 1,
                    "voted_at": "2026-02-12T16:30:00Z"
                },
                response_only=True,
                status_codes=['201']
            )
        ]
    )
    @action(detail=True, methods=['post'])
    def vote(self, request, pk=None):
        """
        Cast a vote for a poll option.

        POST /api/polls/{poll_id}/vote/
        Body: {"option_id": 1}
        """
        poll = self.get_object()
        voter_identifier = get_voter_identifier(request)

        serializer = self.get_serializer(
            data=request.data,
            context={
                'request': request,
                'poll_id': poll.id,
                'voter_identifier': voter_identifier
            }
        )
        serializer.is_valid(raise_exception=True)
        vote = serializer.save()

        return Response(
            {
                'message': 'Vote cast successfully',
                'poll_id': vote.poll.id,
                'option_id': vote.option.id,
                'voted_at': vote.voted_at
            },
            status=status.HTTP_201_CREATED
        )

    @extend_schema(
        summary="Get poll results",
        description=(
            "Retrieve real-time poll results including vote counts and percentages for each option. "
            "Results are computed efficiently using database aggregation."
        ),
        responses={
            200: PollResultSerializer,
            404: OpenApiResponse(description="Poll not found")
        },
        examples=[
            OpenApiExample(
                'Poll Results',
                value={
                    "id": 1,
                    "title": "What is your favorite programming language?",
                    "description": "Choose your top pick",
                    "total_votes": 150,
                    "is_expired": False,
                    "options": [
                        {
                            "id": 1,
                            "text": "Python",
                            "vote_count": 75,
                            "percentage": 50.0
                        },
                        {
                            "id": 2,
                            "text": "JavaScript",
                            "vote_count": 45,
                            "percentage": 30.0
                        },
                        {
                            "id": 3,
                            "text": "Go",
                            "vote_count": 30,
                            "percentage": 20.0
                        }
                    ]
                },
                response_only=True
            )
        ]
    )
    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        """
        Get poll results with vote counts and percentages.

        GET /api/polls/{poll_id}/results/
        """
        poll = self.get_object()

        # Get options with vote counts (use different annotation name to avoid property conflict)
        options_with_counts = list(poll.options.annotate(
            votes_total=Count('votes')
        ).order_by('order'))

        # Calculate total votes from annotations
        total_votes = sum(getattr(option, 'votes_total', 0) for option in options_with_counts)

        # Add vote_count attribute for serializer (copy from votes_total)
        for option in options_with_counts:
            option._vote_count = option.votes_total

        # Manually assign the options list and total for serialization
        poll.options.set(options_with_counts, bulk=False)
        poll.total_votes = total_votes

        # Serialize results
        serializer = self.get_serializer(
            poll,
            context={'total_votes': total_votes}
        )

        return Response(serializer.data)

    @extend_schema(
        summary="Check if user has voted",
        description=(
            "Check whether the current user (identified by IP, session, or user ID) "
            "has already cast a vote in this poll. "
            "Useful for frontend to disable voting UI if user has already voted."
        ),
        responses={
            200: OpenApiResponse(
                description="Vote status check result",
                response={
                    'type': 'object',
                    'properties': {
                        'has_voted': {'type': 'boolean'},
                        'voter_identifier': {'type': 'string'}
                    }
                }
            ),
            404: OpenApiResponse(description="Poll not found")
        },
        examples=[
            OpenApiExample(
                'User Has Voted',
                value={
                    "has_voted": True,
                    "voter_identifier": "ip_192.168.1.100"
                },
                response_only=True
            ),
            OpenApiExample(
                'User Has Not Voted',
                value={
                    "has_voted": False,
                    "voter_identifier": "ip_192.168.1.100"
                },
                response_only=True
            )
        ]
    )
    @action(detail=True, methods=['get'])
    def has_voted(self, request, pk=None):
        """
        Check if the current user has already voted in this poll.

        GET /api/polls/{poll_id}/has_voted/
        """
        poll = self.get_object()
        voter_identifier = get_voter_identifier(request)

        has_voted = poll.user_has_voted(voter_identifier)

        return Response({
            'has_voted': has_voted,
            'voter_identifier': voter_identifier
        })
