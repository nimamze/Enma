from django.core.mail import send_mail
from django.core.files.storage import FileSystemStorage
from celery import shared_task
from celery.exceptions import OperationalError as BrokerConnectionError
from django.conf import settings
from django.core.management import call_command
from django.apps import apps
from datetime import timedelta
from django.utils import timezone
from django.db.models import Q
from core.utils.sms import send_sms


def enqueue_task(task, *args, **kwargs):
    try:
        task.delay(*args, **kwargs)
    except BrokerConnectionError:
        if not settings.DEBUG:
            raise
        task.apply(args=args, kwargs=kwargs)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_sms_task(self, phone, message):
    try:
        send_sms(phone, f"Enma Site:\n{message}")
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_task(self, email_address, message):
    try:
        send_mail(
            "Enma Site",
            message,
            settings.EMAIL_HOST_USER,
            [email_address],
        )
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task
def cleanup_expired_jwt_tokens():
    call_command("flushexpiredtokens")


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def send_email_for_not_login_users(self):
    try:
        user_model = apps.get_model(settings.AUTH_USER_MODEL)
        one_month_ago = timezone.now() - timedelta(days=30)
        inactive_users = user_model.objects.filter(
            Q(last_login__lt=one_month_ago) | Q(last_login__isnull=True)
        )
        for user in inactive_users:
            send_mail(
                subject="Enma Site",
                message="Check the site — you haven't logged in for one month!",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[user.email],
                fail_silently=False,
            )
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def delete_user_avatar_task(self, file_name):
    if not file_name:
        return

    try:
        if settings.SAVE_FILES_LOCALLY:
            storage = FileSystemStorage(location=settings.MEDIA_ROOT)
        else:
            from .storage_backends import UsersMediaStorage

            storage = UsersMediaStorage()
        storage.delete(file_name)
    except Exception as exc:
        raise self.retry(exc=exc)
