import discord
from discord.ext import commands
import os
from utils.db_manager import DatabaseManager
from config import TOKEN

# Khởi tạo instance quản lý Database
db = DatabaseManager()

# Hàm lấy prefix động từ database
async def get_prefix(bot, message):
    if not message.guild:
        return "!"
    return await bot.db.get_prefix(message.guild.id)

# Kế thừa class commands.Bot để quản lý lifecycle tốt hơn
class MyBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True  # Bắt buộc để đọc tin nhắn user
        super().__init__(command_prefix=get_prefix, intents=intents)
        
        # Gán db vào bot để gọi ở mọi nơi (VD: self.bot.db)
        self.db = db

    async def setup_hook(self):
        """Hàm này tự động chạy 1 lần trước khi bot login"""
        print("[-] Đang khởi tạo Database...")
        await self.db.initialize()
        
        print("[-] Đang tải các Cogs...")
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py') and not filename.startswith('__'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f"  [+] Đã tải module: {filename}")
                except Exception as e:
                    print(f"  [x] Lỗi khi tải {filename}: {e}")

    async def on_ready(self):
        print(f'=================================')
        print(f'[+] Bot {self.user} ĐÃ ONLINE!')
        print(f'[+] ID: {self.user.id}')
        print(f'=================================')

# Khởi tạo và chạy bot
if __name__ == "__main__":
    # Đảm bảo thư mục cogs tồn tại
    os.makedirs("./cogs", exist_ok=True)
    
    bot = MyBot()
    bot.run(TOKEN) # Hàm run() đã tự động bao bọc asyncio event loop