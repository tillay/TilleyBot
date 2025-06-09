import discord, os, re, requests, http, json, csv, time
from datetime import datetime, timedelta, timezone
from discord.ext import commands
from html import unescape
from openai import OpenAI

try:
    from Cryptodome.Util.Padding import pad, unpad
    from Cryptodome.Cipher import AES
except ModuleNotFoundError:
    from Crypto.Util.Padding import pad, unpad
    from Crypto.Cipher import AES

bot_token_file = "~/bot_tokens/TilleyBot.token"
user_token_file = "~/bot_tokens/tillay8.token"
ai_token_file = "~/bot_tokens/deepseek.token"

bot = commands.Bot("!", intents=discord.Intents.none())

def get_bot_token():
    with open(os.path.expanduser(bot_token_file), 'r') as f:
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

def get_current_time(gmt_offset):
        offset = timedelta(hours=gmt_offset)
        utc_now = datetime.now(timezone.utc)
        time = utc_now + offset
        time = time.strftime("%H:%M (%I:%M %p)")
        return time

@bot.tree.command(name="repeat", description="repeat previous message")
async def repeat(interaction: discord.Interaction):
    channel_id = interaction.channel.id
    await interaction.response.send_message("repeating", ephemeral=True)
    send_user_message(channel_id, get_most_recent_message(interaction.channel.id))

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

@bot.tree.command(name="scramble", description="scramble text")
async def scramble(interaction: discord.Interaction, message: str):
    substitutions = [('a', 'а'), ('e', 'е'), ('i', 'і'), ('p', 'р'),
                     ('s', 'ѕ'), ('c', 'с'), ('o', 'о'), ('x', 'х'),
                     ('y', 'у')]
    for old, new in substitutions:
        message = message.replace(old, new)
    message = '​'.join(list(message))
    await interaction.response.send_message(message, ephemeral=True)

@bot.tree.command(name="translate", description="translate messages to english")
async def translate(interaction: discord.Interaction, message: str, lang: str = "en"):
    await interaction.response.send_message(translator(message, lang), ephemeral=True)
  
@bot.tree.command(name="catgirl", description="send a catgirl")
async def catgirl(interaction: discord.Interaction):
    await interaction.response.send_message(get_catgirl_link(), ephemeral=False)

@bot.tree.command(name="timezones", description="calculate timezones")
async def timezones(interaction: discord.Interaction, gmt_offset: int = None):
    if gmt_offset is not None:
        gmt_offset = timedelta(hours=gmt_offset)
        utc_now = datetime.utcnow()
        their_time = utc_now + gmt_offset
        their_time = their_time.strftime("%I:%M %p")
        await interaction.response.send_message(f"Their time is {their_time})", ephemeral=True)
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

@bot.tree.command(name="senakot_time", description="print info about senakot's time")
async def senakot_time(interaction):
    await interaction.response.send_message(f"Senakot's current time is {get_current_time(4)}. He lives in UTC+4.")

@bot.tree.command(name="kea_time", description="print info about doctorkea's time")
async def senakot_time(interaction):
    await interaction.response.send_message(f"Doctorkea's current time is {get_current_time(12)}. He lives in UTC+12.")
    
@bot.tree.command(name="neria_time", description="print info about neria's time")
async def neria_time(interaction):
    await interaction.response.send_message(f"Neria's current time is {get_current_time(3)}. He lives in UTC+3.")

@bot.tree.command(name="hidetext", description="hide text behind other text")
async def hidetext(interaction: discord.Interaction, showntext: str, hidetext: str):
    spoiler = "||​" * 400
    await interaction.response.send_message(f"```{showntext}  {spoiler} _ _ _ _ _ _  {hidetext}```", ephemeral=True)

@bot.tree.command(name="ai_tilley", description="make tilley an ai")
async def ai_tilley(interaction: discord.Interaction):
    context = "You are tilley8, a discord user. You like cats and Linux. Respond to this prompt very concisely, only 20 words or less. do not include emojis and be relatively serious"
    prompt = get_most_recent_message(interaction.channel.id)
    await interaction.response.send_message(f"generating message with prompt: {prompt}", ephemeral=True)
    send_user_message(interaction.channel.id, deepseek_query(prompt, context))

@bot.tree.command(name="deepseek", description="get response from deepseek")
async def deepseek(interaction: discord.Interaction, prompt: str):
    await interaction.response.send_message(prompt)
    await interaction.followup.send(deepseek_query(prompt, "You are a discord bot called Tilley Bot who answers questions in a discord server. do not include emojis and be relatively serious. Keep all responses under 1950 characters."))

@bot.tree.command(name="ghost_ping", description="send and delete message fast")
async def ghost_ping(interaction: discord.Interaction, message: str, sniper: str=None, delay: int = None):
    await interaction.response.send_message("you should feel guilty", ephemeral=True)
    send_and_delete(interaction.channel.id, message, delay)
    if sniper: send_and_delete(interaction.channel.id, sniper)

@bot.tree.command(name="status_paid", description="send fake status paid message until noxbotv2 comes out")
async def status_paid(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Status changed!",
        description="Status of your order has changed.",
        color=0xFFFF00
    )
    embed.add_field(name="**Paid**", value="We got your payment. Please be patient and wait for delivery guy to pick you up.", inline=False)
    await interaction.response.send_message(embed=embed)

last_message = None

@bot.tree.command(name="do_the_thing", description="custom response")
async def do_the_thing(interaction: discord.Interaction, message: str = None):
    global last_message
    if message:
        last_message = message
        await interaction.response.send_message(f"next response will be {message}", ephemeral=True)
    elif last_message:
        await interaction.response.send_message(last_message)
    else:
        await interaction.response.send_message("please specify message", ephemeral=True)
        
@bot.tree.command(name="tldr", description="tldr a website")
async def tldr(interaction: discord.Interaction, url: str):
    r = requests.get(url, timeout=10)
    if r.status_code != 200:
        await interaction.response.send_message("Failed to download site", ephemeral=True)
        return
    html = r.text[:15000]
    result = deepseek_query(html + "\n\nExplain this in simple words below 1600 characters", "")
    await interaction.response.send_message(result)
    
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"connected to {bot.user}")
    
bot.run(get_bot_token())
