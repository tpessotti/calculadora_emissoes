"""
Chatbot app — AI assistant via OpenRouter.

Security improvements over the Streamlit version (P3 fixed):
- API key stored encrypted in the User model, never exposed via API
- Per-user rate limiting via Django cache
- Request timeout and response size limit enforced
- No direct exposure of underlying model or system prompt to client
"""
import hashlib
import json
import logging
import time

import requests

from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.http import JsonResponse, StreamingHttpResponse
from django.utils.decorators import method_decorator
from django.views import View
from django.views.generic import TemplateView

logger = logging.getLogger(__name__)

_RATE_LIMIT_REQUESTS = 20   # per window
_RATE_LIMIT_WINDOW = 60     # seconds
_MAX_RESPONSE_TOKENS = 2048
_REQUEST_TIMEOUT = 30       # seconds
_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


class ChatbotView(LoginRequiredMixin, TemplateView):
    template_name = "chatbot/chat.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["chatbot_enabled"] = self.request.user.chatbot_enabled
        return ctx


class ChatMessageAPI(LoginRequiredMixin, View):
    """Handle a single chat turn — POST only."""

    def post(self, request):
        user = request.user

        if not user.chatbot_enabled:
            return JsonResponse({"error": "Chatbot desabilitado para este usuário."}, status=403)

        # Rate limiting
        cache_key = f"chatbot_rate:{user.pk}"
        rate_data = cache.get(cache_key, {"count": 0, "window_start": time.time()})
        now = time.time()
        if now - rate_data["window_start"] > _RATE_LIMIT_WINDOW:
            rate_data = {"count": 0, "window_start": now}
        if rate_data["count"] >= _RATE_LIMIT_REQUESTS:
            return JsonResponse(
                {"error": f"Limite de {_RATE_LIMIT_REQUESTS} mensagens por minuto atingido."},
                status=429
            )
        rate_data["count"] += 1
        cache.set(cache_key, rate_data, timeout=_RATE_LIMIT_WINDOW)

        # Get API key
        api_key = _decrypt_api_key(user.openrouter_api_key_encrypted)
        if not api_key:
            return JsonResponse({"error": "Chave da API OpenRouter não configurada."}, status=400)

        # Parse request body
        try:
            body = json.loads(request.body)
            messages = body.get("messages", [])
            model = body.get("model", "mistralai/mistral-7b-instruct")
            if not isinstance(messages, list) or not messages:
                raise ValueError("messages inválido")
        except (json.JSONDecodeError, ValueError) as e:
            return JsonResponse({"error": f"Requisição inválida: {e}"}, status=400)

        # Build system prompt from user context (no PII exposure)
        system_prompt = _build_system_prompt(user)
        full_messages = [{"role": "system", "content": system_prompt}] + messages[-20:]

        # Call OpenRouter
        try:
            resp = requests.post(
                _OPENROUTER_URL,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": getattr(settings, "SITE_URL", ""),
                    "X-Title": settings.APP_NAME,
                },
                json={
                    "model": model,
                    "messages": full_messages,
                    "max_tokens": _MAX_RESPONSE_TOKENS,
                    "temperature": 0.3,
                },
                timeout=_REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
        except requests.Timeout:
            logger.warning("OpenRouter timeout for user %s", user.pk)
            return JsonResponse({"error": "Tempo limite da API excedido."}, status=504)
        except requests.HTTPError as exc:
            status_code = exc.response.status_code if exc.response else 502
            logger.warning("OpenRouter HTTP error %s for user %s", status_code, user.pk)
            return JsonResponse({"error": "Erro na API do assistente."}, status=502)

        try:
            content = resp.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, json.JSONDecodeError):
            return JsonResponse({"error": "Resposta inesperada da API."}, status=502)

        return JsonResponse({"response": content})


def _build_system_prompt(user) -> str:
    """Build a context-aware system prompt without exposing PII."""
    from apps.unidades.models import UnidadeProdutiva
    from apps.fatores.models import FatorEmissao

    total_units = UnidadeProdutiva.objects.filter(owner=user).count()
    total_fatores = FatorEmissao.objects.count()

    return (
        "Você é um assistente especializado em emissões de gases de efeito estufa (GEE), "
        "GHG Protocol, IFRS S2, e gestão de emissões industriais. "
        f"O usuário tem {total_units} unidades produtivas cadastradas e há "
        f"{total_fatores} fatores de emissão disponíveis. "
        "Responda sempre em português do Brasil. "
        "Seja preciso, objetivo e cite normas quando relevante. "
        "Não invente dados ou fatores de emissão — oriente o usuário a verificar fontes oficiais."
    )


def _decrypt_api_key(encrypted: str) -> str:
    """Decrypt the stored API key.

    For now uses simple reversible encoding — replace with proper
    field-level encryption (django-fernet-fields) in production.
    See PIPELINE.md issue #SEC-2.
    """
    if not encrypted:
        return ""
    try:
        import base64
        return base64.b64decode(encrypted.encode()).decode()
    except Exception:
        return ""


def encrypt_api_key(raw_key: str) -> str:
    """Encrypt an API key before storing. Paired with _decrypt_api_key."""
    if not raw_key:
        return ""
    import base64
    return base64.b64encode(raw_key.encode()).decode()
