# Spanish Buddy 🧡

A bilingual chat companion for learning Spanish. Your friend just opens a
link in any browser — no installs, no accounts, nothing on her end. It's
not a flashcard app: she texts with "Mateo" (or whatever name you give it)
like a real friend, and the model naturally mixes English and Spanish,
teaches a little vocab along the way, and gently corrects mistakes.

This version runs on **free cloud services**, not your computer, so the
link works any time, from any device, even if your laptop is off.

What it costs: $0. What you need to do once: about 10 minutes of setup
(three free sign-ups, no credit card anywhere). What she needs to do: open
a link.

---

## One-time setup (you do this, not her)

### 1. Get a free Groq API key (this is the "brain")

1. Go to **https://console.groq.com** and sign up (email or Google login, no card).
2. Go to **API Keys** -> **Create API Key**. Copy it somewhere safe -- you'll paste it into Render in step 3.

Groq's free tier gives plenty of headroom for two people texting casually --
just don't expect it to hold up under heavy/production-scale traffic.

### 2. Put this project on GitHub

If you don't already have a GitHub account, make a free one at
**https://github.com**. Then create a new repository and upload this whole
`spanish-buddy` folder to it (drag-and-drop upload works fine on github.com,
or use `git push` if you're comfortable with that).

### 3. Deploy it on Render (this is the "hosting")

1. Go to **https://render.com** and sign up free (no card required).
2. Click **New** -> **Web Service**, and connect the GitHub repo from step 2.
3. Render should auto-detect Python. Set:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app`
4. Under **Environment Variables**, add:
   - `GROQ_API_KEY` -> paste the key from step 1
   - (optional) `GROQ_MODEL` -> defaults to `llama-3.3-70b-versatile` if you don't set this
   - (optional) `COMPANION_NAME` -> defaults to `Mateo`
5. Click **Create Web Service**. First deploy takes a couple of minutes.
6. When it's done, Render gives you a URL like `https://spanish-buddy-xxxx.onrender.com`.

**That URL is what you send to your friend.** That's the whole thing on her side.

---

## One thing to set expectations on: cold starts

Render's free tier puts the app to sleep after 15 minutes with no visitors.
The *next* person to open the link after that will wait about 30-60 seconds
for it to wake up before the page loads -- totally normal, not broken. After
that it's snappy for as long as the conversation continues.

---

## Customizing the companion

Everything that shapes the personality lives in `app.py`:

- **`COMPANION_NAME`** -- change the name (also shows as the avatar initial). Can also be set via the `COMPANION_NAME` environment variable on Render without touching code.
- **`BASE_PERSONA`** -- the core personality and texting style.
- **`LEVEL_INSTRUCTIONS`** -- the English/Spanish mix ratio and teaching style for Beginner / Intermediate / Advanced.

After editing, push the change to GitHub -- Render redeploys automatically.

The level she picks in the app (top of the chat) is sent with every message,
so she can switch as she improves.

## How it works (in plain terms)

- The **frontend** (`static/`) is a chat screen in the browser. It keeps the
  conversation in the browser's local storage, so it's still there if she
  closes the tab (but it's per-device/per-browser, not synced anywhere).
- The **backend** (`app.py`) is a small Flask server. On each message it
  sends the whole conversation plus a system prompt (persona + level) to
  Groq's API and relays the reply back.
- **Groq** runs the actual language model (an open-source model like Llama
  3.3) on their hardware and hands back a reply. This is the only part that
  isn't fully private -- messages pass through Groq's API to generate
  replies, same as using any AI chat app.
- **Render** just keeps the Flask server running and gives it a public URL.

## Testing locally before you deploy (optional)

```bash
cd spanish-buddy
pip install -r requirements.txt
export GROQ_API_KEY=your_key_here   # Windows: set GROQ_API_KEY=your_key_here
python app.py
```
Open http://localhost:5000.

## Troubleshooting

- **Status dot shows "offline"** -> check that `GROQ_API_KEY` is set correctly
  in Render's environment variables (Render dashboard -> your service ->
  Environment).
- **"Hit the free-tier rate limit"** -> wait a few seconds and send again;
  Groq's free tier resets quickly.
- **First load is slow** -> that's the cold-start sleep behavior above, not
  an error.
- **Want it always-on with no wake delay** -> that requires a paid Render
  instance (a few dollars/month); the free tier always has this sleep
  behavior.
- **Replies feel too robotic / not bilingual enough** -> tweak
  `LEVEL_INSTRUCTIONS` in `app.py`, or try `GROQ_MODEL=llama-3.1-8b-instant`
  (faster, lighter) vs the default 70B model (smarter, slightly slower).
