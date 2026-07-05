import discord
from discord.ext import commands
import random
import asyncio

START_CHARGES = 3
MAX_ITEMS = 4
MAX_PLAYERS = 4
MIN_PLAYERS = 2

ITEMS = {
    "magnifier": {"emoji": "🔍", "name": "منظار مكبر", "desc": "يخليك تشوف نوع الطلقة الحالية بالمخزن"},
    "saw": {"emoji": "🪚", "name": "منشار", "desc": "يضاعف ضرر طلقتك القادمة (لو كانت حية)"},
    "beer": {"emoji": "🍺", "name": "جعة", "desc": "يفرّغ الطلقة الحالية من المخزن بدون تصويب"},
    "cigarette": {"emoji": "🚬", "name": "سيجارة", "desc": "يرجع لك شحنة واحدة (بحد أقصى الشحنات الأساسية)"},
    "handcuffs": {"emoji": "⛓️", "name": "أصفاد", "desc": "يجمد دور لاعب تختاره (يفوّت دوره القادم)"},
}


# ============ منطق اللعبة (مستقل تماماً عن ديسكورد) ============
class Player:
    def __init__(self, member: discord.Member):
        self.member = member
        self.charges = START_CHARGES
        self.items = []
        self.cuffed = False

    @property
    def alive(self):
        return self.charges > 0

    def charge_bar(self) -> str:
        return "⚡" * self.charges + "🖤" * (START_CHARGES - self.charges) if self.charges <= START_CHARGES else "⚡" * self.charges


class BuckshotGame:
    def __init__(self, players: list):
        self.players = players
        self.turn_index = 0
        self.shells = []
        self.live_total = 0
        self.blank_total = 0
        self.saw_next = False
        self.reload_count = 0
        self.last_log = ""
        self.load_shotgun(first=True)

    def alive_players(self):
        return [p for p in self.players if p.alive]

    def current_player(self) -> Player:
        return self.players[self.turn_index]

    def get_player(self, uid: int):
        for p in self.players:
            if p.member.id == uid:
                return p
        return None

    def load_shotgun(self, first: bool = False):
        n = random.randint(2, 8)
        live = random.randint(1, n - 1)
        blank = n - live
        shells = [True] * live + [False] * blank
        random.shuffle(shells)
        self.shells = shells
        self.live_total, self.blank_total = live, blank
        self.reload_count += 1
        if not first:
            for p in self.alive_players():
                if len(p.items) < MAX_ITEMS:
                    p.items.append(random.choice(list(ITEMS.keys())))

    def advance_turn(self):
        n = len(self.players)
        for _ in range(n + 1):
            self.turn_index = (self.turn_index + 1) % n
            p = self.players[self.turn_index]
            if p.alive:
                if p.cuffed:
                    p.cuffed = False
                    continue
                return

    def peek_shell(self) -> bool:
        """للمنظار: يرجع نوع الطلقة الحالية بدون سحبها"""
        if not self.shells:
            self.load_shotgun()
        return self.shells[0]

    def eject_shell(self):
        """للجعة: يفرغ الطلقة الحالية بدون تصويب"""
        if not self.shells:
            self.load_shotgun()
        shell = self.shells.pop(0)
        if not self.shells:
            self.load_shotgun()
        return shell

    def shoot(self, shooter: Player, target: Player):
        if not self.shells:
            self.load_shotgun()
        shell = self.shells.pop(0)
        dmg = 2 if self.saw_next else 1
        self.saw_next = False
        extra_turn = False
        if shell:
            target.charges = max(0, target.charges - dmg)
        else:
            if target is shooter:
                extra_turn = True
        if not self.shells:
            self.load_shotgun()
        return {"live": shell, "damage": dmg, "extra_turn": extra_turn}

    def is_over(self) -> bool:
        return len(self.alive_players()) <= 1

    def winner(self):
        alive = self.alive_players()
        return alive[0] if len(alive) == 1 else None


