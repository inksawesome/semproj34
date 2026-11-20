import streamlit as st
import cv2
import numpy as np
import random

from mediapipe_face import detect_and_crop_face
from arcface_model import get_embedding
from liveness import passive_liveness_check, sequence_challenge_check, validate_neutral_baseline

from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import av
import threading
import time

from email_service import (
    send_verification_email,
    process_email_response,
    get_request_status
)


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Biometric Authentication using Fractal Geometry",
    page_icon="🔐",
    layout="centered"
)


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

if "access_denied" not in st.session_state:
    st.session_state.access_denied = False

if "embedding" not in st.session_state:
    st.session_state.embedding = None

if "liveness_stage" not in st.session_state:
    st.session_state.liveness_stage = "neutral"

if "liveness_baseline" not in st.session_state:
    st.session_state.liveness_baseline = None

if "liveness_challenge" not in st.session_state:
    st.session_state.liveness_challenge = None

if "liveness_verified" not in st.session_state:
    st.session_state.liveness_verified = False

if "liveness_final_frame" not in st.session_state:
    st.session_state.liveness_final_frame = None


# ============================================================
# HANDLE EMAIL CALLBACK
# ============================================================

email_action = st.query_params.get("email_action")
token = st.query_params.get("token")


if email_action and token:

    result = process_email_response(
        token,
        email_action
    )

    # Remove parameters from the URL after processing
    st.query_params.clear()

    if result == "approved":

        st.session_state.email_verified = True
        st.session_state.access_denied = False

        st.session_state.page = "email_result"

        st.success("Email verification successful!")

        st.write(
            "Your registration request has been approved."
        )

        st.info(
            "You can now return to the original "
            "registration page."
        )

        st.stop()

    elif result == "denied":

        st.session_state.email_verified = False
        st.session_state.access_denied = True

        st.session_state.page = "email_result"

        st.error("Access Denied")

        st.write(
            "The registration request was rejected."
        )

        st.stop()

    else:

        st.error(
            "This verification link is invalid "
            "or has expired."
        )

        st.stop()


# ============================================================
# COMMON BIOMETRIC FUNCTION
# ============================================================

def _decode_camera_image(camera_image):
    """Decode a Streamlit camera capture into an RGB image."""
    image_array = np.frombuffer(camera_image.getvalue(), np.uint8)
    image_bgr = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    if image_bgr is None:
        return None
    return cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)


def _reset_liveness():
    st.session_state.liveness_stage = "neutral"
    st.session_state.liveness_baseline = None
    st.session_state.liveness_challenge = None
    st.session_state.liveness_verified = False
    st.session_state.embedding = None


# Shared frame buffer for the live webcam callback.  The callback runs in a
# separate thread, so access is protected by a lock.
@st.cache_resource
def _get_frame_store():
    return {
        "lock": threading.Lock(),
        "frames": [],
        "max_frames": 120,
    }


def _clear_frame_buffer():
    store = _get_frame_store()

    with store["lock"]:
        store["frames"].clear()


def _store_frame(frame_rgb):
    store = _get_frame_store()

    with store["lock"]:
        store["frames"].append(frame_rgb.copy())

        if len(store["frames"]) > store["max_frames"]:
            del store["frames"][:-store["max_frames"]]


def _get_frames():
    store = _get_frame_store()

    with store["lock"]:
        return [
            frame.copy()
            for frame in store["frames"]
        ]


def _video_frame_callback(frame):
    image = frame.to_ndarray(format="rgb24")
    _store_frame(image)
    return av.VideoFrame.from_ndarray(image, format="rgb24")


def _reset_liveness():
    st.session_state.liveness_stage = "neutral"
    st.session_state.liveness_baseline = None
    st.session_state.liveness_challenge = None
    st.session_state.liveness_verified = False
    st.session_state.embedding = None
    st.session_state.liveness_final_frame = None
    _clear_frame_buffer()


