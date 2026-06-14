import discord
from discord.ext import commands
import random
import asyncio

# ==========================================
# 1. GIAO DIỆN NÚT BẤM CHO TRÒ OẰN TÙ TÌ (RPS)
# ==========================================
# ==========================================
# GIAO DIỆN SẢNH CHỜ BLACKJACK NHIỀU NGƯỜI
# ==========================================
class BJLobbyView(discord.ui.View):
    def __init__(self, ctx, amount, economy_cog):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.amount = amount
        self.economy_cog = economy_cog
        self.players = [ctx.author] # Danh sách người chơi, mặc định có chủ phòng

    async def update_lobby_message(self, interaction):
        players_list = "\n".join([f"👤 {p.mention}" for p in self.players])
        embed = discord.Embed(
            title="🎰 Sảnh Chờ Blackjack Nhóm",
            description=f"**Mức cược:** {self.amount} đồng / người\n**Chủ phòng:** {self.ctx.author.mention}\n\n**Người tham gia ({len(self.players)}/5):**\n{players_list}",
            color=discord.Color.orange()
        )
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Tham Gia", style=discord.ButtonStyle.success, emoji="✋")
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user in self.players:
            await interaction.response.send_message("❌ Bạn đã ở trong bàn rồi!", ephemeral=True)
            return
        
        if len(self.players) >= 5:
            await interaction.response.send_message("❌ Bàn đã đầy (Tối đa 5 người)!", ephemeral=True)
            return

        bal = await self.economy_cog.get_balance(interaction.user.id)
        if bal < self.amount:
            await interaction.response.send_message(f"❌ Bạn không đủ tiền! Cần {self.amount} đồng.", ephemeral=True)
            return

        self.players.append(interaction.user)
        await self.update_lobby_message(interaction)

    @discord.ui.button(label="Bắt Đầu", style=discord.ButtonStyle.primary, emoji="▶️")
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ Chỉ chủ phòng mới được bấm Bắt Đầu!", ephemeral=True)
            return

        # Khởi tạo game
        game_view = BJPartyGameView(self.ctx, self.players, self.amount, self.economy_cog)
        await game_view.start_game(interaction)
        self.stop()

