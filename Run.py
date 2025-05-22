from telethon import TelegramClient, events
import os
import cv2
import numpy as np
import asyncio

# ==== CONFIG ====
API_ID = 21124978
API_HASH = '63f41b60df295e52b2a967e5f9c02977'
SESSION_NAME = 'hexamon_bot'
GROUP_ID = -1001923517416
HEXAMON_BOT_ID = 572621020  # Numeric bot ID
POKEMON_FOLDER = 'pokemon_images'
# ================

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)
expecting_silhouette = False
pokemon_data = []

# ========== HELPER FUNCTIONS ==========

def preprocess_pokemon_image(path):
    img = cv2.imread(path, cv2.IMREAD_UNCHANGED)
    if img is None:
        return None
    if len(img.shape) == 2:
        gray = img
    elif img.shape[2] == 4:
        gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY)
    else:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
    return binary

def preprocess_silhouette(image_bytes):
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, 50, 255, cv2.THRESH_BINARY_INV)
    return binary

def compare_images_fast(img1, img2):
    if img1.shape != img2.shape:
        img2 = cv2.resize(img2, (img1.shape[1], img1.shape[0]))
    err = np.sum((img1.astype("float") - img2.astype("float")) ** 2)
    err /= float(img1.shape[0] * img1.shape[1])
    return -err  # lower error is better

def guess_pokemon(silhouette):
    best_score = -1e9
    best_match = None
    for name, binary in pokemon_data:
        score = compare_images_fast(silhouette, binary)
        if score > best_score:
            best_score = score
            best_match = name
    return best_match

# ========== TELEGRAM HANDLER ==========

@client.on(events.NewMessage(chats=GROUP_ID))
async def handle(event):
    global expecting_silhouette

    if event.raw_text.lower() == "/startguess":
        print("Sending /guess...")
        expecting_silhouette = True
        await client.send_message(GROUP_ID, "/guess")
        return

    if expecting_silhouette and event.photo and event.sender_id == HEXAMON_BOT_ID:
        print("Silhouette received.")
        try:
            image_bytes = await event.download_media(bytes)
            silhouette = preprocess_silhouette(image_bytes)
            name = guess_pokemon(silhouette)
            if name:
                await asyncio.sleep(1.5)  # Adjust if needed
                await client.send_message(GROUP_ID, name)
                print(f"Guessed: {name}")
            else:
                await client.send_message(GROUP_ID, "No match found.")
            expecting_silhouette = False
        except Exception as e:
            print(f"Error: {e}")
            expecting_silhouette = False

# ========== LOAD POKEMON DATA ==========

def load_pokemon_images():
    for filename in os.listdir(POKEMON_FOLDER):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            path = os.path.join(POKEMON_FOLDER, filename)
            binary = preprocess_pokemon_image(path)
            if binary is not None:
                pokemon_data.append((filename.split('.')[0], binary))

# ========== MAIN ==========

print("Loading Pokémon images...")
load_pokemon_images()
print(f"{len(pokemon_data)} Pokémon loaded.")
print("Bot is running. Type /startguess in the group to begin.")
client.start()
client.run_until_disconnected()
