from telethon import TelegramClient, events
import os
import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
import asyncio

# ==== CONFIG ====
API_ID = 21124978
API_HASH = '63f41b60df295e52b2a967e5f9c02977'
SESSION_NAME = 'hexamon_bot'
GROUP_ID = -1001923517416  # Replace with your group's ID or username
POKEMON_FOLDER = 'pokemon_images'
HEXAMON_BOT_ID = 572621020
# ================

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
expecting_silhouette = False  # Track state after sending /guess

def extract_silhouette_from_scene_bytes(image_bytes):
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)
    return binary  # No cropping or resizing

def preprocess_pokemon_image(path):
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ValueError(f"Failed to load image: {path}")
    if len(img.shape) == 2:
        gray = img
    elif img.shape[2] == 4:
        gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY)
    else:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
    return binary

def resize_to_match(img, shape):
    return cv2.resize(img, (shape[1], shape[0]), interpolation=cv2.INTER_AREA)

def compare_images(img1, img2):
    if img1.shape != img2.shape:
        img2 = resize_to_match(img2, img1.shape)
    return ssim(img1, img2)

def guess_pokemon(silhouette):
    best_score = -1
    best_match = None
    for filename in os.listdir(POKEMON_FOLDER):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            path = os.path.join(POKEMON_FOLDER, filename)
            try:
                candidate = preprocess_pokemon_image(path)
                score = compare_images(silhouette, candidate)
                if score > best_score:
                    best_score = score
                    best_match = filename.split('.')[0]
            except Exception as e:
                print(f"Error processing {filename}: {e}")
    return best_match

@client.on(events.NewMessage(chats=GROUP_ID))
async def all_handler(event):
    global expecting_silhouette

    if event.raw_text.lower() == "/startguess":
        print("Sending /guess command...")
        expecting_silhouette = True
        await client.send_message(GROUP_ID, "/guess")
        return

    if expecting_silhouette and event.photo and event.sender_id == HEXAMON_BOT_ID:
        print("Silhouette received from HeXamonBot.")
        try:
            image_bytes = await event.download_media(bytes)
            silhouette = extract_silhouette_from_scene_bytes(image_bytes)
            name = guess_pokemon(silhouette)
            if name:
                await asyncio.sleep(2)
                await client.send_message(GROUP_ID, name)
                print(f"Guessed Pokémon: {name}")
            else:
                await client.send_message(GROUP_ID, "No match found.")
            expecting_silhouette = False
        except Exception as e:
            print(f"Error processing silhouette: {e}")
            expecting_silhouette = False

print("Bot is running. Type /startguess in the group to begin.")
client.start()
client.run_until_disconnected()
