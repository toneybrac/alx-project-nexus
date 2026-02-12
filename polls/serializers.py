from rest_framework import serializers
from django.utils import timezone
from django.utils.html import strip_tags
from .models import Poll, Option, Vote
from .validators import validate_no_html, validate_no_script_tags


class OptionSerializer(serializers.ModelSerializer):
    """Serializer for poll options."""
    vote_count = serializers.IntegerField(read_only=True, required=False)

    class Meta:
        model = Option
        fields = ['id', 'text', 'order', 'vote_count']
        read_only_fields = ['id']


class PollListSerializer(serializers.ModelSerializer):
    """Serializer for listing polls (without options)."""
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Poll
        fields = ['id', 'title', 'description', 'created_at', 'expires_at', 'is_active', 'is_expired']
        read_only_fields = ['id', 'created_at']


class PollDetailSerializer(serializers.ModelSerializer):
    """Serializer for poll details with nested options."""
    options = OptionSerializer(many=True, read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Poll
        fields = ['id', 'title', 'description', 'created_at', 'expires_at', 'is_active', 'is_expired', 'options']
        read_only_fields = ['id', 'created_at']


class PollCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating polls with options."""
    options = OptionSerializer(many=True, write_only=True)

    class Meta:
        model = Poll
        fields = ['id', 'title', 'description', 'expires_at', 'is_active', 'options']
        read_only_fields = ['id']

    def validate_title(self, value):
        """Ensure poll title is not empty and sanitize input."""
        if not value or not value.strip():
            raise serializers.ValidationError("Poll title cannot be empty.")

        # Sanitize HTML to prevent XSS
        value = value.strip()
        validate_no_html(value)
        validate_no_script_tags(value)

        # Length validation
        if len(value) > 200:
            raise serializers.ValidationError("Title must not exceed 200 characters.")

        return value

    def validate_description(self, value):
        """Sanitize description input."""
        if value:
            value = value.strip()
            validate_no_html(value)
            validate_no_script_tags(value)

            if len(value) > 1000:
                raise serializers.ValidationError("Description must not exceed 1000 characters.")

        return value

    def validate_options(self, value):
        """Ensure at least 2 options are provided and sanitize option text."""
        if len(value) < 2:
            raise serializers.ValidationError("A poll must have at least 2 options.")

        # Sanitize each option text
        for option in value:
            if 'text' in option:
                text = option['text'].strip()
                validate_no_html(text)
                validate_no_script_tags(text)
                option['text'] = text

        return value

    def create(self, validated_data):
        """Create poll with nested options."""
        options_data = validated_data.pop('options')
        poll = Poll.objects.create(**validated_data)

        for option_data in options_data:
            Option.objects.create(poll=poll, **option_data)

        return poll


class VoteSerializer(serializers.Serializer):
    """Serializer for casting votes."""
    option_id = serializers.IntegerField(write_only=True)
    poll = serializers.PrimaryKeyRelatedField(read_only=True)
    option = OptionSerializer(read_only=True)
    voted_at = serializers.DateTimeField(read_only=True)

    def validate_option_id(self, value):
        """Validate that the option exists."""
        try:
            option = Option.objects.get(id=value)
            self.context['option'] = option
            return value
        except Option.DoesNotExist:
            raise serializers.ValidationError("Invalid option ID.")

    def validate(self, attrs):
        """Validate poll status and duplicate votes."""
        option = self.context.get('option')
        poll = option.poll

        # Check if poll is active
        if not poll.is_active:
            raise serializers.ValidationError("This poll is not active.")

        # Check if poll has expired
        if poll.is_expired:
            raise serializers.ValidationError("This poll has expired.")

        # Check if option belongs to the poll (from URL)
        poll_id = self.context.get('poll_id')
        if poll.id != poll_id:
            raise serializers.ValidationError("This option does not belong to the specified poll.")

        # Check for duplicate vote
        voter_identifier = self.context.get('voter_identifier')
        if poll.user_has_voted(voter_identifier):
            raise serializers.ValidationError("You have already voted in this poll.")

        attrs['poll'] = poll
        attrs['option'] = option
        attrs['voter_identifier'] = voter_identifier

        return attrs

    def create(self, validated_data):
        """Create a vote record."""
        validated_data.pop('option_id', None)
        vote = Vote.objects.create(**validated_data)
        return vote


class OptionResultSerializer(serializers.ModelSerializer):
    """Serializer for option results with vote counts."""
    vote_count = serializers.SerializerMethodField()
    percentage = serializers.SerializerMethodField()

    class Meta:
        model = Option
        fields = ['id', 'text', 'vote_count', 'percentage']

    def get_vote_count(self, obj):
        """Get vote count from annotated field or fallback to property."""
        return getattr(obj, 'votes_total', obj.vote_count)

    def get_percentage(self, obj):
        """Calculate percentage of votes for this option."""
        total_votes = self.context.get('total_votes', 0)
        if total_votes == 0:
            return 0.0
        vote_count = self.get_vote_count(obj)
        return round((vote_count / total_votes) * 100, 2)


class PollResultSerializer(serializers.ModelSerializer):
    """Serializer for poll results."""
    options = OptionResultSerializer(many=True, read_only=True)
    total_votes = serializers.IntegerField(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)

    class Meta:
        model = Poll
        fields = ['id', 'title', 'description', 'total_votes', 'is_expired', 'options']
