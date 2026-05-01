from django.db import transaction
from accounts.utils.jwt_blacklist import blacklist_user_refresh_tokens
from core.utils.tasks import delete_user_avatar_task, enqueue_task, send_email_task


USER_DELETED_MESSAGE = "Sorry to hear you are leaving us, wish you the best!"


def schedule_user_deleted_effects(user, email_to_notify, avatar_name):
    transaction.on_commit(lambda: blacklist_user_refresh_tokens(user))

    if avatar_name:
        transaction.on_commit(
            lambda: enqueue_task(delete_user_avatar_task, avatar_name)
        )

    transaction.on_commit(
        lambda: enqueue_task(
            send_email_task,
            email_to_notify,
            USER_DELETED_MESSAGE,
        )
    )
