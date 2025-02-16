import os
import tempfile
import time
import re
import requests
from gtts import gTTS
from telethon import TelegramClient, events
from telethon.network.connection import ConnectionTcpAbridged
from pyrogram import Client as PyrogramClient, filters
import pygame
from datetime import datetime
import json
import ast
import threading
import asyncio

reinit_lock = asyncio.Lock()


#
#VARIABLES
#
LOG_FILE = 'bot_logs.txt'
google_sheet_link="https://docs.google.com/spreadsheets/d/sAmPlEtExT/edit?usp=sharing"

# Number of messages Pyrogram skips to be restarted (depends on your messages flow)
count_to_restart = 8 # I use 8

# Length of a channel name to be voiced (in symbols)
title_length = 15 # I use 15

# Length of a message not to be voiced fully (in symbols)
too_long_message = 60 # I use 60

# Speech language
speechlanguage = "en" # Your preferred

# Initialize Telethon and Pyrogram Clients
# It doesn't really matter
telethon_client = TelegramClient("TELETHON SESSION NAME", api_id, api_hash, connection=ConnectionTcpAbridged)
pyrogram_client = PyrogramClient("PYROGRAM SESSION NAME", api_id=api_id, api_hash=api_hash)

api_id = 'YOUR API ID HERE'
api_hash = 'YOUR API HASH HERE'
SESSION_NAME = 'my_userbot'
#
#/VARIABLES
#





# Initialize Pygame Mixer
pygame.mixer.init()
TEMP_DIR = tempfile.gettempdir()
STRINGS_TO_CHECK = {}
last_voiced_messages = {}

# Counters for message tracking
telethon_message_count = 0
last_source = None

def log_message(message):
    """Append the log message to the log file with a timestamp and print it to console."""
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
    print(message)

def get_strings_from_google_sheets(sheet_url):
    """Fetch strings from Google Sheets and return as a dictionary."""
    try:
        json_url = sheet_url.replace('/edit?usp=sharing', '/gviz/tq?tqx=out:json')
        response = requests.get(json_url)
        response.raise_for_status()
        content = response.text
        json_data_match = re.search(r'(\{.*\})', content)
        if json_data_match:
            json_data = json.loads(json_data_match.group(1))
            strings_to_check = {}
            rows = json_data['table']['rows']
            for i, row in enumerate(rows):
                if i == 0:
                    continue
                if len(row['c']) >= 3:
                    channel_title_part = row['c'][0]['v']
                    keywords_string = row['c'][1]['v']
                    anti_keywords_string = row['c'][2]['v']
                    keywords = ast.literal_eval(keywords_string) if keywords_string else []
                    anti_keywords = ast.literal_eval(anti_keywords_string) if anti_keywords_string else []
                    strings_to_check[channel_title_part] = {'keywords': keywords, 'anti_keywords': anti_keywords}
            log_message(f"Fetched {len(strings_to_check)} strings from Google Sheets.")
            return strings_to_check
    except Exception as e:
        log_message(f"Failed to access Google Sheets: {e}")
    return {}

# Load keywords and anti-keywords from Google Sheets initially
STRINGS_TO_CHECK = get_strings_from_google_sheets(google_sheet_link)

@telethon_client.on(events.NewMessage)
async def telethon_message_handler(event):
    """Handle messages received by Telethon."""
    global STRINGS_TO_CHECK, telethon_message_count, last_source

    if event.chat and hasattr(event.chat, 'title'):
        channel_name = event.chat.title
    else:
        channel_name = "Unknown Channel"
        log_message("Received message from a chat without a title.")
        return

    text = event.message.message
    if not text:
        log_message("Skipping non-text message in Telethon.")
        return

    log_message(f"Telethon received message from channel '{channel_name}': {text}")

    if last_source == 'telethon':
        telethon_message_count += 1
    else:
        telethon_message_count = 1
    last_source = 'telethon'

    await process_message(channel_name, text, "telethon")
    await check_and_reinitialize_pyrogram()

@pyrogram_client.on_message()
async def pyrogram_message_handler(client, message):
    """Handle messages received by Pyrogram."""
    global STRINGS_TO_CHECK, telethon_message_count, last_source

    channel_name = message.chat.title
    text = message.text or message.caption or ""

    if not text:
        log_message("Received non-text message with no caption in Pyrogram. Skipping processing.")
        return

    if "123restartbot" in text: ################ This text is always ignored by Pyrogram so you can use it to boost restart
        log_message(f"Ignoring message from Pyrogram containing '123restartbot': {text}")
        return

    log_message(f"Pyrogram received message from channel '{channel_name}': {text}")

    telethon_message_count = 0
    last_source = 'pyrogram'

    await process_message(channel_name, text, "pyrogram")



