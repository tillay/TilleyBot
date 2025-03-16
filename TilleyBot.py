import discord, asyncio, random, os, re, requests, base64, subprocess, http, json, csv, time
from datetime import datetime
from discord.ext import commands
from hashlib import sha256
from html import unescape
from openai import OpenAI

try:
    from Cryptodome.Util.Padding import pad, unpad
    from Cryptodome.Cipher import AES
except ModuleNotFoundError:
    from Crypto.Util.Padding import pad, unpad
    from Crypto.Cipher import AES

user_gmt_offset = -6
bot_token_file = "~/bot_tokens/TilleyBot.token"
user_token_file = "~/bot_tokens/tillay8.token"
ai_token_file = "~/bot_tokens/deepseek.token"

key_file = "/tmp/key"

bot = commands.Bot("!", intents=discord.Intents.none())

def get_bot_token():
    with open(os.path.expanduser(bot_token_file), 'r') as f:
        return f.readline().strip()

def get_passwd():
    with open(os.path.expanduser(key_file), 'r') as f:
        return f.readline().strip()

def get_user_token():
    with open(os.path.expanduser(user_token_file), 'r') as f:
        return f.readline().strip()

def get_ai_token():
    with open(os.path.expanduser(ai_token_file), 'r') as f:
        return f.readline().strip()

header_data = {
    "Content-Type": "application/json",
    "Authorization": get_user_token()
}

client = OpenAI(api_key=get_ai_token(), base_url="https://api.deepseek.com")

def send_user_message(channel_id, message_content):
    conn = http.client.HTTPSConnection("discord.com", 443)
    message_data = json.dumps({
        "content": message_content,
        "tts": False
    })
    conn.request("POST", f"/api/v10/channels/{channel_id}/messages", message_data, header_data)
    response = conn.getresponse()
    if response.status == 200:
        message_info = json.loads(response.read().decode())
        return message_info['id']
    else:
        print(f"Failed to send message: {response.status} {response.reason}")
        return None


def send_and_delete(channel_id, message_content, delay = 0):
    message_id = send_user_message(channel_id, message_content)
    if delay: time.sleep(delay)
    if message_id:
        delete_url = f"https://discord.com/api/v10/channels/{channel_id}/messages/{message_id}"
        requests.delete(delete_url, headers=header_data)

def deepseek_query(prompt, context):
    client = OpenAI(api_key=get_ai_token(), base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": context},
            {"role": "user", "content": prompt},
        ],
        stream=False
    )
    return response.choices[0].message.content

def get_most_recent_message(channel_id):
    conn = http.client.HTTPSConnection("discord.com", 443)
    conn.request("GET", f"/api/v10/channels/{channel_id}/messages?limit=1", headers=header_data)
    response = conn.getresponse()
    if 199 < response.status < 300:
        message = json.loads(response.read().decode())
        return message[0]['content']
    else:
        return None

def send_file(channel_id, file_path):
    conn = http.client.HTTPSConnection("discord.com", 443)
    with open(file_path, 'rb') as file:
        file_data = file.read()
    boundary = '----WebKitFormBoundary' + ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=16))
    body = (
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="file"; filename="{os.path.basename(file_path)}"\r\n'
        'Content-Type: application/octet-stream\r\n\r\n'
    ).encode('utf-8') + file_data + f'\r\n--{boundary}--\r\n'.encode('utf-8')
    headers = {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Authorization": header_data["Authorization"]
    }
    conn.request("POST", f"/api/v10/channels/{channel_id}/messages", body, headers)

def channel_name_from_id(channel_id):
    conn = http.client.HTTPSConnection("discord.com", 443)
    conn.request("GET", f"/api/v10/channels/{channel_id}", headers=header_data)
    response = conn.getresponse()
    data = response.read().decode('utf-8')
    if response.status == 200:
        channel_data = json.loads(data)
        guild_id = channel_data.get("guild_id")
        channel_name = channel_data.get("name")
        conn.request("GET", f"/api/v10/guilds/{guild_id}", headers=header_data)
        guild_response = conn.getresponse()
        guild_data = guild_response.read().decode('utf-8')
        if guild_response.status == 200:
            guild_info = json.loads(guild_data)
            guild_name = guild_info.get("name")
            return [guild_name, channel_name]
        else:
            return None
    else:
        return None

