"""
predict.py — check any message with the trained Sachet model.

Run:  python src/predict.py
Then paste a message and press Enter. Type q to quit.
"""

from pathlib import Path

import joblib

from text_utils import asks_for_secret, clean_text, find_red_flags

MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "sachet_model.joblib"


def load_model():
    if not MODEL_PATH.exists():
        raise SystemExit("No model found. Run  python src/train.py  first.")
    return joblib.load(MODEL_PATH)


def check_message(model, text: str) -> dict:
    """Returns verdict, scam probability (0-1) and red flags for one message."""
    scam_index = list(model.classes_).index("scam")
    prob = model.predict_proba([clean_text(text)])[0][scam_index]
    if asks_for_secret(text):          # rule beats model: asking for an OTP/PIN is always a scam
        prob = max(prob, 0.95)
    if prob >= 0.7:
        verdict = "SCAM"
    elif prob >= 0.4:
        verdict = "SUSPICIOUS"
    else:
        verdict = "LOOKS SAFE"
    return {"verdict": verdict, "scam_probability": prob, "red_flags": find_red_flags(text)}


def main():
    model = load_model()
    print("Sachet — paste a message to check it (q to quit)\n")
    while True:
        text = input("Message: ").strip()
        if text.lower() in {"q", "quit", "exit"}:
            break
        if not text:
            continue
        result = check_message(model, text)
        print(f"  -> {result['verdict']}  (scam probability {result['scam_probability']:.0%})")
        for flag in result["red_flags"]:
            print(f"     ! {flag}")
        print()


if __name__ == "__main__":
    main()
