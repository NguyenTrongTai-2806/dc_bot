import discord
from discord.ext import commands

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Sự kiện: Lắng nghe khi cog được load xong
    @commands.Cog.listener()
    async def on_ready(self):
        print("    -> General Cog is ready!")

    # Lệnh: !ping
    @commands.command(name="ping", help="Kiểm tra độ trễ (latency) của bot.")
    async def ping(self, ctx):
        # self.bot.latency trả về giây, nhân 1000 để ra mili-giây
        latency = round(self.bot.latency * 1000)
        
        # Tạo một embed cho thông báo đẹp mắt hơn
        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"Độ trễ API: **{latency}ms**",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

# Hàm setup bắt buộc để main.py có thể load file này
async def setup(bot):
    await bot.add_cog(General(bot))