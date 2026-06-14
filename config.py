import os
from dotenv import load_dotenv

# Tải các biến từ file .env vào hệ thống
load_dotenv()

# Lấy token và gán vào biến TOKEN (chữ in hoa)
TOKEN = os.getenv("DISCORD_TOKEN")
ENV = os.getenv("ENVIRONMENT", "local")  
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Check an toàn: Nếu không tìm thấy token thì báo lỗi ngay
if not TOKEN:
    raise ValueError("Chưa tìm thấy DISCORD_TOKEN trong file .env!")

if not GEMINI_API_KEY:
    raise ValueError("Chưa tìm thấy GEMINI_API_KEY! Hãy đăng ký tại Google AI Studio.")

if ENV == "local":
    print("🚀 Đang chạy ở chế độ LOCAL (Máy tính cá nhân)")
else:
    print("☁️ Đang chạy ở chế độ DEPLOY (Sẵn sàng 24/24)")