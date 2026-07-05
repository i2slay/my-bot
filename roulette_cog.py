import discord
from discord.ext import commands
import io
import os
import math
import random
import asyncio
from PIL import Image, ImageDraw, ImageFont

# --- إعدادات البوت ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# --- إعدادات العجلة ---
WHEEL_SIZE = 700
COLORS = ["#e74c3c", "#3498db", "#2ecc71", "#f1c40f", "#9b59b6", "#1abc9c", "#e67e22", "#34495e", "#ff6b9d", "#00d2d3"]

def get_font(size):
    return ImageFont.load_default() # استخدام الخط الافتراضي لضمان عدم وجود أخطاء مسارات

def draw_wheel(players, rotation_deg=0):
    size = WHEEL_SIZE
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    center = size // 2
    radius = size // 2 - 15
    n = len(players)
    angle_per = 360 / n
    bbox = [center - radius, center - radius, center + radius, center + radius]
    
    for i in range(n):
        start = rotation_deg + i * angle_per - 90
        end = start + angle_per
        draw.pieslice(bbox, start, end, fill=COLORS[i % len(COLORS)], outline="white", width=2)
        
    draw.polygon([(center - 20, 8), (center + 20, 8), (center, 50)], fill="#FF3B3B")
    return img

class RouletteView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        self.players = []
        self.started = False

    def build_embed(self):
        desc = f"المشاركون ({len(self.players)}):\n" + "\n".join([p.name for p in self.players])
        return discord.Embed(title="🎡 روليت الحظ", description=desc, color=discord.Color.gold())

    @discord.ui.button(label="انضم للعبة", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.started: return
        if interaction.user not in self.players:
            self.players.append(interaction.user)
            await interaction.response.edit_message(embed=self.build_embed())
            if len(self.players) == 1:
                await interaction.channel.send("⏳ ستبدأ اللعبة تلقائياً بعد 15 ثانية!")
                await asyncio.sleep(15)
                if not self.started and len(self.players) >= 2:
                    await self.start_game(interaction)

    async def start_game(self, interaction):
        self.started = True
        msg = await interaction.channel.send("🎡 العجلة تدور...")
        winner = random.choice(self.players)
        for i in range(8):
            img = draw_wheel(self.players, rotation_deg=i*90)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            await msg.edit(content="🎡 جاري التدوير...", attachments=[discord.File(buf, "wheel.png")])
            await asyncio.sleep(0.5)
        await msg.edit(content=f"🎉 الفائز هو: **{winner.mention}**")

@bot.command()
async def روليت(ctx):
    view = RouletteView()
    await ctx.send(embed=view.build_embed(), view=view)

# --- تشغيل البوت ---
token = os.environ.get("DISCORD_TOKEN")
if token:
    bot.run(token)
else:
    print("يرجى ضبط DISCORD_TOKEN في الـ Secrets")
