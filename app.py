"""
Spanish Buddy — a bilingual chat companion. Backend calls Groq's free API
(OpenAI-compatible) instead of a local model, so it can be deployed to a free
host (like Render) and your friend just opens a link — no install on her end.

Local run (for testing before you deploy):
    pip install -r requirements.txt
    export GROQ_API_KEY=your_key_here
    python app.py
Then open http://localhost:5000

Deploy: see README.md for the Render + Groq setup walkthrough.
"""

import os
import requests
from flask import Flask, request, jsonify, send_from_directory

app = Flask(__name__, static_folder="static", static_url_path="")

# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
COMPANION_NAME = os.environ.get("COMPANION_NAME", "Mateo")

# ---------------------------------------------------------------------------
# Persona / teaching logic
# ---------------------------------------------------------------------------
LEVEL_INSTRUCTIONS = {
    "beginner": (
        "The user is a BEGINNER in Spanish. Write mostly in English (about 80%), "
        "and sprinkle in simple Spanish words or short phrases (about 20%). "
        "Every time you use a Spanish word or phrase, immediately give the English "
        "translation in parentheses right after it the first couple of times, e.g. "
        "'¿Qué tal? (how's it going?)'. Keep Spanish vocabulary very basic: greetings, "
        "common nouns, simple verbs in present tense. Never write a full Spanish sentence "
        "without an English translation nearby."
    ),
    "intermediate": (
        "The user is an INTERMEDIATE Spanish learner. Mix English and Spanish naturally, "
        "roughly 50/50, the way a bilingual friend code-switches mid-conversation. You can "
        "use full Spanish sentences, but if you use a word that's likely unfamiliar or advanced, "
        "casually clarify it in English in the same message. Use a mix of tenses (present, past, "
        "near future) at a moderate pace."
    ),
    "advanced": (
        "The user is an ADVANCED Spanish learner. Write mostly in Spanish (about 80%), using "
        "natural, idiomatic, conversational Spanish including slang and varied tenses. Only drop "
        "into English for a word or two if something would otherwise be genuinely confusing, or if "
        "the user explicitly asks for English. Challenge them a little."
    ),
}

BASE_PERSONA = """You are {name}, a warm, funny, supportive friend who is fully bilingual in \
English and Spanish. You are texting with a friend who is learning Spanish. This is NOT a \
classroom and you are NOT a textbook or tutor — you're a friend chatting casually, who happens \
to naturally help them pick up Spanish along the way.

Ground rules, always follow these:
- Keep messages SHORT, like real texts: 1-4 sentences, casual punctuation, occasional emoji (don't overdo it).
- Talk about real things: their day, plans, opinions, music, food, whatever comes up. Ask follow-up questions sometimes to keep the conversation going — but not after every single message.
- Weave in 1-2 new Spanish words or a short phrase naturally when it fits the conversation, don't force vocab lessons.
- If the user writes Spanish with a mistake, gently correct it in-line and keep moving, e.g. "jaja close! it's 'tengo hambre' not 'tener hambre' here 😊 anyway..." — never lecture, never make it feel like a quiz.
- Never break character to talk about being an AI, a model, or a program. You are just {name}, a friend.
- Match the energy and length of the user's messages — don't write paragraphs if they send one line.

{level_instruction}
"""


def build_system_prompt(level: str) -> str:
    level = level if level in LEVEL_INSTRUCTIONS else "intermediate"
    return BASE_PERSONA.format(
        name=COMPANION_NAME,
        level_instruction=LEVEL_INSTRUCTIONS[level],
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/health")
def health():
    """Lets the frontend check whether the Groq API key is configured and working."""
    if not GROQ_API_KEY:
        return jsonify({
            "api_reachable": False,
            "configured_model": GROQ_MODEL,
            "error": "GROQ_API_KEY is not set on the server.",
            "companion_name": COMPANION_NAME,
        })
    try:
        r = requests.get(
            f"{GROQ_URL}/models",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}"},
            timeout=10,
        )
        if r.status_code == 401:
            return jsonify({
                "api_reachable": False,
                "configured_model": GROQ_MODEL,
                "error": "Groq rejected the API key (401). Double-check GROQ_API_KEY.",
                "companion_name": COMPANION_NAME,
            })
        r.raise_for_status()
        return jsonify({
            "api_reachable": True,
            "configured_model": GROQ_MODEL,
            "companion_name": COMPANION_NAME,
        })
    except requests.exceptions.RequestException as e:
        return jsonify({
            "api_reachable": False,
            "configured_model": GROQ_MODEL,
            "error": str(e),
            "companion_name": COMPANION_NAME,
        }), 200


@app.route("/api/chat", methods=["POST"])
def chat():
    if not GROQ_API_KEY:
        return jsonify({"error": "Server is missing GROQ_API_KEY. Set it in your hosting dashboard's environment variables."}), 500

    data = request.get_json(force=True) or {}
    history = data.get("messages", [])  # [{role: "user"|"assistant", content: "..."}]
    level = data.get("level", "intermediate")

    if not history:
        return jsonify({"error": "No messages provided"}), 400

    messages = [{"role": "system", "content": build_system_prompt(level)}] + history

    try:
        r = requests.post(
            f"{GROQ_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GROQ_MODEL,
                "messages": messages,
                "temperature": 0.8,
            },
            timeout=60,
        )
        if r.status_code == 429:
            return jsonify({"error": "Hit the free-tier rate limit for a moment — wait a few seconds and try again."}), 429
        r.raise_for_status()
        payload = r.json()
        reply = payload["choices"][0]["message"]["content"].strip()
        if not reply:
            return jsonify({"error": "Empty response from model"}), 502
        return jsonify({"reply": reply})
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Groq API error: {e}"}), 502


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\nSpanish Buddy starting...")
    print(f"  Model:  {GROQ_MODEL}")
    print(f"  Key set: {'yes' if GROQ_API_KEY else 'NO — set GROQ_API_KEY'}")
    print(f"  Open:    http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
