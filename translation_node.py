import re
import requests
from typing import Dict, Tuple

_CACHE: Dict[Tuple[str, str, str], str] = {}

def _has_ascii_letter(s: str) -> bool:
    return any('A' <= ch <= 'Z' or 'a' <= ch <= 'z' for ch in s)

def _looks_like_traditional_zh(s: str) -> bool:
    # 常見繁中特徵字（實務用，避免已是繁中又被重翻）
    trad_markers = "體臺裏裡覺學國說為這點嗎麼應與並經開關價"
    return any(ch in s for ch in trad_markers)

def _protect_tokens(text: str, do_not_translate: str):
    tokens = [t.strip() for t in (do_not_translate or "").split(",") if t.strip()]
    if not tokens:
        return text, {}

    tokens.sort(key=len, reverse=True)
    mapping = {}
    protected = text

    for i, tok in enumerate(tokens):
        placeholder = f"[[DNT_{i}]]"
        protected = re.sub(re.escape(tok), placeholder, protected)
        mapping[placeholder] = tok

    return protected, mapping

def _restore_tokens(text: str, mapping: Dict[str, str]):
    out = text
    for k, v in mapping.items():
        out = out.replace(k, v)
    return out

def _lmstudio_chat(base_url: str, api_key: str, model: str, system_msg: str, user_msg: str, timeout_sec: int = 120) -> str:
    url = base_url.rstrip("/") + "/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_msg},
        ],
    }
    r = requests.post(url, headers=headers, json=payload, timeout=timeout_sec)
    r.raise_for_status()
    data = r.json()
    return (data["choices"][0]["message"]["content"] or "").strip()

def _translate_to_zh_tw(base_url: str, api_key: str, model: str, text: str) -> str:
    system_msg = (
        "你是一個嚴格的翻譯引擎。\n"
        "你的唯一任務是把輸入內容翻譯成「繁體中文（台灣用語）」。\n"
        "規則：\n"
        "1) 保留原本的標點與換行。\n"
        "2) 任何像 [[DNT_0]] 的佔位符必須完全保留。\n"
        "3) 不要解釋，不要補充，只輸出翻譯結果。\n"
    )
    user_msg = f"請翻譯成繁體中文（台灣用語）：\n\n{text}"
    return _lmstudio_chat(base_url, api_key, model, system_msg, user_msg)

class JetterTranslatePositiveWholeToZHTW:
    """
    單一 positive 整段翻譯
    英文 / 簡中 → 繁中（台灣）
    不做片段級處理
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "positive": ("STRING", {"multiline": True, "default": ""}),
                "lmstudio_base": ("STRING", {"default": "http://127.0.0.1:1234/v1"}),
                "api_key": ("STRING", {"default": "lmstudio"}),
                "model": ("STRING", {"default": "qwen/qwen3-vl-8b"}),
                "do_not_translate": ("STRING", {
                    "default": "masterpiece,best quality,high quality,8k,4k,ultra-detailed,photorealistic,raw photo,cinematic lighting,depth of field,bokeh,sharp focus,soft light,(masterpiece),(best quality)"
                }),
                "skip_if_traditional": (["Yes", "No"],),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("positive_out",)
    FUNCTION = "run"
    CATEGORY = "Text/Translation"

    def run(self, positive, lmstudio_base, api_key, model, do_not_translate, skip_if_traditional):
        text = (positive or "").strip()
        if not text:
            return ("",)

        # 若已是繁中且選擇略過，直接回傳
        if skip_if_traditional == "Yes" and _looks_like_traditional_zh(text):
            return (text,)

        protected, mapping = _protect_tokens(text, do_not_translate)
        key = (protected, model, lmstudio_base)

        if key in _CACHE:
            return (_restore_tokens(_CACHE[key], mapping),)

        translated = _translate_to_zh_tw(lmstudio_base, api_key, model, protected)

        # 保險：若翻完仍有大量英文，強制再翻一次
        if _has_ascii_letter(translated):
            translated = _translate_to_zh_tw(
                lmstudio_base, api_key, model,
                "務必翻成繁體中文（台灣用語），不可保留英文：\n\n" + protected
            )

        _CACHE[key] = translated
        return (_restore_tokens(translated, mapping),)

NODE_CLASS_MAPPINGS = {
    "JetterTranslatePositiveWholeToZHTW": JetterTranslatePositiveWholeToZHTW
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "JetterTranslatePositiveWholeToZHTW": "Positive 整段翻譯→繁中 (LM Studio)"
}
