"""Hybrid AI implementation with Gemini 2.0 (cloud) and HF fallback (CPU-friendly).

Public interface remains the same to avoid changes in other modules:
- class GeminiAI with .initialize() and .get_response(prompt)
- function get_ai_response(user_input: str, use_gemini: bool = True)

Behavior:
- If GOOGLE_API_KEY or API_GEMINI_FREE is set, uses Gemini (default: ``gemini-2.0-flash``)
- Otherwise falls back to local HF text2text model (default: ``cointegrated/rut5-base-multitask``)
- Answers are short by design: limit via AI_MAX_NEW_TOKENS (default 60)
"""
import logging
from typing import Optional

import os
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline

# Optional import: google-generativeai
try:  # pragma: no cover
    import google.generativeai as genai  # type: ignore
except Exception:  # pragma: no cover
    genai = None  # type: ignore

logger = logging.getLogger(__name__)

class GeminiAI:
    """Cloud-first (Gemini) text generator with local HF fallback.

    Keeps the old class name for backward compatibility.
    """

    def __init__(self, model_name: str | None = None, max_new_tokens: int | None = None):
        # Env-configurable
        self.gemini_api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("API_GEMINI_FREE")
        self.model_name = (
            model_name
            or os.getenv("GEMINI_MODEL_NAME")
            or os.getenv("AI_MODEL_NAME", "gemini-2.0-flash")
        )
        # Short answers by default
        self.max_new_tokens = int(os.getenv("AI_MAX_NEW_TOKENS", str(max_new_tokens or 60)))

        # Lazy-initialized clients
        self._gemini_model = None
        self._pipe = None  # HF text2text-generation pipeline

    def _init_gemini(self) -> bool:
        """Initialize Gemini client if api key is available."""
        if self._gemini_model is not None:
            return True
        if not self.gemini_api_key or genai is None:
            return False
        try:
            genai.configure(api_key=self.gemini_api_key)
            self._gemini_model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=(
                    "Ты ассистент GoodRobot. Отвечай кратко (1–2 предложения), по делу и без воды. "
                    "Всегда используй русский язык."
                ),
            )
            logger.info("Gemini initialized: %s", self.model_name)
            return True
        except Exception as e:  # pragma: no cover
            logger.error("Не удалось инициализировать Gemini: %s", e)
            self._gemini_model = None
            return False

    def _init_hf(self) -> bool:
        """Initialize local HF fallback."""
        if self._pipe is not None:
            return True
        # По умолчанию используем русскоязычную инструкционную модель
        local_model_name = os.getenv("AI_MODEL_NAME", "cointegrated/rut5-base-multitask")
        try:
            tokenizer = AutoTokenizer.from_pretrained(local_model_name)
            model = AutoModelForSeq2SeqLM.from_pretrained(local_model_name)
            self._pipe = pipeline(
                "text2text-generation",
                model=model,
                tokenizer=tokenizer,
                device=-1,  # CPU
            )
            logger.info("HF pipeline initialized on CPU: %s", local_model_name)
            return True
        except Exception as e:  # pragma: no cover
            logger.error(f"Ошибка инициализации локальной модели: {e}")
            self._pipe = None
            return False

    def initialize(self) -> None:
        """Try Gemini first, then local HF as fallback."""
        if self._init_gemini():
            return
        self._init_hf()

    def get_response(self, prompt: str) -> Optional[str]:
        """Generate response using Gemini (preferred) or local fallback.

        Returns None if both backends are unavailable.
        """
        # Ensure initialized
        self.initialize()

        # Try Gemini cloud
        if self._gemini_model is not None:
            try:
                resp = self._gemini_model.generate_content(
                    prompt,
                    generation_config={
                        "max_output_tokens": self.max_new_tokens,
                        "temperature": 0.2,
                        "top_p": 0.9,
                    },
                )
                text = getattr(resp, "text", None) or ""
                text = _sanitize_text(text)
                if len(text) > 200:
                    text = text[:200] + "..."
                return text.strip() or None
            except Exception as e:  # pragma: no cover
                logger.error(f"Ошибка генерации Gemini: {e}")
                # fall through to HF

        # Try local HF fallback
        if self._pipe is not None:
            try:
                outputs = self._pipe(
                    prompt,
                    max_new_tokens=self.max_new_tokens,
                    do_sample=False,  # deterministic
                    num_beams=1,
                    early_stopping=True,
                )
                text = outputs[0]["generated_text"]
                text = _sanitize_text(text)
                if len(text) > 200:
                    text = text[:200] + "..."
                return text.strip() or None
            except Exception as e:
                logger.error(f"Ошибка генерации локальной модели: {e}")

        return None

