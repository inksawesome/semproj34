# Streamlit Biometric Authentication Prototype

## Architecture

```text
                    ┌──────────────────────┐
                    │       Streamlit      │
                    │       app.py         │
                    └──────────┬───────────┘
                               │
             ┌─────────────────┼─────────────────┐
             │                 │                 │
             ▼                 ▼                 ▼
      email_service.py   mediapipe_face.py  arcface_model.py
             │                 │                 │
             ▼                 ▼                 ▼
       SMTP email       Face detection      512-D embedding
             │                 │                 │
             ▼                 └────────┬────────┘
       Yes / No link                    │
             │                          ▼
             └──────────────► Authentication result
```

## Current behavior

### Sign Up

1. User selects Sign Up.
2. User enters email.
3. An email containing:
   - Yes, It's Me
   - No, It's Not Me
   is sent.
4. Clicking No changes the request state to denied and the website displays
   Access Denied.
5. Clicking Yes changes the request state to approved.
6. The website displays the Set Biometric step.
7. `st.camera_input()` captures an image.
8. MediaPipe detects the face and produces a bounding box.
9. The face is cropped.
10. ArcFace generates a 512-dimensional embedding.
11. The website displays Biometric Registered Successfully.
12. The vector is hidden until Show Embeddings is clicked.

### Sign In

1. User selects Sign In.
2. No email is requested.
3. Webcam capture is displayed.
4. MediaPipe detects and crops the face.
5. ArcFace generates a 512-dimensional embedding.
6. Because no user database exists yet, the website displays Access Denied.
7. Show Embeddings displays the generated vector.

## Important deployment detail

The links in the email must point to a URL that the user's browser can access.

For local testing, `localhost:8501` in the email will only work if the email is opened
on the same machine. For a real email workflow, use a public HTTPS URL, for example
a deployed Streamlit URL or a secure tunnel.

Set that value in `.env`:

```text
APP_BASE_URL=https://your-public-url
```

## Install

Use a fresh virtual environment.

```bash
pip install -r requirements.txt
```

Then create `.env` from `.env.example` and fill in the SMTP values.

## Run

```bash
streamlit run app.py
```

## Gmail

For Gmail SMTP, use an App Password rather than your normal Gmail password.
The Google account must have 2-Step Verification enabled before an App Password
can be created.

## ArcFace model

The first ArcFace initialization can download the InsightFace `buffalo_l`
model pack, which contains the ResNet50/WebFace600K recognition model.

The model files are relatively large, so the first run may take time.

## Current prototype limitation

The email request state is stored in memory. It is intentionally not PostgreSQL
yet because the current workflow is meant to test the authentication and
biometric pipeline.

For the next version, replace `_requests` in `email_service.py` with persistent
storage and add:

```text
users
-----------------------------
id
email
embedding
created_at
```

Then Sign Up can store the 512-dimensional embedding.

Sign In can retrieve candidate embeddings and use cosine similarity:

```text
similarity = cosine(new_embedding, stored_embedding)

if similarity >= threshold:
    Access Granted
else:
    Access Denied
```

The threshold should be calibrated on representative validation data rather
than blindly choosing a value.