# ==========================================
# GIAO DIỆN BÀN CHƠI BLACKJACK NHIỀU NGƯỜI
# ==========================================
class BJPartyGameView(discord.ui.View):
    def __init__(self, ctx, players, amount, economy_cog):
        super().__init__(timeout=120)
        self.ctx = ctx
        self.players = players
        self.amount = amount
        self.economy_cog = economy_cog
        
        # Tạo bộ bài
        suits = ["♥️", "♦️", "♣️", "♠️"]
        ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
        self.deck = [(s, r) for s in suits for r in ranks]
        random.shuffle(self.deck)

        # Biến trạng thái
        self.current_turn_idx = 0
        self.hands = {player.id: [self.deck.pop(), self.deck.pop()] for player in self.players}
        self.dealer_hand = [self.deck.pop(), self.deck.pop()]
        self.statuses = {player.id: "Đang chơi" for player in self.players} # Lưu trạng thái (Bust, Stand, Win, Lose, Draw)

    def calculate_score(self, hand):
        score, aces = 0, 0
        for card in hand:
            val = card[1]
            if val in ["J", "Q", "K"]: score += 10
            elif val == "A":
                aces += 1
                score += 11
            else: score += int(val)
        while score > 21 and aces:
            score -= 10
            aces -= 1
        return score

    def get_hand_str(self, hand):
        return " ".join([f"`{c[0]}{c[1]}`" for c in hand])

    async def generate_board_embed(self, show_dealer=False):
        current_player = self.players[self.current_turn_idx] if self.current_turn_idx < len(self.players) else None
        
        embed = discord.Embed(title="🃏 Bàn chơi Blackjack Nhóm", color=discord.Color.blurple())
        
        # Phần bài Nhà Cái
        if show_dealer:
            d_score = self.calculate_score(self.dealer_hand)
            embed.add_field(name="🕵️ Nhà cái", value=f"{self.get_hand_str(self.dealer_hand)}\nĐiểm: **{d_score}**", inline=False)
        else:
            embed.add_field(name="🕵️ Nhà cái", value=f"`{self.dealer_hand[0][0]}{self.dealer_hand[0][1]}` `?`", inline=False)

        # Phần bài người chơi
        for idx, p in enumerate(self.players):
            hand = self.hands[p.id]
            score = self.calculate_score(hand)
            status_text = self.statuses[p.id]
            
            # Gắn icon cờ cho người đang tới lượt
            pointer = "🟢 **[TỚI LƯỢT]** " if idx == self.current_turn_idx else ""
            embed.add_field(name=f"👤 {p.name}", value=f"{pointer}{self.get_hand_str(hand)}\nĐiểm: {score} | {status_text}", inline=True)

        return embed

    async def start_game(self, interaction):
        embed = await self.generate_board_embed()
        await interaction.response.edit_message(embed=embed, view=self)

    async def next_turn(self, interaction):
        self.current_turn_idx += 1
        
        # Nếu tất cả người chơi đã xong, đến lượt nhà cái
        if self.current_turn_idx >= len(self.players):
            await self.resolve_dealer(interaction)
        else:
            embed = await self.generate_board_embed()
            await interaction.edit_original_response(embed=embed, view=self)

    async def resolve_dealer(self, interaction):
        d_score = self.calculate_score(self.dealer_hand)
        
        # Nhà cái rút bài
        while d_score < 17:
            self.dealer_hand.append(self.deck.pop())
            d_score = self.calculate_score(self.dealer_hand)

        # Trả thưởng cho từng người
        for p in self.players:
            if self.statuses[p.id] == "💥 Quắc (Bust)": 
                continue # Bị quắc trước đó rồi thì bỏ qua
            
            p_score = self.calculate_score(self.hands[p.id])
            bal = await self.economy_cog.get_balance(p.id)
            
            if d_score > 21 or p_score > d_score:
                self.statuses[p.id] = "🎉 THẮNG"
                await self.ctx.bot.db.execute("UPDATE users_money SET wallet = ? WHERE user_id = ?", (bal + self.amount, p.id))
            elif p_score < d_score:
                self.statuses[p.id] = "💀 THUA"
                await self.ctx.bot.db.execute("UPDATE users_money SET wallet = ? WHERE user_id = ?", (bal - self.amount, p.id))
            else:
                self.statuses[p.id] = "🤝 HÒA"
                # Hòa không bị trừ tiền

        for item in self.children: item.disabled = True
        embed = await self.generate_board_embed(show_dealer=True)
        embed.color = discord.Color.gold()
        await interaction.edit_original_response(embed=embed, view=self)
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        current_player = self.players[self.current_turn_idx]
        if interaction.user.id != current_player.id:
            await interaction.response.send_message(f"❌ Chưa tới lượt của bạn! Đang đợi {current_player.name}.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="Rút bài (Hit)", style=discord.ButtonStyle.primary)
    async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        current_player = self.players[self.current_turn_idx]
        self.hands[current_player.id].append(self.deck.pop())
        score = self.calculate_score(self.hands[current_player.id])

        if score > 21:
            self.statuses[current_player.id] = "💥 Quắc (Bust)"
            # Quắc thì trừ tiền luôn
            bal = await self.economy_cog.get_balance(current_player.id)
            await self.ctx.bot.db.execute("UPDATE users_money SET wallet = ? WHERE user_id = ?", (bal - self.amount, current_player.id))
            await self.next_turn(interaction)
        else:
            embed = await self.generate_board_embed()
            await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="Dừng (Stand)", style=discord.ButtonStyle.secondary)
    async def stand_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        current_player = self.players[self.current_turn_idx]
        self.statuses[current_player.id] = "🛑 Đã Dừng"
        await self.next_turn(interaction)

