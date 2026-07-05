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

# --- [ القسم الأول: كلاس لوحة التحكم بالأزرار الثابتة ] ---
class ControlPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # الأزرار تعمل دائماً ولا تنتهي صلاحيتها

    @discord.ui.button(label="📊 إحصائيات السيرفرات", style=discord.ButtonStyle.primary, custom_id="stats_btn")
    async def stats_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await bot.is_owner(interaction.user):
            return await interaction.response.send_message("❌ عذراً، هذه اللوحة مخصصة لمالك البوت فقط!", ephemeral=True)
            
        guilds_text = "\n".join([f"• {g.name} ({g.member_count} عضو)" for g in bot.guilds])
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
            
        channel = await interaction.guild.create_text_channel(name="روم-تحكم-سريع")
        await interaction.response.send_message(f"✅ تم إنشاء الروم بنجاح: {channel.mention}", ephemeral=True)

    @discord.ui.button(label="🛑 إطفاء البوت", style=discord.ButtonStyle.danger, custom_id="shutdown_btn")
    async def shutdown_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await bot.is_owner(interaction.user):
            return await interaction.response.send_message("❌ لا تملك صلاحية!", ephemeral=True)
            
        await interaction.response.send_message("👋 جاري إغلاق البوت وتأمين الملفات...", ephemeral=True)
        await bot.close()


# --- [ القسم الثاني: كلاس صناعة الأزرار البرمجية الديناميكية ] ---
class DynamicCodeButton(discord.ui.View):
    def __init__(self, code: str, owner_id: int):
        super().__init__(timeout=600) # صلاحية الزر تنتهي بعد 10 دقائق للأمان
        self.code = code
        self.owner_id = owner_id

    @discord.ui.button(label="🚀 تشغيل الكود البرمجي", style=discord.ButtonStyle.primary)
    async def run_dynamic_code(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.owner_id:
            return await interaction.response.send_message("❌ هذا الزر مخصص لمالك الكود فقط!", ephemeral=True)
        
        await interaction.response.defer(ephemeral=True)
        str_obj = io.StringIO()
        
        env = {
            'bot': bot,
            'ctx': await bot.get_context(interaction.message),
            'interaction': interaction,
            'channel': interaction.channel,
            'author': interaction.user,
            'guild': interaction.guild,
            'discord': discord,
            'os': os,
            'sys': sys
        }
        env['print'] = lambda *args, **kwargs: print(*args, file=str_obj, **kwargs)

        formatted_code = "\n".join(f"    {line}" for line in self.code.splitlines())
        exec_text = f"async def __ex(interaction):\n{formatted_code}"
        
        try:
            exec(exec_text, env)
            with contextlib.redirect_stdout(str_obj):
                result = await env["__ex"](interaction)
                
            output = str_obj.getvalue()
            
            if output:
                await interaction.followup.send(f"✅ **تم التنفيذ بنجاح! المخرجات:**\n```py\n{output}\n```", ephemeral=True)
            elif result is not None:
                await interaction.followup.send(f"✅ **تم التنفيذ بنجاح! النتيجة:**\n```py\n{result}\n```", ephemeral=True)
            else:
                await interaction.followup.send("✅ **تم تشغيل كود الأزرار بنجاح في الخلفية!**", ephemeral=True)
                
        except Exception:
            error = traceback.format_exc()
            # هنا تم إصلاح الخطأ المذكور في ملف image_1b0a79.png ليكون متصل وسليم
            await interaction.followup.send(f"❌ **حدث خطأ أثناء التنفيذ:**\n```py\n{error}\n```", ephemeral=True)


# --- [ القسم الثالث: أحداث وأوامر البوت ] ---

@bot.event
async def on_ready():
    print(f"تم تشغيل البوت بنجاح باسم: {bot.user}")
    # تفعيل لوحة التحكم بشكل دائم حتى لو رست البوت
    bot.add_view(ControlPanelView())

# 1. أمر استدعاء لوحة التحكم بالأزرار الجاهزة
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

# 2. أمر البرمجة والتنفيذ المباشر
@bot.command(name="برمج")
@commands.is_owner()
async def execute_code(ctx, *, code: str):
    """يكتب ويشغل أكواد بايثون مباشرة من الشات"""
    if code.startswith("```") and code.endswith("```"):
        code = code.strip("`").strip()
        if code.startswith("py\n"): code = code[3:]
        elif code.startswith("python\n"): code = code[7:]

    str_obj = io.StringIO()
    env = {
        'bot': bot, 'ctx': ctx, 'channel': ctx.channel, 
        'author': ctx.author, 'guild': ctx.guild, 
        'discord': discord, 'os': os, 'sys': sys
    }
    env['print'] = lambda *args, **kwargs: print(*args, file=str_obj, **kwargs)

    formatted_code = "\n".join(f"    {line}" for line in code.splitlines())
    exec_text = f"async def __ex(ctx):\n{formatted_code}"
    
    try:
        exec(exec_text, env)
        with contextlib.redirect_stdout(str_obj):
            result = await env["__ex"](ctx)
            
        output = str_obj.getvalue()
        if output:
            await ctx.send(f"✅ **تم التنفيذ! المخرجات:**\n```py\n{output}\n```")
        elif result is not None:
            await ctx.send(f"✅ **تم التنفيذ! النتيجة المسترجعة:**\n```py\n{result}\n```")
        else:
            await ctx.send("✅ **تم تشغيل الكود بنجاح في الخلفية!**")
            
    except Exception:
        error = traceback.format_exc()
        await ctx.send(f"❌ **حدث خطأ أثناء التنفيذ:**\n```py\n{error}\n```")

# 3. أمر تحويل الأكواد إلى أزرار تفاعلية
@bot.command(name="اصنع_زر")
@commands.is_owner()
async def create_button_command(ctx, *, code: str):
    """تكتب له كود، فيصنع لك زر داخل الشات يشغل هذا الكود عند الضغط عليه!"""
    if code.startswith("```") and code.endswith("```"):
        code = code.strip("`").strip()
        if code.startswith("py\n"): code = code[3:]
        elif code.startswith("python\n"): code = code[7:]

    view = DynamicCodeButton(code, ctx.author.id)
    await ctx.send("⚙️ **تم إنشاء زر برمجي مخصص لكودك بنجاح! اضغط أدناه لتشغيله:**", view=view)


# تشغيل البوت
bot.run(os.environ.get("DISCORD_TOKEN"))
