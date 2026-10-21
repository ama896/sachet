"""
train.py — trains the Sachet scam detector.

How the model works (in plain words):
  1. TF-IDF turns each message into numbers: how often each word / piece of a
     word appears, giving more weight to rare, telling words like "kyc" or "lottery".
     - word features catch whole words and pairs ("kyc update", "aapka account")
     - character features catch spelling variety ("aapka", "apka", "apke" share "apk")
       which matters a lot for Hinglish, where nobody spells the same way.
  2. Logistic Regression learns a weight for every feature and adds them up to give
     a probability that the message is a scam.
  3. class_weight="balanced" stops the model from being lazy: we have ~3x more safe
     messages, so without it the model could call everything "safe" and still look good.

Run from the project folder:  python src/train.py
"""

from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion, Pipeline

from text_utils import asks_for_secret, clean_text

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
MODEL_PATH = ROOT / "models" / "sachet_model.joblib"

# Sources left OUT of training (they stay in combined.csv, so this is easy to undo).
# huggingface: mostly British SMS from ~2010. Its "safe" side is almost all casual chat and its
# "scam" side is almost all formal company messages, so the model learned "formal message with
# an amount = scam". With it, 4 of 8 genuine Indian bank/payment alerts in fresh_messages.csv were
# flagged as scams; without it, 0 were. (Experiment run on 21 Oct 2026 — see README.)
EXCLUDE_SOURCES = {"huggingface"}


def build_model() -> Pipeline:
    features = FeatureUnion([
        ("words", TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=2, sublinear_tf=True)),
        ("chars", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True)),
    ])
    classifier = LogisticRegression(max_iter=2000, class_weight="balanced", C=5.0)
    return Pipeline([("features", features), ("clf", classifier)])


def hybrid_predict(model, texts):
    """Model prediction, overridden to 'scam' when the OTP/PIN rule fires."""
    texts = pd.Series(texts).reset_index(drop=True)
    preds = model.predict(texts.map(clean_text))
    rule_hits = texts.map(asks_for_secret).to_numpy()
    preds[rule_hits] = "scam"
    return preds


def show_results(title, y_true, y_pred):
    print(f"\n===== {title} =====")
    print(classification_report(y_true, y_pred, digits=3, zero_division=0))
    cm = confusion_matrix(y_true, y_pred, labels=["safe", "scam"])
    print("Confusion matrix (rows = actual, columns = predicted):")
    print(f"              pred safe  pred scam")
    print(f"actual safe   {cm[0][0]:>9}  {cm[0][1]:>9}   <- safe msgs wrongly flagged: {cm[0][1]}")
    print(f"actual scam   {cm[1][0]:>9}  {cm[1][1]:>9}   <- scams MISSED: {cm[1][0]}")


def evaluate(model, df, name):
    """Scores the model on a held-out file: model alone, then model + OTP rule."""
    model_only = model.predict(df["text"].map(clean_text))
    pred = hybrid_predict(model, df["text"])   # hybrid = model + rule (asking for OTP/PIN = scam)
    print(f"\n{name}: model only {(model_only == df['label']).mean():.1%}, "
          f"model + rule {(pred == df['label']).mean():.1%}")
    show_results(f"{name} (model + rule)", df["label"], pred)
    wrong = df[df["label"] != pred]
    if len(wrong):
        print("Mistakes:")
        for _, row in wrong.iterrows():
            print(f"  [actual {row.label}] {row.text[:90]}")


def main():
    data = pd.read_csv(DATA / "combined.csv")
    skipped = data["source"].isin(EXCLUDE_SOURCES)
    if skipped.any():
        print(f"Skipping {skipped.sum()} messages from: {', '.join(sorted(EXCLUDE_SOURCES))} (see EXCLUDE_SOURCES)")
    data = data[~skipped].reset_index(drop=True)
    print(f"Training on {len(data)} messages: {data.label.value_counts().to_dict()}")
    data["clean"] = data["text"].map(clean_text)

    # ---- 1. validation split: hold back 20% to see how the model does on messages it never saw ----
    train_df, val_df = train_test_split(data, test_size=0.2, random_state=42, stratify=data["label"])
    model = build_model()
    model.fit(train_df["clean"], train_df["label"])
    val_pred = model.predict(val_df["clean"])
    show_results("Validation set (20% of combined.csv)", val_df["label"], val_pred)

    # accuracy per source — tells you where the model is weak
    val_df = val_df.assign(pred=val_pred)
    print("Accuracy by source:")
    for src, grp in val_df.groupby("source"):
        print(f"  {src:<15} {(grp.label == grp.pred).mean():.1%}  ({len(grp)} msgs)")

    # ---- 2. honest checks: messages never used for training ----
    #   test_messages.csv  — 36 hand-written messages with different wording
    #   fresh_messages.csv — 16 everyday Indian messages: bank alerts, transaction OTPs, common scams
    for filename in ["test_messages.csv", "fresh_messages.csv"]:
        path = DATA / filename
        if path.exists():
            evaluate(model, pd.read_csv(path), filename)

    # ---- 3. final model: retrain on ALL data, then save ----
    final_model = build_model()
    final_model.fit(data["clean"], data["label"])
    MODEL_PATH.parent.mkdir(exist_ok=True)
    joblib.dump(final_model, MODEL_PATH)
    print(f"\nSaved model to {MODEL_PATH}")


if __name__ == "__main__":
    main()
