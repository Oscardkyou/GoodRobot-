"""Simple local AI implementation using FLAN-T5 (instruction-tuned, CPU-friendly).

Public interface remains the same to avoid changes in other modules:
- class GeminiAI with .initialize() and .get_response(prompt)
- function get_ai_response(user_input: str, use_gemini: bool = True)
"""
import logging
from typing import Optional

import os
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline

logger = logging.getLogger(__name__)

class GeminiAI:
    """Local CPU-friendly text generator wrapper based on FLAN-T5.

    Keeps the old class name for backward compatibility.
    """

    def __init__(self, model_name: str | None = None, max_new_tokens: int | None = None):
        # Allow configuring via env
        # По умолчанию используем русскоязычную инструкционную модель
        self.model_name = model_name or os.getenv("AI_MODEL_NAME", "cointegrated/rut5-base-multitask")
        # flan-t5-small is ~80MB weights; flan-t5-base ~250MB; choose per server resources
        self.max_new_tokens = int(os.getenv("AI_MAX_NEW_TOKENS", str(max_new_tokens or 120)))
        self._pipe = None  # lazy-initialized text2text-generation pipeline

    def initialize(self) -> None:
        """Lazy-load the text-generation pipeline.

        Safe for repeated calls. Uses CPU-only inference.
        """
        if self._pipe is not None:
            return
        try:
            tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
            self._pipe = pipeline(
                "text2text-generation",
                model=model,
                tokenizer=tokenizer,
                device=-1,  # CPU
            )
            logger.info("FLAN-T5 pipeline initialized on CPU: %s", self.model_name)
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
                do_sample=False,  # deterministic
                num_beams=1,
                early_stopping=True,
            )
            text = outputs[0]["generated_text"]
            # For text2text-generation, HF returns "generated_text" directly without the prompt
            text = _sanitize_text(text)
            # Trim to 200 chars for Telegram UX
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
    """Сгенерировать ответ локально (DistilGPT-2).

    Параметр use_gemini сохранен для обратной совместимости и игнорируется.
    """
    try:
        logger.info("Используем локальную DistilGPT-2 для ответа")

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
            "Отвечай кратко (1–3 предложения), по делу и без лишней воды. Если вопрос общий, кратко объясни: "
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
