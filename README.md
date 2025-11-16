# Bot MD5 Tài Xỉu - Advanced

## Mô tả
Bot Telegram xử lý chuỗi/MD5 theo logic MD5 → Xúc Xắc → Tài/Xỉu.
Bao gồm hệ thống admin, rate-limit, logging SQLite, tạm ban spam.

## Yêu cầu
- Python 3.10+
- pip install -r requirements.txt

## Cài đặt nhanh
1. Sửa file `config.py`: đặt ADMINS = [your_user_id]
2. Thiết lập biến môi trường chứa token:
   export BOT_TOKEN="123456:ABC..."
3. Cài dependencies:
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
4. Chạy:
   python bot.py

## Lệnh
- Người dùng: gửi chuỗi để tính
- Admin: /stats, /ban, /unban, /setlimit, /whois

## Ghi chú
- DB: bot_data.sqlite3 được tạo trong thư mục chạy.
- Để deploy 24/7, dùng VPS/Heroku/Railway; webhook có thể thêm nếu cần.