def _sanitize_text(text: str) -> str:
    """Clean up LLM output: remove excessive repeats and artifacts."""
    import re
    s = text.strip()
    # Remove leading markers like "Ответ:" or "Assistant:"
    s = re.sub(r"^(Ответ|Assistant|Bot)\s*:\s*", "", s, flags=re.IGNORECASE)

    # Collapse 3+ repeated punctuation
    s = re.sub(r"([!?.,])\1{2,}", r"\1\1", s)
    # Remove long runs of the same short word
    s = re.sub(r"\b(\w{1,3})\b(\s+\1\b){2,}", r"\1", s, flags=re.IGNORECASE)

    # Sentence-level de-duplication for short sentences like "Что?"
    parts = re.split(r"(\s*[!?\.]+\s*)", s)  # keep delimiters
    rebuilt: list[str] = []
    last_short_norm: str | None = None

    def norm_sent(x: str) -> str:
        return re.sub(r"\s+", " ", x.strip().lower())

    i = 0
    while i < len(parts):
        sent = parts[i]
        delim = parts[i + 1] if i + 1 < len(parts) else ""
        full = (sent + (delim or "")).strip()
        if full:
            sent_norm = norm_sent(full)
            # consider short if <= 12 chars or <= 2 words
            is_short = len(sent_norm) <= 12 or len(sent_norm.split()) <= 2
            if is_short and last_short_norm == sent_norm:
                # skip consecutive duplicate
                pass
            else:
                rebuilt.append(full)
            last_short_norm = sent_norm if is_short else None
        i += 2

    s = " ".join(rebuilt).strip()
    return s


def get_ai_response(user_input: str, use_gemini: bool = True) -> str:
    """Сгенерировать ответ с приоритетом Gemini 2.0 и фоллбеком на локальную HF-модель.

    Параметр use_gemini сохранен для обратной совместимости и игнорируется.
    """
    try:
        logger.info("Пробуем Gemini 2.0 (короткие ответы), фоллбек на локальную модель")

        gemini = GeminiAI()
        gemini.initialize()

        # If input is too short or non-informative, ask a clarifying question
        short = len(user_input.strip()) < 5
        if short or user_input.strip().lower() in {"что", "что?", "??", "помощь", "help"}:
            return (
                "Чем могу помочь? Кратко опишите задачу: что нужно сделать, где и когда. "
                "Например: ‘Сантехник для замены смесителя, Алматы, сегодня вечером’."
            )

        prompt = (
            "Инструкция: Ты — ассистент русскоязычного сервиса GoodRobot по поиску мастеров. "
            "Отвечай кратко (1–2 предложения), по делу и без лишней воды. Если вопрос общий, кратко объясни: "
            "как создать заявку, как выбрать мастера, как проходит оплата. Избегай повторов и бессмысленных фраз.\n\n"
            f"Вопрос: {user_input}\n"
            "Краткий ответ:"
        )

        generated_text = gemini.get_response(prompt)
        if not generated_text:
            return (
                "Извините, я не могу дать точный ответ на этот вопрос. "
                "Попробуйте задать более конкретный вопрос."
            )

        cleaned = _sanitize_text(generated_text)
        # If still low-signal after cleaning, provide structured fallback
        if len(cleaned) < 5:
            return (
                "Не совсем понимаю запрос. Уточните, пожалуйста: категорию работ, адрес и удобное время. "
                "Например: ‘Электрик, замена розетки, завтра 10:00’."
            )
        return cleaned
    except Exception as e:
        logger.error(f"Ошибка генерации ответа: {e}")
        return "Извините, в настоящее время у меня технические трудности. Попробуйте позже."
