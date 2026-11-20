# Master Prompt: Random-Walk OTP System (TOTP-style, Independent Generation)

## Context
Build a One-Time Password (OTP) authentication module that works like Google Authenticator / TOTP (RFC 6238), but replaces the standard HMAC-SHA1 core with a **random walk on a graph** as the pseudo-random generation function. Both the server and the client must be able to compute the *same* OTP independently, at the same time step, with zero network round-trip needed for generation itself.

This is a second-factor authentication module for a larger project (face-recognition login system). Fractal-geometry-based seed derivation will be integrated later — for now, use a securely generated random secret as the seed. Design the seed-input interface so it can be swapped later without breaking the rest of the system.

## Objective
Implement Model B: independent, synchronized OTP generation on both server and client, using a shared secret established once at enrollment.

## Core Algorithm Spec

### 1. Enrollment (one-time, per user/device)
- Server generates a cryptographically random secret `K` (min 128-bit entropy) when a device is paired.
- `K` is transmitted to the client exactly once, over an already-authenticated channel (e.g., shown as a QR code / delivered during an already-logged-in session).
- Both server and client persist `K` securely (never transmitted again).
- Also generate/store a `graph_config` (the graph structure the walk runs on — see §3) alongside `K`. This can be a fixed shared graph (hardcoded/config file) for now, not user-specific, unless time permits.

### 2. Time-step counter
- `T = floor(current_unix_time / time_step)`, where `time_step` = 30 or 60 seconds (make configurable).
- Assume synced clocks (NTP) between client and server — standard TOTP assumption, don't build custom clock sync.
- Allow a validation window of ±1 step on the server to tolerate minor client/server clock drift.

### 3. Random-walk generation function (replaces HMAC)
- Define a fixed or seed-derived graph `G` (start with a fixed graph: e.g., N nodes, degree-k, generated once and shared as config — not secret).
- Seed the walk's randomness using a PRNG initialized from `HMAC-SHA256(K, T)` or similar — i.e., `K` and `T` combine to deterministically seed *which* random walk gets taken (the walk itself must be deterministic given the seed, even though it "looks" random).
- Take a fixed number of steps `S` (configurable, e.g., 10–20) starting from a seed-determined start node.
- Record the path taken (sequence of visited node IDs or edge labels).
- Encode the path into a byte string (e.g., concatenate node IDs, or edge-transition labels).

### 4. Truncation to OTP
- Hash or directly truncate the encoded path to produce a 6-digit numeric OTP (mirror RFC 4226's dynamic truncation approach: take the encoded byte string, derive an integer, mod 10^6, zero-pad to 6 digits).

### 5. Validity / invalidation
- OTP for time-step `T` is valid only during that window; once `T` increments, the previous OTP is invalid.
- Server must reject reused/expired OTPs (store last-used `T` per user to prevent replay within the same window).

## Server Requirements
- Enrollment endpoint: generate `K`, return it (QR-code payload or raw string) to be paired with a client, mark device as trusted.
- OTP verification endpoint: accept `{user_id/device_id, submitted_otp}`, compute the expected OTP(s) for `T-1, T, T+1`, compare, return valid/invalid, and record `T` used to prevent replay.
- Secure storage for `K` per user/device (encrypted at rest).
- Config for `time_step`, `S` (walk steps), and graph structure.

## Client Requirements
- Store `K` securely after enrollment (e.g., encrypted local storage / keychain).
- Independently compute the OTP every `time_step` seconds using the same algorithm (§2–§4) — no network call required to generate.
- Display the current OTP and countdown to next refresh, for the user to read/enter (or auto-submit, depending on UX choice).

## Security Requirements
- `K` must never be transmitted or logged after the initial enrollment exchange.
- All enrollment transport must happen over TLS and only within an already-authenticated session.
- Rate-limit OTP verification attempts per user/device to prevent brute force (6-digit space is small).
- Log verification failures for anomaly detection (not for this MVP but stub the hook).

## Deliverables
1. `walk_otp.py` (or equivalent) — shared core module implementing §2–§4, usable identically by both server and client.
2. Server app exposing `/enroll` and `/verify` endpoints.
3. Client app (CLI is fine for MVP) that enrolls once and then generates OTPs locally on a loop.
4. Unit tests proving: (a) server and client produce identical OTPs given the same `K`/`T`, (b) OTP changes after `time_step` elapses, (c) expired OTPs are rejected.
5. README explaining the seed-swap point where fractal-derived seeds will later replace the random `K`.

## Suggested Stack (adjust if a different stack fits the project's existing code better)
- Python 3.11+, FastAPI for the server, `cryptography`/`secrets` for key generation, `httpx` or plain `requests` only for enrollment (not for OTP generation).
- Keep the random-walk/OTP core (`walk_otp.py`) as a pure, dependency-light module so it can be imported unchanged by both server and client, and later swapped to a fractal-seeded version.

## Explicitly Out of Scope for This Task
- Fractal-geometry seed derivation (future integration point — just leave `K` as a clean injectable parameter).
- Face recognition / login flow (separate module, being built by a teammate).
- Push-notification delivery model (not using Model A).
