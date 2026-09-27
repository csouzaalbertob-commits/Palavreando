# autentica/backends.py
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User

class EmailOrUsernameModelBackend(ModelBackend):
    """
    Permite autenticação utilizando tanto o nome de usuário (username)
    quanto o e-mail cadastrado.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get('email')

        try:
            # Verifica se o valor inserido corresponde a um e-mail ou a um username
            if '@' in username:
                user = User.objects.get(email__iexact=username.strip())
            else:
                user = User.objects.get(username__iexact=username.strip())
        except User.DoesNotExist:
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None