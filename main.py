from flask import Flask
from threading import Thread
import os

app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is running 24/7!"

def run_flask():
    app.run(host='0.0.0.0', port=8080)

Thread(target=run_flask).start()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
from discord import app_commands
import json
import base64
import time
import random
import os as os_module
import sys
import asyncio
import glob
from datetime import datetime, timedelta
import aiohttp
from typing import Optional, Dict, List, Any
from io import BytesIO

from bs4 import BeautifulSoup
from PIL import Image, ImageDraw, ImageFont

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
if not BOT_TOKEN:
    print("❌ Chưa set BOT_TOKEN trong Secrets!")
    sys.exit(1)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

user_tokens = {}
players = {}

NSFW_DIR = "nsfw_images"
if not os_module.path.exists(NSFW_DIR):
    os_module.makedirs(NSFW_DIR)

NSFW_CATEGORIES = {
    "waifu": os_module.path.join(NSFW_DIR, "waifu"), "neko": os_module.path.join(NSFW_DIR, "neko"),
    "trap": os_module.path.join(NSFW_DIR, "trap"), "blowjob": os_module.path.join(NSFW_DIR, "blowjob"),
    "hentai": os_module.path.join(NSFW_DIR, "hentai"), "boobs": os_module.path.join(NSFW_DIR, "boobs"),
    "pussy": os_module.path.join(NSFW_DIR, "pussy"), "anal": os_module.path.join(NSFW_DIR, "anal"),
    "gonewild": os_module.path.join(NSFW_DIR, "gonewild"),
}
for cat_dir in NSFW_CATEGORIES.values():
    if not os_module.path.exists(cat_dir): os_module.makedirs(cat_dir)

nsfw_web_cache = {}
cache_timestamp = {}

CLASSES = {
    "warrior": {"name":"⚔️ Chiến Binh","hp":150,"atk":20,"def":10,"skill":"Chém Mạnh","emoji":"⚔️","crit":10},
    "mage": {"name":"🔮 Pháp Sư","hp":100,"atk":30,"def":5,"skill":"Cầu Lửa","emoji":"🔮","crit":15},
    "archer": {"name":"🏹 Cung Thủ","hp":120,"atk":25,"def":7,"skill":"Tên Độc","emoji":"🏹","crit":20},
    "assassin": {"name":"🗡️ Sát Thủ","hp":110,"atk":35,"def":3,"skill":"Đâm Lén","emoji":"🗡️","crit":25},
    "tank": {"name":"🛡️ Tank","hp":200,"atk":10,"def":20,"skill":"Khiên Thép","emoji":"🛡️","crit":5},
}
ITEMS = [
    {"name":"Kiếm Sắt","type":"weapon","atk":10,"price":100,"emoji":"🗡️"},
    {"name":"Kiếm Vàng","type":"weapon","atk":25,"price":300,"emoji":"⚔️"},
    {"name":"Giáp Da","type":"armor","def":8,"price":100,"emoji":"🛡️"},
    {"name":"Giáp Sắt","type":"armor","def":20,"price":300,"emoji":"🛡️"},
    {"name":"Nhẫn Lửa","type":"ring","atk":15,"price":500,"emoji":"💍"},
    {"name":"Bùa Hộ Mệnh","type":"amulet","hp":50,"price":400,"emoji":"📿"},
    {"name":"Giày Bay","type":"boots","spd":10,"price":350,"emoji":"👢"},
    {"name":"Mũ Phù Thủy","type":"helmet","def":12,"price":250,"emoji":"🎩"},
]
WC_TEAMS = ["🇧🇷 Brazil","🇦🇷 Argentina","🇫🇷 Pháp","🇩🇪 Đức","🇪🇸 Tây Ban Nha","🇵🇹 Bồ Đào Nha","🇬🇧 Anh","🇳🇱 Hà Lan","🇮🇹 Ý","🇧🇪 Bỉ","🇺🇾 Uruguay","🇭🇷 Croatia","🇲🇦 Ma Rốc","🇯🇵 Nhật Bản","🇰🇷 Hàn Quốc","🇸🇳 Senegal"]

HEADERS_WEB = {
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36","Accept":"text/html,application/xhtml+xml","Accept-Language":"vi-VN,vi;q=0.9"
}