def _live_camera():
    return webrtc_streamer(
        key="biometric-live-camera",
        mode=WebRtcMode.SENDRECV,
        video_frame_callback=_video_frame_callback,
        media_stream_constraints={"video": True, "audio": False},
        async_processing=True,
        rtc_configuration=RTCConfiguration(
            {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
        ),
    )
frame_count = len(_get_frames())

st.caption(
    f"Webcam frames captured: {frame_count}"
)

def biometric_capture():
    st.subheader("Set Biometric")

    st.write(
        "Complete the continuous webcam liveness challenge before creating your face template."
    )

    if st.button("Restart liveness check", type="secondary"):
        _reset_liveness()
        st.rerun()

    _live_camera()

    stage = st.session_state.liveness_stage

    if stage == "neutral":
        st.info(
            "Step 1 of 2 — Start the camera, look straight at it with both eyes open, "
            "then click **Capture Neutral Baseline**."
        )

        if st.button("Capture Neutral Baseline", type="primary"):
            frames = _get_frames()
            if len(frames) < 8:
                st.error("Not enough webcam frames yet. Keep the camera running for a moment and try again.")
                return

            # Use recent frames to ensure the baseline is stable rather than
            # relying on one still image.
            recent = frames[-20:]
            results = [passive_liveness_check(frame) for frame in recent]
            valid = [result for result in results if result.passed]

            if len(valid) < max(5, len(recent) // 2):
                st.error("Neutral baseline could not be established consistently.")
                st.info("Keep exactly one face centered, well lit, and with both eyes open.")
                return

            metrics = {
                key: float(np.median([r.metrics[key] for r in valid]))
                for key in ("brightness", "sharpness", "face_area", "face_count", "ear", "nose_position")
                if key in valid[0].metrics
            }

            neutral = validate_neutral_baseline(metrics)
            if not neutral.passed:
                st.error("Neutral baseline rejected.")
                for reason in neutral.reasons:
                    st.write(f"• {reason}")
                return

            st.session_state.liveness_baseline = metrics
            st.session_state.liveness_challenge = random.choice(["blink", "turn"])
            st.session_state.liveness_stage = "challenge"
            _clear_frame_buffer()
            st.success("Neutral baseline captured. Now perform the randomized challenge.")
            st.rerun()

        return

    if stage == "challenge":
        challenge = st.session_state.liveness_challenge
        if challenge == "blink":
            st.info(
                "Step 2 of 2 — **Blink once naturally** while the camera is running. "
                "Then click **Verify Liveness**."
            )
        else:
            st.info(
                "Step 2 of 2 — **Turn your head clearly to either side** while the camera is running. "
                "Then click **Verify Liveness**."
            )

        st.caption("The system is recording consecutive webcam frames for the challenge; do not upload or substitute a photo.")

        if st.button("Verify Liveness", type="primary"):
            frames = _get_frames()
            result = sequence_challenge_check(challenge, frames)

            if not result.passed:
                st.error("Active liveness check failed.")
                for reason in result.reasons:
                    st.write(f"• {reason}")
                _clear_frame_buffer()
                return

            st.session_state.liveness_verified = True
            st.session_state.liveness_stage = "verified"
            st.success("Continuous liveness challenge passed.")

            # Use the latest valid frame for face recognition after liveness.
            image_rgb = frames[-1]

            with st.spinner("Checking final face frame..."):
                passive_result = passive_liveness_check(image_rgb)

            if not passive_result.passed:
                st.error("Final face frame failed image-quality checks.")
                for reason in passive_result.reasons:
                    st.write(f"• {reason}")
                return

            st.session_state.liveness_final_frame = image_rgb
            st.rerun()

        return

    # --------------------------------------------------------
    # MEDIAPIPE + ARCFACE after verified liveness
    # --------------------------------------------------------
    image_rgb = st.session_state.get("liveness_final_frame")
    if image_rgb is None:
        st.error("No final verified face frame is available. Restart the liveness check.")
        return

    st.write("### Face Detection")
    with st.spinner("Detecting face using MediaPipe..."):
        face_crop, bbox = detect_and_crop_face(image_rgb)

    if face_crop is None:
        st.error("No face detected. Please restart and position your face clearly.")
        return

    st.success("Face detected successfully!")

    st.write("### ArcFace")
    with st.spinner("Generating 512-dimensional embedding..."):
        embedding = get_embedding(face_crop)

    if embedding is None:
        st.error("Failed to generate the face embedding.")
        return

    st.session_state.embedding = embedding
    st.success("Biometric Generated Successfully!")
    st.write(f"Embedding dimension: **{len(embedding)}**")

    if len(embedding) != 512:
        st.error(f"Unexpected embedding dimension: {len(embedding)}")
        return

    st.success("ArcFace successfully generated a 512-dimensional embedding.")

    if st.button("Show Embeddings", key="show_embedding"):
        st.write("### 512-Dimensional ArcFace Embedding")
        st.code(np.array2string(embedding, precision=8, separator=", "))


# ============================================================
# HOME PAGE
# ============================================================

if st.session_state.page == "home":

    st.title("🔐 Biometric Authentication")

    st.write(
        "Welcome to the biometric authentication system."
    )

    st.write(
        "Choose an option below:"
    )

    col1, col2 = st.columns(2)

    with col1:

        if st.button(
            "Sign Up",
            use_container_width=True
        ):

            st.session_state.page = "signup"
            st.session_state.access_denied = False

            st.rerun()

    with col2:

        if st.button(
            "Sign In",
            use_container_width=True
        ):

            st.session_state.page = "signin"
            st.session_state.access_denied = False

            st.rerun()


# ============================================================
# SIGN UP
# ============================================================

elif st.session_state.page == "signup":

    st.title("📝 Sign Up")

    st.write(
        "Enter your email address to begin registration."
    )

    email = st.text_input(
        "Email Address",
        value=st.session_state.signup_email
    )

    if st.button(
        "Send Authentication Email"
    ):

        if not email:

            st.error(
                "Please enter an email address."
            )

        elif "@" not in email:

            st.error(
                "Please enter a valid email address."
            )

        else:

            with st.spinner(
                "Sending authentication email..."
            ):

                success, result = (
                    send_verification_email(email)
                )

            if success:

                st.session_state.signup_email = email
                st.session_state.verification_token = result
                st.session_state.email_verified = False
                st.session_state.access_denied = False

                st.success(
                    "Authentication email sent successfully!"
                )

                st.info(
                    "Check your email and click "
                    "**Yes, It's Me** to continue."
                )

            else:

                st.error(
                    "Could not send authentication email."
                )

                st.error(
                    str(result)
                )

    # --------------------------------------------------------
    # CHECK VERIFICATION STATUS
    # --------------------------------------------------------

    if st.session_state.verification_token:

        st.divider()

        st.subheader(
            "Email Verification"
        )

        status = get_request_status(
            st.session_state.verification_token
        )

        if status == "pending":

            st.warning(
                "Waiting for email confirmation..."
            )

            st.write(
                "After clicking **Yes, It's Me** "
                "in your email, click the button below."
            )

            if st.button(
                "Check Verification Status"
            ):

                st.rerun()

        elif status == "approved":

            st.session_state.email_verified = True

            st.success(
                "Email Verified ✓"
            )

        elif status == "denied":

            st.session_state.access_denied = True

            st.error(
                "Access Denied"
            )

        # ----------------------------------------------------
        # VERIFIED
        # ----------------------------------------------------

        if st.session_state.email_verified:

            st.divider()

            st.success(
                "Your email has been verified."
            )

            if st.button(
                "Set Biometric"
            ):

                st.session_state.page = "set_biometric"

                st.rerun()


# ============================================================
# SET BIOMETRIC
# ============================================================

elif st.session_state.page == "set_biometric":

    st.title("🔐 Register Biometric")

    if not st.session_state.email_verified:

        st.error(
            "Email verification is required first."
        )

        st.stop()

    biometric_capture()


# ============================================================
# SIGN IN
# ============================================================

elif st.session_state.page == "signin":

    st.title("🔑 Sign In")

    st.write(
        "No email address is required for Sign In."
    )

    st.write(
        "Use the webcam to authenticate using your face."
    )

    biometric_capture()

    # --------------------------------------------------------
    # CURRENT DATABASE-FREE BEHAVIOR
    # --------------------------------------------------------

    if st.session_state.embedding is not None:

        st.divider()

        st.error(
            "Access Denied"
        )

        st.info(
            "Face embedding generated successfully, "
            "but no registered-user database exists yet. "
            "Therefore the embedding cannot currently "
            "be compared against a stored biometric."
        )


# ============================================================
# EMAIL RESULT PAGE
# ============================================================

elif st.session_state.page == "email_result":

    st.title("📧 Email Verification")

    if st.session_state.access_denied:

        st.error(
            "Access Denied"
        )

        st.write(
            "The registration request was rejected."
        )

    elif st.session_state.email_verified:

        st.success(
            "Email Verified ✓"
        )

        st.write(
            "Your email verification was successful."
        )

        st.write(
            "Return to the original browser window "
            "to continue registration."
        )

    if st.button("Go to Home"):

        st.session_state.page = "home"

        st.session_state.email_verified = False
        st.session_state.access_denied = False
        st.session_state.verification_token = None

        st.rerun()
