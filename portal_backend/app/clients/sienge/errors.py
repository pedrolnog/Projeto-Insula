class SiengeError(Exception):
    """Falha genérica ao chamar a API do Sienge."""

    def __init__(self, mensagem: str, status_code: int | None = None):
        super().__init__(mensagem)
        self.status_code = status_code


class SiengeNotFound(SiengeError):
    """Recurso não existe (ex.: diário apagado no Sienge)."""


class SiengeQuotaExceeded(SiengeError):
    """HTTP 429 persistente: a cota acabou. A sincronização deve parar imediatamente."""
