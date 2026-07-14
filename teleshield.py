#!/usr/bin/env python3
"""
Telegram 個人帳號廣告封鎖工具
───────────────────────────
用法：
  1. 前往 https://my.telegram.org/apps 取得 API_ID 和 API_HASH
  2. 執行 python3 tg-spam-blocker.py --setup
     輸入 API_ID、API_HASH、手機號碼 → 輸入驗證碼 → 登入完成
  3. 之後執行 python3 tg-spam-blocker.py --scan
     掃描最近訊息，自動封鎖發廣告的非聯絡人

可選：排程每小時自動掃描（Hermes cron）
"""

import asyncio, os, json, re, sys, time, tempfile
from pathlib import Path
from datetime import datetime, timedelta, timezone
from telethon import events

# ──────────── 設定 ────────────
SESSION_DIR = Path("/root/.tg-sessions")
SESSION_FILE = SESSION_DIR / "user.session"
CONFIG_FILE = SESSION_DIR / "config.json"
SPAM_PATTERNS = [
    # 中文廣告常見模式
    r"加[\s\-]*[LlvVXx]|[LlvVXx][\s\-]*信",
    r"tg[\s\-]*@?[a-zA-Z0-9_]{3,}",
    r"https?://t\.me/",
    r"@\w{4,}",
    r"兼職|刷單|日入|月入|躺賺|被動收入|在家工作|輕鬆賺",
    r"投資|理財|帶單|跟單|量化|穩賺|穩健|高回報|高收益",
    r"色情|A片|av|成人|裸聊|約炮|援交|包養",
    r"賭|博|彩|casino|betting",
    r"註冊送|免費領|紅包|禮金|優惠碼|推廣碼",
    r"點贊|關注|刷粉|刷讚|漲粉",
    r"售|賣|出|供應|批發|代購|代發",
    # English patterns
    r"promote|promotion|advertisement|sponsor",
    r"click\s*(here|this\s*link|the\s*link)",
    r"earn\s*money|work\s*from\s*home|passive\s*income",
    r"free\s*crypto|free\s*bitcoin|airdrop|giveaway",
    r"limited\s*offer|discount\s*\d{2,}%|buy\s*now",
]

# ──────────── 工具函式 ────────────

def load_config():
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text())
    return {}

def save_config(cfg):
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2))

def is_spam(text: str) -> bool:
    """檢查文字是否包含廣告模式"""
    if not text:
        return False
    for pattern in SPAM_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


# ──────────── 圖片 OCR ────────────

def ocr_image(image_path: str) -> str:
    """用本地 Tesseract OCR 辨識圖片中的文字"""
    try:
        from PIL import Image
        import pytesseract
        img = Image.open(image_path)
        # 用中文+英文語言包
        text = pytesseract.image_to_string(img, lang="chi_sim+eng")
        return text.strip()
    except Exception as e:
        print(f"    ⚠️ OCR 失敗: {e}")
        return ""


async def check_photo(client, msg) -> str:
    """下載圖片並 OCR，回傳辨識出的文字，無圖片時回傳空字串"""
    if not msg or not msg.photo:
        return ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            tmp = f.name
        await client.download_media(msg, file=tmp)
        text = ocr_image(tmp)
        os.unlink(tmp)
        return text
    except Exception as e:
        return ""

# ──────────── 首次設定 ────────────

async def setup(api_id: str = None, api_hash: str = None, phone: str = None, code: str = None):
    """首次設定：登入並儲存 session"""
    from telethon import TelegramClient

    print("\n═══════════════════════════════")
    print("  Telegram 廣告封鎖工具 - 設定")
    print("═══════════════════════════════\n")

    # 從參數或互動輸入取得 API 憑證
    if not api_id:
        api_id = input("API ID (從 my.telegram.org/apps 取得): ").strip()
    else:
        print(f"API ID: {api_id}")
    if not api_hash:
        api_hash = input("API Hash: ").strip()
    else:
        print(f"API Hash: {api_hash}")
    if not phone:
        phone = input("手機號碼 (含國碼，如 +85264305931): ").strip()
    else:
        print(f"手機: {phone[:5]}****{phone[-4:] if len(phone)>8 else ''}")

    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    client = TelegramClient(str(SESSION_FILE), int(api_id), api_hash)

    try:
        await client.start(phone=phone, code_callback=lambda: code or input("請輸入驗證碼: "))
        me = await client.get_me()
        print(f"\n✅ 登入成功！")
        print(f"   帳號: {me.first_name} (@{me.username or '無'})")
        print(f"   ID: {me.id}")

        # 儲存設定
        save_config({
            "api_id": int(api_id),
            "api_hash": api_hash,
            "phone": phone,
            "user_id": me.id,
            "username": me.username,
            "blocked_count": 0,
            "last_scan": None,
        })
        print("\n✅ 設定已儲存")
        await client.disconnect()
        return True
    except Exception as e:
        print(f"\n❌ 登入失敗: {e}")
        return False