# ============ واجهة الانضمام ============
class JoinView(discord.ui.View):
    def __init__(self, host: discord.Member, timeout: float = 60):
        super().__init__(timeout=timeout)
        self.host = host
        self.members: list[discord.Member] = [host]
        self.message: discord.Message = None
        self.started = False

    def build_embed(self) -> discord.Embed:
        names = "\n".join(f"• {m.mention}" for m in self.members)
        embed = discord.Embed(
            title="🔫 باك شوت روليت - جولة جديدة",
            description=(
                f"لعبة حظ وخطر جماعية بشوتجن فيه شلات حية وفاضية!\n"
                f"يحتاج {MIN_PLAYERS}-{MAX_PLAYERS} لاعبين.\n\n"
                f"**👥 اللاعبين ({len(self.members)}/{MAX_PLAYERS}):**\n{names}"
            ),
            color=discord.Color.dark_red()
        )
        embed.set_footer(text=f"صاحب اللعبة: {self.host.display_name}")
        return embed

    @discord.ui.button(label="✅ انضمام", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user in self.members:
            return await interaction.response.send_message("⚠️ أنت مشارك بالفعل!", ephemeral=True)
        if len(self.members) >= MAX_PLAYERS:
            return await interaction.response.send_message("❌ اكتمل عدد اللاعبين!", ephemeral=True)
        self.members.append(interaction.user)
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="▶️ ابدأ اللعبة", style=discord.ButtonStyle.primary)
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.host:
            return await interaction.response.send_message("❌ فقط صاحب اللعبة يقدر يبدأ!", ephemeral=True)
        if len(self.members) < MIN_PLAYERS:
            return await interaction.response.send_message(
                f"❌ تحتاج {MIN_PLAYERS} لاعبين على الأقل! (حالياً {len(self.members)})", ephemeral=True
            )
        self.started = True
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

        game = BuckshotGame([Player(m) for m in self.members])
        await send_turn_message(interaction.channel, game)

    async def on_timeout(self):
        if self.started:
            return
        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(
                    embed=discord.Embed(title="⏰ انتهى وقت الانضمام، اللعبة أُلغيت", color=discord.Color.dark_gray()),
                    view=self
                )
            except discord.NotFound:
                pass


# ============ بناء عرض حالة اللعبة ============
def build_game_embed(game: BuckshotGame, log: str = "") -> discord.Embed:
    cur = game.current_player()
    status_lines = []
    for p in game.players:
        marker = "👉 " if p is cur and p.alive else ("💀 " if not p.alive else "")
        cuff = " ⛓️" if p.cuffed else ""
        items_str = " ".join(ITEMS[i]["emoji"] for i in p.items) or "—"
        status_lines.append(f"{marker}**{p.member.display_name}** {p.charge_bar()}{cuff}\n   🎒 {items_str}")

    embed = discord.Embed(
        title="🔫 باك شوت روليت",
        description=(
            f"🔴 حية: **{game.live_total}** مجهولة الترتيب | 🔵 فاضية: **{game.blank_total}**\n"
            f"شلات متبقية بالمخزن: **{len(game.shells)}**\n\n" + "\n\n".join(status_lines)
        ),
        color=discord.Color.dark_red()
    )
    if log:
        embed.add_field(name="📜 آخر حدث", value=log, inline=False)
    embed.set_footer(text=f"دور: {cur.member.display_name}")
    return embed


async def send_turn_message(channel: discord.abc.Messageable, game: BuckshotGame, log: str = ""):
    if game.is_over():
        winner = game.winner()
        embed = discord.Embed(
            title="🎉 انتهت اللعبة!",
            description=f"### 🏆 الفائز: {winner.member.mention}" if winner else "لا يوجد فائز!",
            color=discord.Color.gold()
        )
        await channel.send(embed=embed)
        return

    view = TurnView(game)
    embed = build_game_embed(game, log)
    msg = await channel.send(embed=embed, view=view)
    view.message = msg


# ============ واجهة الدور (تصويب / آيتمز) ============
class TargetSelect(discord.ui.Select):
    def __init__(self, game: BuckshotGame):
        cur = game.current_player()
        options = [
            discord.SelectOption(label=f"🔫 صوب على نفسي", value=str(cur.member.id))
        ]
        for p in game.alive_players():
            if p is not cur:
                options.append(discord.SelectOption(label=f"🎯 صوب على {p.member.display_name}", value=str(p.member.id)))
        super().__init__(placeholder="اختر هدف التصويب...", options=options)
        self.game = game

    async def callback(self, interaction: discord.Interaction):
        game = self.game
        cur = game.current_player()
        if interaction.user.id != cur.member.id:
            return await interaction.response.send_message("❌ مو دورك!", ephemeral=True)

        target = game.get_player(int(self.values[0]))
        result = game.shoot(cur, target)

        shell_txt = "🔴 طلقة حية!" if result["live"] else "🔵 طلقة فاضية (سليمة)"
        if target is cur:
            log = f"**{cur.member.display_name}** صوب على نفسه → {shell_txt}"
            if result["live"]:
                log += f" (خسر {result['damage']} شحنة)"
            elif result["extra_turn"]:
                log += " 🔁 دور إضافي!"
        else:
            log = f"**{cur.member.display_name}** صوب على **{target.member.display_name}** → {shell_txt}"
            if result["live"]:
                log += f" (خسر {result['damage']} شحنة)"

        if not result["extra_turn"]:
            game.advance_turn()

        for item in self.view.children:
            item.disabled = True
        await interaction.response.edit_message(view=self.view)
        await send_turn_message(interaction.channel, game, log)


