"""Simple local AI implementation using DistilGPT-2 (CPU-friendly).

Replaces external Gemini API with a lightweight local model suitable
for low-resource servers (2 CPU / 2GB RAM). Public interface remains the same
to avoid changes in other modules:
- class GeminiAI with .initialize() and .get_response(prompt)
- function get_ai_response(user_input: str, use_gemini: bool = True)
"""
import logging
from typing import Optional

from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline

logger = logging.getLogger(__name__)

class GeminiAI:
    """Local CPU-friendly text generator wrapper (DistilGPT-2).

    Keeps the same name for backward compatibility with existing imports.
    """

    def __init__(self, model_name: str = "distilgpt2", max_new_tokens: int = 120):
        self.model_name = model_name
        self.max_new_tokens = max_new_tokens
        self._pipe = None  # lazy-initialized text-generation pipeline

    def initialize(self) -> None:
        """Lazy-load the text-generation pipeline.

        Safe for repeated calls. Uses CPU-only inference.
        """
        if self._pipe is not None:
            return
        try:
            tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            model = AutoModelForCausalLM.from_pretrained(self.model_name)
            self._pipe = pipeline(
                "text-generation",
                model=model,
                tokenizer=tokenizer,
                device=-1,  # CPU
            )
            logger.info("DistilGPT-2 pipeline initialized on CPU")
        except Exception as e:
            logger.error(f"Ошибка инициализации локальной модели: {e}")
            self._pipe = None

    def get_response(self, prompt: str) -> Optional[str]:
        """Generate response using local model.

        Returns None if model is unavailable.
        """
        if self._pipe is None:
            # try to initialize on first use
            self.initialize()
        if self._pipe is None:
            return None

        try:
            # Keep generation short and safe for Telegram
            outputs = self._pipe(
                prompt,
                max_new_tokens=self.max_new_tokens,
                do_sample=True,
                top_k=50,
                top_p=0.95,
                temperature=0.7,
                num_return_sequences=1,
                pad_token_id=self._pipe.tokenizer.eos_token_id,
            )
            text = outputs[0]["generated_text"]
            # Return only the continuation after the prompt if present
            if text.startswith(prompt):
                text = text[len(prompt):].lstrip()
            # Trim to 200 chars for Telegram UX
            if len(text) > 200:
                text = text[:200] + "..."
            return text.strip() or None
        except Exception as e:
            logger.error(f"Ошибка генерации локальной модели: {e}")
            return None

def get_ai_response(user_input: str, use_gemini: bool = True) -> str:
    """Сгенерировать ответ локально (DistilGPT-2).

    Параметр use_gemini сохранен для обратной совместимости и игнорируется.
    """
    try:
        logger.info("Используем локальную DistilGPT-2 для ответа")

        gemini = GeminiAI()
        gemini.initialize()

        prompt = (
            "Вы — помощник сервиса поиска мастеров. Ответьте кратко и по делу.\n"
            f"Вопрос: {user_input}\n"
            "Ответ:"
        )

        generated_text = gemini.get_response(prompt)
        if not generated_text:
            return (
                "Извините, я не могу дать точный ответ на этот вопрос. "
                "Попробуйте задать более конкретный вопрос."
            )

        return generated_text
    except Exception as e:
        logger.error(f"Ошибка генерации ответа: {e}")
        return "Извините, в настоящее время у меня технические трудности. Попробуйте позже."
