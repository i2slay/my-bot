import discord
from discord.ext import commands
import io
import os
import random
import asyncio
from PIL import Image, ImageDraw

# 1. إعداد البوت
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# 2. إعدادات العجلة (رسم بسيط بدون الحاجة لخطوط خارجية)
def draw_wheel(players, rotation=0):
    img = Image.new("RGBA", (700, 700), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    n = len(players)
    angle = 360 / n
    for i in range(n):
        draw.pieslice([50, 50, 650, 650], rotation + i*angle, rotation + (i+1)*angle, 
                      fill=["#e74c3c", "#3498db", "#2ecc71", "#f1c40f"][i % 4], outline="white")
    return img

# 3. نظام اللعبة
class RouletteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.players = []
        self.started = False

    @discord.ui.button(label="انضم للعبة", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user not in self.players:
            self.players.append(interaction.user)
            await interaction.response.send_message(f"{interaction.user.name} انضم!", ephemeral=True)
            if len(self.players) == 1:
                await interaction.channel.send("⏳ ستبدأ اللعبة تلقائياً بعد 15 ثانية!")
                await asyncio.sleep(15)
                if not self.started and len(self.players) >= 2:
                    await self.start_game(interaction.channel)

    async def start_game(self, channel):
        self.started = True
        msg = await channel.send("🎡 العجلة تدور...")
        winner = random.choice(self.players)
        for i in range(5):
            buf = io.BytesIO()
            draw_wheel(self.players, rotation=i*72).save(buf, format="PNG")
            buf.seek(0)
            await msg.edit(content="🎡 جاري التدوير...", attachments=[discord.File(buf, "wheel.png")])
            await asyncio.sleep(0.5)
        await msg.edit(content=f"🎉 الفائز هو: **{winner.mention}**")

@bot.command()
async def روليت(ctx):
    await ctx.send("🎡 اضغط الزر للبدء:", view=RouletteView())

# 4. تشغيل
token = os.environ.get("DISCORD_TOKEN")
bot.run(token)
