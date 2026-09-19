import streamlit as st
import cv2
import numpy as np

from mediapipe_face import detect_and_crop_face
from arcface_model import get_embedding

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

def biometric_capture():

    st.subheader("Set Biometric")

    st.write(
        "Position your face clearly in front of the webcam "
        "and capture an image."
    )

    camera_image = st.camera_input(
        "Take a photo"
    )

    if camera_image is None:

        st.info(
            "Click **Take a photo** to capture your face."
        )

        return

    # --------------------------------------------------------
    # Convert webcam image
    # --------------------------------------------------------

    image_bytes = camera_image.getvalue()

    image_array = np.frombuffer(
        image_bytes,
        np.uint8
    )

    image_bgr = cv2.imdecode(
        image_array,
        cv2.IMREAD_COLOR
    )

    if image_bgr is None:

        st.error(
            "Could not process the webcam image."
        )

        return

    # BGR -> RGB
    image_rgb = cv2.cvtColor(
        image_bgr,
        cv2.COLOR_BGR2RGB
    )

    # --------------------------------------------------------
    # MEDIAPIPE
    # --------------------------------------------------------

    st.write("### Face Detection")

    with st.spinner(
        "Detecting face using MediaPipe..."
    ):

        face_crop, bbox = detect_and_crop_face(
            image_rgb
        )

    if face_crop is None:

        st.error(
            "No face detected. "
            "Please position your face clearly "
            "and try again."
        )

        return

    st.success(
        "Face detected successfully!"
    )

    # We deliberately DO NOT display the cropped face.

    # --------------------------------------------------------
    # ARCFACE
    # --------------------------------------------------------

    st.write("### ArcFace")

    with st.spinner(
        "Generating 512-dimensional embedding..."
    ):

        embedding = get_embedding(
            face_crop
        )

    if embedding is None:

        st.error(
            "Failed to generate the face embedding."
        )

        return

    # --------------------------------------------------------
    # STORE EMBEDDING IN SESSION
    # --------------------------------------------------------

    st.session_state.embedding = embedding

    st.success(
        "Biometric Generated Successfully!"
    )

    st.write("### Embedding")

    st.write(
        f"Embedding dimension: **{len(embedding)}**"
    )

    if len(embedding) == 512:

        st.success(
            "ArcFace successfully generated "
            "a 512-dimensional embedding."
        )

    else:

        st.error(
            f"Unexpected embedding dimension: "
            f"{len(embedding)}"
        )

        return

    # --------------------------------------------------------
    # SHOW EMBEDDING
    # --------------------------------------------------------

    if st.button(
        "Show Embeddings",
        key="show_embedding"
    ):

        st.write(
            "### 512-Dimensional ArcFace Embedding"
        )

        st.code(
            np.array2string(
                embedding,
                precision=8,
                separator=", "
            )
        )


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