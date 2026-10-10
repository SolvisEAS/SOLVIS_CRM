"""Autenticación JWT que además corta el acceso si el cliente está suspendido."""
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed


class TenantJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if user.tenant_id and not user.tenant.is_active:
            raise AuthenticationFailed("El acceso de esta empresa está suspendido.", code="inactive_tenant")
        return user
