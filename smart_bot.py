import random, json, os, asyncio
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, ContextTypes

# === CONFIG ===
BOT_TOKEN = "7370344743:AAEQDkF25sB66KiT57cIv8jcbSc8GSQCgOM"
CHAT_ID = 978173046

positions = [f"{chr(65 + r)}{c + 1}" for r in range(5) for c in range(5)]  # A1–E5

# === JSON I/O ===
def load_json(file, default):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return default

def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=2)

# === TIME HANDLING ===
def get_current_time():
    return datetime.now().strftime('%H:%M')

# === PATTERN GENERATION ===
def generate_pattern_for_time():
    current_time = get_current_time()
    learning = load_json("time_learning.json", {})
    used = load_json("used_patterns.json", [])

    if current_time in learning and learning[current_time]["correct"]:
        safe = random.choice(learning[current_time]["correct"])
    else:
        for _ in range(1000):
            safe = sorted(random.sample(positions, 3))
            if safe not in learning.get(current_time, {}).get("wrong", []):
                break

    pattern_id = str(random.randint(1000, 9999))
    used.append({"id": pattern_id, "pattern": safe, "time": current_time})
    save_json("used_patterns.json", used)
    return safe, pattern_id, current_time

# === GRID BUILDER ===
def build_grid(safe):
    grid = ["💎" if p in safe else "💣" for p in positions]
    return "\n".join(" ".join(grid[i:i+5]) for i in range(0, 25, 5))

# === LEARNING UPDATE ===
def update_time_learning(safe, time_str, result):
    learning = load_json("time_learning.json", {})
    if time_str not in learning:
        learning[time_str] = {"correct": [], "wrong": []}

    if result == "correct":
        if safe not in learning[time_str]["correct"]:
            learning[time_str]["correct"].append(safe)
        learning[time_str]["wrong"] = [p for p in learning[time_str]["wrong"] if p != safe]
    else:
        if safe not in learning[time_str]["wrong"]:
            learning[time_str]["wrong"].append(safe)
        learning[time_str]["correct"] = [p for p in learning[time_str]["correct"] if p != safe]

    save_json("time_learning.json", learning)

# === PREDICTION SENDER ===
async def send_prediction(bot):
    safe, pattern_id, time_str = generate_pattern_for_time()
    grid = build_grid(safe)
    text = f"""🔮 *Smart Prediction Bot*

🆔 *Pattern ID:* #{pattern_id}
🕒 *Time:* {time_str}
✅ *Safe Cells:* {', '.join(safe)}

🧠 *Prediction Grid:*
{grid}
"""
    buttons = [[
        InlineKeyboardButton("✅ Correct", callback_data=f"correct|{','.join(safe)}|{pattern_id}|{time_str}"),
        InlineKeyboardButton("❌ Wrong", callback_data=f"wrong|{','.join(safe)}|{pattern_id}|{time_str}")
    ]]
    await bot.send_message(
        chat_id=CHAT_ID,
        text=text,
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# === FEEDBACK HANDLER ===
async def feedback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    result, safe_str, pattern_id, time_str = query.data.split("|")
    safe = sorted(safe_str.split(","))
    update_time_learning(safe, time_str, result)
    await query.edit_message_reply_markup(reply_markup=None)
    await query.message.reply_text(
        f"📝 Feedback saved for *#{pattern_id}* — Marked as *{result.upper()}* at {time_str}",
        parse_mode='Markdown'
    )

# === BACKGROUND LOOP (1-minute syncing) ===
async def background_loop(app):
    while True:
        now = datetime.now()
        seconds_until_next_minute = 60 - now.second
        await asyncio.sleep(seconds_until_next_minute)
        await send_prediction(app.bot)

# === MAIN FUNCTION ===
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CallbackQueryHandler(feedback_handler))
    asyncio.create_task(background_loop(app))
    print("✅ Bot started polling & predicting...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    while True:
        await asyncio.sleep(1)

# === RUN ===
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("🛑 Bot stopped manually.")