def create_embed(title, description="", color=discord.Color.blue(), fields=None, thumbnail=None, image=None, footer=None, timestamp=False):
    embed = discord.Embed(title=title, description=description, color=color, timestamp=datetime.now() if timestamp else None)
    if fields:
        for f in fields: embed.add_field(name=f.get("name",""), value=f.get("value",""), inline=f.get("inline",True))
    if thumbnail: embed.set_thumbnail(url=thumbnail)
    if image: embed.set_image(url=image)
    if footer: embed.set_footer(text=footer)
    return embed

def check_token(uid): return user_tokens.get(uid)
def check_player(uid): return players.get(uid)

async def scrape_anhanime4k():
    images=[]
    try:
        async with aiohttp.ClientSession() as session:
            page=random.randint(1,20)
            url=f"https://anhanime4k.com/hentai/page/{page}/" if page>1 else "https://anhanime4k.com/hentai/"
            async with session.get(url, headers={**HEADERS_WEB,"Referer":"https://anhanime4k.com/"}, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status==200:
                    html=await resp.text()
                    soup=BeautifulSoup(html,'lxml')
                    for img in soup.find_all('img'):
                        src=img.get('src') or img.get('data-src')
                        if src and ('wp-content' in src or 'uploads' in src):
                            if src.startswith('//'): src='https:'+src
                            if src.startswith('http') and any(e in src.lower() for e in ['.jpg','.png','.gif']): images.append(src)
    except Exception as e: print(f"[SCRAPE] {e}")
    return list(set(images))

async def scrape_quatvn():
    images=[]
    try:
        async with aiohttp.ClientSession() as session:
            for endpoint in ["https://quatvn.biz/","https://quatvn.biz/wp-json/wp/v2/media?per_page=20"]:
                try:
                    async with session.get(endpoint, headers={**HEADERS_WEB,"Referer":"https://quatvn.biz/"}, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                        if resp.status==200:
                            ct=resp.headers.get('Content-Type','')
                            if 'application/json' in ct:
                                data=await resp.json()
                                for item in data:
                                    if 'source_url' in item: images.append(item['source_url'])
                            else:
                                html=await resp.text()
                                soup=BeautifulSoup(html,'lxml')
                                for img in soup.find_all('img'):
                                    src=img.get('src') or img.get('data-src')
                                    if src and src.startswith('http'): images.append(src)
                except: pass
    except Exception as e: print(f"[SCRAPE] {e}")
    return list(set(images))

async def get_web_nsfw_url(category):
    cache_key="hentai" if category=="hentai" else "quatvn"
    if cache_key in nsfw_web_cache and cache_key in cache_timestamp:
        if time.time()-cache_timestamp[cache_key]<300:
            if nsfw_web_cache[cache_key]: return random.choice(nsfw_web_cache[cache_key])
    images=await scrape_anhanime4k() if category=="hentai" else await scrape_quatvn()
    if images:
        nsfw_web_cache[cache_key]=images
        cache_timestamp[cache_key]=time.time()
        return random.choice(images)
    return None

def get_local_nsfw_file(category):
    cat_dir=NSFW_CATEGORIES.get(category, os_module.path.join(NSFW_DIR,"waifu"))
    files=[]
    for ext in ["*.jpg","*.jpeg","*.png","*.gif","*.webp"]:
        files.extend(glob.glob(os_module.path.join(cat_dir,ext)))
    if files:
        fp=random.choice(files)
        return discord.File(fp), os_module.path.basename(fp)
    return None, None

@bot.event
async def on_ready():
    print(f"Bot Online: {bot.user}")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="/help | v3.0"))
    try: 
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands")
    except Exception as e: print(f"Sync error: {e}")

