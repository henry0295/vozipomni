"""JWT authentication middleware for Django Channels WebSockets."""

from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.middleware import BaseMiddleware
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import AccessToken


class JwtAuthMiddleware(BaseMiddleware):
    async def __call__(self, scope, receive, send):
        scope['user'] = await self._get_user(scope)
        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def _get_user(self, scope):
        token = parse_qs(scope.get('query_string', b'').decode()).get('token', [None])[0]
        if not token:
            from django.contrib.auth.models import AnonymousUser
            return AnonymousUser()
        try:
            access_token = AccessToken(token)
            return get_user_model().objects.get(
                id=access_token['user_id'], is_active=True
            )
        except (TokenError, KeyError, get_user_model().DoesNotExist, ValueError):
            from django.contrib.auth.models import AnonymousUser
            return AnonymousUser()


def JwtAuthMiddlewareStack(inner):
    return JwtAuthMiddleware(inner)