def get_catgirl_link():
    url = "https://nekos.moe/api/v1/random/image"
    response = requests.get(url, params={'nsfw': False})
    data = response.json()
    image_id = data['images'][0]['id']
    return f"https://nekos.moe/image/{image_id}"

def translator(inp, to):
    try:
        encoded_input = requests.utils.quote(inp.strip())
        url = f"https://translate.google.com/m?sl=auto&tl={to}&hl=en&q={encoded_input}"
        response = requests.get(url)
        match = re.search(r'class="result-container">([^<]*)</div>', response.text)
        
        if match:
            translated_text = match.group(1)
            return unescape(translated_text)
        else:
            return "Translation failed"
    except Exception as e:
        return "Translation failed"

def tcrypt(plaintext, passphrase):
    key, iv = sha256((passphrase).encode()).digest(), os.urandom(AES.block_size)
    return base64.b64encode(iv + AES.new(key, AES.MODE_CBC, iv).encrypt(pad(plaintext.encode(), AES.block_size))).decode()

def tdcrypt(ciphertext, passphrase):
    try:
        decoded = base64.b64decode(ciphertext)
        return unpad(AES.new(sha256((passphrase).encode()).digest(), AES.MODE_CBC, decoded[:AES.block_size]).decrypt(decoded[AES.block_size:]), AES.block_size).decode()
    except (ValueError, KeyError): return None

def execute_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            output = result.stdout
        else:
            output = result.stderr
        return f"```ansi\n{output}\n```"
    except Exception as e:
        return f"An error occurred: {str(e)}"

def generate_task_id():
    return random.randint(1000, 9999)

repeat_tasks = {}

@bot.tree.command(name="echo", description="Send a message as tillay8")
async def echo(interaction: discord.Interaction, tosay: str, channel_id: str = None):
    channel_id = interaction.channel.id if not channel_id else int(channel_id)
    await interaction.response.send_message("Echoing", ephemeral=True)
    send_user_message(channel_id, tosay)

@bot.tree.command(name="test", description="Is bot alive?")
async def test(interaction: discord.Interaction):
    await interaction.response.send_message(interaction.channel, ephemeral=True)

@bot.tree.command(name="maze", description="Generate maze")
async def maze(interaction: discord.Interaction, size: int, channel_id: str = None):
    channel_id = interaction.channel.id if not channel_id else int(channel_id)
    await interaction.response.send_message("Generating maze", ephemeral=True)
    send_user_message(channel_id, f"-maze {size}")
    await asyncio.to_thread(os.system, f"./maze {size} maze.png")
    send_file(channel_id, "./maze.png")

@bot.tree.command(name="repeat", description="Repeat a message in a channel at a specified interval")
async def repeat(interaction: discord.Interaction, interval: float, message: str):
    try:
        channel_id = interaction.channel.id
        if channel_id in repeat_tasks:
            repeat_tasks[channel_id].cancel()

        up_pattern = re.compile(r"<up(\d+)>")
        down_pattern = re.compile(r"<down(\d+)>")
        second_pattern = re.compile(r"<second>")

        up_counter = int(up_pattern.search(message).group(1)) if up_pattern.search(message) else None
        down_counter = int(down_pattern.search(message).group(1)) if down_pattern.search(message) else None
        second_counter = 1 if second_pattern.search(message) else None

        async def repeat_task():
            nonlocal up_counter, down_counter, second_counter
            while True:
                updated_message = message
                if up_counter is not None:
                    updated_message = up_pattern.sub(str(up_counter), updated_message)
                    up_counter += 1
                if down_counter is not None:
                    updated_message = down_pattern.sub(str(down_counter), updated_message)
                    down_counter -= 1
                    if down_counter < 0:
                        break
                if second_counter is not None:
                    updated_message = second_pattern.sub(str(second_counter), updated_message)
                    second_counter += interval
                    if str(second_counter).endswith(".0"):
                        second_counter = int(second_counter)

                send_user_message(channel_id, updated_message)
                await asyncio.sleep(interval)

        task = asyncio.create_task(repeat_task())
        repeat_tasks[channel_id] = task

        await interaction.response.send_message("Started repeat in this channel.", ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"Failed to start repeating task: {e}", ephemeral=True)

