from django.test import TestCase
from django.utils import timezone
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from datetime import timedelta

from .models import Poll, Option, Vote
from .services import get_voter_identifier


class PollModelTest(TestCase):
    """Test cases for Poll model."""

    def setUp(self):
        """Set up test data."""
        self.poll = Poll.objects.create(
            title="Test Poll",
            description="Test Description",
            is_active=True
        )
        self.option1 = Option.objects.create(poll=self.poll, text="Option 1", order=1)
        self.option2 = Option.objects.create(poll=self.poll, text="Option 2", order=2)

    def test_poll_creation(self):
        """Test poll is created correctly."""
        self.assertEqual(self.poll.title, "Test Poll")
        self.assertEqual(self.poll.description, "Test Description")
        self.assertTrue(self.poll.is_active)
        self.assertIsNotNone(self.poll.created_at)

    def test_poll_str(self):
        """Test poll string representation."""
        self.assertEqual(str(self.poll), "Test Poll")

    def test_is_expired_no_expiry(self):
        """Test poll without expiry date is not expired."""
        self.assertFalse(self.poll.is_expired)

    def test_is_expired_future_date(self):
        """Test poll with future expiry is not expired."""
        self.poll.expires_at = timezone.now() + timedelta(days=7)
        self.poll.save()
        self.assertFalse(self.poll.is_expired)

    def test_is_expired_past_date(self):
        """Test poll with past expiry is expired."""
        self.poll.expires_at = timezone.now() - timedelta(days=1)
        self.poll.save()
        self.assertTrue(self.poll.is_expired)

    def test_user_has_voted(self):
        """Test checking if user has voted."""
        voter_id = "test_voter_123"
        self.assertFalse(self.poll.user_has_voted(voter_id))

        Vote.objects.create(
            poll=self.poll,
            option=self.option1,
            voter_identifier=voter_id
        )
        self.assertTrue(self.poll.user_has_voted(voter_id))

    def test_get_results(self):
        """Test getting poll results."""
        Vote.objects.create(poll=self.poll, option=self.option1, voter_identifier="voter1")
        Vote.objects.create(poll=self.poll, option=self.option1, voter_identifier="voter2")
        Vote.objects.create(poll=self.poll, option=self.option2, voter_identifier="voter3")

        results = self.poll.get_results()
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0].votes_total, 2)
        self.assertEqual(results[1].votes_total, 1)


class OptionModelTest(TestCase):
    """Test cases for Option model."""

    def setUp(self):
        """Set up test data."""
        self.poll = Poll.objects.create(title="Test Poll")
        self.option = Option.objects.create(poll=self.poll, text="Test Option", order=1)

    def test_option_creation(self):
        """Test option is created correctly."""
        self.assertEqual(self.option.text, "Test Option")
        self.assertEqual(self.option.order, 1)
        self.assertEqual(self.option.poll, self.poll)

    def test_option_str(self):
        """Test option string representation."""
        self.assertEqual(str(self.option), "Test Poll - Test Option")

    def test_vote_count(self):
        """Test vote count property."""
        self.assertEqual(self.option.vote_count, 0)

        Vote.objects.create(poll=self.poll, option=self.option, voter_identifier="voter1")
        Vote.objects.create(poll=self.poll, option=self.option, voter_identifier="voter2")

        self.assertEqual(self.option.vote_count, 2)


class VoteModelTest(TestCase):
    """Test cases for Vote model."""

    def setUp(self):
        """Set up test data."""
        self.poll = Poll.objects.create(title="Test Poll")
        self.option = Option.objects.create(poll=self.poll, text="Test Option")

    def test_vote_creation(self):
        """Test vote is created correctly."""
        vote = Vote.objects.create(
            poll=self.poll,
            option=self.option,
            voter_identifier="test_voter"
        )
        self.assertEqual(vote.poll, self.poll)
        self.assertEqual(vote.option, self.option)
        self.assertEqual(vote.voter_identifier, "test_voter")
        self.assertIsNotNone(vote.voted_at)

    def test_vote_str(self):
        """Test vote string representation."""
        vote = Vote.objects.create(
            poll=self.poll,
            option=self.option,
            voter_identifier="test_voter"
        )
        self.assertIn("Test Option", str(vote))
        self.assertIn("Test Poll", str(vote))

    def test_unique_constraint(self):
        """Test unique constraint prevents duplicate votes."""
        Vote.objects.create(
            poll=self.poll,
            option=self.option,
            voter_identifier="test_voter"
        )

        # Try to create duplicate vote
        with self.assertRaises(Exception):
            Vote.objects.create(
                poll=self.poll,
                option=self.option,
                voter_identifier="test_voter"
            )


