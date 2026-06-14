import discord
from discord.ext import commands
import time

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_user_data(self, user_id: int):
        """Lấy toàn bộ dòng dữ liệu của user"""
        query = "SELECT wallet, last_daily FROM users_money WHERE user_id = ?"
        result = await self.bot.db.fetch_one(query, (user_id,))
        if result:
            return result # Trả về tuple (wallet, last_daily)
        else:
            await self.bot.db.execute("INSERT INTO users_money (user_id, wallet, last_daily) VALUES (?, 0, 0)", (user_id,))
            return (0, 0)

    # Hàm helper này dùng cho cả các cog khác gọi ké
    async def get_balance(self, user_id: int):
        data = await self.get_user_data(user_id)
        return data[0]

    @commands.command(name="bal", help="Kiểm tra ví tiền của bạn.")
    async def balance(self, ctx):
        wallet = await self.get_balance(ctx.author.id)
        embed = discord.Embed(
            title="💰 Tài khoản ngân hàng",
            description=f"**{ctx.author.name}**, bạn đang có: **{wallet}** đồng.",
            color=discord.Color.gold()
        )
        await ctx.send(embed=embed)

    @commands.command(name="daily", help="Nhận tiền công điểm danh mỗi ngày.")
    async def daily(self, ctx):
        wallet, last_daily = await self.get_user_data(ctx.author.id)
        
        current_time = int(time.time()) # Lấy thời gian hiện tại kiểu số nguyên (Unix timestamp)
        cooldown_time = 86400 # 24 tiếng tính bằng giây
        
        # Kiểm tra xem thời gian trôi qua đã đủ 24h chưa
        if current_time - last_daily < cooldown_time:
            time_left = cooldown_time - (current_time - last_daily)
            hours, remainder = divmod(time_left, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            await ctx.send(f"⏳ Bạn đã nhận quà hôm nay rồi! Thử lại sau **{hours} giờ {minutes} phút** nữa nhé.")
            return

        reward = 500
        # Cập nhật cả tiền VÀ thời gian nhận mới vào DB
        await self.bot.db.execute(
            "UPDATE users_money SET wallet = ?, last_daily = ? WHERE user_id = ?", 
            (wallet + reward, current_time, ctx.author.id)
        )
        
        await ctx.send(f"💸 Bạn vừa nhận được **{reward}** đồng! Dữ liệu đã được lưu an toàn vào DB.")

async def setup(bot):
    await bot.add_cog(Economy(bot))