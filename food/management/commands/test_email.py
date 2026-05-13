from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = 'Send a test email using the configured Django email backend.'

    def add_arguments(self, parser):
        parser.add_argument('recipient', help='Email address that should receive the test message.')

    def handle(self, *args, **options):
        recipient = options['recipient']
        self.stdout.write(f'Backend: {settings.EMAIL_BACKEND}')
        self.stdout.write(f'Host: {settings.EMAIL_HOST or "not configured"}')
        self.stdout.write(f'From: {settings.DEFAULT_FROM_EMAIL}')

        message = EmailMultiAlternatives(
            'Tonmoy Eats email test',
            'This is a test email from your Tonmoy Eats Django project.',
            settings.DEFAULT_FROM_EMAIL,
            [recipient],
        )
        try:
            sent = message.send(fail_silently=False)
        except Exception as exc:
            raise CommandError(f'Email failed: {exc}') from exc

        if settings.EMAIL_BACKEND == 'django.core.mail.backends.console.EmailBackend':
            self.stdout.write(
                self.style.WARNING(
                    'Console email backend is active. Django printed the email above, but it did not go to a real inbox.'
                )
            )
            return

        if sent:
            self.stdout.write(self.style.SUCCESS(f'Test email sent to {recipient}.'))
        else:
            raise CommandError('Django did not send the email. Check EMAIL_* settings.')