class PollAPITest(APITestCase):
    """Test cases for Poll API endpoints."""

    def setUp(self):
        """Set up test client and data."""
        self.client = APIClient()
        self.poll = Poll.objects.create(
            title="API Test Poll",
            description="Test Description",
            is_active=True
        )
        self.option1 = Option.objects.create(poll=self.poll, text="Option 1", order=1)
        self.option2 = Option.objects.create(poll=self.poll, text="Option 2", order=2)

    def test_list_polls(self):
        """Test listing all polls."""
        url = reverse('poll-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 1)

    def test_retrieve_poll(self):
        """Test retrieving a single poll."""
        url = reverse('poll-detail', kwargs={'pk': self.poll.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], "API Test Poll")
        self.assertEqual(len(response.data['options']), 2)

    def test_create_poll(self):
        """Test creating a new poll."""
        url = reverse('poll-list')
        data = {
            'title': 'New Poll',
            'description': 'New Description',
            'is_active': True,
            'options': [
                {'text': 'Option A', 'order': 1},
                {'text': 'Option B', 'order': 2}
            ]
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Poll.objects.count(), 2)
        self.assertEqual(Option.objects.filter(poll__title='New Poll').count(), 2)

    def test_create_poll_insufficient_options(self):
        """Test creating poll with less than 2 options fails."""
        url = reverse('poll-list')
        data = {
            'title': 'Invalid Poll',
            'is_active': True,
            'options': [
                {'text': 'Only One Option', 'order': 1}
            ]
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_poll(self):
        """Test updating a poll."""
        url = reverse('poll-detail', kwargs={'pk': self.poll.id})
        data = {
            'title': 'Updated Poll Title',
            'description': 'Updated Description',
            'is_active': False
        }
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.poll.refresh_from_db()
        self.assertEqual(self.poll.title, 'Updated Poll Title')

    def test_delete_poll(self):
        """Test deleting a poll."""
        url = reverse('poll-detail', kwargs={'pk': self.poll.id})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Poll.objects.count(), 0)


class VoteAPITest(APITestCase):
    """Test cases for voting API."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.poll = Poll.objects.create(title="Vote Test Poll", is_active=True)
        self.option1 = Option.objects.create(poll=self.poll, text="Option 1", order=1)
        self.option2 = Option.objects.create(poll=self.poll, text="Option 2", order=2)

    def test_cast_vote(self):
        """Test casting a vote."""
        url = reverse('poll-vote', kwargs={'pk': self.poll.id})
        data = {'option_id': self.option1.id}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Vote.objects.count(), 1)
        self.assertIn('message', response.data)

    def test_duplicate_vote_prevention(self):
        """Test that duplicate voting is prevented."""
        url = reverse('poll-vote', kwargs={'pk': self.poll.id})
        data = {'option_id': self.option1.id}

        # First vote should succeed
        response1 = self.client.post(url, data, format='json')
        self.assertEqual(response1.status_code, status.HTTP_201_CREATED)

        # Second vote should fail
        response2 = self.client.post(url, data, format='json')
        self.assertEqual(response2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_vote_on_inactive_poll(self):
        """Test voting on inactive poll fails."""
        self.poll.is_active = False
        self.poll.save()

        url = reverse('poll-vote', kwargs={'pk': self.poll.id})
        data = {'option_id': self.option1.id}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_vote_on_expired_poll(self):
        """Test voting on expired poll fails."""
        self.poll.expires_at = timezone.now() - timedelta(days=1)
        self.poll.save()

        url = reverse('poll-vote', kwargs={'pk': self.poll.id})
        data = {'option_id': self.option1.id}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_vote_with_invalid_option(self):
        """Test voting with invalid option ID."""
        url = reverse('poll-vote', kwargs={'pk': self.poll.id})
        data = {'option_id': 99999}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


class ResultsAPITest(APITestCase):
    """Test cases for results API."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.poll = Poll.objects.create(title="Results Test Poll")
        self.option1 = Option.objects.create(poll=self.poll, text="Option 1", order=1)
        self.option2 = Option.objects.create(poll=self.poll, text="Option 2", order=2)

        # Create some votes
        Vote.objects.create(poll=self.poll, option=self.option1, voter_identifier="voter1")
        Vote.objects.create(poll=self.poll, option=self.option1, voter_identifier="voter2")
        Vote.objects.create(poll=self.poll, option=self.option2, voter_identifier="voter3")

    def test_get_results(self):
        """Test getting poll results."""
        url = reverse('poll-results', kwargs={'pk': self.poll.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['total_votes'], 3)
        self.assertEqual(len(response.data['options']), 2)

    def test_results_vote_counts(self):
        """Test vote counts in results."""
        url = reverse('poll-results', kwargs={'pk': self.poll.id})
        response = self.client.get(url)
        options = response.data['options']

        option1_data = next(opt for opt in options if opt['text'] == 'Option 1')
        option2_data = next(opt for opt in options if opt['text'] == 'Option 2')

        self.assertEqual(option1_data['vote_count'], 2)
        self.assertEqual(option2_data['vote_count'], 1)

    def test_results_percentages(self):
        """Test percentage calculations in results."""
        url = reverse('poll-results', kwargs={'pk': self.poll.id})
        response = self.client.get(url)
        options = response.data['options']

        option1_data = next(opt for opt in options if opt['text'] == 'Option 1')
        option2_data = next(opt for opt in options if opt['text'] == 'Option 2')

        self.assertAlmostEqual(option1_data['percentage'], 66.67, places=1)
        self.assertAlmostEqual(option2_data['percentage'], 33.33, places=1)


class HasVotedAPITest(APITestCase):
    """Test cases for has_voted API."""

    def setUp(self):
        """Set up test data."""
        self.client = APIClient()
        self.poll = Poll.objects.create(title="Has Voted Test Poll")
        self.option = Option.objects.create(poll=self.poll, text="Option 1")

    def test_has_not_voted(self):
        """Test checking vote status when user hasn't voted."""
        url = reverse('poll-has-voted', kwargs={'pk': self.poll.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(response.data['has_voted'])

    def test_has_voted(self):
        """Test checking vote status when user has voted."""
        # Cast a vote first
        vote_url = reverse('poll-vote', kwargs={'pk': self.poll.id})
        self.client.post(vote_url, {'option_id': self.option.id}, format='json')

        # Check vote status
        url = reverse('poll-has-voted', kwargs={'pk': self.poll.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['has_voted'])


class SecurityTest(APITestCase):
    """Test cases for security features."""

    def setUp(self):
        """Set up test client."""
        self.client = APIClient()

    def test_html_injection_in_title(self):
        """Test that HTML tags in poll title are rejected."""
        url = reverse('poll-list')
        data = {
            'title': '<script>alert("XSS")</script>Test Poll',
            'is_active': True,
            'options': [
                {'text': 'Option A', 'order': 1},
                {'text': 'Option B', 'order': 2}
            ]
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_html_injection_in_description(self):
        """Test that HTML tags in description are rejected."""
        url = reverse('poll-list')
        data = {
            'title': 'Valid Title',
            'description': '<b>Bold text</b>',
            'is_active': True,
            'options': [
                {'text': 'Option A', 'order': 1},
                {'text': 'Option B', 'order': 2}
            ]
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_html_injection_in_option_text(self):
        """Test that HTML tags in option text are rejected."""
        url = reverse('poll-list')
        data = {
            'title': 'Valid Title',
            'is_active': True,
            'options': [
                {'text': '<img src=x onerror=alert(1)>', 'order': 1},
                {'text': 'Option B', 'order': 2}
            ]
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_valid_input_accepted(self):
        """Test that valid input without HTML is accepted."""
        url = reverse('poll-list')
        data = {
            'title': 'Valid Poll Title',
            'description': 'This is a valid description',
            'is_active': True,
            'options': [
                {'text': 'Option A', 'order': 1},
                {'text': 'Option B', 'order': 2}
            ]
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_title_max_length(self):
        """Test that overly long titles are rejected."""
        url = reverse('poll-list')
        data = {
            'title': 'A' * 201,  # 201 characters
            'is_active': True,
            'options': [
                {'text': 'Option A', 'order': 1},
                {'text': 'Option B', 'order': 2}
            ]
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_description_max_length(self):
        """Test that overly long descriptions are rejected."""
        url = reverse('poll-list')
        data = {
            'title': 'Valid Title',
            'description': 'A' * 1001,  # 1001 characters
            'is_active': True,
            'options': [
                {'text': 'Option A', 'order': 1},
                {'text': 'Option B', 'order': 2}
            ]
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