# ──────────── 掃描並封鎖 ────────────

async def scan_and_block(dry_run: bool = False):
    """掃描近期對話，封鎖發廣告的非聯絡人"""
    from telethon import TelegramClient
    from telethon.tl.functions.contacts import BlockRequest
    from telethon.tl.types import User, Message, InputPhoneContact

    cfg = load_config()
    if not cfg.get("api_id"):
        print("❌ 尚未設定，請先執行 --setup")
        return

    print(f"{'🧪 試運行模式（不實際封鎖）' if dry_run else '🔍 掃描模式'}")
    print(f"{'─'*50}")

    client = TelegramClient(str(SESSION_FILE), cfg["api_id"], cfg["api_hash"])
    try:
        await client.start(phone=cfg["phone"])

        # 取得聯絡人列表（白名單）
        from telethon.tl.functions.contacts import GetContactsRequest
        contacts = (await client(GetContactsRequest(hash=0))).users
        contact_ids = {c.id for c in contacts}
        print(f"📇 聯絡人: {len(contact_ids)} 位")

        now = datetime.now(timezone.utc)
        scan_interval = timedelta(hours=cfg.get("scan_interval", 6))
        cutoff = now - scan_interval

        blocked = 0
        skipped = 0

        # 取得最近的對話
        dialogs = await client.get_dialogs(limit=30)

        for dialog in dialogs:
            entity = dialog.entity
            
            # 只處理用戶（非群組/頻道）
            if not isinstance(entity, User):
                continue
            if entity.is_self:
                continue
            if entity.id in contact_ids:
                continue
            if entity.bot:
                continue

            # 檢查最近訊息
            try:
                msgs = await client.get_messages(entity, limit=5)
            except:
                continue

            spam_found = False
            spam_text = ""
            for msg in msgs:
                if not msg:
                    continue
                if msg.date and msg.date < now - timedelta(days=14):
                    continue  # 太舊的跳過
                # 檢查文字
                msg_text = msg.text or ""
                if is_spam(msg_text):
                    spam_found = True
                    spam_text = msg_text[:120]
                    break
                # 檢查圖片 OCR
                if msg.photo:
                    ocr_text = await check_photo(client, msg)
                    if ocr_text and is_spam(ocr_text):
                        spam_found = True
                        spam_text = f"[圖片OCR] {ocr_text[:100]}"
                        break

            if not spam_found:
                continue

            # 顯示該用戶
            name = f"{entity.first_name or ''} {entity.last_name or ''}".strip()
            uname = f"@{entity.username}" if entity.username else ""
            print(f"\n  ⚠️  疑似廣告: {name} {uname}")
            print(f"     訊息: {spam_text}{'...' if len(spam_text)>=120 else ''}")

            if dry_run:
                skipped += 1
                continue

            # 實際封鎖
            try:
                await client(BlockRequest(id=entity.id))
                blocked += 1
                print(f"      ✅ 已封鎖")
            except Exception as e:
                print(f"      ❌ 封鎖失敗: {e}")

        print(f"\n{'─'*50}")
        print(f"結果:")
        print(f"  📋 掃描對話數: {len([d for d in dialogs if isinstance(d.entity, User)])}")
        print(f"  🚫 {'已封鎖' if not dry_run else '發現(試運行)'}: {blocked if not dry_run else skipped}")
        if dry_run:
            print(f"  ℹ️  執行 --block 來實際封鎖")

        # 更新計數
        if not dry_run and blocked > 0:
            cfg["blocked_count"] = cfg.get("blocked_count", 0) + blocked
        cfg["last_scan"] = now.isoformat()
        save_config(cfg)

        await client.disconnect()

    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        await client.disconnect()

# ──────────── 即時監聽 ────────────