class RPSMultiplayerView(discord.ui.View):
    def __init__(self, ctx, opponent: discord.Member, amount: int, economy_cog):
        super().__init__(timeout=60)  # Trận đấu tự hủy sau 60 giây nếu không ai bấm
        self.ctx = ctx
        self.player_a = ctx.author
        self.player_b = opponent
        self.amount = amount
        self.economy_cog = economy_cog
        
        # Lưu trữ lựa chọn của 2 người
        self.choice_a = None
        self.choice_b = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Chỉ cho phép 2 người trong cuộc bấm nút
        if interaction.user.id not in [self.player_a.id, self.player_b.id]:
            await interaction.response.send_message("❌ Bạn không phải là người tham gia trận thách đấu này!", ephemeral=True)
            return False
        return True

    async def handle_choice(self, interaction: discord.Interaction, choice: str):
        # Kiểm tra số dư tài khoản của cả 2 trước khi ghi nhận lượt đi
        bal_a = await self.economy_cog.get_balance(self.player_a.id)
        bal_b = await self.economy_cog.get_balance(self.player_b.id)
        
        if bal_a < self.amount or bal_b < self.amount:
            await interaction.response.send_message("❌ Một trong hai người không còn đủ tiền cược để tiếp tục trận đấu!", ephemeral=True)
            self.stop()
            return

        # Ghi nhận lựa chọn dựa trên người bấm nút
        if interaction.user.id == self.player_a.id:
            if self.choice_a is not None:
                await interaction.response.send_message("⚠️ Bạn đã ra chiêu rồi, không thể đổi ý!", ephemeral=True)
                return
            self.choice_a = choice
            await interaction.response.send_message(f"🔒 Bạn đã chọn `{choice.upper()}` bí mật thành công!", ephemeral=True)
        
        elif interaction.user.id == self.player_b.id:
            if self.choice_b is not None:
                await interaction.response.send_message("⚠️ Bạn đã ra chiêu rồi, không thể đổi ý!", ephemeral=True)
                return
            self.choice_b = choice
            await interaction.response.send_message(f"🔒 Bạn đã chọn `{choice.upper()}` bí mật thành công!", ephemeral=True)

        # Cập nhật giao diện bàn đấu công khai để mọi người biết ai đã đi
        status_a = "✅ Đã ra chiêu" if self.choice_a else "⏳ Đang suy nghĩ..."
        status_b = "✅ Đã ra chiêu" if self.choice_b else "⏳ Đang suy nghĩ..."
        
        embed = discord.Embed(
            title="⚔️ Trận đấu Oẳn Tù Tì PvP",
            description=f"**Tiền cược:** {self.amount} đồng.\n\n"
                        f"👤 {self.player_a.mention}: {status_a}\n"
                        f"👤 {self.player_b.mention}: {status_b}",
            color=discord.Color.orange()
        )
        
        # Cập nhật lại tin nhắn gốc (bàn đấu công khai)
        await interaction.message.edit(embed=embed, view=self)

        # Nếu cả 2 người đã chọn xong thì tiến hành phân định thắng thua
        if self.choice_a and self.choice_b:
            await self.resolve_match(interaction.message)

    async def resolve_match(self, message: discord.Message):
        # Vô hiệu hóa các nút bấm sau khi kết thúc
        for item in self.children:
            item.disabled = True

        bal_a = await self.economy_cog.get_balance(self.player_a.id)
        bal_b = await self.economy_cog.get_balance(self.player_b.id)

        emojis = {"bua": "🪨 Búa", "bao": "📜 Bao", "keo": "✂️ Kéo"}

        if self.choice_a == self.choice_b:
            title = "🤝 Trận Đấu Hòa Nhau!"
            desc = f"Cả hai cùng ra **{emojis[self.choice_a]}**.\nTiền cược được giữ nguyên."
            color = discord.Color.light_grey()
        
        # Các kịch bản Người A thắng
        elif (self.choice_a == "bua" and self.choice_b == "keo") or \
             (self.choice_a == "bao" and self.choice_b == "bua") or \
             (self.choice_a == "keo" and self.choice_b == "bao"):
            title = f"🎉 {self.player_a.name} Giành Chiến Thắng!"
            desc = f"{self.player_a.mention} ra **{emojis[self.choice_a]}** thắng {self.player_b.mention} ra **{emojis[self.choice_b]}**.\n" \
                   f"💰 {self.player_a.name} nhận `+{self.amount}` đồng.\n" \
                   f"📉 {self.player_b.name} mất `-{self.amount}` đồng."
            color = discord.Color.green()
            # Cập nhật số dư vào DB
            await self.ctx.bot.db.execute("UPDATE users_money SET wallet = ? WHERE user_id = ?", (bal_a + self.amount, self.player_a.id))
            await self.ctx.bot.db.execute("UPDATE users_money SET wallet = ? WHERE user_id = ?", (bal_b - self.amount, self.player_b.id))
        
        # Các kịch bản Người B thắng
        else:
            title = f"🎉 {self.player_b.name} Giành Chiến Thắng!"
            desc = f"{self.player_b.mention} ra **{emojis[self.choice_b]}** thắng {self.player_a.mention} ra **{emojis[self.choice_a]}**.\n" \
                   f"💰 {self.player_b.name} nhận `+{self.amount}` đồng.\n" \
                   f"📉 {self.player_a.name} mất `-{self.amount}` đồng."
            color = discord.Color.green()
            # Cập nhật số dư vào DB
            await self.ctx.bot.db.execute("UPDATE users_money SET wallet = ? WHERE user_id = ?", (bal_a - self.amount, self.player_a.id))
            await self.ctx.bot.db.execute("UPDATE users_money SET wallet = ? WHERE user_id = ?", (bal_b + self.amount, self.player_b.id))

        final_embed = discord.Embed(title=title, description=desc, color=color)
        await message.edit(embed=final_embed, view=self)
        self.stop()

    @discord.ui.button(label="Búa", emoji="🪨", style=discord.ButtonStyle.primary)
    async def bua_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, "bua")

    @discord.ui.button(label="Bao", emoji="📜", style=discord.ButtonStyle.success)
    async def bao_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, "bao")

    @discord.ui.button(label="Kéo", emoji="✂️", style=discord.ButtonStyle.danger)
    async def keo_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_choice(interaction, "keo")

