# Sachet — Dataset

Every row is a message plus a label: `scam` or `safe`.

| File | What it is |
|---|---|
| `messages.csv` | ~830 synthetic Hinglish/English messages from `scripts/make_dataset.py` (35 scam patterns, 35 safe patterns) |
| `test_messages.csv` | 36 hand-written messages with **different wording**. Never used for training, only for checking the model honestly |
| `real_messages.csv` | Real messages **you** collect (2 examples inside, add more) |
| `raw/hf_scam.json` | Optional: Hugging Face dataset, download yourself (see below) |
| `combined.csv` | Final merged file, built by `scripts/build_dataset.py` — this is what training uses |

## Step 1 — Add the Hugging Face dataset
1. Open https://huggingface.co/bolewara/hinglish-scam-text-dataset → **Files** tab
2. Download the JSON file, rename it `hf_scam.json`, put it in `data/raw/`
3. License is CC-BY-4.0 → credit "Anuj Bolewar" in your project README

Heads-up: most of it is English (from the UCI SMS Spam set), and its "spam" includes plain ads, not just scams. Only ~63 rows are Hinglish.

## Step 2 — Collect real messages (the most valuable part)
Where to find them:
- Your own SMS inbox and WhatsApp (scam ones *and* normal ones)
- Ask family — parents usually get the most KYC / electricity / lottery scams
- Screenshots posted on Twitter/X, Reddit (r/india, r/IndiaInvestments), news articles about scams
- Official warnings: Sanchar Saathi "Chakshu", RBI and bank fraud-awareness pages

Rules:
- **Remove personal info** before saving: names, phone numbers, account numbers → replace with `XXXX`
- Copy the message as it was written (typos, CAPS, Hinglish spelling) — that's what makes the data real
- Collect safe ones too, especially tricky ones: real bank OTP/debit alerts, delivery updates, bill reminders
- Aim for 100+ real messages, roughly half scam, half safe

Add them to `real_messages.csv` like this (put the text in quotes if it has a comma):
```
text,label
"Aapka bijli bill pending hai, aaj raat connection kat jayega. Call 98XXXXXXXX",scam
"Bhai kal lab hai na 9 baje?",safe
```

## Step 3 — Build the final file
```
python scripts/build_dataset.py
```
It merges everything, cleans it, removes duplicates and any test messages, and prints a count per source.
