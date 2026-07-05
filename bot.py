import discord
from discord.ext import commands
import os
import sys
import io
import contextlib
import traceback

# 1. إعداد الـ Intents والصلاحيات الأساسية
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="/", intents=intents)

MAX_MSG_LEN = 1900  # حد أمان أقل من 2000 حرف اللي يفرضه ديسكورد


def truncate(text: str, limit: int = MAX_MSG_LEN) -> str:
    """يقص أي نص طويل عشان ما تنطيح رسالة ديسكورد"""
    if len(text) <= limit:
        return text
    cut = text[:limit]
    return cut + f"\n... [تم قص {len(text) - limit} حرف إضافي]"


def clean_code_block(code: str) -> str:
    """يشيل علامات ```py أو ``` من الكود المكتوب بالشات"""
    code = code.strip()
    if code.startswith("```") and code.endswith("```"):
        code = code[3:-3].strip()
        if code.startswith("py\n"):
            code = code[3:]
        elif code.startswith("python\n"):
            code = code[7:]
    return code


async def run_user_code(code: str, env: dict):
    """
    دالة مشتركة تشغل الكود وترجع (output, result, error)
    تستخدمها كل من أمر 'برمج' وزر التشغيل الديناميكي - عشان ما يتكرر المنطق
    """
    str_obj = io.StringIO()
    env = dict(env)  # نسخة عشان ما نأثر على القاموس الأصلي
    env["print"] = lambda *args, **kwargs: print(*args, file=str_obj, **kwargs)

    code = clean_code_block(code)
    formatted_code = "\n".join(f"    {line}" for line in code.splitlines())
    exec_text = f"async def __ex():\n{formatted_code}"

    try:
        exec(exec_text, env)
        with contextlib.redirect_stdout(str_obj):
            result = await env["__ex"]()
        output = str_obj.getvalue()
        return output, result, None
    except Exception:
        return str_obj.getvalue(), None, traceback.format_exc()


def build_result_message(output, result, error) -> str:
    """يبني رسالة النتيجة النهائية بشكل موحّد ومقصوصة بأمان"""
    if error:
        return truncate(f"❌ **حدث خطأ أثناء التنفيذ:**\n```py\n{error}\n```")
    if output:
        return truncate(f"✅ **تم التنفيذ! المخرجات:**\n```py\n{output}\n```")
    if result is not None:
        return truncate(f"✅ **تم التنفيذ! النتيجة المسترجعة:**\n```py\n{result}\n```")
    return "✅ **تم تشغيل الكود بنجاح في الخلفية!**"


