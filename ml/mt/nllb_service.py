"""
NLLB Machine Translation Service
Translates text between 200+ languages
"""
import asyncio
import logging
from typing import Dict, Optional
import torch

logger = logging.getLogger(__name__)


class NLLBService:
    """NLLB translation service for real-time text translation"""
    
    # Language code mapping (ISO 639-1 to NLLB codes)
    LANG_CODES = {
        'en': 'eng_Latn',
        'zh': 'zho_Hans',
        'hi': 'hin_Deva',
        'es': 'spa_Latn',
        'ar': 'arb_Arab',
        'bn': 'ben_Beng',
        'pt': 'por_Latn',
        'ru': 'rus_Cyrl',
        'ja': 'jpn_Jpan',
        'pa': 'pan_Guru',
        'de': 'deu_Latn',
        'jv': 'jav_Latn',
        'ko': 'kor_Hang',
        'fr': 'fra_Latn',
        'te': 'tel_Telu',
        'mr': 'mar_Deva',
        'tr': 'tur_Latn',
        'ta': 'tam_Taml',
        'vi': 'vie_Latn',
        'ur': 'urd_Arab',
        'it': 'ita_Latn',
        'th': 'tha_Thai',
        'gu': 'guj_Gujr',
        'pl': 'pol_Latn',
        'uk': 'ukr_Cyrl',
        'ml': 'mal_Mlym',
        'kn': 'kan_Knda',
        'or': 'ori_Orya',
        'fa': 'pes_Arab',
        'my': 'mya_Mymr',
        'nl': 'nld_Latn',
        'ro': 'ron_Latn',
        'cs': 'ces_Latn',
        'sv': 'swe_Latn',
        'el': 'ell_Grek',
        'hu': 'hun_Latn',
        'he': 'heb_Hebr',
        'fi': 'fin_Latn',
        'da': 'dan_Latn',
        'no': 'nob_Latn',
        'id': 'ind_Latn',
        'ms': 'msa_Latn',
        'fil': 'tgl_Latn',
        'sw': 'swa_Latn',
        'bg': 'bul_Cyrl',
        'sk': 'slk_Latn',
        'hr': 'hrv_Latn',
        'sr': 'srp_Cyrl',
        'lt': 'lit_Latn',
        'sl': 'slv_Latn'
    }
    
    def __init__(self, model_name: str = "facebook/nllb-200-distilled-600M", device: str = "cuda"):
        """
        Initialize NLLB service
        
        Args:
            model_name: NLLB model to use
            device: Device to run on (cuda or cpu)
        """
        self.model_name = model_name
        self.device = device if torch.cuda.is_available() else "cpu"
        self.model = None
        self.tokenizer = None
        logger.info(f"Initializing NLLB MT: {model_name} on {self.device}")
    
    def load(self):
        """Load translation model"""
        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
            
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.model = AutoModelForSeq2SeqLM.from_pretrained(self.model_name)
            
            if self.device == "cuda":
                self.model = self.model.to(self.device)
                self.model = self.model.half()  # Use FP16 for speed
            
            self.model.eval()
            logger.info("✅ NLLB model loaded successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to load NLLB model: {e}")
            raise
    
    async def translate(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str,
        max_length: int = 400
    ) -> str:
        """
        Translate text from source to target language
        
        Args:
            text: Text to translate
            source_lang: Source language code (ISO 639-1)
            target_lang: Target language code (ISO 639-1)
            max_length: Maximum output length
        
        Returns:
            Translated text
        """
        return await asyncio.to_thread(
            self._translate_blocking,
            text,
            source_lang,
            target_lang,
            max_length,
        )

    def _translate_blocking(
        self,
        text: str,
        source_lang: str,
        target_lang: str,
        max_length: int,
    ) -> str:
        try:
            if source_lang == target_lang:
                return text

            src_code = self.LANG_CODES.get(source_lang, 'eng_Latn')
            tgt_code = self.LANG_CODES.get(target_lang, 'eng_Latn')

            if self.model is None or self.tokenizer is None:
                logger.warning("Model not loaded, using mock translation")
                return f"[{target_lang.upper()}] {text}"

            self.tokenizer.src_lang = src_code
            inputs = self.tokenizer(
                text,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512
            )

            if self.device == "cuda":
                inputs = {k: v.to(self.device) for k, v in inputs.items()}

            forced_bos_token_id = None
            lang_code_map = getattr(self.tokenizer, "lang_code_to_id", None)
            if lang_code_map and tgt_code in lang_code_map:
                forced_bos_token_id = lang_code_map[tgt_code]
            else:
                try:
                    token_id = self.tokenizer.convert_tokens_to_ids(tgt_code)
                    if token_id != self.tokenizer.unk_token_id:
                        forced_bos_token_id = token_id
                except Exception:  # noqa: BLE001
                    forced_bos_token_id = None

            generate_kwargs = {
                "max_length": max_length,
                "num_beams": 1,
                "early_stopping": True,
            }
            if forced_bos_token_id is not None:
                generate_kwargs["forced_bos_token_id"] = forced_bos_token_id

            with torch.no_grad():
                translated_tokens = self.model.generate(
                    **inputs,
                    **generate_kwargs
                )

            translated_text = self.tokenizer.batch_decode(
                translated_tokens,
                skip_special_tokens=True
            )[0]

            logger.info(
                "Translated: '%s' → '%s' (%s→%s)",
                text,
                translated_text,
                source_lang,
                target_lang,
            )
            return translated_text

        except Exception as exc:  # noqa: BLE001
            logger.error("Translation error: %s", exc)
            return text
    
    def get_supported_languages(self) -> Dict[str, str]:
        """Get list of supported languages"""
        return {code: f"Language {code}" for code in self.LANG_CODES.keys()}


# Singleton instance
nllb_service = NLLBService()