# Global dictionary to track the last voiced message timestamps for each channel
last_voiced_timestamps = {}

async def process_message(channel_name, text, source):
    """Process incoming messages from either bot."""
    global last_voiced_timestamps

    current_time = time.time()

    # Check if the message should be voiced based on the 100 seconds rule
    if channel_name.lower() == "test":
        if text.strip() == "0":
            STRINGS_TO_CHECK.update(get_strings_from_google_sheets(google_sheet_link))
            success_message = "Refresh successful"
            await play_text_to_speech(success_message)
            return

        channel_links = re.findall(r'(https://t\.me/[a-zA-Z0-9_+/]+)', text)
        if channel_links:
            for channel_link in channel_links:
                try:
                    if '+' in channel_link:
                        joined_chat = await pyrogram_client.join_chat(channel_link)
                    else:
                        channel_username = channel_link.split('/')[-1]
                        joined_chat = await pyrogram_client.join_chat(f"@{channel_username}")

                    joined_channel_title = joined_chat.title if joined_chat else channel_link
                    success_message = f"Succesfully join channel {joined_channel_title}"
                    log_message(success_message)
                    await play_text_to_speech(success_message)

                except Exception as e:
                    log_message(f"Error joining channel {channel_link}: {e}")

    for key_string, data in STRINGS_TO_CHECK.items():
        if key_string.lower() in channel_name.lower():
            matched, anti_matched = False, False
            
            for anti_keyword in data['anti_keywords']:
                if anti_keyword.lower() in text.lower():
                    anti_matched = True
                    log_message(f"Anti-keyword '{anti_keyword}' matched in message from '{channel_name}'.")
                    break
            
            if not anti_matched:
                for keyword in data['keywords']:
                    if isinstance(keyword, tuple):
                        if all(kw.lower() in text.lower() for kw in keyword):
                            matched = True
                            break
                    elif keyword.lower() in text.lower():
                        matched = True
                    
                if matched:
                    # Check if this message has been voiced within the last 100 seconds
                    message_key = f"{channel_name}:{text.strip()}"

                    # If the message has been voiced within the last 100 seconds, skip it
                    if message_key in last_voiced_timestamps:
                        last_voiced_time = last_voiced_timestamps[message_key]
                        if current_time - last_voiced_time < 100:  ############ You can edit this value if it has any point
                            log_message(f"Skipping repeated message from '{channel_name}' voiced within the last 100 seconds.")
                            return

                    # If it's a new message or after the 100 seconds window, voice it and update the timestamp
                    last_voiced_timestamps[message_key] = current_time

                    short_channel_name = channel_name[:title_length]
                    full_message = f"Warning in channel {short_channel_name}" if len(text) > too_long_message else f"Warning. {text}. Channel {short_channel_name}"
                    await play_text_to_speech(full_message)
                    break




async def play_text_to_speech(full_message):
    """Convert text to speech and play it."""
    try:
        tts = gTTS(text=full_message, lang=speechlanguage)
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            temp_file_path = f.name
            tts.save(temp_file_path)

        log_message(f"Audio file saved: {temp_file_path}")
        
        pygame.mixer.music.load(temp_file_path)
        pygame.mixer.music.play()
        
        while pygame.mixer.music.get_busy():
            time.sleep(0.1)

    except Exception as e:
        log_message(f"Error in play_text_to_speech: {e}")

async def check_and_reinitialize_pyrogram():
    """Check Telethon message count and re-initialize Pyrogram client if necessary."""
    global telethon_message_count, pyrogram_client

    if telethon_message_count >= count_to_restart:
        async with reinit_lock:
            try:
                log_message("Re-initializing Pyrogram client...")
                telethon_message_count = 0
                await pyrogram_client.session.stop()
                await asyncio.sleep(5)
                await pyrogram_client.session.start()
                log_message("Pyrogram client re-initia0lized successfully.")
                telethon_message_count = 0
                
            except Exception as e:
                log_message(f"Failed to re-initialize Pyrogram client: {e}")

def periodic_logging():
    """Log that the bot is still running every 20 minutes."""
    while True:
        log_message("Bot is still running...")
        time.sleep(1200)

threading.Thread(target=periodic_logging, daemon=True).start()

if __name__ == "__main__":
    try:
        telethon_client.start()
        pyrogram_client.start()
        
        telethon_client.run_until_disconnected()
        pyrogram_client.run_until_disconnected()
        
    except Exception as e:
        log_message(f"An error occurred: {e}")