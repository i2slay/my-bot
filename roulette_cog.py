import discord
from discord.ext import commands
import io
import os
import math
import random
import asyncio
from PIL import Image, ImageDraw, ImageFont

# محاولة استيراد مكتبات دعم تشكيل النص العربي (اختيارية لكن مهمة لعرض الأسماء بشكل سليم)
try:
    import arabic_reshaper
    from bidi.algorithm import get_display
    ARABIC_SUPPORT = True
except ImportError:
    ARABIC_SUPPORT = False

WHEEL_SIZE = 700
COLORS = ["#e74c3c", "#3498db", "#2ecc71", "#f1c40f", "#9b59b6",
          "#1abc9c", "#e67e22", "#34495e", "#ff6b9d", "#00d2d3"]

# ضع خط يدعم العربي بجانب هذا الملف باسم arabic_font.ttf لعرض أفضل للأسماء
FONT_PATH_AR = "arabic_font.ttf"
FONT_PATH_FALLBACK = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def get_font(size: int):
    path = FONT_PATH_AR if os.path.exists(FONT_PATH_AR) else FONT_PATH_FALLBACK
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def shape_text(name: str) -> str:
    """يشكل النص العربي بشكل صحيح (يربط الحروف) قبل رسمه"""
    if ARABIC_SUPPORT:
        try:
            reshaped = arabic_reshaper.reshape(name)
            return get_display(reshaped)
        except Exception:
            return name
    return name


def draw_wheel(players: list, rotation_deg: float = 0, highlight_index: int = None) -> Image.Image:
    """يرسم عجلة الحظ بالأسماء، بزاوية دوران معينة، مع تمييز الفائز إذا حدد"""
    size = WHEEL_SIZE
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    center = size // 2
    radius = size // 2 - 15
    n = len(players)
    angle_per = 360 / n
    bbox = [center - radius, center - radius, center + radius, center + radius]

    name_font = get_font(22)

    for i in range(n):
        start = rotation_deg + i * angle_per - 90
        end = start + angle_per
        color = COLORS[i % len(COLORS)]
        is_winner = (i == highlight_index)
        outline = "#FFD700" if is_winner else "#FFFFFF"
        width = 8 if is_winner else 2
        draw.pieslice(bbox, start, end, fill=color, outline=outline, width=width)

    for i, member in enumerate(players):
        name = shape_text(member.display_name[:14])
        mid_deg = rotation_deg + i * angle_per + angle_per / 2 - 90
        mid_rad = math.radians(mid_deg)
        tx = center + math.cos(mid_rad) * radius * 0.62
        ty = center + math.sin(mid_rad) * radius * 0.62

        txt_img = Image.new("RGBA", (220, 50), (0, 0, 0, 0))
        td = ImageDraw.Draw(txt_img)
        td.text((0, 0), name, font=name_font, fill="white",
                 stroke_width=2, stroke_fill="black")
        rotated = txt_img.rotate(-(mid_deg + 90), expand=True)
        img.paste(rotated, (int(tx - rotated.width / 2), int(ty - rotated.height / 2)), rotated)

    hub_r = 45
    draw.ellipse([center - hub_r, center - hub_r, center + hub_r, center + hub_r],
                 fill="#2c2f33", outline="#FFD700", width=4)
    hub_font = get_font(30)
    draw.text((center, center), "🎡", font=hub_font, anchor="mm")

    draw.polygon([(center - 20, 8), (center + 20, 8), (center, 50)],
                 fill="#FF3B3B", outline="white", width=2)

    return img


def image_to_file(img: Image.Image, filename: str = "wheel.png") -> discord.File:
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return discord.File(buf, filename=filename)


def ease_out_cubic(t: float) -> float:
    return 1 - pow(1 - t, 3)