class ItemSelect(discord.ui.Select):
    def __init__(self, game: BuckshotGame):
        cur = game.current_player()
        options = [
            discord.SelectOption(
                label=f"{ITEMS[i]['emoji']} {ITEMS[i]['name']}", value=i, description=ITEMS[i]["desc"]
            )
            for i in cur.items
        ]
        super().__init__(placeholder="🎒 استخدم آيتم (اختياري)...", options=options)
        self.game = game

    async def callback(self, interaction: discord.Interaction):
        game = self.game
        cur = game.current_player()
        if interaction.user.id != cur.member.id:
            return await interaction.response.send_message("❌ مو دورك!", ephemeral=True)

        item_key = self.values[0]
        cur.items.remove(item_key)
        log = f"**{cur.member.display_name}** استخدم {ITEMS[item_key]['emoji']} {ITEMS[item_key]['name']}"

        if item_key == "magnifier":
            shell = game.peek_shell()
            txt = "🔴 حية" if shell else "🔵 فاضية"
            await interaction.response.send_message(f"🔍 الطلقة الحالية بالمخزن: **{txt}**", ephemeral=True)
            # الآيتم يُستهلك ولا يرجع؛ نحدث الرسالة الأصلية بدون تغيير الدور
            new_view = TurnView(game)
            await interaction.message.edit(embed=build_game_embed(game, log), view=new_view)
            new_view.message = interaction.message
            return

        elif item_key == "saw":
            game.saw_next = True

        elif item_key == "beer":
            shell = game.eject_shell()
            txt = "🔴 حية" if shell else "🔵 فاضية"
            log += f" → طلعت **{txt}** وتم تفريغها بأمان"

        elif item_key == "cigarette":
            cur.charges = min(START_CHARGES, cur.charges + 1)
            log += f" → رجعت له شحنة (الحالي: {cur.charges})"

        elif item_key == "handcuffs":
            others = [p for p in game.alive_players() if p is not cur]
            if others:
                target = random.choice(others)
                target.cuffed = True
                log += f" → تم تجميد دور **{target.member.display_name}**"

        new_view = TurnView(game)
        await interaction.response.edit_message(embed=build_game_embed(game, log), view=new_view)
        new_view.message = interaction.message


class TurnView(discord.ui.View):
    def __init__(self, game: BuckshotGame, timeout: float = 120):
        super().__init__(timeout=timeout)
        self.game = game
        self.message: discord.Message = None
        self.add_item(TargetSelect(game))
        if game.current_player().items:
            self.add_item(ItemSelect(game))

    async def on_timeout(self):
        # لو ما تصرف اللاعب، يصوب على نفسه تلقائياً (عقاب بسيط على التأخير)
        game = self.game
        cur = game.current_player()
        target = cur
        result = game.shoot(cur, target)
        shell_txt = "🔴 طلقة حية!" if result["live"] else "🔵 طلقة فاضية"
        log = f"⏰ **{cur.member.display_name}** تأخر فصوب على نفسه تلقائياً → {shell_txt}"
        if not result["extra_turn"]:
            game.advance_turn()

        for item in self.children:
            item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
                await send_turn_message(self.message.channel, game, log)
            except discord.NotFound:
                pass


# ============ الكوج ============
class BuckshotCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="باك_شوت")
    async def buckshot(self, ctx: commands.Context):
        """يبدأ لعبة باك شوت روليت الجماعية (2-4 لاعبين)"""
        view = JoinView(host=ctx.author)
        msg = await ctx.send(embed=view.build_embed(), view=view)
        view.message = msg


async def setup(bot: commands.Bot):
    await bot.add_cog(BuckshotCog(bot))
