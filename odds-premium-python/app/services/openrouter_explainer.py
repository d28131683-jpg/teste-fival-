from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class OpenRouterExplainer:
    def __init__(self) -> None:
        self.settings = get_settings()

    def build_explanation(self, payload: dict[str, Any], fallback_text: str) -> str:
        if not self.settings.openrouter_api_key:
            return fallback_text

        try:
            response = httpx.post(
                f'{self.settings.openrouter_base_url}/chat/completions',
                headers={
                    'Authorization': f'Bearer {self.settings.openrouter_api_key}',
                    'Content-Type': 'application/json',
                },
                json={
                    'model': self.settings.openrouter_model,
                    'messages': [
                        {
                            'role': 'system',
                            'content': (
                                'Você explica apostas esportivas de forma técnica, curta e responsável. '
                                'Use apenas os dados estruturados recebidos. Não invente dados.'
                            ),
                        },
                        {'role': 'user', 'content': str(payload)},
                    ],
                    'temperature': 0.2,
                    'max_tokens': 180,
                },
                timeout=20,
            )
            response.raise_for_status()
            content = response.json()['choices'][0]['message']['content'].strip()
            return content or fallback_text
        except Exception:
            logger.exception('Falha ao gerar explicação via OpenRouter. Usando fallback.')
            return fallback_text