class RPSView(discord.ui.View):
    def __init__(self, ctx, amount, economy_cog):
        super().__init__(timeout=30)  # Người chơi có 30 giây để bấm nút
        self.ctx = ctx
        self.amount = amount
        self.economy_cog = economy_cog

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Chỉ cho phép người gọi lệnh bấm nút
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ Đây không phải lượt chơi của bạn!", ephemeral=True)
            return False
        return True

    async def handle_rps(self, interaction: discord.Interaction, player_choice: str):
        # Kiểm tra lại số dư một lần nữa trước khi xử lý kết quả
        current_balance = await self.economy_cog.get_balance(self.ctx.author.id)
        if current_balance < self.amount:
            await interaction.response.edit_message(content="❌ Bạn không đủ tiền cược!", view=None)
            self.stop()
            return

        choices = ["bua", "bao", "keo"]
        bot_choice = random.choice(choices)
        
        # Định dạng hiển thị emoji
        emojis = {"bua": "🪨 Búa", "bao": "📜 Bao", "keo": "✂️ Kéo"}
        
        # Phân định thắng thua
        if player_choice == bot_choice:
            result_text = " hòa nhau! Tiền cược được hoàn trả."
            new_balance = current_balance
        elif (player_choice == "bua" and bot_choice == "keo") or \
             (player_choice == "bao" and bot_choice == "bua") or \
             (player_choice == "keo" and bot_choice == "bao"):
            result_text = f" thắng! Bạn nhận được **{self.amount}** đồng."
            new_balance = current_balance + self.amount
        else:
            result_text = f" thua! Bạn mất **{self.amount}** đồng."
            new_balance = current_balance - self.amount

        # Cập nhật database
        await self.ctx.bot.db.execute("UPDATE users_money SET wallet = ? WHERE user_id = ?", (new_balance, self.ctx.author.id))
        
        # Disable toàn bộ nút sau khi chơi xong
        for item in self.children:
            item.disabled = True

        embed = discord.Embed(
            title="✂️ Kết quả Oẳn Tù Tì",
            description=f"Bạn chọn: **{emojis[player_choice]}**\nBot chọn: **{emojis[bot_choice]}**\n\nKết quả: Bạn{result_text}\nSố dư mới: **{new_balance}** đồng.",
            color=discord.Color.blue()
        )
        await interaction.response.edit_message(embed=embed, view=self)
        self.stop()

    @discord.ui.button(label="Búa", emoji="🪨", style=discord.ButtonStyle.primary)
    async def bua_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_rps(interaction, "bua")

    @discord.ui.button(label="Bao", emoji="📜", style=discord.ButtonStyle.success)
    async def bao_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_rps(interaction, "bao")

    @discord.ui.button(label="Kéo", emoji="✂️", style=discord.ButtonStyle.danger)
    async def keo_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.handle_rps(interaction, "keo")


