import discord
from discord.ext import commands

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # 1. Lệnh Xóa Tin Nhắn Hàng Loạt (!clear [số lượng])
    @commands.command(name="clear", help="Xóa hàng loạt tin nhắn trong kênh.")
    @commands.has_permissions(manage_messages=True) # Chỉ ai có quyền quản lý tin nhắn mới dùng được
    async def clear(self, ctx, amount: int):
        if amount <= 0:
            await ctx.send("❌ Số lượng tin nhắn cần xóa phải lớn hơn 0")
            return
            
        # Xóa tin nhắn lệnh của người dùng gõ + số lượng tin nhắn yêu cầu
        deleted = await ctx.channel.purge(limit=amount + 1)
        
        # Gửi thông báo tạm thời rồi tự xóa sau 5 giây cho sạch kênh
        msg = await ctx.send(f"🧹 Đã dọn dẹp xong **{len(deleted) - 1}** tin nhắn.")
        await msg.delete(delay=5)

    # 2. Lệnh Cảnh Cáo (!warn @user [lý do])
    @commands.command(name="warn", help="Cảnh cáo một thành viên vi phạm.")
    @commands.has_permissions(kick_members=True) # Người có quyền sút member mới được warn
    async def warn(self, ctx, member: discord.Member, *, reason: str):
        # Không cho phép tự warn chính mình hoặc warn bot
        if member.id == ctx.author.id:
            await ctx.send("❌ Bạn không thể tự cảnh cáo chính mình!")
            return
        if member.bot:
            await ctx.send("❌ Bạn không thể cảnh cáo bot.")
            return

        # Lưu thông tin vi phạm vào Database thông qua db_manager đã viết
        await self.bot.db.add_warning(
            guild_id=ctx.guild.id,
            user_id=member.id,
            reason=reason,
            moderator_id=ctx.author.id
        )

        embed = discord.Embed(
            title="⚠️ Thành viên bị cảnh cáo",
            description=f"**Người vi phạm:** {member.mention}\n**Lý do:** {reason}\n**Người phạt:** {ctx.author.mention}",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)

        # Cố gắng gửi tin nhắn riêng nhắc nhở cho người vi phạm biết
        try:
            await member.send(f"⚠️ Bạn đã bị cảnh cáo tại server **{ctx.guild.name}** vì lý do: {reason}")
        except discord.Forbidden:
            pass

    # 3. Lệnh Xem Lịch Sử Vi Phạm (!warnings @user)
    @commands.command(name="warnings", help="Xem lịch sử các lần bị cảnh cáo của một thành viên.")
    @commands.has_permissions(kick_members=True)
    async def warnings(self, ctx, member: discord.Member):
        # Viết câu lệnh truy vấn trực tiếp bằng hàm fetch_all của db_manager
        query = """
            SELECT reason, moderator_id, timestamp 
            FROM user_warnings 
            WHERE guild_id = ? AND user_id = ?
            ORDER BY timestamp DESC
        """
        results = await self.bot.db.fetch_all(query, (ctx.guild.id, member.id))

        if not results:
            await ctx.send(f"✅ Thành viên {member.mention} hiện tại chưa có tiền án tiền sự nào.")
            return

        embed = discord.Embed(
            title=f"📋 Lịch sử vi phạm của {member.name}",
            color=discord.Color.yellow()
        )
        
        for idx, row in enumerate(results, 1):
            reason, mod_id, timestamp = row
            # Lấy object moderator để hiển thị tên cho đẹp, nếu không tìm thấy thì hiện ID
            moderator = ctx.guild.get_member(mod_id)
            mod_name = moderator.mention if moderator else f"ID: {mod_id}"
            
            embed.add_field(
                name=f"Lần phạt #{idx} ({timestamp.split()[0]})",
                value=f"**Lý do:** {reason}\n**Người phạt:** {mod_name}",
                inline=False
            )
            
        await ctx.send(embed=embed)

    # 4. Lệnh Sút Thành Viên (!kick @user [lý do])
    @commands.command(name="kick", help="Sút thành viên ra khỏi server.")
    @commands.has_permissions(kick_members=True)
    async def kick(self, ctx, member: discord.Member, *, reason: str = "Không có lý do cụ thể"):
        if member.top_role >= ctx.author.top_role:
            await ctx.send("❌ Bạn không thể sút người có vai trò ngang bằng hoặc cao hơn mình!")
            return

        await member.kick(reason=reason)
        await ctx.send(f"👢 Đã sút thành viên **{member.name}** ra khỏi server. Lý do: {reason}")

    # 5. Lệnh Cấm Thành Viên (!ban @user [lý do])
    @commands.command(name="ban", help="Cấm thành viên tham gia server.")
    @commands.has_permissions(ban_members=True)
    async def ban(self, ctx, member: discord.Member, *, reason: str = "Không có lý do cụ thể"):
        if member.top_role >= ctx.author.top_role:
            await ctx.send("❌ Bạn không thể cấm người có vai trò ngang bằng hoặc cao hơn mình!")
            return

        await member.ban(reason=reason)
        await ctx.send(f"🔨 Đã cấm cửa thành viên **{member.name}** khỏi server. Lý do: {reason}")

# Hàm setup để đăng ký Cog với bot
async def setup(bot):
    await bot.add_cog(Moderation(bot))