@bot.tree.command(name="help", description="Menu chinh")
async def help_command(interaction: discord.Interaction):
    embed=create_embed(title="DISCORD ALL-IN-ONE BOT v3.0", description="**Bot da nang**\n------------------------------------", color=discord.Color.purple(),
        fields=[
            {"name":"🛠️ Server Setup","value":"`/autosetup` `/autosetupsv` `/clear`","inline":False},
            {"name":"👤 Profile","value":"`/settoken` `/activity` `/spotify` `/avatar`","inline":False},
            {"name":"⚔️ Game","value":"`/create` `/profile` `/battle` `/shop` `/buy` `/leaderboard` `/daily`","inline":False},
            {"name":"🔞 NSFW","value":"`/nsfw waifu` `/nsfw neko` `/nsfw hentai` `/nsfw list`","inline":False},
        ])
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="nsfw", description="NSFW content (18+)")
@app_commands.describe(category="The loai")
@app_commands.choices(category=[
    app_commands.Choice(name="Waifu",value="waifu"),app_commands.Choice(name="Neko",value="neko"),
    app_commands.Choice(name="Hentai",value="hentai"),app_commands.Choice(name="Boobs",value="boobs"),
    app_commands.Choice(name="Pussy",value="pussy"),app_commands.Choice(name="Anal",value="anal"),
    app_commands.Choice(name="Blowjob",value="blowjob"),app_commands.Choice(name="Gonewild",value="gonewild"),
    app_commands.Choice(name="Danh sach",value="list"),
])
async def nsfw_command(interaction: discord.Interaction, category: str = "waifu"):
    if isinstance(interaction.channel, discord.TextChannel) and not interaction.channel.is_nsfw():
        await interaction.response.send_message("🔞 Chỉ dùng trong kênh NSFW!", ephemeral=True); return
    if category=="list":
        await interaction.response.send_message(embed=create_embed(title="NSFW LIST", description="Dùng /nsfw <the_loai>", color=discord.Color.dark_red())); return
    await interaction.response.defer()
    image_url=await get_web_nsfw_url(category)
    if image_url:
        await interaction.followup.send(embed=create_embed(title=f"🔞 {category.upper()}", description=f"By {interaction.user.mention}", color=discord.Color.dark_red(), image=image_url))
        return
    file, filename = get_local_nsfw_file(category)
    if file:
        await interaction.followup.send(embed=create_embed(title=f"🔞 {category.upper()}", description=f"Local: {filename}", color=discord.Color.dark_red()), file=file)
    else:
        await interaction.followup.send("❌ Không có ảnh!")

@bot.tree.command(name="clear", description="Xoa tin nhan")
@app_commands.describe(amount="So luong (1-100)")
@app_commands.default_permissions(manage_messages=True)
async def clear_command(interaction: discord.Interaction, amount: int = 10):
    if amount<1: amount=1
    if amount>100: amount=100
    await interaction.response.defer(ephemeral=True)
    try:
        deleted=await interaction.channel.purge(limit=amount)
        await interaction.followup.send(f"✅ Đã xóa {len(deleted)} tin nhắn!", ephemeral=True)
    except:
        await interaction.followup.send("❌ Thiếu quyền!", ephemeral=True)

@bot.tree.command(name="autosetup", description="Setup server co ban")
@app_commands.default_permissions(administrator=True)
async def autosetup_command(interaction: discord.Interaction):
    await interaction.response.send_message("✅ Dùng `/autosetupsv` để setup NSFW zone.", ephemeral=True)