# --- [ القسم الأول: كلاس لوحة التحكم بالأزرار الثابتة ] ---
class ControlPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # الأزرار تعمل دائماً ولا تنتهي صلاحيتها

    @discord.ui.button(label="📊 إحصائيات السيرفرات", style=discord.ButtonStyle.primary, custom_id="stats_btn")
    async def stats_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await bot.is_owner(interaction.user):
            return await interaction.response.send_message("❌ عذراً، هذه اللوحة مخصصة لمالك البوت فقط!", ephemeral=True)

        guilds_text = "\n".join([f"• {g.name} ({g.member_count} عضو)" for g in bot.guilds])
        guilds_text = truncate(guilds_text, 3800)  # حد وصف الـ embed هو 4096 حرف
        embed = discord.Embed(
            title="📊 إحصائيات التواجد",
            description=f"إجمالي السيرفرات: **{len(bot.guilds)}**\n\n**قائمة السيرفرات:**\n{guilds_text}",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🎮 تغيير الحالة إلى (نشط)", style=discord.ButtonStyle.success, custom_id="status_btn")
    async def status_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await bot.is_owner(interaction.user):
            return await interaction.response.send_message("❌ لا تملك صلاحية!", ephemeral=True)

        await bot.change_presence(activity=discord.Game(name="تحت التحكم المباشر 🛠️"))
        await interaction.response.send_message("✅ تم تغيير حالة البوت بنجاح!", ephemeral=True)

    @discord.ui.button(label="➕ إنشاء روم سريع", style=discord.ButtonStyle.secondary, custom_id="create_channel_btn")
    async def channel_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await bot.is_owner(interaction.user):
            return await interaction.response.send_message("❌ لا تملك صلاحية!", ephemeral=True)

        if interaction.guild is None:
            return await interaction.response.send_message(
                "❌ هذا الزر يعمل فقط داخل سيرفر، لا يعمل بالرسائل الخاصة!", ephemeral=True
            )

        try:
            channel = await interaction.guild.create_text_channel(name="روم-تحكم-سريع")
            await interaction.response.send_message(f"✅ تم إنشاء الروم بنجاح: {channel.mention}", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ البوت ما يملك صلاحية إنشاء رومات بهذا السيرفر!", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(truncate(f"❌ خطأ غير متوقع: {e}"), ephemeral=True)

    @discord.ui.button(label="🛑 إطفاء البوت", style=discord.ButtonStyle.danger, custom_id="shutdown_btn")
    async def shutdown_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await bot.is_owner(interaction.user):
            return await interaction.response.send_message("❌ لا تملك صلاحية!", ephemeral=True)

        await interaction.response.send_message("👋 جاري إغلاق البوت وتأمين الملفات...", ephemeral=True)
        await bot.close()


# --- [ القسم الثاني: كلاس صناعة الأزرار البرمجية الديناميكية ] ---
class DynamicCodeButton(discord.ui.View):
    def __init__(self, code: str, owner_id: int):
        super().__init__(timeout=600)  # صلاحية الزر تنتهي بعد 10 دقائق للأمان
        self.code = code
        self.owner_id = owner_id
        self.run_dynamic_code.label = "🚀 تشغيل الكود البرمجي"

    async def on_timeout(self):
        # لما تنتهي الصلاحية، عطّل الزر ووضح ذلك بدل ما يصير "ميت" بصمت
        for item in self.children:
            item.disabled = True
            item.label = "⏰ انتهت صلاحية هذا الزر"
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                pass

    @discord.ui.button(label="🚀 تشغيل الكود البرمجي", style=discord.ButtonStyle.primary)
    async def run_dynamic_code(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            return await interaction.response.send_message("❌ هذا الزر مخصص لمالك الكود فقط!", ephemeral=True)

        await interaction.response.defer(ephemeral=True)

        env = {
            'bot': bot,
            'interaction': interaction,
            'channel': interaction.channel,
            'author': interaction.user,
            'guild': interaction.guild,
            'discord': discord,
            'os': os,
            'sys': sys
        }

        output, result, error = await run_user_code(self.code, env)
        await interaction.followup.send(build_result_message(output, result, error), ephemeral=True)


# --- [ القسم الثالث: أحداث وأوامر البوت ] ---

@bot.event
async def on_ready():
    print(f"تم تشغيل البوت بنجاح باسم: {bot.user}")
    bot.add_view(ControlPanelView())  # تفعيل لوحة التحكم بشكل دائم حتى لو رست البوت


@bot.command(name="لوحة")
@commands.is_owner()
async def send_panel(ctx):
    """يرسل لوحة التحكم المليئة بالأزرار لإدارة البوت"""
    embed = discord.Embed(
        title="🎛️ لوحة التحكم المطلقة للبوت",
        description="اضغط على الأزرار أدناه للتحكم بالبوت وإدارته فوراً بدون كتابة أوامر.",
        color=discord.Color.dark_theme()
    )
    await ctx.send(embed=embed, view=ControlPanelView())


@bot.command(name="برمج")
@commands.is_owner()
async def execute_code(ctx, *, code: str):
    """يكتب ويشغل أكواد بايثون مباشرة من الشات"""
    env = {
        'bot': bot, 'ctx': ctx, 'channel': ctx.channel,
        'author': ctx.author, 'guild': ctx.guild,
        'discord': discord, 'os': os, 'sys': sys
    }
    output, result, error = await run_user_code(code, env)
    await ctx.send(build_result_message(output, result, error))


@bot.command(name="اصنع_زر")
@commands.is_owner()
async def create_button_command(ctx, *, code: str):
    """تكتب له كود، فيصنع لك زر داخل الشات يشغل هذا الكود عند الضغط عليه!"""
    view = DynamicCodeButton(clean_code_block(code), ctx.author.id)
    msg = await ctx.send("⚙️ **تم إنشاء زر برمجي مخصص لكودك بنجاح! اضغط أدناه لتشغيله:**", view=view)
    view.message = msg  # نخزن الرسالة عشان on_timeout يقدر يعدلها


# معالجة أخطاء الأوامر النصية (مثل استخدام شخص غير الأونر لأمر محمي)
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.NotOwner):
        await ctx.send("❌ هذا الأمر مخصص لمالك البوت فقط!")
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(f"❌ ناقص معطى مطلوب: `{error.param.name}`")
    else:
        print(f"خطأ غير متوقع: {error}")


# تشغيل البوت
if __name__ == "__main__":
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        print("❌ لم يتم ضبط متغير البيئة DISCORD_TOKEN. أضف التوكن قبل التشغيل.")
        sys.exit(1)
    bot.run(token)
