"""
build_dataset.py — merges every data source into ONE clean training file.

Sources (any that exist are used, missing ones are skipped):
  1. data/messages.csv          -> our synthetic Hinglish starter set (scripts/make_dataset.py)
  2. data/raw/hf_scam.json       -> Hugging Face "bolewara/hinglish-scam-text-dataset" (CC-BY-4.0)
                                    download it yourself and save it with this name
  3. data/claude_messages.csv    -> ~250 realistic messages hand-written by Claude (synthetic, not real)
  4. data/real_messages.csv      -> REAL messages you collect yourself (columns: text,label)

Output: data/combined.csv  (columns: text, label, source)   label = "scam" / "safe"

Run:  python scripts/build_dataset.py
"""

import json
from pathlib import Path

import pandas as pd

DATA = Path(__file__).resolve().parent.parent / "data"
frames = []


def report(name, df):
    print(f"  + {name:<22} {len(df):>5} rows  (scam {int((df.label == 'scam').sum())}, safe {int((df.label == 'safe').sum())})")


# 1. synthetic starter set
p = DATA / "messages.csv"
if p.exists():
    df = pd.read_csv(p)
    df["source"] = "synthetic"
    frames.append(df)
    report("synthetic", df)

# 2. Hugging Face dataset (JSON with a top-level "rows" list, label 0 = benign, 1 = scam)
p = DATA / "raw" / "hf_scam.json"
if p.exists():
    raw = json.loads(p.read_text(encoding="utf-8"))
    rows = raw["rows"] if isinstance(raw, dict) and "rows" in raw else raw
    rows = [r.get("row", r) for r in rows]          # handles both export styles
    df = pd.DataFrame(rows)[["text", "label"]]
    df["label"] = df["label"].map({0: "safe", 1: "scam", "0": "safe", "1": "scam"})
    df["source"] = "huggingface"
    frames.append(df)
    report("huggingface", df)
else:
    print("  - huggingface            skipped (data/raw/hf_scam.json not found)")

# 3. hand-written (by Claude) realistic Indian scam + tricky safe messages — NOT real, kept separate
p = DATA / "claude_messages.csv"
if p.exists():
    df = pd.read_csv(p)
    df["source"] = "claude-written"
    frames.append(df)
    report("claude-written", df)

# 4. your own real messages
p = DATA / "real_messages.csv"
if p.exists():
    df = pd.read_csv(p)
    df["source"] = "real"
    frames.append(df)
    report("real (yours)", df)

data = pd.concat(frames, ignore_index=True)

# ---- cleaning ----
data["text"] = data["text"].astype(str).str.strip()
data["label"] = data["label"].astype(str).str.strip().str.lower()
data = data[data["label"].isin(["scam", "safe"])]          # drop bad labels
data = data[data["text"].str.len() > 3]                     # drop empty rows
data = data.drop_duplicates(subset="text")                  # drop exact repeats

# never let test / check messages leak into training
for held_out in ["test_messages.csv", "fresh_messages.csv"]:
    path = DATA / held_out
    if path.exists():
        held_texts = set(pd.read_csv(path)["text"].str.strip())
        data = data[~data["text"].isin(held_texts)]

out = DATA / "combined.csv"
data.to_csv(out, index=False)
print(f"\nSaved {len(data)} messages to {out}")
print(data.groupby(["source", "label"]).size().unstack(fill_value=0))
