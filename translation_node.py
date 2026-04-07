import re
import requests
from typing import Dict, Tuple

_CACHE: Dict[Tuple[str, str, str, str], str] = {}

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

def _translate(base_url: str, api_key: str, model: str, text: str, target: str) -> str:
    """
    target:
      - "zh-TW" (繁體中文/台灣)
      - "en"    (English)
    """
    if target == "zh-TW":
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

    if target == "en":
        system_msg = (
            "You are a STRICT translation engine.\n"
            "Your ONLY task is to translate the input into English.\n"
            "Rules:\n"
            "1) Preserve punctuation and line breaks.\n"
            "2) Keep placeholders like [[DNT_0]] unchanged.\n"
            "3) Return ONLY the translation. No explanations.\n"
        )
        user_msg = f"Translate the following into English:\n\n{text}"
        return _lmstudio_chat(base_url, api_key, model, system_msg, user_msg)

    if target == "zh-CN":
        system_msg = (
            "你是一個嚴格的翻譯引擎。\n"
            "你的唯一任務是把輸入內容翻譯成「簡體中文」。\n"
            "規則：\n"
            "1) 保留原本的標點與換行。\n"
            "2) 任何像 [[DNT_0]] 的佔位符必須完全保留。\n"
            "3) 不要解釋，不要補充，只輸出翻譯結果。\n"
        )
        user_msg = f"請翻譯成簡體中文：\n\n{text}"
        return _lmstudio_chat(base_url, api_key, model, system_msg, user_msg)

    raise ValueError(f"Unknown target: {target}")

class JetterTranslatePositiveWhole:
    """
    Positive 整段翻譯
    模式：
      1) EN/ZH-CN → ZH-TW
      2) ZH → EN
      3) ZH-TW → ZH-CN
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "positive": ("STRING", {"multiline": True, "default": ""}),
                "mode": (["EN/ZH-CN → ZH-TW", "ZH → EN", "ZH-TW → ZH-CN"],),
                "lmstudio_base": ("STRING", {"default": "http://127.0.0.1:1234/v1"}),
                "api_key": ("STRING", {"default": "lmstudio"}),
                "model": ("STRING", {"default": "qwen/qwen3-vl-8b"}),
                "do_not_translate": ("STRING", {
                    "default": "masterpiece,best quality,high quality,8k,4k,ultra-detailed,photorealistic,raw photo,cinematic lighting,depth of field,bokeh,sharp focus,soft light,(masterpiece),(best quality),Jetter"
                }),
                # 只對「轉繁中」模式有效
                "skip_if_traditional": (["Yes", "No"],),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("positive_out",)
    FUNCTION = "run"
    CATEGORY = "Text/Translation"

    def run(self, positive, mode, lmstudio_base, api_key, model, do_not_translate, skip_if_traditional):
        text = (positive or "").strip()
        if not text:
            return ("",)

        # 決定目標語言
        if mode == "EN/ZH-CN → ZH-TW":
            target = "zh-TW"
            # 已是繁中就略過（可選）
            if skip_if_traditional == "Yes" and _looks_like_traditional_zh(text):
                return (text,)
        elif mode == "ZH → EN":
            target = "en"
        elif mode == "ZH-TW → ZH-CN":
            target = "zh-CN"
            # 這個模式不需要 skip_if_traditional（保留參數但不使用）

        protected, mapping = _protect_tokens(text, do_not_translate)
        cache_key = (protected, target, model, lmstudio_base)

        if cache_key in _CACHE:
            return (_restore_tokens(_CACHE[cache_key], mapping),)

        translated = _translate(lmstudio_base, api_key, model, protected, target=target)

        # 保險重試：
        # - 目標是 zh-TW：若仍有大量英文，重翻一次更硬
        # - 目標是 EN：若仍大量中文（以簡單條件判斷：沒有英文字母但原文有中文），也重翻一次
        if target == "zh-TW" and _has_ascii_letter(translated):
            translated = _translate(
                lmstudio_base, api_key, model,
                "務必翻成繁體中文（台灣用語），不可保留英文：\n\n" + protected,
                target="zh-TW"
            )

        if target == "en":
            # 若翻完還幾乎沒有英文，視為可能沒翻成功（簡易判斷）
            if not _has_ascii_letter(translated):
                translated = _translate(
                    lmstudio_base, api_key, model,
                    "You MUST translate into English. Do not keep Chinese.\n\n" + protected,
                    target="en"
                )

        _CACHE[cache_key] = translated
        return (_restore_tokens(translated, mapping),)

NODE_CLASS_MAPPINGS = {
    "JetterTranslatePositiveWhole": JetterTranslatePositiveWhole
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "JetterTranslatePositiveWhole": "Positive 整段翻譯 (LM Studio, 可切換方向)"
}
