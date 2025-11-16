# Cấu hình chính
# Thay ADMINS bằng user_id Telegram của bạn (số nguyên).
ADMINS = [123456789]  # <-- thay bằng Telegram user_id của bạn (có thể nhiều người)
BOT_TOKEN_ENV = "BOT_TOKEN"  # tên biến môi trường chứa token

# Hạn mức / spam
DEFAULT_DAILY_LIMIT = 200
COOLDOWN_SECONDS = 3  # thời gian tối thiểu giữa 2 request xử lý cho 1 user
SPAM_WINDOW_SECONDS = 10  # cửa sổ để tính spam
SPAM_THRESHOLD = 10       # nếu gửi > SPAM_THRESHOLD tin trong SPAM_WINDOW_SECONDS thì tạm ban
TEMP_BAN_SECONDS = 3600   # tạm ban 1h khi phát hiện spam

# DB file
DB_FILE = "bot_data.sqlite3"