class RouletteView(discord.ui.View):
    def __init__(self, host: discord.Member, min_players: int = 2, max_players: int = 10, timeout: float = 90):
        super().__init__(timeout=timeout)
        self.host = host
        self.players: list[discord.Member] = [host]
        self.min_players = min_players
        self.max_players = max_players
        self.message: discord.Message = None
        self.started = False

    def build_embed(self) -> discord.Embed:
        names = "\n".join(f"• {p.mention}" for p in self.players) or "لا يوجد لاعبين بعد"
        embed = discord.Embed(
            title="🎡 عجلة الحظ - روليت",
            description=(
                f"اضغط **انضم** للمشاركة باللعبة!\n"
                f"الحد الأدنى للبدء: {self.min_players} لاعبين | الحد الأقصى: {self.max_players}\n\n"
                f"**👥 المشاركون ({len(self.players)}):**\n{names}"
            ),
            color=discord.Color.gold()
        )
        embed.set_footer(text=f"صاحب اللعبة: {self.host.display_name}")
        return embed

    async def refresh(self, interaction: discord.Interaction):
        await interaction.response.edit_message(embed=self.build_embed(), view=self)

    @discord.ui.button(label="✅ انضمام", style=discord.ButtonStyle.success)
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.started:
            return await interaction.response.send_message("❌ اللعبة بدأت بالفعل!", ephemeral=True)
        if interaction.user in self.players:
            return await interaction.response.send_message("⚠️ أنت مشارك بالفعل!", ephemeral=True)
        if len(self.players) >= self.max_players:
            return await interaction.response.send_message("❌ اكتمل عدد اللاعبين المسموح!", ephemeral=True)

        self.players.append(interaction.user)
        await self.refresh(interaction)

    @discord.ui.button(label="🚪 انسحاب", style=discord.ButtonStyle.secondary)
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.started:
            return await interaction.response.send_message("❌ اللعبة بدأت، ما تقدر تنسحب الحين!", ephemeral=True)
        if interaction.user not in self.players:
            return await interaction.response.send_message("⚠️ أنت غير مشارك أصلاً!", ephemeral=True)
        if interaction.user == self.host:
            return await interaction.response.send_message("❌ أنت صاحب اللعبة، استخدم زر الإلغاء بدلاً من الانسحاب!", ephemeral=True)

        self.players.remove(interaction.user)
        await self.refresh(interaction)

    @discord.ui.button(label="▶️ ابدأ الدوران", style=discord.ButtonStyle.primary)
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.host:
            return await interaction.response.send_message("❌ فقط صاحب اللعبة يقدر يبدأ الدوران!", ephemeral=True)
        if self.started:
            return await interaction.response.send_message("⚠️ اللعبة بدأت بالفعل!", ephemeral=True)
        if len(self.players) < self.min_players:
            return await interaction.response.send_message(
                f"❌ تحتاج على الأقل {self.min_players} لاعبين للبدء! (حالياً {len(self.players)})",
                ephemeral=True
            )

        self.started = True
        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            embed=discord.Embed(title="🎡 جاري تحضير العجلة...", color=discord.Color.gold()),
            view=self
        )
        await spin_and_announce(interaction, self.players)

    @discord.ui.button(label="❌ إلغاء", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.host:
            return await interaction.response.send_message("❌ فقط صاحب اللعبة يقدر يلغي!", ephemeral=True)
        if self.started:
            return await interaction.response.send_message("⚠️ ما تقدر تلغي، اللعبة بدأت بالفعل!", ephemeral=True)

        for item in self.children:
            item.disabled = True
        await interaction.response.edit_message(
            embed=discord.Embed(title="🚫 تم إلغاء اللعبة", color=discord.Color.red()),
            view=self
        )
        self.stop()

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


async def spin_and_announce(interaction: discord.Interaction, players: list):
    """يشغل تأثير الدوران المتحرك ثم يعلن الفائز"""
    winner_index = random.randrange(len(players))
    n = len(players)
    angle_per = 360 / n

    target_angle = -(winner_index * angle_per + angle_per / 2)
    full_spins = 4 * 360
    final_rotation = full_spins + target_angle

    frames = 16
    msg = None
    for f in range(1, frames + 1):
        t = f / frames
        eased = ease_out_cubic(t)
        current_rotation = final_rotation * eased
        img = draw_wheel(players, rotation_deg=current_rotation)
        file = image_to_file(img)

        embed = discord.Embed(title="🎡 العجلة تدور...", color=discord.Color.gold())
        embed.set_image(url="attachment://wheel.png")

        if f == 1:
            msg = await interaction.followup.send(embed=embed, file=file)
        else:
            await msg.edit(embed=embed, attachments=[file])

        delay = 0.08 + (t ** 2) * 0.5
        await asyncio.sleep(delay)

    final_img = draw_wheel(players, rotation_deg=final_rotation, highlight_index=winner_index)
    final_file = image_to_file(final_img)
    winner = players[winner_index]

    result_embed = discord.Embed(
        title="🎉 لدينا فائز!",
        description=f"### 🏆 {winner.mention} فاز باللعبة!",
        color=discord.Color.gold()
    )
    result_embed.set_image(url="attachment://wheel.png")
    result_embed.set_footer(text=f"إجمالي اللاعبين: {n}")
    await msg.edit(embed=result_embed, attachments=[final_file])


class RouletteCog(commands.Cog):
    """يحتوي أمر لعبة الروليت بالعجلة التفاعلية"""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="روليت")
    async def roulette(self, ctx: commands.Context):
        """يبدأ لعبة روليت جماعية بعجلة تفاعلية"""
        view = RouletteView(host=ctx.author)
        msg = await ctx.send(embed=view.build_embed(), view=view)
        view.message = msg


async def setup(bot: commands.Bot):
    """نقطة الدخول التي يستخدمها discord.py لتحميل هذا الملف كـ extension"""
    await bot.add_cog(RouletteCog(bot))