@bot.tree.command(name="autosetupsv", description="Setup NSFW zone")
@app_commands.default_permissions(administrator=True)
async def autosetupsv_command(interaction: discord.Interaction):
    guild=interaction.guild
    if not guild: await interaction.response.send_message("❌ Server only!", ephemeral=True); return
    await interaction.response.defer(ephemeral=True)
    role=discord.utils.get(guild.roles, name="🔞 18+ Verified")
    if not role:
        try: role=await guild.create_role(name="🔞 18+ Verified", color=discord.Color.dark_red(), hoist=True, mentionable=True)
        except: await interaction.followup.send("❌ Thiếu quyền!", ephemeral=True); return
    cat=discord.utils.get(guild.categories, name="🔞 NSFW ZONE")
    if not cat:
        try:
            cat=await guild.create_category(name="🔞 NSFW ZONE")
            await cat.set_permissions(guild.default_role, view_channel=False)
        except: await interaction.followup.send("❌ Thiếu quyền!", ephemeral=True); return
    verify=discord.utils.get(guild.text_channels, name="🔞-xac-nhan-18")
    if not verify:
        try:
            verify=await guild.create_text_channel(name="🔞-xac-nhan-18", category=cat, topic="Xác nhận 18+")
            await verify.set_permissions(guild.default_role, view_channel=True, send_messages=False)
            await verify.set_permissions(role, view_channel=True, send_messages=False)
        except: pass
    if verify:
        try: await verify.purge(limit=10)
        except: pass
        class V(discord.ui.View):
            def __init__(self): super().__init__(timeout=None)
            @discord.ui.button(label="✅ Tôi trên 18 tuổi", style=discord.ButtonStyle.green, custom_id="v18")
            async def ok(self, bi, b):
                r=discord.utils.get(bi.guild.roles, name="🔞 18+ Verified")
                if r and r not in bi.user.roles:
                    try: await bi.user.add_roles(r); await bi.response.send_message("✅ Thành công!", ephemeral=True)
                    except: await bi.response.send_message("❌ Lỗi!", ephemeral=True)
                else: await bi.response.send_message("✅ Đã xác nhận!", ephemeral=True)
        await verify.send(embed=create_embed(title="🔞 XÁC NHẬN 18+", description="Nhấn nút bên dưới để xác nhận.", color=discord.Color.dark_red()), view=V())
    nsfw_ch=discord.utils.get(guild.text_channels, name="🔞-nsfw-18")
    if not nsfw_ch:
        try:
            nsfw_ch=await guild.create_text_channel(name="🔞-nsfw-18", category=cat, nsfw=True)
            await nsfw_ch.set_permissions(guild.default_role, view_channel=False)
            await nsfw_ch.set_permissions(role, view_channel=True, send_messages=True, embed_links=True)
        except: pass
    if nsfw_ch:
        try: await nsfw_ch.purge(limit=10)
        except: pass
        await nsfw_ch.send(embed=create_embed(title="🔞 KÊNH NSFW", description="Dùng `/nsfw waifu` `/nsfw hentai`...", color=discord.Color.dark_purple()))
    chat_ch=discord.utils.get(guild.text_channels, name="🔞-chat-18")
    if not chat_ch:
        try:
            chat_ch=await guild.create_text_channel(name="🔞-chat-18", category=cat)
            await chat_ch.set_permissions(guild.default_role, view_channel=False)
            await chat_ch.set_permissions(role, view_channel=True, send_messages=True)
        except: pass
    if chat_ch:
        try: await chat_ch.purge(limit=10)
        except: pass
        await chat_ch.send(embed=create_embed(title="💬 CHAT 18+", description="Chào mừng!", color=discord.Color.gold()))
    await interaction.followup.send("✅ NSFW Zone đã sẵn sàng!", ephemeral=True)

@bot.tree.command(name="meme", description="Meme")
async def meme(interaction: discord.Interaction):
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get("https://meme-api.com/gimme", timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status==200:
                    d=await r.json()
                    await interaction.response.send_message(embed=create_embed(title=d.get('title','Meme'), image=d.get('url',''), color=discord.Color.random()))
                else: await interaction.response.send_message("❌ Lỗi!")
    except: await interaction.response.send_message("😂 No meme!")

@bot.tree.command(name="dice", description="Tung xuc xac")
async def dice(interaction: discord.Interaction): await interaction.response.send_message(f"🎲 **{random.randint(1,6)}**")

@bot.tree.command(name="coin", description="Tung dong xu")
async def coin(interaction: discord.Interaction): await interaction.response.send_message(f"🪙 **{'Ngua' if random.random()<0.5 else 'Sap'}**")

@bot.tree.command(name="hack", description="Hack fake")
async def hack(interaction: discord.Interaction, user: discord.User):
    await interaction.response.send_message(f"💻 HACKING {user.name}...")
    await asyncio.sleep(2)
    await interaction.channel.send(f"🔓 Email: {user.name.lower()}{random.randint(1,99)}@gmail.com\n🔑 Pass: ***\n💀 Done! (jk)")

@bot.tree.command(name="ship", description="Ship 2 nguoi")
async def ship(interaction: discord.Interaction, user1: discord.User, user2: discord.User):
    r=random.randint(0,100)
    bar="█"*(r//10)+"░"*(10-r//10)
    await interaction.response.send_message(f"💕 **{user1.name}** x **{user2.name}**\n❤️ [{bar}] **{r}%**")

if __name__ == "__main__":
    try: bot.run(BOT_TOKEN)
    except Exception as e: print(f"Loi: {e}")