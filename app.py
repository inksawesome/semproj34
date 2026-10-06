import streamlit as st
import cv2
import numpy as np
import random
import sys
import os
import torch
import time
from streamlit_autorefresh import st_autorefresh

# Import our custom modules
from mediapipe_face import detect_and_crop_face
from arcface_model import get_embedding
from fas_checker import check_liveness, model as fas_model
from explainability.gradcam import GradCAM, overlay_heatmap
from explainability.frequency_explanation import visualize_frequency_spectrum
from explainability.explanation import generate_explanation
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
from webrtc_liveness import LivenessVideoProcessor
from email_service import send_verification_email, process_email_response, get_request_status

# Import database
from database import register_user, get_all_users, get_user_by_email

# Import OTP system
sys.path.append(os.path.join(os.path.dirname(__file__), 'semprojOTP', 'otp_system'))
from walk_otp import generate_secret, verify_otp, secret_to_b32, b32_to_secret

# ============================================================
# PAGE CONFIGURATION
# ============================================================
st.set_page_config(page_title="Biometric Authentication", page_icon="🔐", layout="centered")

def load_css():
    with open("style.css", "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

load_css()


# ============================================================
# SESSION STATE
# ============================================================
if "page" not in st.session_state:
    st.session_state.page = "home"
if "signup_email" not in st.session_state:
    st.session_state.signup_email = ""
if "verification_token" not in st.session_state:
    st.session_state.verification_token = None
if "email_verified" not in st.session_state:
    st.session_state.email_verified = False
if "authenticated_user" not in st.session_state:
    st.session_state.authenticated_user = None
if "face_matched_email" not in st.session_state:
    st.session_state.face_matched_email = None
if "liveness_passed" not in st.session_state:
    st.session_state.liveness_passed = False
if "final_face_frame" not in st.session_state:
    st.session_state.final_face_frame = None

# ============================================================
# UTILS
# ============================================================
def cosine_similarity(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def match_face(embedding, threshold=0.45):
    users = get_all_users()
    best_match = None
    best_score = -1
    for user in users:
        score = cosine_similarity(embedding, user['embedding'])
        if score > best_score:
            best_score = score
            best_match = user['email']
    if best_score > threshold:
        return best_match, best_score
    return None, best_score

# ============================================================
# HANDLE EMAIL CALLBACK
# ============================================================
email_action = st.query_params.get("email_action")
token = st.query_params.get("token")
if email_action and token:
    result = process_email_response(token, email_action)
    st.query_params.clear()
    if result == "approved":
        st.session_state.email_verified = True
        st.session_state.page = "signup_capture"
        st.success("Email verification successful!")
    else:
        st.error("Access Denied or Token Invalid")
    st.stop()

# ============================================================
# ROUTING
# ============================================================

if st.session_state.page == "home":
    st.title("🔐 Biometric Authentication System")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Sign Up", use_container_width=True):
            st.session_state.page = "signup"
            st.rerun()
    with col2:
        if st.button("Sign In", use_container_width=True):
            st.session_state.page = "signin"
            st.rerun()

# ============================================================
# SIGN UP
# ============================================================
elif st.session_state.page == "signup":
    st.title("📝 Sign Up")
    email = st.text_input("Email Address", value=st.session_state.signup_email)
    if st.button("Send Authentication Email"):
        if email and "@" in email:
            with st.spinner("Sending email..."):
                success, result = send_verification_email(email)
            if success:
                st.session_state.signup_email = email
                st.session_state.verification_token = result
                st.success("Authentication email sent! Check your inbox.")
            else:
                st.error(f"Error: {result}")
        else:
            st.error("Invalid email.")
            
    if st.session_state.verification_token:
        status = get_request_status(st.session_state.verification_token)
        if status == "pending":
            st.warning("Waiting for email confirmation... click the link in your email.")
            if st.button("Check Verification Status"):
                st.rerun()
        elif status == "approved":
            st.session_state.email_verified = True
            st.session_state.page = "signup_capture"
            st.rerun()

elif st.session_state.page == "signup_capture":
    st.title("📷 Capture Face for Enrollment")
    img_buffer = st.camera_input("Take a picture to register your face")
    if img_buffer:
        bytes_data = img_buffer.getvalue()
        cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
        rgb_img = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)
        
        with st.spinner("Extracting facial features..."):
            face_crop, _ = detect_and_crop_face(rgb_img)
            if face_crop is None:
                st.error("No face detected. Please try again.")
            else:
                embedding = get_embedding(face_crop)
                if embedding is None:
                    st.error("Could not generate embedding.")
                else:
                    otp_secret = generate_secret()
                    otp_b32 = secret_to_b32(otp_secret)
                    if register_user(st.session_state.signup_email, embedding, otp_b32):
                        st.success("Successfully registered!")
                        st.session_state.authenticated_user = st.session_state.signup_email
                        st.session_state.page = "dashboard"
                        st.rerun()
                    else:
                        st.error("User already exists or database error.")

# ============================================================
# SIGN IN
# ============================================================
elif st.session_state.page == "signin":
    st.title("🔑 Sign In")
    st.write("Step 1: Face Recognition")
    
    img_buffer = st.camera_input("Take a picture to sign in")
    if img_buffer:
        bytes_data = img_buffer.getvalue()
        cv2_img = cv2.imdecode(np.frombuffer(bytes_data, np.uint8), cv2.IMREAD_COLOR)
        rgb_img = cv2.cvtColor(cv2_img, cv2.COLOR_BGR2RGB)
        
        with st.spinner("Matching face..."):
            face_crop, _ = detect_and_crop_face(rgb_img)
            if face_crop is None:
                st.error("No face detected.")
            else:
                embedding = get_embedding(face_crop)
                matched_email, score = match_face(embedding)
                
                if matched_email:
                    st.success(f"Face recognized as {matched_email}! (Score: {score:.2f})")
                    st.session_state.face_matched_email = matched_email
                    st.session_state.page = "signin_liveness"
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error(f"Face not recognized in database. (Highest score: {score:.2f})")
                    st.info("If you are trying to access a friend's account, use OTP instead.")
                    st.session_state.page = "signin_otp"
                    time.sleep(2)
                    st.rerun()

elif st.session_state.page == "signin_liveness":
    st.title("🛡️ Step 2: Liveness & Anti-Spoofing")
    st.write(f"Authenticating as: **{st.session_state.face_matched_email}**")
    
    # Auto-refresh to check WebRTC state without blocking UI
    count = st_autorefresh(interval=1000, limit=100, key="webrtc_fresher")

    webrtc_ctx = webrtc_streamer(
        key="liveness-check",
        mode=WebRtcMode.SENDRECV,
        video_processor_factory=LivenessVideoProcessor,
        media_stream_constraints={"video": True, "audio": False},
        async_processing=True,
        rtc_configuration=RTCConfiguration({"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]})
    )
    
    if webrtc_ctx.video_processor:
        state = webrtc_ctx.video_processor.state
        if state == "FAILED":
            st.error("Active liveness check failed (Timeout).")
            if st.button("Restart Liveness"):
                st.rerun()
        elif state == "PASSED":
            st.success("Continuous Liveness Challenge Passed!")
            st.session_state.liveness_passed = True
            st.session_state.final_face_frame = webrtc_ctx.video_processor.final_face_frame
            st.session_state.page = "signin_xai"
            st.rerun()
        else:
            st.info("Please follow the instructions on the camera feed.")

elif st.session_state.page == "signin_xai":
    st.title("🔍 Step 3: XAI & Deep Learning Validation")
    image_rgb = st.session_state.final_face_frame
    
    with st.spinner("Running PyTorch Deep Learning Models..."):
        face_crop, _ = detect_and_crop_face(image_rgb)
        
        if face_crop is None:
            st.error("Error extracting face from final liveness frame.")
            if st.button("Retry"):
                st.session_state.page = "signin_liveness"
                st.rerun()
        else:
            is_real_passive, real_prob = check_liveness(face_crop)
            spectrum_img = visualize_frequency_spectrum(face_crop)
            
            # Proper GradCAM hook usage
            input_tensor = torch.tensor(face_crop, dtype=torch.float32).permute(2, 0, 1).unsqueeze(0) / 255.0
            x_freq = torch.zeros_like(input_tensor)
            input_tensor.requires_grad_(True)
            
            gradcam = GradCAM(fas_model, fas_model.spatial_encoder[-1])
            heatmap_raw = gradcam.generate_heatmap(input_tensor, x_freq)
            heatmap_overlay = overlay_heatmap(face_crop, heatmap_raw)
            
            # Prevent memory leak by removing PyTorch hooks
            if hasattr(gradcam, 'hook_handles'):
                for handle in gradcam.hook_handles:
                    handle.remove()
                    
            explanation = generate_explanation(
                spatial_score=real_prob, 
                freq_score=real_prob, # Note: using heuristic score for both temporarily
                active_pass=True, 
                heatmap=heatmap_overlay,
                spectrum=spectrum_img
            )

            if explanation["verdict"] == "SPOOF":
                st.error("Authentication Rejected (SPOOF DETECTED)")
                st.warning(explanation["reasoning"])
            else:
                st.success("Authentication Approved! Granted Access.")
                st.session_state.authenticated_user = st.session_state.face_matched_email
                
            col1, col2 = st.columns(2)
            with col1:
                st.image(heatmap_overlay, caption="Spatial Heatmap (Grad-CAM)")
            with col2:
                st.image(spectrum_img, caption="Frequency Spectrum (FFT)")
                
            if explanation["verdict"] == "REAL":
                if st.button("Go to Dashboard"):
                    st.session_state.page = "dashboard"
                    st.rerun()
            else:
                if st.button("Try Again"):
                    st.session_state.page = "home"
                    st.rerun()

# ============================================================
# OTP SIGN IN
# ============================================================
elif st.session_state.page == "signin_otp":
    st.title("🎟️ Delegated Access (OTP)")
    st.write("Enter the email of the account owner and the temporary OTP they shared with you.")
    
    target_email = st.text_input("Account Owner's Email")
    otp_input = st.text_input("6-Digit OTP", max_chars=8)
    
    if st.button("Verify OTP"):
        user = get_user_by_email(target_email)
        if not user:
            st.error("User not found.")
        else:
            secret_b32 = user['otp_secret_b32']
            secret_bytes = b32_to_secret(secret_b32)
            is_valid, matched_counter = verify_otp(secret_bytes, otp_input)
            
            if is_valid:
                st.success(f"Access granted to {target_email}'s account via OTP!")
                st.session_state.authenticated_user = target_email
                time.sleep(1)
                st.session_state.page = "dashboard"
                st.rerun()
            else:
                st.error("Invalid or expired OTP.")

# ============================================================
# DASHBOARD
# ============================================================
elif st.session_state.page == "dashboard":
    st.title("🏠 Dashboard")
    st.write(f"Welcome, **{st.session_state.authenticated_user}**!")
    
    st.divider()
    st.subheader("Share Access (OTP)")
    st.write("Generate a temporary one-time password to give a friend access to your account.")
    
    user = get_user_by_email(st.session_state.authenticated_user)
    if user:
        secret_bytes = b32_to_secret(user['otp_secret_b32'])
        
        import semprojOTP.otp_system.walk_otp as otp_module
        from otp_animation import render_otp_animation
        
        current_time = time.time()
        time_step = otp_module.DEFAULT_TIME_STEP
        counter = int(current_time // time_step)
        time_remaining = time_step - int(current_time % time_step)
        
        current_otp, _ = otp_module.generate_otp(secret_bytes, counter=counter)
        
        config = otp_module.OTPConfig()
        seed_bytes = otp_module._derive_walk_seed(secret_bytes, counter)
        graph_adj = config.graph.adjacency()
        path = otp_module._perform_walk(seed_bytes, graph_adj, config.graph.num_nodes, config.walk_steps)
        
        render_otp_animation(graph_adj, path, current_otp, counter, time_remaining, time_step)
        
        st.info("Share this code with your friend. It changes every 30 seconds.")
    else:
        st.error("Error loading user profile.")
        
    st.divider()
    if st.button("Log Out"):
        st.session_state.clear()
        st.session_state.page = "home"
        st.rerun()

