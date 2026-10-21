"""
make_dataset.py — builds a starter dataset of Hinglish/English SMS & WhatsApp messages.

Why a generator?  Real Indian scam datasets are rare and messy, so we start with
template-based *synthetic* messages that copy the patterns real scams use
(KYC blocks, fake lottery, OTP requests, job offers, electricity cut-off, etc.)
plus everyday "safe" messages. Later you should add REAL messages you collect
(remove personal info first!) to data/real_messages.csv — train.py merges them.

Run:  python scripts/make_dataset.py
Output: data/messages.csv  (columns: text, label)   label = "scam" or "safe"
"""

import csv
import random
from pathlib import Path

random.seed(42)  # same dataset every run -> reproducible results

# ---------- reusable fillers ----------
BANKS = ["SBI", "HDFC", "ICICI", "Axis", "PNB", "Kotak", "Bank of Baroda", "Paytm Payments Bank"]
APPS = ["Paytm", "PhonePe", "GPay", "Amazon", "Flipkart", "Jio", "Airtel"]
AMOUNTS = ["5,000", "10,000", "25,000", "49,999", "1,00,000", "2,50,000", "15 lakh", "25 lakh"]
SHORT_LINKS = ["bit.ly/kyc-upd8", "tinyurl.com/sbi-verify", "cutt.ly/rewardz", "kyc-update.in/login",
               "sbi-yono-update.co", "bit.ly/3xRwin", "is.gd/claimnow", "free-gift-india.xyz",
               "hdfc-netbank-verify.com", "rb.gy/elec-bill"]
NAMES = ["Rahul", "Priya", "Aman", "Neha", "Rohit", "Simran", "Karan", "Anjali", "Vikram", "Pooja"]
TIMES = ["5 baje", "7 pm", "kal subah", "lunch ke baad", "shaam ko", "10 min mein", "Sunday ko"]
PLACES = ["canteen", "library", "metro station", "mall", "ghar", "hostel", "gym", "college gate"]

# ---------- SCAM templates ----------
SCAM_TEMPLATES = [
    "Dear customer aapka {bank} account aaj raat block ho jayega. KYC update karne ke liye turant click kare {link}",
    "Your {bank} account will be suspended today. Update PAN/KYC immediately: {link}",
    "{bank} ALERT: aapka debit card band kar diya gaya hai. Chalu karne ke liye yaha click kare {link}",
    "Congratulations! Aapne {app} lucky draw me Rs {amt} jeeta hai. Claim karne ke liye {link} pe jaye",
    "Badhai ho!! KBC lottery me aapka number select hua hai, prize Rs {amt}. Processing fee Rs 4999 bhejein",
    "Bhai mera phone kharab hai, urgent {amt2} bhej do is UPI pe, kal wapas kar dunga. Kisi ko mat batana",
    "Hello sir {app} se bol rahe hai, aapke account me galti se Rs {amt2} aa gaye hai, OTP batao reverse karne ke liye",
    "Your OTP is being requested to verify refund of Rs {amt2}. Share OTP with our executive on call to receive money",
    "Dear consumer aapka bijli connection aaj raat 9:30 baje kaat diya jayega kyunki pichla bill update nahi hua. Turant call kare 98{num}",
    "Electricity Dept: Your power will be disconnected tonight. Contact officer immediately at 70{num}",
    "Work from home job! Roz Rs {amt2} kamaye sirf YouTube videos like karke. Joining ke liye WhatsApp kare {link}",
    "Part time job offer: earn {amt2}/day from mobile. No experience needed. Register fee only Rs 499 {link}",
    "Aapka {app} reward point Rs {amt2} aaj expire ho raha hai, abhi redeem kare {link}",
    "Your parcel could not be delivered due to incomplete address. Pay Rs 25 redelivery fee here {link}",
    "India Post: aapka parcel warehouse me ruka hai. Address update kare 24 ghante me warna return ho jayega {link}",
    "Sir aapke beta drugs case me police custody me hai, case band karne ke liye abhi Rs {amt} transfer kare",
    "CBI/Customs officer: aapke naam pe illegal parcel pakda gaya hai. Digital arrest se bachne ke liye video call join kare",
    "Aapka SIM card 24 ghante me band ho jayega. Re-verify karne ke liye 1 dabaye ya call kare 80{num}",
    "Free recharge offer! {app} de raha hai 3 mahine free recharge. Abhi claim kare {link}",
    "Get instant loan Rs {amt} without CIBIL check! Approved in 5 min. Download app {link}",
    "Pre-approved loan of Rs {amt} on your PAN. Pay processing charge Rs 1999 to get disbursal today",
    "Income Tax Dept: aapko Rs {amt2} ka refund approve hua hai. Bank details verify kare {link}",
    "Hi dear, main {name} hu, crypto trading se maine 1 hafte me {amt} kamaye. Tum bhi join karo, guaranteed 300% return",
    "Invest Rs 10,000 today and get Rs {amt} in 7 days. 100% guaranteed profit, limited seats {link}",
    "Mummy ye mera naya number hai, purana phone gir gaya. Urgent {amt2} chahiye, is account me bhej do please",
    "Your Netflix subscription has expired. Update payment details to avoid suspension {link}",
    "Aadhaar ko PAN se link nahi kiya toh kal se Rs 10,000 fine lagega. Abhi link kare {link}",
    "Dear user your {app} wallet KYC is pending. Complete within 24 hrs or wallet will be blocked {link}",
    "Scan this QR code to receive Rs {amt2} cashback in your account. Offer valid only today",
    "Aapne {app} pe Rs {amt2} ka order kiya hai. Cancel karna hai toh 1 dabaye ya call kare 91{num}",
    "URGENT: Unusual login on your {bank} netbanking. If not you, verify immediately at {link}",
    "Gas connection KYC pending hai, subsidy band ho jayegi. Officer ko call kare 99{num}",
    "Army officer hu, apna bike sell kar raha hu sasta {amt2} me. Advance bhejo toh courier kar dunga",
    "Telegram group join karo, daily stock tips, 1 din me paisa double. Fees sirf Rs 999 {link}",
    "Your electricity bill of Rs {amt2} is overdue. Pay now via this link to avoid disconnection {link}",
]