@bot.tree.command(name="stop-repeat", description="Stop the repeating task in this channel")
async def stop_repeat(interaction: discord.Interaction):
    try:
        channel_id = interaction.channel.id
        if channel_id in repeat_tasks:
            repeat_tasks[channel_id].cancel()
            del repeat_tasks[channel_id]
            await interaction.response.send_message("Stopped repeat in this channel.", ephemeral=True)
        else:
            await interaction.response.send_message("No repeat task running in this channel.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Failed to stop repeating task: {e}", ephemeral=True)

@bot.tree.command(name="daily-maze", description="Send a daily maze at a specific time")
async def daily_maze(interaction: discord.Interaction, size: int, hour: int, minute: int, startnum: int):
    try:
        channel_id = interaction.channel.id
        task_id = generate_task_id()
        while task_id in repeat_tasks:
            task_id = generate_task_id()

        async def repeat_task():
            i = startnum
            while True:
                now = datetime.now()
                if now.hour == hour and now.minute == minute:
                    await asyncio.to_thread(os.system, f"./maze {size} maze.png")
                    send_user_message(channel_id, f"daily maze #{i}")
                    send_file(channel_id, "./maze.png")
                    i += 1
                await asyncio.sleep(60)

        task = asyncio.create_task(repeat_task())
        repeat_tasks[task_id] = (task, channel_id)
        await interaction.response.send_message(f"Started daily maze: {task_id}", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Failed to start daily maze: {e}", ephemeral=True)

@bot.tree.command(name="pfp", description="Send pfp of a user")
async def pfp(interaction: discord.Interaction, user: str):
    try:
        member = await bot.fetch_user(int(user))
    except discord.NotFound:
        await interaction.response.send_message("User not found.", ephemeral=True)
        return
    await interaction.response.send_message(member.display_avatar.url, ephemeral=True)

@bot.tree.command(name="printas", description="Say something as the bot")
async def printas(interaction: discord.Interaction, message: str):
    await interaction.response.send_message(message)

@bot.tree.command(name="encrypt", description="encrypt a message using server password")
async def encrypt(interaction: discord.Interaction, message: str):
    await interaction.response.send_message(f"&&{tcrypt(message, get_passwd())}", ephemeral=True)

@bot.tree.command(name="decrypt", description="decrypt a message using server password")
async def decrypt(interaction: discord.Interaction, encrypted: str):
    await interaction.response.send_message(tdcrypt(encrypted[2:], get_passwd()), ephemeral=True)

@bot.tree.command(name="runcommand", description="Run a command in the terminal and get the output")
async def runcommand(interaction: discord.Interaction, command: str):
    await interaction.response.send_message(execute_command(command), ephemeral=True)

@bot.tree.command(name="scramble", description="scramble text")
async def scramble(interaction: discord.Interaction, message: str):
    substitutions = [('a', 'а'), ('e', 'е'), ('i', 'і'), ('p', 'р'),
                     ('s', 'ѕ'), ('c', 'с'), ('o', 'о'), ('x', 'х'),
                     ('y', 'у')]
    for old, new in substitutions:
        message = message.replace(old, new)
    message = '﻿'.join(list(message))
    await interaction.response.send_message(message, ephemeral=True)

@bot.tree.command(name="translate", description="translate messages to english")
async def translate(interaction: discord.Interaction, message: str, lang: str = "en"):
    await interaction.response.send_message(translator(message, lang), ephemeral=True)
        
@bot.tree.command(name="channelinfo", description="get info from channel id")
async def channelinfo(interaction: discord.Interaction, id: str):
    await interaction.response.send_message(channel_name_from_id(id))

@bot.tree.command(name="catgirl", description="send a catgirl")
async def catgirl(interaction: discord.Interaction):
    await interaction.response.send_message(get_catgirl_link(), ephemeral=False)

@bot.tree.command(name="diddy", description="generate a diddy")
async def diddy(interaction: discord.Interaction):
    await interaction.response.send_message("https://www.lafocusnews.com/wp-content/uploads/2023/08/Diddy-681x1024.jpg", ephemeral=False)

def get_timezone_name(offset):
    gmt_offset_names = [
        (-12, "International Date Line West (IDLW)"),
        (-11, "Niue Time (NUT)"),
        (-10, "Hawaii-Aleutian Time (HAT)"),
        (-9, "Alaska Time (AKT)"),
        (-8, "Pacific Time (PT)"),
        (-7, "Mountain Time (MT)"),
        (-6, "Central Time (CT)"),
        (-5, "Eastern Time (ET)"),
        (-4, "Atlantic Time (AT)"),
        (-3, "Argentina Time (ART)"),
        (-2, "South Georgia Time (SGT)"),
        (-1, "Azores Time (AZOT)"),
        (0, "Greenwich Mean Time (GMT)"),
        (1, "Central European Time (CET)"),
        (2, "Eastern European Time (EET)"),
        (3, "Moscow Time (MSK)"),
        (4, "Gulf Standard Time (GST)"),
        (5, "Pakistan Standard Time (PKT)"),
        (6, "Bangladesh Time (BST)"),
        (7, "Indochina Time (ICT)"),
        (8, "China Standard Time (CST)"),
        (9, "Japan Standard Time (JST)"),
        (10, "Australian Eastern Time (AET)"),
        (11, "Solomon Islands Time (SBT)"),
        (12, "New Zealand Standard Time (NZST)")
    ]
    for gmt_offset, name in gmt_offset_names:
        if gmt_offset == offset:
            return name

@bot.tree.command(name="timezones", description="calculate timezones")
async def timezones(interaction: discord.Interaction, their_time: int = None, your_time: int = None, offset: int = None):
    now = datetime.now()
    if your_time and their_time:
        offset = (their_time - your_time) % 24
        if offset > 12:
            offset -= 24
        offset_total = offset + user_gmt_offset
        gmt_sign = "+" if offset_total > 0 else ""
        mdt_sign = "+" if offset > 0 else ""
        timezone_name = get_timezone_name(offset_total % 12)
        await interaction.response.send_message(
            f"GMT{gmt_sign}{offset_total}, MDT{mdt_sign}{offset}, {timezone_name}",
            ephemeral=True
        )
    elif their_time and offset:
        your_time = (their_time - offset) % 24
        await interaction.response.send_message(f"Your time is: {your_time}", ephemeral=True)
    elif offset:
        their_hour = (now.hour + offset - user_gmt_offset) % 24
        await interaction.response.send_message(
            f"Their time is: {their_hour}:{'0' if len(str(now.minute)) == 1 else ''}{now.minute}",
            ephemeral=True
        )
    else:
        await interaction.response.send_message("http://www.hoelaatishetnuprecies.nl/wp-content/uploads/2015/03/world-timezone-large.jpg")

@bot.tree.command(name="downloader", description="download messages")
async def downloader(interaction: discord.Interaction, num: int):
    filename = "messages.txt"
    channel_id = interaction.channel.id
    total_messages_to_fetch = num
    messages_fetched = 0
    before_id = None
    await interaction.response.send_message(f"Downloading {num} messages from {interaction.channel.id}", ephemeral=True)
    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        while messages_fetched < total_messages_to_fetch:
            remaining_messages = total_messages_to_fetch - messages_fetched
            current_batch_size = min(100, remaining_messages)
            url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
            params = {"limit": current_batch_size}
            if before_id:
                params["before"] = before_id
            response = requests.get(url, headers=header_data, params=params)
            if response.status_code == 200:
                messages = response.json()
                if messages:
                    for message in messages:
                        writer.writerow([message['content']])
                    messages_fetched += len(messages)
                    before_id = messages[-1]["id"]
                else:
                    break
            else:
                break
    with open(filename, mode='r', encoding='utf-8') as file:
        lines = file.readlines()
    with open(filename, mode='w', encoding='utf-8') as file:
        file.writelines(reversed(lines))
    await interaction.followup.send(file=discord.File(filename), ephemeral=True)

@bot.tree.command(name="bots", description="check active bots")
async def bots(interaction: discord.Interaction, kill: int = 0):
    if kill:
        await interaction.response.send_message(execute_command(f"kill {kill}"), ephemeral=True)
    else:
        await interaction.response.send_message(execute_command("ps aux | grep python3 | head -n -2 | awk '{print $2, $12, $13, $14}'"), ephemeral=True)

@bot.tree.command(name="info", description="display info about the bot")
async def info(interaction: discord.Interaction):
    await interaction.response.send_message(
    "I am tilley bot! FAQ:\n\n"
    "What do I do?\n"
    "- I'm a general purpose utility bot\n"
    "Can everyone use me?\n"
    "- No. This is a private bot only tilley can use.\n"
    "- However, source code is [public](<https://github.com/tillay8/TilleyBot>)\n"
    "Do I violate TOS?\n"
    "- no comment\n"
    "Who is my profile picture?\n"
    "- [anzu](<https://gup.fandom.com/wiki/Anzu_Kadotani>) from girls und panzer\n"
    )
    
@bot.tree.command(name="password", description="set password for encryption")
async def password(interaction: discord.Interaction, password: str):
    with open(os.path.expanduser(key_file), 'w') as f:
        f.write(password)
    await interaction.response.send_message("password set!", ephemeral=True)

@bot.tree.command(name="date", description="make fancy date embed")
async def date(interaction: discord.Interaction, month: int = None, day: int = None, hour: int = None, minute: int = None):
    now = datetime.now()
    target_month = month if month is not None else now.month
    target_day = day if day is not None else now.day
    target_hour = hour if hour is not None else now.hour
    target_minute = minute if minute is not None else now.minute
    try:
        target_date = datetime(now.year, target_month, target_day, target_hour, target_minute)
        unix_time = int(target_date.timestamp())
        fancy_date = f"<t:{unix_time}:F>"
        await interaction.response.send_message(f"{fancy_date}```{fancy_date}```", ephemeral=True)
    except ValueError:
        await interaction.response.send_message("invalid data", ephemeral=True)

@bot.tree.command(name="hidetext", description="hide text behind other text")
async def hidetext(interaction: discord.Interaction, showntext: str, hidetext: str):
    spoiler = "||​" * 400
    await interaction.response.send_message(
        f"```{showntext}  {spoiler} _ _ _ _ _ _  {hidetext}```",
        ephemeral=True
    )

@bot.tree.command(name="ai_tilley", description="make tilley an ai")
async def ai_tilley(interaction: discord.Interaction):
    context = "You are tilley8, a discord user. You like cats and Linux. Respond to this prompt very concisely, only 20 words or less. do not include emojis and be relatively serious"
    prompt = get_most_recent_message(interaction.channel.id)
    await interaction.response.send_message(f"generating message with prompt: {prompt}", ephemeral=True)
    send_user_message(interaction.channel.id, deepseek_query(prompt, context))

@bot.tree.command(name="deepseek", description="get response from deepseek")
async def deepseek(interaction: discord.Interaction, prompt: str):
    await interaction.response.send_message(prompt)
    await interaction.followup.send(deepseek_query(prompt, "You are a discord bot called Tilley Bot who answers questions in a discord server. do not include emojis and be relatively serious"))

@bot.tree.command(name="ghost_ping", description="send and delete message fast")
async def ghost_ping(interaction: discord.Interaction, message: str, sniper: str=None, delay: int = None):
    await interaction.response.send_message("you should feel guilty", ephemeral=True)
    send_and_delete(interaction.channel.id, message, delay)
    if sniper: send_and_delete(interaction.channel.id, sniper)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"connected to {bot.user}")
    
bot.run(get_bot_token())
