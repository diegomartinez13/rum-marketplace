"""
Management command to delete all conversations and messages.
Usage: python manage.py clear_all_chats
       python manage.py clear_all_chats --confirm (to skip confirmation)
"""
from django.core.management.base import BaseCommand
from store_app.models import Conversation, Message


class Command(BaseCommand):
    help = 'Delete all conversations and messages from the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Skip confirmation prompt',
        )

    def handle(self, *args, **options):
        # Count existing data
        conversation_count = Conversation.objects.count()
        message_count = Message.objects.count()
        
        if conversation_count == 0 and message_count == 0:
            self.stdout.write(
                self.style.SUCCESS('No conversations or messages found. Nothing to delete.')
            )
            return
        
        # Show what will be deleted
        self.stdout.write(
            self.style.WARNING(
                f'\nThis will delete:\n'
                f'  - {conversation_count} conversation(s)\n'
                f'  - {message_count} message(s)\n'
            )
        )
        
        # Ask for confirmation unless --confirm flag is used
        if not options['confirm']:
            confirm = input('Are you sure you want to delete all conversations and messages? (yes/no): ')
            if confirm.lower() not in ['yes', 'y']:
                self.stdout.write(self.style.ERROR('Operation cancelled.'))
                return
        
        # Delete messages first (due to foreign key constraint)
        deleted_messages = Message.objects.all().delete()
        self.stdout.write(
            self.style.SUCCESS(f'Successfully deleted {deleted_messages[0]} message(s)')
        )
        
        # Delete conversations
        deleted_conversations = Conversation.objects.all().delete()
        self.stdout.write(
            self.style.SUCCESS(f'Successfully deleted {deleted_conversations[0]} conversation(s)')
        )
        
        self.stdout.write(
            self.style.SUCCESS('\n✓ All chats have been cleared successfully!')
        )

