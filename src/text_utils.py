"""
text_utils.py — cleans a message before the model sees it.

Why: the model learns from words. A link like "sbi-kyc-update.in" or a phone
number like 98XXXXXXXX is different in every scam, so the model can't learn
from the exact text. We replace them with a fixed token ("urltoken",
"phonetoken") so the model learns the *pattern*: "this message has a link".
"""

import re

URL_RE = re.compile(
    r"(https?://\S+|www\.\S+|\b[\w-]+(\.[\w-]+)*\.(com|in|co|net|org|xyz|top|online|shop|info|app|apk|ly|gd|me)(/\S*)?\b)",
    re.IGNORECASE,
)
PHONE_RE = re.compile(r"\b(\+?91[\s-]?)?[6-9]\d{1,3}X{4,}\b|\b(\+?91[\s-]?)?[6-9]\d{9}\b", re.IGNORECASE)
MONEY_RE = re.compile(r"(rs\.?|inr|₹)\s?[\d,]+(\.\d+)?|\b\d+\s?(lakh|crore)\b", re.IGNORECASE)
LONG_NUM_RE = re.compile(r"\b\d{4,}\b")
# masked numbers in our data (XXXXXX, XX4521, xxXXXX) must look the SAME as real digits,
# otherwise the model learns "XXXXXX = safe, real digits = scam" — and real users send real digits
MASKED_NUM_RE = re.compile(r"\b[0-9xX]*[xX]{3,}[0-9xX]*\b")


def clean_text(text: str) -> str:
    """Lowercase + swap links, phone numbers, amounts and long numbers for tokens."""
    text = str(text)
    text = URL_RE.sub(" urltoken ", text)
    text = PHONE_RE.sub(" phonetoken ", text)
    text = MONEY_RE.sub(" moneytoken ", text)
    text = MASKED_NUM_RE.sub(" numtoken ", text)
    text = LONG_NUM_RE.sub(" numtoken ", text)
    text = text.lower()
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ---------- red flags: human-readable reasons shown next to the prediction ----------
RED_FLAGS = [
    (r"urltoken", "Contains a link"),
    (r"\b(kyc|ekyc|re-?kyc|pan|aadhaa?r)\b", "Asks to update KYC / PAN / Aadhaar"),
    (r"\b(otp|upi pin|pin|cvv)\b", "Mentions OTP / PIN / CVV"),
    (r"\b(block(ed)?|band|suspend(ed)?|deactivat\w*|freez\w*|blacklist\w*|kaat|cut|disconnect\w*)\b", "Threatens to block or cut a service"),
    (r"\b(urgent\w*|turant|immediately|abhi|jaldi|today|aaj raat|within \d+|24 (hrs|hours|ghante))\b", "Creates urgency"),
    (r"\b(lottery|lucky draw|won|jeet\w*|winner|prize|inaam|congratulations|badhai)\b", "Promises a prize or lottery win"),
    (r"\b(fee|fees|charge|processing|registration|deposit|advance|tax)\b", "Asks you to pay a fee first"),
    (r"\b(police|cbi|ed|customs|arrest|fir|warrant|court|narcotics|cyber crime|trai)\b", "Uses police / government threats"),
    (r"\b(guaranteed|double|return|profit|crypto|bitcoin|trading|invest\w*)\b", "Promises guaranteed money or returns"),
    (r"\b(naya number|new number|phone (kharab|gir|broke)|mat batana|don'?t tell|kisi ko mat)\b", "Asks for secrecy or claims a new number"),
    (r"\b(anydesk|quicksupport|teamviewer|apk|download app)\b", "Asks to install an app"),
    (r"\b(work from home|part time|daily income|per day|ghar baithe)\b", "Too-good-to-be-true job offer"),
]


def find_red_flags(text: str) -> list[str]:
    cleaned = clean_text(text)
    flags = [reason for pattern, reason in RED_FLAGS if re.search(pattern, cleaned)]
    if asks_for_secret(text):
        flags.insert(0, "Asks you to SHARE your OTP / PIN / CVV — banks never do this")
    return flags


# ---------- RULE: "asks you to share a secret" ----------
# The ML model can't tell "share the OTP" from "do NOT share the OTP" — both contain the
# same words. This rule looks at the words right next to each other to catch the difference.

SECRET = r"(otp|one time password|upi pin|atm pin|pin|cvv|password|verification code|\d digit code|code)"
SHARE = r"(share|send|tell|give|provide|enter|type|forward|bata\w*|bhej\w*|daal\w*|dal\w*|de do|dijiye)"
NEGATION = r"(do not|don't|dont|never|not|mat|na|nahi|kabhi|avoid|without)"
GAP = r"(?:\s+\S+){0,3}?\s+"          # up to 3 words in between


def asks_for_secret(text: str) -> bool:
    """True if the message ASKS the reader to share an OTP/PIN/CVV (and doesn't say 'don't')."""
    t = clean_text(text)
    patterns = [
        rf"(?P<verb>{SHARE}){GAP}{SECRET}\b",   # English order: "share the OTP", "enter UPI PIN"
        rf"\b{SECRET}{GAP}(?P<verb>{SHARE})",   # Hinglish order: "OTP batao", "UPI PIN daaliye"
    ]
    for pattern in patterns:
        for m in re.finditer(pattern, t):
            # look at the few words just before the verb for a "don't / never / mat"
            before_verb = t[max(0, m.start("verb") - 25): m.start("verb")]
            if not re.search(rf"\b{NEGATION}\b", before_verb):
                return True
    return False
