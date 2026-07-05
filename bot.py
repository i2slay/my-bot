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
            await interaction.followup.send(f"❌ **حدث خطأ أثناء التنفيذ:**\n```py\n{error}\n