# ==========================================
# 2. GIAO DIỆN NÚT BẤM CHO TRÒ BLACKJACK
# ==========================================
class BlackjackView(discord.ui.View):
    def __init__(self, ctx, amount, economy_cog, player_hand, dealer_hand, deck):
        super().__init__(timeout=60)
        self.ctx = ctx
        self.amount = amount
        self.economy_cog = economy_cog
        self.player_hand = player_hand
        self.dealer_hand = dealer_hand
        self.deck = deck

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("❌ Đây không phải bàn chơi của bạn!", ephemeral=True)
            return False
        return True

    def calculate_score(self, hand):
        score = 0
        aces = 0
        for card in hand:
            value = card[1]
            if value in ["J", "Q", "K"]:
                score += 10
            elif value == "A":
                aces += 1
                score += 11
            else:
                score += int(value)
        
        while score > 21 and aces:
            score -= 10
            aces -= 1
        return score

    def get_hand_string(self, hand):
        return " ".join([f"`{card[0]}{card[1]}`" for card in hand])

    async def end_game(self, interaction, player_score, dealer_score, status):
        current_balance = await self.economy_cog.get_balance(self.ctx.author.id)
        
        if status == "win":
            new_balance = current_balance + self.amount
            title = "🎉 Bạn Thắng!"
            color = discord.Color.green()
            desc = f"Nhận được **{self.amount}** đồng."
        elif status == "lose":
            new_balance = current_balance - self.amount
            title = "💀 Bạn Thua!"
            color = discord.Color.red()
            desc = f"Mất **{self.amount}** đồng."
        else:
            new_balance = current_balance
            title = "🤝 Hòa Nhau!"
            color = discord.Color.light_grey()
            desc = "Tiền cược được hoàn trả."

        await self.ctx.bot.db.execute("UPDATE users_money SET wallet = ? WHERE user_id = ?", (new_balance, self.ctx.author.id))

        for item in self.children:
            item.disabled = True

        embed = discord.Embed(title=title, color=color)
        embed.add_field(name="🃏 Bài của bạn", value=f"{self.get_hand_string(self.player_hand)}\nĐiểm: **{player_score}**", inline=True)
        embed.add_field(name="🕵️ Nhà cái", value=f"{self.get_hand_string(self.dealer_hand)}\nĐiểm: **{dealer_score}**", inline=True)
        embed.add_field(name="💰 Kết quả", value=f"{desc}\nSố dư mới: **{new_balance}** đồng.", inline=False)
        
        await interaction.edit_original_response(embed=embed, view=self)
        self.stop()

    @discord.ui.button(label="Rút bài (Hit)", style=discord.ButtonStyle.primary)
    async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        self.player_hand.append(self.deck.pop())
        player_score = self.calculate_score(self.player_hand)

        if player_score > 21:
            await self.end_game(interaction, player_score, self.calculate_score(self.dealer_hand), "lose")
        else:
            embed = discord.Embed(title="🃏 Bàn chơi Blackjack", color=discord.Color.blurple())
            embed.add_field(name="🃏 Bài của bạn", value=f"{self.get_hand_string(self.player_hand)}\nĐiểm: **{player_score}**", inline=True)
            embed.add_field(name="🕵️ Nhà cái", value=f"`{self.dealer_hand[0][0]}{self.dealer_hand[0][1]}` `?`", inline=True)
            await interaction.edit_original_response(embed=embed, view=self)

    @discord.ui.button(label="Dừng (Stand)", style=discord.ButtonStyle.secondary)
    async def stand_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        player_score = self.calculate_score(self.player_hand)
        dealer_score = self.calculate_score(self.dealer_hand)

        # Nhà cái phải rút cho đến khi đạt từ 17 điểm trở lên
        while dealer_score < 17:
            self.dealer_hand.append(self.deck.pop())
            dealer_score = self.calculate_score(self.dealer_hand)

        if dealer_score > 21 or player_score > dealer_score:
            await self.end_game(interaction, player_score, dealer_score, "win")
        elif player_score < dealer_score:
            await self.end_game(interaction, player_score, dealer_score, "lose")
        else:
            await self.end_game(interaction, player_score, dealer_score, "draw")