# ---------- SAFE templates ----------
SAFE_TEMPLATES = [
    "Bhai {time} {place} pe milte hai, notes le aana",
    "{name} kal ka assignment submit ho gaya kya? Mera abhi tak pending hai",
    "Mummy main {time} tak ghar aa jaunga, khana rakh dena",
    "Kya scene hai aaj? {place} chalna hai {time}?",
    "Happy birthday {name}! Party kab de raha hai?",
    "Rs {amt2} debited from your {bank} A/c XX1234 on 12-Oct via UPI. Not you? Call the number on the back of your card",
    "Your {app} order has been shipped and will be delivered by Thursday",
    "Your OTP for login is 482913. Do not share it with anyone, including bank staff. -{bank}",
    "{bank}: Never share your OTP, PIN or CVV with anyone. Bank never asks for these details on call",
    "Recharge of Rs 299 successful on your {app} number. Validity 28 days",
    "Class {time} cancel ho gayi hai, sir ne group pe bola",
    "{name} ne tujhe yaad kiya, call kar lena jab free ho",
    "Bro match dekhne aa raha hai {time}? {place} pe screen lagi hai",
    "Dear student, mid semester exam schedule has been uploaded on the college portal",
    "Your appointment with Dr. Sharma is confirmed for {time}. Please arrive 10 min early",
    "Papa ne bola hai {time} tak fees jama kar dena, receipt sambhal ke rakhna",
    "Salary of Rs {amt} credited to your {bank} account. Available balance updated",
    "Thank you for shopping at {app}. Rate your experience in the app",
    "Kal practical hai, lab coat le aana bhool mat jana",
    "Movie ke tickets book kar diye, {time} ka show hai {place} wale PVR me",
    "Didi ki shaadi ki date fix ho gayi, December me hai",
    "Aaj gym nahi aa paunga yaar, thoda bukhaar hai",
    "Your {bank} credit card statement is ready. Total due Rs {amt2}, due date 5 Nov",
    "{name} sorry late reply, phone silent pe tha",
    "Library ki book return kar di? Fine lag jayega warna",
    "Bhai pizza order kar raha hu, tera kya mangau?",
    "Electricity bill of Rs {amt2} generated for October. Pay via official app or website before due date",
    "Meeting {time} shift ho gayi hai, sabko bata dena",
    "Ghar pahunch gaya, chinta mat karna",
    "Your {app} refund of Rs {amt2} has been processed to the original payment method",
    "Kal se semester break hai, ghar kab ja raha hai?",
    "Mera hotspot on hai, connect kar le",
    "Jio: You have used 80% of your daily data. Data speed may reduce after limit",
    "Sir I will submit the project report {time}, thoda delay ho gaya",
    "{name} ka number bhej de please, group me add karna hai",
]


def fill(template: str) -> str:
    """Replace {slots} in a template with random realistic values."""
    return template.format(
        bank=random.choice(BANKS),
        app=random.choice(APPS),
        amt=random.choice(AMOUNTS),
        amt2=random.choice(["500", "1,200", "2,000", "3,499", "5,000", "7,800", "10,000"]),
        link=random.choice(SHORT_LINKS),
        num=random.randint(10000000, 99999999),
        name=random.choice(NAMES),
        time=random.choice(TIMES),
        place=random.choice(PLACES),
    )


def light_noise(text: str) -> str:
    """Make messages look more like real typed SMS: random case/punctuation changes."""
    r = random.random()
    if r < 0.15:
        text = text.upper()
    elif r < 0.30:
        text = text.lower()
    if random.random() < 0.2:
        text = text.replace(".", "")
    if random.random() < 0.15:
        text += random.choice(["!!", " pls", " jaldi", " ..."])
    return text


def main():
    rows = set()
    # several variants of every template -> ~ 500 scam + ~ 500 safe messages
    for tpl in SCAM_TEMPLATES:
        for _ in range(15):
            rows.add((light_noise(fill(tpl)), "scam"))
    for tpl in SAFE_TEMPLATES:
        for _ in range(15):
            rows.add((light_noise(fill(tpl)), "safe"))

    rows = list(rows)
    random.shuffle(rows)

    out = Path(__file__).resolve().parent.parent / "data" / "messages.csv"
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["text", "label"])
        writer.writerows(rows)

    n_scam = sum(1 for _, l in rows if l == "scam")
    print(f"Saved {len(rows)} messages to {out}  ({n_scam} scam, {len(rows) - n_scam} safe)")


if __name__ == "__main__":
    main()
