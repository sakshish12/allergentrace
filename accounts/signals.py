from django.contrib import messages
from django.contrib.auth.signals import user_logged_out
from django.dispatch import receiver
from django.utils.translation import gettext as _


@receiver(user_logged_out)
def confirm_logout(sender, request, user, **kwargs):
    # Logouts without a browser request (e.g. the test client) have no message storage.
    messages.info(request, _("You are logged out."), fail_silently=True)
