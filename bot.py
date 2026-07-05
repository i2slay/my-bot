import discord
from discord.ext import commands
import os
import requests

# إعدادات البوت الأساسية
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)

# رابط الـ Gist الخاص بأوامرك باللغة العربية
COMMANDS_URL = "https://gist.githubusercontent.com/i2slay/ee49043d01506a27d183c96eb0b6fcb1/raw/3c280625a9fcd1836e60069b15b8aa0119f0947a/gistfile1.txt"

@bot.event
async def on_ready():
    print(f"تم تشغيل البوت بنجاح باسم: {bot.user}")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    # ميزة التحديث التلقائي للأوامر من الرابط
    if message.content.startswith("/"):
        cmd_name = message.content[1:]
        try:
            response = requests.get(COMMANDS_URL)
            lines = response.text.split("\n")
            for line in lines:
                if ":" in line:
                    name, reply = line.split(":", 1)
                    if name.strip() == cmd_name:
                        await message.channel.send(reply.strip())
                        return
        except Exception as e:
            print(f"خطأ في قراءة الأوامر: {e}")

    await bot.process_commands(message)

# تشغيل البوت باستخدام التوكن السري من إعدادات Railway
bot.run(os.environ.get("DISCORD_TOKEN"))
