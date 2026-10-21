"""
app.py — the Sachet web app.

Run from the project folder:   streamlit run src/app.py
It opens in your browser at http://localhost:8501

Streamlit re-runs this whole script top to bottom every time the user clicks
something. @st.cache_resource makes sure the model is loaded only once.
"""

import streamlit as st

from predict import MODEL_PATH, check_message

st.set_page_config(page_title="Sachet — Scam Message Checker", page_icon="🛡️", layout="centered")

EXAMPLES = {
    "KYC scam": "Dear customer aapka SBI account aaj raat block ho jayega. KYC update karne ke liye turant click kare sbi-kyc-update.in",
    "Real bank OTP": "Your OTP is 552019 for SBI transaction of Rs 3,200 at Amazon. Do not share it with anyone",
    "OTP scam": "Hello sir PhonePe se bol rahe hai, aapke account me galti se Rs 5,000 aa gaye hai, OTP batao reverse karne ke liye",
    "Family scam": "Mummy mera phone kho gaya, naye number se bol raha hu, 6000 bhej do jaldi, kisi ko mat batana",
    "Normal chat": "Bhai kal 10 baje library aa jana, notes le aana",
}

VERDICT_STYLE = {
    "SCAM": ("🚨", "error", "This looks like a scam. Don't click links, don't share OTP/PIN, don't send money."),
    "SUSPICIOUS": ("⚠️", "warning", "Be careful. Verify with the bank or person through a number you already trust."),
    "LOOKS SAFE": ("✅", "success", "No strong scam signs found. Still, never share your OTP, PIN or CVV with anyone."),
}


@st.cache_resource
def get_model():
    import joblib
    return joblib.load(MODEL_PATH)


# ---------------- page ----------------
st.title("🛡️ Sachet")
st.caption("Paste an SMS or WhatsApp message — Hinglish, Hindi (Roman) or English — and check if it's a scam.")

if not MODEL_PATH.exists():
    st.error("Model not found. Run `python src/train.py` first, then reload this page.")
    st.stop()

model = get_model()

# example buttons fill the text box
if "message" not in st.session_state:
    st.session_state.message = ""

st.write("**Try an example:**")
cols = st.columns(len(EXAMPLES))
for col, (label, text) in zip(cols, EXAMPLES.items()):
    if col.button(label, use_container_width=True):
        st.session_state.message = text

message = st.text_area("Message", key="message", height=140,
                       placeholder="e.g. Aapka bijli connection aaj raat kat jayega, turant call kare...")

if st.button("Check message", type="primary", use_container_width=True):
    if not message.strip():
        st.warning("Paste a message first.")
    else:
        result = check_message(model, message)
        icon, kind, advice = VERDICT_STYLE[result["verdict"]]
        prob = result["scam_probability"]

        getattr(st, kind)(f"### {icon} {result['verdict']}\n{advice}")
        st.progress(float(prob), text=f"Scam probability: {prob:.0%}")

        if result["red_flags"]:
            st.write("**Worth noting:**" if result["verdict"] == "LOOKS SAFE" else "**Why:**")
            for flag in result["red_flags"]:
                st.write(f"- {flag}")
        else:
            st.write("No red-flag patterns found in this message.")

with st.expander("How does Sachet work?"):
    st.markdown(
        """
- **Machine learning model:** a TF-IDF + Logistic Regression classifier trained on ~1,100
  Hinglish/English messages. It reads both whole words and pieces of words, so different
  spellings like *aapka / apka / apke* are understood as similar.
- **Rule layer:** if a message *asks you to share* an OTP, PIN or CVV (and doesn't say
  "do not"), it's marked as a scam no matter what — banks never ask for these.
- **Red flags:** simple patterns (links, urgency, KYC, prizes, threats) shown so you can see
  *why* a message looks suspicious.

Sachet is a student project and can make mistakes. When in doubt, call your bank on the
number printed on your card, or report fraud at **1930** / cybercrime.gov.in.
"""
    )
