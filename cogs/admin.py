import discord
from discord.ext import commands

class Admin(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # Lệnh: Đổi prefix (!setprefix [kí_tự])
    @commands.command(name="setprefix", help="Đổi prefix gọi lệnh của bot cho server này.")
    @commands.has_permissions(administrator=True) # Bắt buộc phải là Admin server mới được xài
    async def setprefix(self, ctx, prefix: str):
        # Chặn mấy pha đổi prefix dài ngoằng
        if len(prefix) > 3:
            await ctx.send("❌ Prefix dài quá! Chọn cái nào từ 1-3 ký tự thôi cho dễ gõ.")
            return

        # Cú pháp UPSERT của SQLite: 
        # Cố gắng chèn dữ liệu mới, nếu server (guild_id) đã tồn tại thì chuyển sang Cập nhật (UPDATE)
        query = """
            INSERT INTO guild_config (guild_id, prefix) 
            VALUES (?, ?) 
            ON CONFLICT(guild_id) DO UPDATE SET prefix = ?
        """
        # Truyền 3 tham số: guild_id, prefix (cho INSERT), prefix (cho UPDATE)
        await self.bot.db.execute(query, (ctx.guild.id, prefix, prefix))
        
        # Tạo Embed thông báo cho ngầu
        embed = discord.Embed(
            title="⚙️ Cập nhật hệ thống",
            description=f"✅ Đã đổi prefix thành công!\nTừ giờ hãy dùng `{prefix}tên_lệnh` nhé.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)

# Khai báo để main.py có thể load được file này
async def setup(bot):
    await bot.add_cog(Admin(bot))