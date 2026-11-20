# VaultTrust — face anti-spoofing + random-walk OTP step-up authentication

Semester project: *Design of an Authentication System Using Fractal Geometry with Graph-Based
Random-Walk OTP Generation*, applied to step-up authorisation of high-value bank transfers.

* **Inherence:** active liveness (random challenges) + passive spatial/frequency CNN anti-spoofing +
  ArcFace matching on a cancelable, chaos-keyed template — all explained (Grad-CAM, branch evidence,
  frequency profile, fractal texture, liveness timeline).
* **Possession:** a phone authenticator that computes random-walk OTPs offline, bound to the exact
  transaction (amount + payee).

```bash
pip install -r requirements.txt
python -m streamlit run app.py
```

* [DEMO.md](DEMO.md) — setup, phone pairing over a hotspot, demo script, examiner Q&A
* [architecture.md](architecture.md) — components, flows, OTP v2 algorithm, data model
* Tests: `python -m pytest tests/test_pipeline.py semprojOTP/otp_system/tests/test_vectors.py -q`