# ==========================================
# 3. CLASS HỆ THỐNG COGS CHÍNH
# ==========================================
class Minigames(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # --- LỆNH TUNG ĐỒNG XU (GIỮ NGUYÊN BẢN 40%) ---
    @commands.command(name="coinflip", aliases=["cf"])
    async def coinflip(self, ctx, choice: str, amount: int):
        choice = choice.lower()
        if choice not in ["sap", "ngua"]:
            await ctx.send("❌ Chỉ được chọn `sap` hoặc `ngua` thôi.")
            return
        if amount <= 0:
            await ctx.send("❌ Tiền cược phải lớn hơn 0 đồng.")
            return

        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog: return

        current_balance = await economy_cog.get_balance(ctx.author.id)
        if current_balance < amount:
            await ctx.send(f"❌ Bạn không đủ tiền! Số dư: {current_balance} đồng.")
            return

        is_user_winner = random.random() < 0.40
        if is_user_winner:
            result = choice
            new_balance = current_balance + amount
            msg = f"🪙 Đồng xu ra **{result.upper()}**! Bạn trúng mánh và nhận được **{amount}** đồng."
        else:
            result = "ngua" if choice == "sap" else "sap"
            new_balance = current_balance - amount
            msg = f"🪙 Đồng xu ra **{result.upper()}**! Bạn đã mất trắng **{amount}** đồng."

        await self.bot.db.execute("UPDATE users_money SET wallet = ? WHERE user_id = ?", (new_balance, ctx.author.id))
        await ctx.send(msg)

    # --- GAME 1: SLOTS (MÁY QUAY HŨ) ---
    @commands.command(name="slots", aliases=["sl"])
    async def slots(self, ctx, amount: int):
        if amount <= 0:
            await ctx.send("❌ Tiền cược phải lớn hơn 0 đồng.")
            return

        economy_cog = self.bot.get_cog("Economy")
        current_balance = await economy_cog.get_balance(ctx.author.id)
        if current_balance < amount:
            await ctx.send(f"❌ Số dư của bạn không đủ! ({current_balance} đồng)")
            return

        emojis = ["🍎", "🍊", "🍇", "💎"]
        
        # Gửi thông báo mô phỏng đang quay
        embed = discord.Embed(title="🎰 Đang quay Slots...", description="[ ⏳ | ⏳ | ⏳ ]", color=discord.Color.orange())
        msg = await ctx.send(embed=embed)
        await asyncio.sleep(1.5) # Tạo độ trễ kịch tính

        # Kết quả ngẫu nhiên
        slot1 = random.choice(emojis)
        slot2 = random.choice(emojis)
        slot3 = random.choice(emojis)

        if slot1 == slot2 == slot3:
            multiplier = 5 if slot1 == "💎" else 3
            winnings = amount * multiplier
            new_balance = current_balance + winnings
            result_text = f"🎉 ĐẠI THẮNG! Nổ hũ x{multiplier}, nhận ngay **{winnings}** đồng!"
            color = discord.Color.green()
        elif slot1 == slot2 or slot2 == slot3 or slot1 == slot3:
            winnings = int(amount * 1.5)
            new_balance = current_balance + winnings - amount
            result_text = f"💵 Thắng nhỏ! Khớp 2 cặp, nhận lại **{winnings}** đồng!"
            color = discord.Color.light_grey()
        else:
            new_balance = current_balance - amount
            result_text = f"😭 Thua sạch! Chúc bạn may mắn lần sau."
            color = discord.Color.red()

        await self.bot.db.execute("UPDATE users_money SET wallet = ? WHERE user_id = ?", (new_balance, ctx.author.id))
        
        embed = discord.Embed(
            title="🎰 Kết quả Slots",
            description=f"[ {slot1} | {slot2} | {slot3} ]\n\n{result_text}\nSố dư mới: **{new_balance}** đồng.",
            color=color
        )
        await msg.edit(embed=embed)

    # --- GAME 2: OẰN TÙ TÌ (RPS) BAO GỒM PHẦN GỌI VIEW BUTTONS ---
    @commands.command(name="rps", help="Thách đấu Oẳn Tù Tì 1vs1. Cú pháp: !rps @member [tiền_cược]")
    async def rps(self, ctx,opponent: discord.Member, amount: int):

        if opponent.id == ctx.author.id:
            await ctx.send("❌ Bạn không thể tự oẳn tù tì với cái bóng của mình!")
            return

        if opponent.bot:
            await ctx.send("❌ Đừng rủ bot chơi, tội nghiệp nó.")
            return

        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog:
            await ctx.send("❌ Hệ thống ngân hàng đang gặp sự cố.")
            return

        # Kiểm tra tiền của cả người thách đấu và người được thách đấu
        bal_a = await economy_cog.get_balance(ctx.author.id)
        bal_b = await economy_cog.get_balance(opponent.id)

        if bal_a < amount:
            await ctx.send(f"❌ Bạn không đủ tiền! Số dư của bạn: {bal_a} đồng.")
            return
        if bal_b < amount:
            await ctx.send(f"❌ Đối thủ không đủ tiền! Số dư của {opponent.name}: {bal_b} đồng.")
            return

        # Khởi tạo giao diện trận đấu công khai ban đầu
        embed = discord.Embed(
            title="⚔️ Lời Thách Đấu Oẳn Tù Tì PvP",
            description=f"💥 {ctx.author.mention} đã gửi một lời thách đấu trị giá **{amount}** đồng tới {opponent.mention}!\n\n"
                        f"👤 {ctx.author.mention}: ⏳ Đang suy nghĩ...\n"
                        f"👤 {opponent.mention}: ⏳ Đang suy nghĩ...\n\n"
                        f"👇 Cả hai hãy nhấn nút phía dưới để ra chiêu bí mật!",
            color=discord.Color.orange()
        )
        
        view = RPSMultiplayerView(ctx, opponent, amount, economy_cog)
        await ctx.send(embed=embed, view=view)

    # --- GAME 3: BLACKJACK ---
    @commands.command(name="blackjack", aliases=["bj"])
    async def blackjack(self, ctx, amount: int):
        if amount <= 0:
            await ctx.send("❌ Tiền cược phải lớn hơn 0 đồng.")
            return

        economy_cog = self.bot.get_cog("Economy")
        current_balance = await economy_cog.get_balance(ctx.author.id)
        if current_balance < amount:
            await ctx.send(f"❌ Bạn không đủ tiền! Số dư: {current_balance} đồng.")
            return

        # Khởi tạo bộ bài tiêu chuẩn
        suits = ["♥️", "♦️", "♣️", "♠️"]
        ranks = ["2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K", "A"]
        deck = [(s, r) for s in suits for r in ranks]
        random.shuffle(deck)

        # Chia 2 lá đầu tiên
        player_hand = [deck.pop(), deck.pop()]
        dealer_hand = [deck.pop(), deck.pop()]

        embed = discord.Embed(title="🃏 Bàn chơi Blackjack", color=discord.Color.blurple())
        embed.add_field(name="🃏 Bài của bạn", value=f"`{player_hand[0][0]}{player_hand[0][1]}` `{player_hand[1][0]}{player_hand[1][1]}`", inline=True)
        embed.add_field(name="🕵️ Nhà cái", value=f"`{dealer_hand[0][0]}{dealer_hand[0][1]}` `?`", inline=True)

        view = BlackjackView(ctx, amount, economy_cog, player_hand, dealer_hand, deck)
        await ctx.send(embed=embed, view=view)
    
    @commands.command(name="bjp", aliases=["bjparty"], help="Mở bàn Blackjack cho nhiều người chơi. Cú pháp: !bjp [tiền_cược]")
    async def bjparty(self, ctx, amount: int):
        if amount <= 0:
            await ctx.send("❌ Tiền cược phải lớn hơn 0 đồng.")
            return

        economy_cog = self.bot.get_cog("Economy")
        if not economy_cog: return

        current_balance = await economy_cog.get_balance(ctx.author.id)
        if current_balance < amount:
            await ctx.send(f"❌ Bạn không đủ tiền mở bàn! Cần: {amount} đồng.")
            return

        embed = discord.Embed(
            title="🎰 Sảnh Chờ Blackjack Nhóm", 
            description=f"**Mức cược:** {amount} đồng / người\n**Chủ phòng:** {ctx.author.mention}\n\n**Người tham gia (1/5):**\n👤 {ctx.author.mention}",
            color=discord.Color.orange()
        )
        
        view = BJLobbyView(ctx, amount, economy_cog)
        await ctx.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Minigames(bot))