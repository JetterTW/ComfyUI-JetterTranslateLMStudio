# ComfyUI -- Positive Prompt 翻譯→繁體中文（LM Studio）

這是一個 **ComfyUI 自訂節點（Custom Node）**，\
使用 **LM Studio（OpenAI-compatible API）**，將 **Positive Prompt**\
從 **英文 / 簡體中文** 翻譯成 **繁體中文（台灣用語）**。

本節點設計理念是「簡單、可預期、不耍花樣」： - 不做片段級切割 - 不處理
negative prompt - 整段直接交給模型翻譯

------------------------------------------------------------------------

## ✨ 功能特色

-   ✅ **只處理 Positive Prompt**
-   🔁 **英文 → 繁體中文（台灣）**
-   🔁 **簡體中文 → 繁體中文（台灣）**
-   ⛔ 可選擇 **已是繁中則略過翻譯**（避免詞彙漂移）
-   🏷️ 支援 `do_not_translate`，保留指定 tag / 專有名詞
-   ⚡ 內建簡單快取，避免重複翻譯
-   🔌 使用 **LM Studio 本機模型（OpenAI-compatible API）**

------------------------------------------------------------------------

## 📦 需求環境

-   ComfyUI
-   LM Studio
    -   啟用 **Local Server**
    -   啟用 **OpenAI compatible API**
-   Python 套件
    -   `requests`

------------------------------------------------------------------------

## 🚀 安裝方式（git clone）

### 1️⃣ Clone 到 ComfyUI 的 custom_nodes 目錄

``` bash
cd ComfyUI/custom_nodes
git clone https://github.com/JetterTW/ComfyUI-JetterTranslateLMStudio.git
```

------------------------------------------------------------------------

### 2️⃣ 安裝相依套件

請使用 **ComfyUI 實際執行用的 Python 環境**：

``` bash
pip install -r requirements.txt
```

（Windows 使用者請特別注意是否需要用 `.venv\Scripts\python.exe -m pip`）

------------------------------------------------------------------------

### 3️⃣ 重啟 ComfyUI

完成後重啟 ComfyUI。

------------------------------------------------------------------------

## ⚙️ LM Studio 設定

在 LM Studio 中：

1.  開啟 **Local Server**
2.  勾選 **Enable OpenAI-compatible API**
3.  預設 Base URL 為：

```{=html}
<!-- -->
```
    http://127.0.0.1:1234/v1

4.  請確認你已載入欲使用的模型，例如：

```{=html}
<!-- -->
```
    yasco/gpt-oss-20b

------------------------------------------------------------------------

## 🧩 節點位置

    Text → Translation → Positive 整段翻譯→繁中 (LM Studio)

------------------------------------------------------------------------

## 🧪 節點參數說明

  參數名稱              說明
  --------------------- ---------------------------------------
  positive              要翻譯的 Positive Prompt（整段）
  lmstudio_base         LM Studio API Base URL
  model                 LM Studio 中載入的模型名稱
  do_not_translate      不要翻譯的 tag / 專有名詞（逗號分隔）
  skip_if_traditional   已是繁中是否略過翻譯

------------------------------------------------------------------------

## 🧠 設計說明

-   本節點 **不做片段級翻譯**
-   不會解析或拆解 prompt 結構
-   適合用途：
    -   英文 prompt → 快速轉繁中理解
    -   簡中 prompt → 轉成台灣用語
    -   希望整段語感一致的翻譯情境

------------------------------------------------------------------------

## 📄 License

MIT License
