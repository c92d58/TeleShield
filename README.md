<div align="center">
  <h1>🛡️ TeleShield</h1>
  <p><strong>Telegram 個人帳號廣告封鎖守衛</strong><br>
  <em>Your personal Telegram spam firewall — real-time, self-hosted, zero compromise.</em></p>

  <p>
    <img src="https://img.shields.io/badge/python-3.9%2B-blue" alt="Python">
    <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
    <img src="https://img.shields.io/badge/telethon-1.44%2B-purple" alt="Telethon">
  </p>
</div>

---

## 📋 概述 / Overview

**TeleShield** 是一個基於 Telethon 的 Telegram 個人帳號廣告封鎖工具。不同於 Bot API，它直接以你的身份登入，能夠處理 **個人私訊** 的廣告攔截——這是 Bot 做不到的。

*TeleShield is a Telegram personal-account spam blocker powered by Telethon. Unlike Bot API bots, it logs in as you and blocks spam in **private DMs** — something bots simply cannot do.*

---

## ✨ 功能 / Features

| 功能 | 說明 |
|------|------|
| 🔍 **掃描封鎖** `--scan` | 掃描近期非聯絡人對話，自動比對廣告模式並封鎖 |
| 🛡️ **即時監聽** `--listen` | 後台常駐，新訊息即時檢測，秒封廣告 |
| 🧪 **試運行** `--dry-run` | 安全預覽，只顯示結果不實際封鎖 |
| 📊 **狀態查詢** `--status` | 查看累計封鎖數、最後掃描時間 |
| 📸 **圖片 OCR** `內建` | 純圖片廣告也能辨識，Tesseract 本地 OCR，資料不外傳 |
| 🧠 **智能識別** | 20+ 中英文廣告正則模式，覆蓋投資、色情、賭博、推廣等 |
| 📇 **白名單保護** | 你的聯絡人不會被掃描或封鎖 |

---

## 🚀 快速開始 / Quick Start

### 前置需求 / Prerequisites

- Python 3.9+
- Telegram API 憑證（[my.telegram.org/apps](https://my.telegram.org/apps)）

### 安裝 / Install

```bash
# 克隆倉庫
git clone https://github.com/c92d58/TeleShield.git
cd TeleShield

# 安裝依賴
pip install telethon

# 圖片 OCR 支援（選用）
apt install tesseract-ocr tesseract-ocr-chi-sim
pip install pytesseract Pillow
```

### 首次設定 / First-time Setup

```bash
python teleshield.py --setup
```

依序輸入：
1. `API ID` — 從 [my.telegram.org/apps](https://my.telegram.org/apps) 取得
2. `API Hash` — 同上
3. `手機號碼` — 含國碼，如 `+85264305931`
4. `驗證碼` — Telegram 會發送驗證碼到你手機

登入成功後會自動儲存 Session，下次不需重複登入。

### 基本用法 / Usage

```bash
# 先試運行看看結果
python teleshield.py --dry-run

# 實際掃描並封鎖
python teleshield.py --scan

# 啟動即時監聽（後台常駐）
python teleshield.py --listen

# 查看狀態
python teleshield.py --status
```

---

## 📖 命令參考 / Commands

| 命令 | 說明 |
|------|------|
| `--setup <api_id> <api_hash> <phone> [code]` | 首次設定 / 重新登入 |
| `--scan` | 掃描近期對話並封鎖廣告 |
| `--dry-run` | 試掃描（不實際封鎖） |
| `--listen` | 即時監聽模式，後台常駐 |
| `--status` | 查看當前狀態和統計 |

---

## 🔍 廣告識別模式 / Spam Patterns

TeleShield 內建 20+ 正則表達式，覆蓋以下類別：

| 類別 | 範例關鍵字 |
|------|-----------|
| 💰 投資理財 | 投資、帶單、跟單、量化、穩賺 |
| 💼 兼職詐騙 | 兼職、刷單、日入、躺賺、被動收入 |
| 🔞 色情 | 裸聊、約炮、援交、成人 |
| 🎰 賭博 | 賭、博彩、casino、betting |
| 📣 群組推廣 | @xxx、t.me/xxx、加微信 |
| 🎁 假優惠 | 免費領、紅包、優惠碼、推廣碼 |
| 📢 **英文 Spam** | promotion, giveaway, earn money, free crypto |
| 📸 **圖片 OCR** | 純圖片廣告→Tesseract 本地辨識文字→模式比對 |

> 可自行在 `teleshield.py` 中的 `SPAM_PATTERNS` 列表中添加自定義模式。

---

## ⚠️ 安全注意事項 / Security Notes

- **Session 文件** (`user.session`) 相當於你的 Telegram 登入憑證，請妥善保管
- 建議設定檔案權限：`chmod 600 user.session config.json`
- 不要將 Session 文件提交到 Git（已在 `.gitignore` 中排除）
- API 憑證（`api_id` / `api_hash`）不要公開洩露

---

## 🗂️ 專案結構 / Project Structure

```
TeleShield/
├── teleshield.py       # 主程式
├── README.md           # 本文件
├── LICENSE             # MIT 授權
└── .gitignore
```

運行後會自動生成：
```
.tg-sessions/
├── user.session        # Telegram 登入 Session（已加密）
└── config.json         # 設定檔案
```

---

## 🧩 後續計劃 / Roadmap

- [ ] 群組管理：自動踢除發廣告的群組成員
- [ ] 學習模式：手動標記後自動歸納特徵
- [ ] 封鎖日報：每日 / 每週封鎖摘要報告
- [ ] 白名單 / 黑名單管理指令
- [x] 圖片廣告辨識：Tesseract 本地 OCR

---

## 📄 License

[MIT](LICENSE) © 2026 WAHSUN

---

<div align="center">
  <sub>Made with ❤️ by WAHSUN · 讓 Telegram 清淨一點</sub>
</div>
