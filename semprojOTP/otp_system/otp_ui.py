import sys, time
from pathlib import Path

# Ensure the core module can be imported
sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st
from walk_otp import generate_secret, generate_otp, verify_otp, OTPConfig

# ── Page Configuration ────────────────────────────────────────────────────────
st.set_page_config(page_title="OTP Standalone Demo", layout="wide", page_icon="🔐")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700&family=JetBrains+Mono:wght@400;700&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
.stApp { background: #0d1117; color: #e6edf3; }

.box { 
    padding: 2.5rem; 
    border-radius: 16px; 
    background: #161b22; 
    border: 1px solid #30363d; 
    height: 100%; 
    min-height: 460px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.2);
}
.otp-display { 
    font-size: 5rem; 
    font-family: 'JetBrains Mono', monospace; 
    color: #3fb950; 
    text-align: center; 
    letter-spacing: 0.75rem; 
    font-weight: 700; 
    padding: 2rem 0; 
    text-shadow: 0 0 20px rgba(63,185,80,0.3); 
}
.title { 
    color: #58a6ff; 
    font-weight: 700; 
    margin-bottom: 1rem; 
    border-bottom: 1px solid #30363d; 
    padding-bottom: 1rem; 
    font-size: 1.5rem;
}
.server-box { border-top: 5px solid #1f6feb; }
.client-box { border-top: 5px solid #238636; }

/* Progress bar styling */
.stProgress > div > div > div > div { background-color: #1f6feb; }

/* Form inputs */
.stTextInput > div > div > input { background: #0d1117 !important; color: #e6edf3 !important; border: 1px solid #30363d !important; font-size: 1.2rem; padding: 0.75rem; }
.stButton > button { background: #238636 !important; color: #fff !important; border: 1px solid #2ea043 !important; font-weight: 600 !important; padding: 0.75rem !important; }
.stButton > button:hover { opacity: 0.85 !important; }
</style>
""", unsafe_allow_html=True)

# ── 100% Standalone State (No FastAPI needed) ─────────────────────────────────
if "demo_secret" not in st.session_state:
    st.session_state["demo_secret"] = generate_secret(32)
    st.session_state["used_counters"] = set()  # Tracks used OTPs to prevent replay attacks
    
secret_k = st.session_state["demo_secret"]
cfg = OTPConfig() # Uses default graph, 30s step, 16 walk steps

# ── UI Layout ─────────────────────────────────────────────────────────────────
st.title("🔐 Standalone Random-Walk OTP Demo")
st.markdown("This dashboard is **100% standalone** (no external server required). It simulates both the Server (generating the OTP) and the Client (verifying it) side-by-side.")
st.markdown("---")

col1, col2 = st.columns(2, gap="large")

# ==============================================================================
# LEFT SIDE: SERVER (OTP GENERATOR)
# ==============================================================================
with col1:
    st.markdown('<div class="box server-box">', unsafe_allow_html=True)
    st.markdown('<h3 class="title">🖥️ Server (OTP Generator)</h3>', unsafe_allow_html=True)
    st.markdown("The server independently computes the OTP for the current 30-second time step using the random graph walk.")
    
    # Streamlit 1.37+ allows auto-refreshing fragments without reloading the whole page!
    if hasattr(st, "fragment"):
        @st.fragment(run_every=1)
        def render_otp():
            otp, counter = generate_otp(secret_k, config=cfg)
            t_rem = cfg.time_step - (int(time.time()) % cfg.time_step)
            
            st.markdown(f'<div class="otp-display">{otp}</div>', unsafe_allow_html=True)
            st.progress(t_rem / cfg.time_step, text=f"Valid for {t_rem}s (Time Window T = {counter})")
        render_otp()
    else:
        # Fallback for older Streamlit versions
        otp, counter = generate_otp(secret_k, config=cfg)
        t_rem = cfg.time_step - (int(time.time()) % cfg.time_step)
        
        st.markdown(f'<div class="otp-display">{otp}</div>', unsafe_allow_html=True)
        st.progress(t_rem / cfg.time_step, text=f"Valid for {t_rem}s (Time Window T = {counter})")
        if st.button("🔄 Refresh Time"):
            st.rerun()
            
    st.markdown("</div>", unsafe_allow_html=True)


# ==============================================================================
# RIGHT SIDE: CLIENT (LOGIN PORTAL)
# ==============================================================================
with col2:
    st.markdown('<div class="box client-box">', unsafe_allow_html=True)
    st.markdown('<h3 class="title">💻 Client (Login Portal)</h3>', unsafe_allow_html=True)
    st.markdown("Enter the OTP shown on the server. It must be valid within the ±1 time window (to account for clock drift).")
    
    st.write("") # spacing
    
    with st.form("verify_form", border=False):
        user_otp = st.text_input("Enter 6-digit OTP:", max_chars=6, placeholder="e.g. 123456")
        st.write("")
        submitted = st.form_submit_button("✅ Verify OTP", use_container_width=True)
        
        if submitted:
            if not user_otp.isdigit() or len(user_otp) != 6:
                st.error("❌ Please enter a valid 6-digit number.")
            else:
                # Direct Python verification (no API call needed)
                is_valid, matched_counter = verify_otp(secret_k, user_otp, config=cfg, window=1)
                
                if not is_valid:
                    st.error("❌ **Verification Failed!** OTP is completely invalid or expired.")
                elif matched_counter in st.session_state["used_counters"]:
                    st.warning("⚠️ **Replay Attack Detected!** This OTP was already used in this time window.")
                else:
                    # Mark this counter as used to prevent replay
                    st.session_state["used_counters"].add(matched_counter)
                    st.success(f"✅ **Verification Successful!** (Matched in time window T={matched_counter})")
                    st.balloons()
                    
    st.markdown("</div>", unsafe_allow_html=True)
