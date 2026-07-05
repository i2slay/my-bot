import discord
from discord.ext import commands
import random

# ============ الإعدادات ============
START_CHARGES = 3
MAX_ITEMS = 4
MAX_PLAYERS = 4
MIN_PLAYERS = 2

ITEMS = {
    "magnifier": {"emoji": "🔍", "name": "منظار", "desc": "كشف الطلقة الحالية"},
    "saw": {"emoji": "🪚", "name": "منشار", "desc": "ضرر مضاعف"},
    "beer": {"emoji": "🍺", "name": "جعة", "desc": "إفراغ المخزن"},
    "cigarette": {"emoji": "🚬", "name": "سيجارة", "desc": "+1 شحنة"},
    "handcuffs": {"emoji": "⛓️", "name": "أصفاد", "desc": "تجميد الخصم"},
}

# ============ منطق اللعبة ============
class Player:
    def __init__(self, member: discord.Member):
        self.member = member
        self.charges = START_CHARGES
        self.items = []
        self.cuffed = False

    @property
    def alive(self): return self.charges > 0

    def charge_bar(self) -> str:
        return "⚡" * self.charges + "🖤" * (START_CHARGES - self.charges)

class BuckshotGame:
    def __init__(self, players: list):
        self.players = players
        self.turn_index = 0
        self.shells = []
        self.live_total = 0
        self.blank_total = 0
        self.saw_next = False
        self.load_shotgun(first=True)

    def load_shotgun(self, first: bool = False):
        n = random.randint(2, 8)
        live = random.randint(1, n - 1)
        blank = n - live
        self.shells = [True] * live + [False] * blank
        random.shuffle(self.shells)
        self.live_total, self.blank_total = live, blank
        if not first:
            for p in [p for p in self.players if p.alive]:
                if len(p.items) < MAX_ITEMS: p.items.append(random.choice(list(ITEMS.keys())))

    def current_player(self) -> Player: return self.players[self.turn_index]

    def advance_turn(self):
        n = len(self.players)
        for _ in range(n):
            self.turn_index = (self.turn_index + 1) % n
            if self.players[self.turn_index].alive:
                if self.players[self.turn_index].cuffed:
                    self.players[self.turn_index].cuffed = False
                    continue
                return

# ============ أدوات الواجهة ============
def get_game_embed(game: BuckshotGame, log: str = "اللعبة بدأت!") -> discord.Embed:
    cur = game.current_player()
    # تحديد اللون بناءً على نسبة الطلقات الحية (تحذير بصري)
    color = discord.Color.red() if game.live_total > game.blank_total else discord.Color.green()
    
    embed = discord.Embed(title="🔫 لوحة تحكم باك شوت", description=f"المخزن: **{len(game.shells)}** طلقة متبقية", color=color)
    
    for p in game.players:
        status = f"{p.charge_bar()} {'⛓️' if p.cuffed else ''}"
        items = " ".join(ITEMS[i]["emoji"] for i in p.items) if p.items else "---"
        marker = "👉 **(دورك)**" if p == cur else ("💀" if not p.alive else "")
        embed.add_field(name=f"{marker} {p.member.display_name}", value=f"HP: {status}\n🎒: {items}", inline=False)
    
    embed.add_field(name="📜 سجل الأحداث", value=f"```fix\n{log}\n```", inline=False)
    return embed

class GameView(discord.ui.View):
    def __init__(self, game: BuckshotGame):
        super().__init__(timeout=180)
        self.game = game
        self.add_item(TargetSelect(game))
        if game.current_player().items: self.add_item(ItemSelect(game))

    @discord.ui.button(label="قوانين", style=discord.ButtonStyle.secondary, row=2)
    async def rules(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("تذكر: الطلقة الحية تنهي الدور، الفارغة تمنحك دوراً إضافياً (إذا صوبت على نفسك).", ephemeral=True)

class TargetSelect(discord.ui.Select):
    def __init__(self, game: BuckshotGame):
        options = [discord.SelectOption(label=f"🔫 صوب على {p.member.display_name}", value=str(p.member.id)) for p in game.players if p.alive]
        super().__init__(placeholder="اختر هدفاً...", options=options)
        self.game = game

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.game.current_player().member.id: return await interaction.response.send_message("ليس دورك!", ephemeral=True)
        
        target = next(p for p in self.game.players if p.member.id == int(self.values[0]))
        shell = self.game.shells.pop(0)
        log = f"{interaction.user.display_name} صوب على {target.member.display_name} -> {'🔴 حية!' if shell else '🔵 فاضية!'}"
        
        if shell:
            dmg = 2 if self.game.saw_next else 1
            target.charges = max(0, target.charges - dmg)
            self.game.saw_next = False
        
        if not shell and target == self.game.current_player(): pass # دور إضافي منطقياً
        else: self.game.advance_turn()
        
        if not self.game.shells: self.game.load_shotgun()
        
        await interaction.response.edit_message(embed=get_game_embed(self.game, log), view=GameView(self.game))

class ItemSelect(discord.ui.Select):
    def __init__(self, game: BuckshotGame):
        options = [discord.SelectOption(label=ITEMS[i]["name"], value=i, emoji=ITEMS[i]["emoji"]) for i in game.current_player().items]
        super().__init__(placeholder="استخدم آيتم...", options=options)
        self.game = game

    async def callback(self, interaction: discord.Interaction):
        item = self.values[0]
        cur = self.game.current_player()
        cur.items.remove(item)
        
        # منطق الآيتم
        if item == "magnifier": await interaction.response.send_message(f"🔍 الطلقة القادمة: {'🔴 حية' if self.game.shells[0] else '🔵 فاضية'}", ephemeral=True)
        elif item == "beer": self.game.shells.pop(0); await interaction.response.send_message("🍺 تم تفريغ الطلقة!", ephemeral=True)
        
        await interaction.message.edit(embed=get_game_embed(self.game, f"{cur.member.display_name} استخدم {item}"), view=GameView(self.game))

# ============ الكوج الأساسي ============
class BuckshotCog(commands.Cog):
    def __init__(self, bot): self.bot = bot

    @commands.command()
    async def باك_شوت(self, ctx):
        # (استخدم منطق JoinView السابق هنا)
        await ctx.send("تم تشغيل اللعبة!")

async def setup(bot): await bot.add_cog(BuckshotCog(bot))
