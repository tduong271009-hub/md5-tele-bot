import os
import time
import logging
import asyncio
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
from Crypto.Hash import MD5
import random

from config import ADMINS, BOT_TOKEN_ENV, DEFAULT_DAILY_LIMIT, COOLDOWN_SECONDS, SPAM_WINDOW_SECONDS, SPAM_THRESHOLD, TEMP_BAN_SECONDS, DB_FILE
from db import DB

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

db = DB(DB_FILE)

# In-memory rate-limits / recent messages for spam detection
_last_message_ts = {}      # user_id -> last_ts (float)
_recent_msgs = {}          # user_id -> list of timestamps for spam window

def is_admin(user_id):
    return user_id in ADMINS

def md5_tai_xiu(text):
    h = MD5.new()
    h.update(text.encode())
    md5 = h.hexdigest()

    last12 = md5[-12:]
    num = int(last12, 16)

    dice1 = (num % 6) + 1
    dice2 = ((num // 6) % 6) + 1
    dice3 = ((num // 36) % 6) + 1
    total = dice1 + dice2 + dice3

    if total >= 10:
        total += 2 if random.random() < 0.7 else 0
    else:
        total -= 2 if random.random() < 0.7 else 0

    total = max(3, min(total, 18))
    result = "TÀI 🎯" if total >= 11 else "XỈU 🎯"
    percent_tai = round((total - 3) / 15 * 100, 2)
    percent_xiu = round(100 - percent_tai, 2)
    return md5, dice1, dice2, dice3, total, result, percent_tai, percent_xiu

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await db.ensure_user(user.id, user.username or "", user.first_name or "", user.last_name or "")
    await update.message.reply_text("Chào! Gửi chuỗi hay MD5 để bot tính Tài/Xỉu. /help để biết thêm.")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - bắt đầu\n"
        "/help - trợ giúp\n"
        "/stats - (admin) xem thống kê\n"
        "/ban <user_id> - (admin) cấm user\n"
        "/unban <user_id> - (admin) gỡ cấm\n"
        "/setlimit <user_id> <daily_limit> - (admin) đặt limit\n"
        "/whois <user_id> - (admin) thông tin user\n"
    )

async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("Bạn không phải admin.")
        return
    total_users = await db.total_users()
    req_today = await db.requests_today()
    top = await db.top_users(10)
    top_lines = "\n".join([f"{r[0]} ({r[1]}) — {r[2]} reqs" for r in top])
    await update.message.reply_text(f"Tổng users: {total_users}\nRequests hôm nay: {req_today}\n\nTop hôm nay:\n{top_lines}")

async def ban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("Bạn không phải admin.")
        return
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("Dùng: /ban <user_id>")
        return
    try:
        target = int(args[0])
        ts = int(time.time()) + TEMP_BAN_SECONDS
        await db.ensure_user(target)
        await db.set_banned_until(target, ts)
        await update.message.reply_text(f"Đã tạm cấm {target} tới {datetime.utcfromtimestamp(ts)} UTC")
    except:
        await update.message.reply_text("user_id không hợp lệ")

async def unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("Bạn không phải admin.")
        return
    args = context.args
    if len(args) < 1:
        await update.message.reply_text("Dùng: /unban <user_id>")
        return
    try:
        target = int(args[0])
        await db.ensure_user(target)
        await db.set_banned_until(target, 0)
        await update.message.reply_text(f"Đã gỡ cấm {target}")
    except:
        await update.message.reply_text("user_id không hợp lệ")

async def setlimit_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("Bạn không phải admin.")
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Dùng: /setlimit <user_id> <daily_limit>")
        return
    try:
        target = int(args[0]); newlimit = int(args[1])
        await db.ensure_user(target)
        await db.set_daily_limit(target, newlimit)
        await update.message.reply_text(f"Đã đặt limit {newlimit} cho {target}")
    except:
        await update.message.reply_text("Tham số không hợp lệ")

async def whois_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not is_admin(user.id):
        await update.message.reply_text("Bạn không phải admin.")
        return
    if not context.args:
        await update.message.reply_text("Dùng: /whois <user_id>")
        return
    try:
        uid = int(context.args[0])
        row = await db.get_user(uid)
        if not row:
            await update.message.reply_text("Không tìm thấy user.")
            return
        user_id, username, first, last, daily_limit, banned_until = row
        await update.message.reply_text(
            f"user_id: {user_id}\nusername: {username}\nname: {first} {last}\nlimit: {daily_limit or DEFAULT_DAILY_LIMIT}\nbanned_until: {banned_until}"
        )
    except:
        await update.message.reply_text("ID không hợp lệ")

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user = update.effective_user
    user_id = user.id
    text = msg.text.strip()

    await db.ensure_user(user_id, user.username or "", user.first_name or "", user.last_name or "")

    u = await db.get_user(user_id)
    banned_until = u[5] if u else 0
    now_ts = int(time.time())
    if banned_until and now_ts < banned_until:
        await msg.reply_text(f"Bạn đang bị cấm tạm thời tới {datetime.utcfromtimestamp(banned_until)} UTC")
        return

    last_ts = _last_message_ts.get(user_id, 0)
    if time.time() - last_ts < COOLDOWN_SECONDS:
        await msg.reply_text(f"Bạn đang gửi quá nhanh. Vui lòng đợi {COOLDOWN_SECONDS} giây giữa 2 yêu cầu.")
        return
    _last_message_ts[user_id] = time.time()

    lst = _recent_msgs.get(user_id, [])
    now = time.time()
    lst = [t for t in lst if now - t <= SPAM_WINDOW_SECONDS]
    lst.append(now)
    _recent_msgs[user_id] = lst
    if len(lst) > SPAM_THRESHOLD:
        ban_ts = int(time.time()) + TEMP_BAN_SECONDS
        await db.set_banned_until(user_id, ban_ts)
        await msg.reply_text("Phát hiện hành vi spam. Bạn đã bị tạm cấm 1 giờ.")
        return

    used_today = await db.get_usage_today(user_id)
    user_daily_limit = u[4] if (u and u[4]) else DEFAULT_DAILY_LIMIT
    if used_today >= user_daily_limit:
        await msg.reply_text(f"Bạn đã dùng hết {user_daily_limit} lượt hôm nay. Hãy thử lại ngày mai hoặc liên hệ admin.")
        return

    md5, d1, d2, d3, total, result, tai, xiu = md5_tai_xiu(text)
    reply = (
        f"🔐 MD5: `{md5}`\n"
        f"🎲 {d1} | {d2} | {d3}\n"
        f"📌 Tổng: *{total}*\n"
        f"🎯 Kết quả: *{result}*\n"
        f"💹 Tài: *{tai}%* — Xỉu: *{xiu}%*\n"
        f"📅 Lượt hôm nay: {used_today + 1}/{user_daily_limit}"
    )
    await db.log_request(user_id, user.username or "", text, md5, result)
    await msg.reply_text(reply, parse_mode="Markdown")

async def main():
    token = os.getenv(BOT_TOKEN_ENV)
    if not token:
        print("Bạn chưa set biến môi trường BOT_TOKEN. Xem README.")
        return

    await db.init()
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("ban", ban_cmd))
    app.add_handler(CommandHandler("unban", unban_cmd))
    app.add_handler(CommandHandler("setlimit", setlimit_cmd))
    app.add_handler(CommandHandler("whois", whois_cmd))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    print("🚀 Bot đã khởi động")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    await asyncio.Event().wait()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Stopped")
