"""
Management command to seed the database with sample polls, options, and votes.

Usage:
    python manage.py seed_data
    python manage.py seed_data --clear  # Clear existing data first
    python manage.py seed_data --votes 50  # Create 50 votes per poll
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
import random

from polls.models import Poll, Option, Vote


class Command(BaseCommand):
    help = 'Seed the database with sample polls, options, and votes'

    def add_arguments(self, parser):
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing polls, options, and votes before seeding',
        )
        parser.add_argument(
            '--votes',
            type=int,
            default=30,
            help='Number of votes to create per poll (default: 30)',
        )

    def handle(self, *args, **options):
        if options['clear']:
            self.stdout.write(self.style.WARNING('Clearing existing data...'))
            Vote.objects.all().delete()
            Option.objects.all().delete()
            Poll.objects.all().delete()
            self.stdout.write(self.style.SUCCESS('✓ All existing data cleared'))

        self.stdout.write(self.style.NOTICE('\nSeeding database with sample data...'))

        # Sample data
        sample_polls = [
            {
                'title': 'What is your favorite programming language?',
                'description': 'Choose your top pick for software development',
                'expires_at': timezone.now() + timedelta(days=30),
                'is_active': True,
                'options': [
                    {'text': 'Python', 'order': 1},
                    {'text': 'JavaScript', 'order': 2},
                    {'text': 'Java', 'order': 3},
                    {'text': 'C++', 'order': 4},
                    {'text': 'Go', 'order': 5},
                ]
            },
            {
                'title': 'Best web framework in 2026?',
                'description': 'Vote for the most powerful and developer-friendly web framework',
                'expires_at': timezone.now() + timedelta(days=60),
                'is_active': True,
                'options': [
                    {'text': 'Django', 'order': 1},
                    {'text': 'Flask', 'order': 2},
                    {'text': 'FastAPI', 'order': 3},
                    {'text': 'Express.js', 'order': 4},
                    {'text': 'Spring Boot', 'order': 5},
                ]
            },
            {
                'title': 'Preferred code editor?',
                'description': 'Which code editor do you use for daily development?',
                'is_active': True,
                'options': [
                    {'text': 'VS Code', 'order': 1},
                    {'text': 'PyCharm', 'order': 2},
                    {'text': 'Sublime Text', 'order': 3},
                    {'text': 'Vim/Neovim', 'order': 4},
                    {'text': 'IntelliJ IDEA', 'order': 5},
                ]
            },
            {
                'title': 'Best database for web applications?',
                'description': 'Choose the most reliable database for modern web apps',
                'expires_at': timezone.now() + timedelta(days=45),
                'is_active': True,
                'options': [
                    {'text': 'PostgreSQL', 'order': 1},
                    {'text': 'MySQL', 'order': 2},
                    {'text': 'MongoDB', 'order': 3},
                    {'text': 'SQLite', 'order': 4},
                    {'text': 'Redis', 'order': 5},
                ]
            },
            {
                'title': 'Favorite frontend framework?',
                'description': 'Modern JavaScript frameworks for building UIs',
                'is_active': True,
                'options': [
                    {'text': 'React', 'order': 1},
                    {'text': 'Vue.js', 'order': 2},
                    {'text': 'Angular', 'order': 3},
                    {'text': 'Svelte', 'order': 4},
                ]
            },
            {
                'title': 'Preferred operating system for development?',
                'description': 'Which OS do you use for software development?',
                'expires_at': timezone.now() + timedelta(days=90),
                'is_active': True,
                'options': [
                    {'text': 'Linux', 'order': 1},
                    {'text': 'macOS', 'order': 2},
                    {'text': 'Windows', 'order': 3},
                    {'text': 'WSL on Windows', 'order': 4},
                ]
            },
            {
                'title': 'Best API architecture?',
                'description': 'Which API design pattern do you prefer?',
                'is_active': True,
                'options': [
                    {'text': 'REST', 'order': 1},
                    {'text': 'GraphQL', 'order': 2},
                    {'text': 'gRPC', 'order': 3},
                    {'text': 'WebSocket', 'order': 4},
                ]
            },
            {
                'title': 'Cloud provider preference?',
                'description': 'Which cloud platform do you prefer for deployment?',
                'expires_at': timezone.now() + timedelta(days=20),
                'is_active': True,
                'options': [
                    {'text': 'AWS', 'order': 1},
                    {'text': 'Google Cloud', 'order': 2},
                    {'text': 'Azure', 'order': 3},
                    {'text': 'DigitalOcean', 'order': 4},
                    {'text': 'Heroku', 'order': 5},
                ]
            },
            {
                'title': 'Testing framework choice?',
                'description': 'What do you use for testing your Python code?',
                'is_active': True,
                'options': [
                    {'text': 'pytest', 'order': 1},
                    {'text': 'unittest', 'order': 2},
                    {'text': 'nose2', 'order': 3},
                    {'text': 'doctest', 'order': 4},
                ]
            },
            {
                'title': 'Expired poll example - Should pineapple go on pizza?',
                'description': 'This poll has expired - demonstrating expired poll handling',
                'expires_at': timezone.now() - timedelta(days=7),  # Expired 7 days ago
                'is_active': True,
                'options': [
                    {'text': 'Yes, absolutely!', 'order': 1},
                    {'text': 'No, never!', 'order': 2},
                    {'text': 'I don\'t care', 'order': 3},
                ]
            },
            {
                'title': 'Inactive poll example - Favorite color?',
                'description': 'This poll is inactive - demonstrating inactive poll handling',
                'is_active': False,
                'options': [
                    {'text': 'Red', 'order': 1},
                    {'text': 'Blue', 'order': 2},
                    {'text': 'Green', 'order': 3},
                ]
            },
        ]

        votes_per_poll = options['votes']
        total_polls = 0
        total_options = 0
        total_votes = 0

        for poll_data in sample_polls:
            # Extract options from poll data
            options_data = poll_data.pop('options')

            # Create poll
            poll = Poll.objects.create(**poll_data)
            total_polls += 1

            self.stdout.write(f'  ✓ Created poll: "{poll.title}"')

            # Create options for the poll
            poll_options = []
            for option_data in options_data:
                option = Option.objects.create(poll=poll, **option_data)
                poll_options.append(option)
                total_options += 1

            self.stdout.write(f'    → Added {len(poll_options)} options')

            # Create votes for active, non-expired polls
            if poll.is_active and not poll.is_expired:
                votes_created = self._create_votes(poll, poll_options, votes_per_poll)
                total_votes += votes_created
                self.stdout.write(f'    → Created {votes_created} votes')
            else:
                status = 'expired' if poll.is_expired else 'inactive'
                self.stdout.write(self.style.WARNING(f'    → Skipped votes ({status} poll)'))

        # Summary
        self.stdout.write(self.style.SUCCESS('\n' + '=' * 60))
        self.stdout.write(self.style.SUCCESS('Database seeding completed successfully!'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'📊 Total Polls Created:   {total_polls}')
        self.stdout.write(f'📝 Total Options Created: {total_options}')
        self.stdout.write(f'🗳️  Total Votes Created:   {total_votes}')
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.NOTICE('\nYou can now:'))
        self.stdout.write('  • Visit http://localhost:8000/api/polls/ to see all polls')
        self.stdout.write('  • Visit http://localhost:8000/api/docs/ for API documentation')
        self.stdout.write('  • Visit http://localhost:8000/admin/ to manage polls')
        self.stdout.write('')

    def _create_votes(self, poll, options, num_votes):
        """Create random votes for a poll."""
        votes_created = 0

        # Create weighted random distribution for more realistic results
        weights = self._generate_weights(len(options))

        for i in range(num_votes):
            # Select a random option based on weights
            option = random.choices(options, weights=weights)[0]

            # Generate unique voter identifier
            voter_identifier = f'seed_voter_{poll.id}_{i}'

            try:
                Vote.objects.create(
                    poll=poll,
                    option=option,
                    voter_identifier=voter_identifier
                )
                votes_created += 1
            except Exception as e:
                # Skip if duplicate (shouldn't happen with unique identifiers)
                pass

        return votes_created

    def _generate_weights(self, num_options):
        """
        Generate realistic weights for vote distribution.
        Creates a more natural distribution where some options are more popular.
        """
        # Generate random weights
        weights = [random.uniform(0.5, 2.0) for _ in range(num_options)]

        # Normalize weights
        total = sum(weights)
        weights = [w / total for w in weights]

        return weights