async def listen():
    """即時監聽新訊息，自動封鎖廣告發送者"""
    from telethon import TelegramClient
    from telethon.tl.functions.contacts import BlockRequest
    from telethon.tl.types import User, Message
    from telethon.tl.functions.contacts import GetContactsRequest

    cfg = load_config()
    if not cfg.get("api_id"):
        print("❌ 尚未設定，請先執行 --setup")
        return

    print("👂 即時監聽模式啟動中...")
    print("    有新訊息進來時自動檢測並封鎖廣告")
    print("    按 Ctrl+C 停止\n")

    client = TelegramClient(str(SESSION_FILE), cfg["api_id"], cfg["api_hash"])

    @client.on(events.NewMessage(incoming=True))
    async def handler(event):
        msg = event.message
        if not msg:
            return
        sender = await event.get_sender()
        if not isinstance(sender, User) or sender.is_self or sender.bot:
            return

        # 檢查是否為聯絡人
        try:
            contacts = (await client(GetContactsRequest(hash=0))).users
            contact_ids = {c.id for c in contacts}
            if sender.id in contact_ids:
                return
        except:
            pass

        # 檢查文字是否為廣告
        spam_text = msg.text or ""
        is_spam_by_text = is_spam(spam_text)

        # 如果有圖片，也進行 OCR 檢查
        ocr_found_spam = False
        if not is_spam_by_text and msg.photo:
            ocr_text = await check_photo(client, msg)
            if ocr_text and is_spam(ocr_text):
                ocr_found_spam = True
                spam_text = ocr_text[:100]

        if not is_spam_by_text and not ocr_found_spam:
            return

        name = f"{sender.first_name or ''} {sender.last_name or ''}".strip()
        uname = f"@{sender.username}" if sender.username else ""
        now_str = datetime.now(timezone.utc).strftime("%H:%M:%S")
        source = "📸" if ocr_found_spam else ""
        print(f"\n[{now_str}] {source}⚠️  廣告: {name} {uname}")
        print(f"    訊息: {spam_text[:100]}")

        try:
            await client(BlockRequest(id=sender.id))
            cfg["blocked_count"] = cfg.get("blocked_count", 0) + 1
            save_config(cfg)
            print(f"     ✅ 已封鎖（累計 {cfg['blocked_count']} 人）")
        except Exception as e:
            print(f"     ❌ 封鎖失敗: {e}")

    try:
        await client.start(phone=cfg["phone"])
        print(f"✅ 已上線 — 監聽中...")
        await client.run_until_disconnected()
    except KeyboardInterrupt:
        print("\n\n👋 監聽已停止")
        await client.disconnect()
    except Exception as e:
        print(f"\n❌ 錯誤: {e}")
        await client.disconnect()

# ──────────── 主程式 ────────────

async def main():
    if len(sys.argv) < 2:
        print("用法:")
        print("  python3 tg-spam-blocker.py --setup    首次設定")
        print("  python3 tg-spam-blocker.py --scan     掃描並封鎖")
        print("  python3 tg-spam-blocker.py --dry-run  試掃描（不實際封鎖）")
        print("  python3 tg-spam-blocker.py --listen   即時監聽（後台常駐）")
        print("  python3 tg-spam-blocker.py --status   查看狀態")
        return

    cmd = sys.argv[1]

    if cmd == "--setup":
        api_id = sys.argv[2] if len(sys.argv) > 2 else None
        api_hash = sys.argv[3] if len(sys.argv) > 3 else None
        phone = sys.argv[4] if len(sys.argv) > 4 else None
        code = sys.argv[5] if len(sys.argv) > 5 else None
        await setup(api_id, api_hash, phone, code)
    elif cmd == "--scan":
        await scan_and_block(dry_run=False)
    elif cmd == "--dry-run":
        await scan_and_block(dry_run=True)
    elif cmd == "--status":
        cfg = load_config()
        if cfg:
            print("📊 當前狀態:")
            print(f"  帳號: {cfg.get('username','?')} (ID: {cfg.get('user_id','?')})")
            print(f"  累計封鎖: {cfg.get('blocked_count',0)} 人")
            print(f"  最後掃描: {cfg.get('last_scan','從未')}")
        else:
            print("❌ 尚未設定")
    elif cmd == "--listen":
        await listen()
    else:
        print(f"未知指令: {cmd}")

if __name__ == "__main__":
    asyncio.run(main())
