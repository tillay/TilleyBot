import json, os, http.client, random

TOKEN_FILE = "./tillay8_token"


def get_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'r') as f:
           return f.readline().strip()

header_data = {
    "Content-Type": "application/json",
    "Authorization": get_token()
}

def send_message(channel_id, message_content):
    conn = http.client.HTTPSConnection("discord.com", 443)
    message_data = json.dumps({
        "content": message_content,
        "tts": False
    })
    conn.request("POST", f"/api/v10/channels/{channel_id}/messages", message_data, header_data)
    response = conn.getresponse()
    print("Message sent successfully.")


def get_most_recent_message(channel_id):
    conn = http.client.HTTPSConnection("discord.com", 443)
    conn.request("GET", f"/api/v10/channels/{channel_id}/messages?limit=1", headers=header_data)
    response = conn.getresponse()
    if 199 < response.status < 300:
        message = json.loads(response.read().decode())
        return message[0]['content'], message[0]['author']['username']
    else:
        return f"Discord aint happy: {response.status} error"

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
    response = conn.getresponse()
    if 199 < response.status < 300:
        print("File sent successfully.")
    else:
        print(f"discord aint happy: {response.status} {response.reason}")

def get_guild_names(guild_id):
    conn = http.client.HTTPSConnection("discord.com", 443)
    conn.request("GET", f"/api/v10/guilds/{guild_id}/channels", headers=header_data)
    response = conn.getresponse()
    data = response.read().decode('utf-8')
    if response.status == 200:
        channels = json.loads(data)
        channel_list = [channel["name"] for channel in channels]
        return channel_list
    else:
        print(f"Failed to fetch names: {response.status} {response.reason}")

def get_guild_ids(guild_id):
    conn = http.client.HTTPSConnection("discord.com", 443)
    conn.request("GET", f"/api/v10/guilds/{guild_id}/channels", headers=header_data)
    response = conn.getresponse()
    data = response.read().decode('utf-8')
    if response.status == 200:
        channels = json.loads(data)
        channel_list = [channel["id"] for channel in channels]
        return channel_list
    else:
        print(f"Failed to fetch ids: {response.status} {response.reason}")


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
            print(f"Failed to fetch guild info: {guild_response.status} {guild_response.reason}")
            return None
    else:
        print(f"Failed to fetch channel info: {response.status} {response.reason}")
        return None

