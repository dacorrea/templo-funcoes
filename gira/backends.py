# gira/backends.py
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model

User = get_user_model()

class CelularBackend(BaseBackend):
    def authenticate(self, request, celular=None, **kwargs):
        try:
            return User.objects.get(celular=celular)
        except User.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
