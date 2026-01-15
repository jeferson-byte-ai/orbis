"""
Fast Marian Translator for common language pairs.
Provides a lightweight alternative to NLLB for low-latency scenarios.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Dict, Optional, Tuple

import torch
from transformers import MarianMTModel, MarianTokenizer

logger = logging.getLogger(__name__)


class FastMarianService:
    """Caches small Marian MT models for frequent language pairs."""

    MODEL_MAP: Dict[Tuple[str, str], str] = {
        ("pt", "en"): "Helsinki-NLP/opus-mt-pt-en",
        ("en", "pt"): "Helsinki-NLP/opus-mt-en-pt",
        ("es", "en"): "Helsinki-NLP/opus-mt-es-en",
        ("en", "es"): "Helsinki-NLP/opus-mt-en-es",
        ("fr", "en"): "Helsinki-NLP/opus-mt-fr-en",
        ("en", "fr"): "Helsinki-NLP/opus-mt-en-fr",
        ("de", "en"): "Helsinki-NLP/opus-mt-de-en",
        ("en", "de"): "Helsinki-NLP/opus-mt-en-de",
    }

    def __init__(self) -> None:
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._models: Dict[Tuple[str, str], MarianMTModel] = {}
        self._tokenizers: Dict[Tuple[str, str], MarianTokenizer] = {}
        self._locks: Dict[Tuple[str, str], asyncio.Lock] = {}
        self._failed_pairs: set[Tuple[str, str]] = set()

    def can_translate(self, source_lang: str, target_lang: str) -> bool:
        pair = (source_lang, target_lang)
        return pair in self.MODEL_MAP and pair not in self._failed_pairs

    async def translate(self, text: str, source_lang: str, target_lang: str) -> Optional[str]:
        pair = (source_lang, target_lang)
        if not text.strip() or pair not in self.MODEL_MAP or pair in self._failed_pairs:
            return None

        if pair not in self._locks:
            self._locks[pair] = asyncio.Lock()

        async with self._locks[pair]:
            if pair not in self._models:
                try:
                    await asyncio.to_thread(self._load_model, pair)
                except Exception as load_err:  # noqa: BLE001
                    logger.warning(
                        "⚠️ Fast Marian unavailable for %s→%s: %s",
                        pair[0],
                        pair[1],
                        load_err,
                    )
                    self._failed_pairs.add(pair)
                    return None

        try:
            return await asyncio.to_thread(self._run_translation, pair, text)
        except Exception as translate_err:  # noqa: BLE001
            logger.error(
                "❌ Fast Marian translation error for %s→%s: %s",
                pair[0],
                pair[1],
                translate_err,
            )
            self._failed_pairs.add(pair)
            return None

    def _load_model(self, pair: Tuple[str, str]) -> None:
        model_name = self.MODEL_MAP[pair]
        logger.info("Loading fast Marian MT model %s for %s→%s", model_name, *pair)
        try:
            tokenizer = MarianTokenizer.from_pretrained(model_name)
            model = MarianMTModel.from_pretrained(model_name)
        except Exception as load_err:  # noqa: BLE001
            self._failed_pairs.add(pair)
            raise RuntimeError(load_err) from load_err

        if self.device == "cuda":
            model = model.to(self.device)
        model.eval()
        self._models[pair] = model
        self._tokenizers[pair] = tokenizer
        logger.info("✅ Fast Marian model ready for %s→%s", *pair)

    def _run_translation(self, pair: Tuple[str, str], text: str) -> str:
        model = self._models[pair]
        tokenizer = self._tokenizers[pair]
        batch = tokenizer(
            [text],
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512,
        )
        if self.device == "cuda":
            batch = {k: v.to(self.device) for k, v in batch.items()}

        with torch.no_grad():
            generated = model.generate(
                **batch,
                max_new_tokens=256,
                num_beams=1,
                do_sample=False,
                early_stopping=True,
            )

        translated = tokenizer.batch_decode(generated, skip_special_tokens=True)[0]
        logger.debug("Marian translated '%s' → '%s' (%s→%s)", text[:40], translated[:40], *pair)
        return translated


fast_marian_service = FastMarianService()
