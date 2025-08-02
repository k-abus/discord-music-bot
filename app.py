#!/usr/bin/env python3
import discord
from discord.ext import commands
import yt_dlp
import asyncio
import os
import logging

# إعداد الـ logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.voice_states = True

bot = commands.Bot(command_prefix="", intents=intents)

# متغيرات عامة
repeat = False
paused = False
current_url = None
voice_client = None

YDL_OPTIONS = {
    'format': 'bestaudio',
    'noplaylist': 'True',
    'no_warnings': True,
    'quiet': True,
    'extract_flat': False,
    'ignoreerrors': False,
    'nocheckcertificate': True,
    'geo_bypass': True,
    'geo_bypass_country': 'US',
    'geo_bypass_ip_block': '1.1.1.1',
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    },
    'socket_timeout': 30,
    'retries': 3
}

FFMPEG_OPTIONS = {
    'options': '-vn',
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5'
}

def get_audio_source(url):
    """الحصول على مصدر الصوت"""
    try:
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
            return info['url']
    except Exception as e:
        logger.error(f"Error getting audio source: {e}")
        return None

async def join_and_play(message, url):
    """الانضمام للروم وتشغيل الأغنية"""
    global voice_client, current_url
    
    try:
        # التحقق من أن المستخدم في روم صوتي
        if not message.author.voice:
            await message.channel.send("🎧 لازم تدخل روم صوتي أولاً.")
            return
        
        channel = message.author.voice.channel
        current_url = url
        
        # الانضمام للروم
        if message.guild.voice_client is None:
            voice_client = await channel.connect()
            await message.channel.send(f"✅ انضممت لروم: {channel.name}")
        else:
            voice_client = message.guild.voice_client
            await voice_client.move_to(channel)
            await message.channel.send(f"✅ انتقلت إلى روم: {channel.name}")
        
        # الحصول على مصدر الصوت
        audio_url = get_audio_source(url)
        if not audio_url:
            await message.channel.send("❌ ما قدرت أحصل على الصوت.")
            return
        
        # تشغيل الصوت
        source = discord.FFmpegPCMAudio(audio_url, **FFMPEG_OPTIONS)
        
        def after_playing(error):
            if error:
                logger.error(f"Error after playing: {error}")
            if repeat and current_url:
                asyncio.run_coroutine_threadsafe(join_and_play(message, current_url), bot.loop)
            else:
                asyncio.run_coroutine_threadsafe(voice_client.disconnect(), bot.loop)
        
        voice_client.play(source, after=after_playing)
        await message.channel.send("🎵 جاري تشغيل الأغنية...")
        
    except Exception as e:
        logger.error(f"Error in join_and_play: {e}")
        await message.channel.send("❌ حدث خطأ أثناء تشغيل الأغنية.")

@bot.event
async def on_ready():
    """Bot ready event"""
    logger.info(f"✅ البوت جاهز! اسمه: {bot.user.name}")
    logger.info(f"🆔 Bot ID: {bot.user.id}")
    logger.info(f"📊 عدد السيرفرات: {len(bot.guilds)}")
    
    for guild in bot.guilds:
        logger.info(f"🏠 السيرفر: {guild.name}")

@bot.event
async def on_message(message):
    global repeat, paused, voice_client, current_url

    if message.author.bot:
        return

    content = message.content.strip()

    try:
        if content.startswith("ش "):  # شغل
            query = content[2:]
            await message.channel.send(f"🎵 يتم البحث عن: {query}")
            await join_and_play(message, query)

        elif content == "قف":
            if message.guild.voice_client:
                await message.guild.voice_client.disconnect()
                await message.channel.send("⏹️ تم الإيقاف والخروج من الروم.")
            else:
                await message.channel.send("❌ البوت مش في روم صوتي.")

        elif content == "كرر":
            repeat = True
            await message.channel.send("🔁 تم تفعيل التكرار.")

        elif content == "ا":
            repeat = False
            await message.channel.send("🚫 تم إلغاء التكرار.")

        elif content == "شوي":
            if message.guild.voice_client and message.guild.voice_client.is_playing():
                message.guild.voice_client.pause()
                paused = True
                await message.channel.send("⏸️ تم الإيقاف المؤقت.")
            else:
                await message.channel.send("❌ لا يوجد شيء شغال.")

        elif content == "كمل":
            if message.guild.voice_client and paused:
                message.guild.voice_client.resume()
                paused = False
                await message.channel.send("▶️ تم الاستئناف.")
            else:
                await message.channel.send("❌ لا يوجد شيء موقوف مؤقت.")

        elif content == "دخل":
            if not message.author.voice:
                await message.channel.send("🎧 لازم تدخل روم صوتي أولاً.")
                return
            
            channel = message.author.voice.channel
            if message.guild.voice_client is None:
                voice_client = await channel.connect()
                await message.channel.send(f"✅ انضممت لروم: {channel.name}")
            else:
                await message.guild.voice_client.move_to(channel)
                await message.channel.send(f"✅ انتقلت إلى روم: {channel.name}")

        elif content == "اخرج":
            if message.guild.voice_client:
                await message.guild.voice_client.disconnect()
                await message.channel.send("👋 خرجت من الروم الصوتي.")
            else:
                await message.channel.send("❌ البوت مش في روم صوتي.")

        elif content == "حالة":
            voice_status = "في روم صوتي" if message.guild.voice_client and message.guild.voice_client.is_connected() else "ليس في روم صوتي"
            
            embed = discord.Embed(
                title="🤖 حالة البوت",
                description="معلومات البوت الحالية:",
                color=0x00ff00
            )
            embed.add_field(name="🟢 الحالة", value="متصل وعامل", inline=True)
            embed.add_field(name="📊 السيرفرات", value=len(bot.guilds), inline=True)
            embed.add_field(name="🎵 التكرار", value="مفعل" if repeat else "غير مفعل", inline=True)
            embed.add_field(name="🎧 الروم الصوتي", value=voice_status, inline=True)
            
            await message.channel.send(embed=embed)

        elif content == "مساعدة":
            embed = discord.Embed(
                title="🎵 أوامر البوت",
                description="قائمة الأوامر المتاحة:",
                color=0x00ff00
            )
            embed.add_field(name="ش [رابط]", value="تشغيل أغنية", inline=False)
            embed.add_field(name="دخل", value="انضم للروم الصوتي", inline=False)
            embed.add_field(name="اخرج", value="اخرج من الروم الصوتي", inline=False)
            embed.add_field(name="قف", value="إيقاف الأغنية والخروج", inline=False)
            embed.add_field(name="كرر", value="تفعيل التكرار", inline=False)
            embed.add_field(name="ا", value="إلغاء التكرار", inline=False)
            embed.add_field(name="شوي", value="إيقاف مؤقت", inline=False)
            embed.add_field(name="كمل", value="استئناف", inline=False)
            embed.add_field(name="حالة", value="عرض حالة البوت", inline=False)
            embed.add_field(name="مساعدة", value="عرض هذه القائمة", inline=False)
            
            await message.channel.send(embed=embed)

    except Exception as e:
        logger.error(f"Error in on_message: {e}")
        await message.channel.send("❌ حدث خطأ في معالجة الأمر.")

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        logger.error("❌ خطأ: DISCORD_TOKEN غير محدد")
        exit(1)
    
    logger.info("🚀 بدء تشغيل البوت...")
    bot.run(token) 