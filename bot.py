import discord
from discord.ext import commands
import os
import requests

# إعداد الصلاحيات (Intents) للبوت
intents = discord.Intents.default()
intents.message_content = True

# تحديد بادئة الأوامر (Prefix)
bot = commands.Bot(command_prefix="/", intents=intents)

@bot.event
async def on_ready():
    print(f'تم تشغيل البوت بنجاح باسم: {bot.user}')

# جلب التوكن بأمان من إعدادات الاستضافة
TOKEN = os.getenv("DISCORD_TOKEN")

if TOKEN:
    bot.run(TOKEN)
else:
    print("خطأ: لم يتم العثور على DISCORD_TOKEN في إعدادات البيئة (Environment Variables)!")
