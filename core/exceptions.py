"""
Manejo centralizado de excepciones para la API.

Uniforma el formato de error de todas las respuestas de la API en:

    {
        "detail": "mensaje legible",
        "code": "codigo_interno_opcional"
    }

Se registra en REST_FRAMEWORK["EXCEPTION_HANDLER"] cuando haga falta
(a partir de la Fase 2, cuando aparezcan errores de negocio propios).
"""
from rest_framework.views import exception_handler as drf_exception_handler


class BusinessRuleError(Exception):
    """Excepción base para errores de reglas de negocio del CRM.

    Ejemplo futuro: intentar convertir un Lead que ya fue convertido.
    """

    def __init__(self, message: str, code: str | None = None):
        self.message = message
        self.code = code or "business_rule_error"
        super().__init__(message)


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)

    if isinstance(exc, BusinessRuleError):
        from rest_framework.response import Response
        from rest_framework import status

        return Response(
            {"detail": exc.message, "code": exc.code},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return response
