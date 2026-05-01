from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.db import transaction
from core.utils.tasks import enqueue_task, send_email_task

User = get_user_model()


@receiver(post_save, sender=User, dispatch_uid="user_created_signal")
def userCreatedHandler(sender, instance, created, **kwargs):
    if created:
        transaction.on_commit(
            lambda: enqueue_task(
                send_email_task,
                instance.email,
                "Welcome to our site!",
            )
        )
