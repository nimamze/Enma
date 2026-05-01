from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.db import transaction
from core.utils.tasks import delete_user_avatar_task, enqueue_task

User = get_user_model()


@receiver(pre_save, sender=User)
def delete_old_avatar_on_update(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        old = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        return
    old_image = old.image
    new_image = instance.image
    if old_image and old_image != new_image:
        old_file = old_image.name
        transaction.on_commit(
            lambda: enqueue_task(delete_user_avatar_task, old_file)  # type: ignore
        )
