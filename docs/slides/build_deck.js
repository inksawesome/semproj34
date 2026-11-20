// Final-review deck (25 slides) for VaultTrust, built from reports/eval/*.json and the report figures.
//   node docs/slides/build_deck.js   (needs pptxgenjs, react, react-dom, react-icons, sharp)
const path = require("path");
const fs = require("fs");
const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa");

const ROOT = path.resolve(__dirname, "..", "..");
const FIG = path.join(ROOT, "docs", "report", "figures");
const EVF = path.join(ROOT, "reports", "eval", "figures");
const J = (n) => JSON.parse(fs.readFileSync(path.join(ROOT, "reports", "eval", n), "utf8"));
const face = J("face_metrics.json"), live = J("liveness_metrics.json"), fas = J("fas_metrics.json");
const sys = J("system_metrics.json"), otp = J("otp_metrics.json"), lat = J("latency_metrics.json");
const T = sys.combinations.deployed, B = sys.combinations.before_continuity_fix;
const pct = (x, d = 1) => (100 * x).toFixed(d) + "%";
const OUT = path.join(__dirname, "VaultTrust_Final_Review.pptx");

const THEME = {
  name: "VaultTrust Ink", headFontFace: "Cambria", bodyFontFace: "Calibri",
  colors: { dk1: "14212B", lt1: "FFFFFF", dk2: "24465A", lt2: "EEF3F6", accent1: "0F7C8C", accent2: "E39B2D",
            accent3: "C8553D", accent4: "3A9E6F", accent5: "7B5EA7", accent6: "8A8F98", hlink: "0F7C8C", folHlink: "7B5EA7" },
};
const HEX = THEME.colors;

async function icon(Comp, color, size = 256) {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size: String(size) }));
  const buf = await sharp(Buffer.from(svg)).png().toBuffer();
  return "image/png;base64," + buf.toString("base64");
}

async function fitImage(slide, file, x, y, w, h, opts = {}) {
  const m = await sharp(file).metadata();
  const r = Math.min(w / m.width, h / m.height);
  const iw = m.width * r, ih = m.height * r;
  slide.addImage({ path: file, x: x + (w - iw) / 2, y: y + (h - ih) / 2, w: iw, h: ih, ...opts });
}

(async () => {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
  pres.title = "VaultTrust – Final Review";
  pres.author = "Magizharasan K, Nilay Kant Shahi, Rwitankar Giri";
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const C = pres.SchemeColor;

  pres.defineSlideMaster({
    title: "Title Dark", background: { color: HEX.dk1 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 1.7, w: 11.7, h: 1.9, fontSize: 40, bold: true,
        color: C.background1, fontFace: "Cambria", valign: "bottom", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 3.8, w: 11.7, h: 1.0, fontSize: 20,
        color: C.accent2, valign: "top", margin: 0 }, text: "" } },
    ],
  });
  pres.defineSlideMaster({
    title: "Content", background: { color: HEX.lt1 },
    margin: [0.5, 0.6, 0.6, 0.6],
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.35, w: 12.1, h: 0.85, fontSize: 30, bold: true,
        color: C.text1, fontFace: "Cambria", valign: "middle", margin: 0 }, text: "" } },
      { text: { text: "VaultTrust  ·  BITE497J Project I  ·  Final Review", options: { x: 0.6, y: 7.05, w: 7, h: 0.3,
        fontSize: 10, color: C.accent6, margin: 0 } } },
    ],
    slideNumber: { x: 12.2, y: 7.05, w: 0.5, h: 0.3, fontSize: 10, color: C.accent6, align: "right" },
  });
  pres.defineSlideMaster({
    title: "Section Dark", background: { color: HEX.dk2 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.8, y: 2.6, w: 11.7, h: 1.4, fontSize: 40, bold: true,
        color: C.background1, fontFace: "Cambria", margin: 0 }, text: "" } },
      { placeholder: { options: { name: "body", type: "body", x: 0.8, y: 4.0, w: 11.7, h: 0.9, fontSize: 20,
        color: C.accent2, margin: 0 }, text: "" } },
    ],
    slideNumber: { x: 12.2, y: 7.05, w: 0.5, h: 0.3, fontSize: 10, color: C.background2, align: "right" },
  });

  const icons = {};
  for (const [k, comp, col] of [["shield", fa.FaShieldAlt, HEX.lt1], ["eye", fa.FaEye, HEX.lt1], ["wave", fa.FaWaveSquare, HEX.lt1],
    ["user", fa.FaUserCheck, HEX.lt1], ["lock", fa.FaLock, HEX.lt1], ["phone", fa.FaMobileAlt, HEX.lt1], ["chart", fa.FaChartBar, HEX.lt1],
    ["link", fa.FaLink, HEX.lt1], ["bug", fa.FaBug, HEX.lt1], ["search", fa.FaSearch, HEX.lt1], ["clock", fa.FaClock, HEX.lt1],
    ["layers", fa.FaLayerGroup, HEX.lt1], ["key", fa.FaKey, HEX.lt1], ["random", fa.FaRandom, HEX.lt1], ["db", fa.FaDatabase, HEX.lt1],
    ["check", fa.FaCheck, HEX.lt1], ["times", fa.FaTimes, HEX.lt1], ["money", fa.FaMoneyBillWave, HEX.lt1]]) {
    icons[k] = await icon(comp, col);
  }
  const circleIcon = (slide, key, x, y, d = 0.62, color = C.accent1) => {
    slide.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color }, line: { color, width: 0 }, objectName: "icon circle " + key });
    slide.addImage({ data: icons[key], x: x + d * 0.24, y: y + d * 0.24, w: d * 0.52, h: d * 0.52, objectName: "icon " + key });
  };
  const card = (slide, x, y, w, h, fill = C.background2) =>
    slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.08, fill: { color: fill }, line: { color: fill, width: 0 } });
  const text = (slide, t, o) => slide.addText(t, { isTextBox: true, margin: 0, fontSize: 16, color: C.text1, valign: "top", ...o });
  const stat = (slide, x, y, w, big, label, color = C.accent1) => {
    text(slide, big, { x, y, w, h: 0.85, fontSize: 44, bold: true, color, fontFace: "Cambria" });
    text(slide, label, { x, y: y + 0.9, w, h: 0.75, fontSize: 14, color: C.text2 });
  };
  const notes = (s, n) => s.addNotes(n);
  const axis = { catAxisLabelColor: "4B5563", valAxisLabelColor: "4B5563", catAxisLabelFontSize: 12, valAxisLabelFontSize: 11,
    catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", dataLabelFontFace: "+mn-lt", dataLabelFontSize: 11,
    dataLabelColor: "1F2937", valGridLine: { color: "E5E7EB", size: 0.75 }, catGridLine: { style: "none" },
    legendFontFace: "+mn-lt", legendFontSize: 12, titleFontFace: "+mn-lt", titleFontSize: 14, titleColor: "1F2937" };
  const SEC = { intro: "Problem and goals", design: "Design", demo: "Demonstration", results: "Results", close: "Conclusion" };

  // 1 ---------------------------------------------------------------- title
  pres.addSection({ title: SEC.intro });
  let s = pres.addSlide({ masterName: "Title Dark", sectionTitle: SEC.intro });
  s.addText("VaultTrust: Step-Up Authentication with Explainable Face Anti-Spoofing and Transaction-Bound OTP", { placeholder: "title" });
  s.addText("Design of an Authentication System Using Fractal Geometry with Graph-Based Random-Walk OTP Generation", { placeholder: "body" });
  text(s, "Magizharasan K (23BIT0319)   ·   Nilay Kant Shahi (23BIT0334)   ·   Rwitankar Giri (23BIT0335)",
    { x: 0.8, y: 5.3, w: 11.7, h: 0.4, fontSize: 16, color: C.background1 });
  text(s, "Guide: Prof. Mohanraj G, Assistant Professor Senior Grade 2  ·  SCORE, VIT Vellore  ·  BITE497J Project I  ·  November 2026",
    { x: 0.8, y: 5.8, w: 11.7, h: 0.4, fontSize: 14, color: "B8C4CE" });
  circleIcon(s, "shield", 0.8, 0.7, 0.8, C.accent1);
  notes(s, "Introduce the team and the project. VaultTrust asks for a live face and the paired phone at the moment a large transfer is made.");

  // 2 ---------------------------------------------------------------- problem
  s = pres.addSlide({ masterName: "Content", sectionTitle: SEC.intro });
  s.addText("A signed-in session can move any amount of money", { placeholder: "title" });
  const probs = [["key", "Stolen password or session", "Nothing proves the person sending money is the one who signed in."],
    ["eye", "Faces are easy to copy", "A photo or video from social media shows the right face to a face-recognition system."],
    ["phone", "OTPs authorise who, not what", "A code typed under pressure approves whatever transfer the attacker set up."]];
  probs.forEach(([ic, h, b], i) => {
    const x = 0.6 + i * 4.1;
    card(s, x, 1.55, 3.8, 3.1);
    circleIcon(s, ic, x + 0.3, 1.8);
    text(s, h, { x: x + 0.3, y: 2.6, w: 3.2, h: 0.8, fontSize: 19, bold: true, valign: "top" });
    text(s, b, { x: x + 0.3, y: 3.45, w: 3.2, h: 1.1, fontSize: 15, color: C.text2 });
  });
  card(s, 0.6, 4.95, 12.1, 1.7, C.text1);
  text(s, "Our question", { x: 0.95, y: 5.15, w: 3, h: 0.4, fontSize: 14, bold: true, color: C.accent2 });
  text(s, "Using only a laptop webcam, a laptop CPU and the user's phone, can we prove at transfer time that the enrolled account holder is physically present – and approves exactly this amount and payee?",
    { x: 0.95, y: 5.55, w: 11.4, h: 0.95, fontSize: 18, color: C.background1 });
  notes(s, "Motivation: authentication is strongest at login and weakest afterwards. PSD2's dynamic linking principle asks for codes bound to amount and payee.");

  // 3 ---------------------------------------------------------------- objectives
  s = pres.addSlide({ masterName: "Content", sectionTitle: SEC.intro });
  s.addText("Five objectives, each measured in the evaluation", { placeholder: "title" });
  const objs = [["wave", "Detect presentation attacks", "Dual-branch spatial + FFT CNN with Grad-CAM explanations"],
    ["eye", "Prove a live response", "Two random challenges, plus face continuity from start to finish"],
    ["user", "Recognise the account holder", "ArcFace matched on a cancelable, revocable template"],
    ["random", "Bind the second factor", "Random-walk OTP seeded by the amount and payee"],
    ["chart", "Measure everything", "A, L, F alone and in all 7 combinations; latency; comparison with prior work"]];
  objs.forEach(([ic, h, b], i) => {
    const y = 1.5 + i * 1.04;
    circleIcon(s, ic, 0.7, y + 0.08, 0.66);
    text(s, h, { x: 1.6, y, w: 4.6, h: 0.45, fontSize: 19, bold: true });
    text(s, b, { x: 1.6, y: y + 0.44, w: 6.2, h: 0.45, fontSize: 15, color: C.text2 });
  });
  card(s, 8.3, 1.5, 4.4, 5.1, C.background2);
  text(s, "Scope", { x: 8.6, y: 1.75, w: 3.8, h: 0.4, fontSize: 18, bold: true, color: C.accent1 });
  text(s, [
    { text: "In: web bank app, step-up at $1,000, face + phone, explanation, evaluation", options: { bullet: true, breakLine: true } },
    { text: "Out: deepfake / virtual-camera injection, 3-D masks, real payment network", options: { bullet: true } }],
    { x: 8.6, y: 2.25, w: 3.85, h: 3.2, fontSize: 15, color: C.text2, paraSpaceAfter: 10 });
  notes(s, "Each objective maps to a measured result in the results section.");

  // 4 ---------------------------------------------------------------- flow
  s = pres.addSlide({ masterName: "Content", sectionTitle: SEC.intro });
  s.addText("Large transfers need the face and the phone, right now", { placeholder: "title" });
  const steps = [["money", "Transfer ≥ $1,000", "Below the limit it settles at once"],
    ["eye", "Live face check", "Calibrate, then 2 random challenges"],
    ["shield", "Verify", "Anti-spoofing · ArcFace · continuity"],
    ["phone", "Phone approves", "QR shows amount and payee"],
    ["lock", "Code checked", "Bound to the transfer; no replay"]];
  steps.forEach(([ic, h, b], i) => {
    const x = 0.6 + i * 2.48;
    card(s, x, 1.7, 2.2, 3.0, i < 3 ? C.background2 : "F3ECF8");
    circleIcon(s, ic, x + 0.78, 1.95, 0.64, i < 3 ? C.accent1 : C.accent5);
    text(s, h, { x: x + 0.15, y: 2.8, w: 1.9, h: 0.75, fontSize: 17, bold: true, align: "center" });
    text(s, b, { x: x + 0.15, y: 3.55, w: 1.9, h: 1.0, fontSize: 14, color: C.text2, align: "center" });
    if (i < 4) s.addShape(pres.shapes.RIGHT_TRIANGLE, { x: x + 2.24, y: 3.05, w: 0.2, h: 0.3, rotate: 90, fill: { color: C.accent6 }, line: { color: C.accent6, width: 0 } });
  });
  text(s, "INHERENCE  –  live, genuine, matching face (A + L + F)", { x: 0.6, y: 4.95, w: 7.2, h: 0.4, fontSize: 15, bold: true, color: C.accent1 });
  text(s, "POSSESSION  –  paired phone, transaction-bound code", { x: 8.05, y: 4.95, w: 4.7, h: 0.4, fontSize: 15, bold: true, color: C.accent5 });
  text(s, "Every decision, with its reasons and evidence, is written to a per-user security log. Three failed face checks or three wrong codes block the transfer.",
    { x: 0.6, y: 5.6, w: 12.1, h: 0.8, fontSize: 16, color: C.text2 });
  notes(s, "Walk through the step-up flow. The face step proves inherence; the phone step proves possession and binds the code to the transfer.");

  // 5 ---------------------------------------------------------------- literature
  s = pres.addSlide({ masterName: "Content", sectionTitle: SEC.intro });
  s.addText("Prior work: excellent in one dataset, weaker everywhere else", { placeholder: "title" });
  const hdr = { bold: true, color: "FFFFFF", fill: { color: HEX.dk2 }, fontSize: 13 };
  const litRows = [
    [{ text: "Work", options: hdr }, { text: "Approach", options: hdr }, { text: "Reported result", options: hdr }, { text: "What it leaves open", options: hdr }],
    ["Yu et al. 2020 (CDCN++)", "Central difference convolution", "ACER 0.2% OULU-NPU P1; HTER 29.8% cross-dataset", "Generalisation to new data"],
    ["Jia et al. 2020 (SSDG)", "Domain generalisation", "HTER 7.4–15.6% leave-one-out", "Needs many source datasets"],
    ["Prokofiev (LCC-FASD)", "MobileNetV3", "AUC 0.921, EER 16.1%", "Same dataset as ours"],
    ["Pan et al. 2007", "Spontaneous blink", "Defeats photos", "Fooled by video replay"],
    ["Deng et al. 2019 (ArcFace)", "Angular-margin loss", "LFW 99.83%", "Recognises the photo too"],
    ["Teoh et al. 2004 (BioHashing)", "Token-keyed projection", "≈0% EER if token is secret", "Raw-level if token stolen"],
    ["RFC 6238 (TOTP)", "HMAC time codes", "Uniform, standard", "Not bound to the transfer"]];
  s.addTable(litRows.map((r, i) => i === 0 ? r : r.map((c) => ({ text: c, options: { fontSize: 13, color: HEX.dk1, fill: { color: i % 2 ? "FFFFFF" : HEX.lt2 } } }))),
    { x: 0.6, y: 1.45, w: 12.1, colW: [2.9, 2.6, 3.7, 2.9], border: { type: "solid", pt: 0.5, color: "D1D9E0" }, rowH: 0.48, valign: "middle" });
  text(s, "Over 20 works surveyed in the report (Chapter 2); every number above is quoted from its source paper.",
    { x: 0.6, y: 5.6, w: 12.1, h: 0.4, fontSize: 13, italic: true, color: C.accent6 });
  notes(s, "Key point: intra-dataset error rates are near zero, cross-dataset error rates are 10-30%. Liveness and recognition each leave a gap the other covers.");

  // 6 ---------------------------------------------------------------- gaps
  s = pres.addSlide({ masterName: "Content", sectionTitle: SEC.intro });
  s.addText("Gaps we set out to close", { placeholder: "title" });
  const gaps = [["layers", "Components measured together", "Recognition, liveness and anti-spoofing are rarely evaluated on the same attacks, alone and combined."],
    ["link", "Active and passive see the same face", "Checks that run separately can each pass on a different presentation – a swap."],
    ["search", "Deployment-camera generalisation", "Public datasets do not look like one laptop webcam; unseen people are rarely tested."],
    ["random", "Codes bound to the payment", "Biometric step-up usually unlocks a session, not one specific transfer."]];
  gaps.forEach(([ic, h, b], i) => {
    const x = 0.6 + (i % 2) * 6.15, y = 1.55 + Math.floor(i / 2) * 2.55;
    card(s, x, y, 5.95, 2.3);
    circleIcon(s, ic, x + 0.3, y + 0.3);
    text(s, h, { x: x + 1.15, y: y + 0.32, w: 4.5, h: 0.6, fontSize: 19, bold: true });
    text(s, b, { x: x + 1.15, y: y + 0.95, w: 4.5, h: 1.2, fontSize: 15, color: C.text2 });
  });
  notes(s, "These four gaps define the project's contributions.");

  // 7 ---------------------------------------------------------------- architecture
  pres.addSection({ title: SEC.design });
  s = pres.addSlide({ masterName: "Content", sectionTitle: SEC.design });
  s.addText("One Python server, three models, a phone that never talks back", { placeholder: "title" });
  await fitImage(s, path.join(FIG, "architecture.png"), 0.6, 1.35, 8.0, 5.55);
  text(s, [
    { text: "Streamlit UI; camera over WebRTC at 640×480, 15 fps", options: { bullet: true, breakLine: true } },
    { text: "MediaPipe landmarks, spatial-frequency CNN, InsightFace ArcFace", options: { bullet: true, breakLine: true } },
    { text: "SQLite with Fernet-encrypted keys; raw face embeddings never stored", options: { bullet: true, breakLine: true } },
    { text: "Phone page computes codes offline; data reaches it only through QR codes", options: { bullet: true } }],
    { x: 8.9, y: 1.6, w: 3.85, h: 4.8, fontSize: 16, color: C.text2, paraSpaceAfter: 14 });
  notes(s, "Architecture overview. Everything runs locally on a CPU-only laptop.");

  // 8 ---------------------------------------------------------------- liveness
  s = pres.addSlide({ masterName: "Content", sectionTitle: SEC.design });
  s.addText("Active liveness: respond to a prompt a video cannot predict", { placeholder: "title" });
  await fitImage(s, path.join(FIG, "liveness_state_machine.png"), 0.6, 1.35, 7.4, 4.3);
  const ch = [["Blink twice", "eye closure above max(0.45, rest + 0.3), twice"], ["Turn left / right", "yaw change above 18°"],
    ["Look up", "pitch change above 12°"], ["Smile", "smile score above max(0.45, rest + 0.25)"]];
  card(s, 8.3, 1.45, 4.4, 4.2);
  text(s, "Two of five challenges, 9 s each", { x: 8.55, y: 1.65, w: 4, h: 0.45, fontSize: 18, bold: true, color: C.accent1 });
  ch.forEach(([a, b], i) => {
    text(s, a, { x: 8.55, y: 2.25 + i * 0.82, w: 4, h: 0.35, fontSize: 16, bold: true });
    text(s, b, { x: 8.55, y: 2.6 + i * 0.82, w: 4, h: 0.4, fontSize: 13, color: C.text2 });
  });
  text(s, "Thresholds are relative to each user's own calibrated baseline, so glasses, a resting smile or a tilted camera don't skew the result.",
    { x: 0.6, y: 5.9, w: 12.1, h: 0.7, fontSize: 16, color: C.text2 });
  notes(s, "MediaPipe Face Landmarker gives 478 landmarks, 52 blendshapes and a head-pose matrix. Processing takes about 11-18 ms per frame.");

  // 9 ---------------------------------------------------------------- swap story
  s = pres.addSlide({ masterName: "Content", sectionTitle: SEC.design });
  s.addText("We broke our own system – then closed the hole", { placeholder: "title" });
  card(s, 0.6, 1.5, 5.9, 4.6, "FBE9E6");
  circleIcon(s, "bug", 0.9, 1.75, 0.62, C.accent3);
  text(s, "10 Oct: the swap attack", { x: 1.75, y: 1.8, w: 4.5, h: 0.5, fontSize: 20, bold: true, color: C.accent3 });
  text(s, [
    { text: "A phone photo was shown during calibration", options: { bullet: true, breakLine: true } },
    { text: "then removed, and a live person did the challenges", options: { bullet: true, breakLine: true } },
    { text: "Anti-spoofing scored only the phone (0.72); liveness saw only the person", options: { bullet: true, breakLine: true } },
    { text: "Each check passed on a different presentation → accepted", options: { bullet: true } }],
    { x: 0.95, y: 2.6, w: 5.3, h: 3.3, fontSize: 16, paraSpaceAfter: 10 });
  card(s, 6.85, 1.5, 5.85, 4.6, "E9F6EF");
  circleIcon(s, "link", 7.15, 1.75, 0.62, C.accent4);
  text(s, "11 Oct: continuity", { x: 8.0, y: 1.8, w: 4.5, h: 0.5, fontSize: 20, bold: true, color: C.accent4 });
  text(s, [
    { text: "Track one face from calibration to the last challenge", options: { bullet: true, breakLine: true } },
    { text: "Gap > 0.7 s, jump > 0.5 face widths or a 2nd face → restart or fail", options: { bullet: true, breakLine: true } },
    { text: "Server: challenge frames must be the same person (ArcFace ≥ 0.35) and pass anti-spoofing", options: { bullet: true, breakLine: true } },
    { text: "Recording replayed as a test: blocked at 70.05 s", options: { bullet: true } }],
    { x: 7.2, y: 2.6, w: 5.25, h: 3.3, fontSize: 16, paraSpaceAfter: 10 });
  text(s, `Spliced swap tests: ${pct(B["A+L+F"].acceptance.swap, 1)} accepted before the fix → ${pct(T["A+L+F"].acceptance.swap, 1)} after (A+L+F)`,
    { x: 0.6, y: 6.3, w: 12.1, h: 0.45, fontSize: 17, bold: true, color: C.text1 });
  notes(s, "Most important design lesson. Genuine recordings never moved more than 0.03 face widths between detections, nor went more than 0.07 s without a face, so the continuity limits leave a wide safety margin.");

  // 10 --------------------------------------------------------------- FAS network
  s = pres.addSlide({ masterName: "Content", sectionTitle: SEC.design });
  s.addText("Passive anti-spoofing: texture and spectrum in two branches", { placeholder: "title" });
  await fitImage(s, path.join(FIG, "fas_network.png"), 0.6, 1.3, 12.1, 3.15);
  const rec = [["Subject-wise split", "no person in two splits"], ["Fine-tune layer3–4", "both ResNet-18 encoders"],
    ["Camera augmentation", "distance, backlight, blur, noise, JPEG"], ["Threshold", "equal-error point on webcam clips"]];
  rec.forEach(([a, b], i) => {
    const x = 0.6 + i * 3.08;
    card(s, x, 4.6, 2.85, 1.45);
    text(s, a, { x: x + 0.2, y: 4.75, w: 2.5, h: 0.45, fontSize: 17, bold: true, color: C.accent1 });
    text(s, b, { x: x + 0.2, y: 5.22, w: 2.5, h: 0.7, fontSize: 14, color: C.text2 });
  });
  text(s, "22.6 M parameters · deployed v5 (threshold 0.185) · median of 10 frames decides", { x: 0.6, y: 6.3, w: 12.1, h: 0.4, fontSize: 15, color: C.text2 });
  notes(s, "The teammates' network. The original model memorised LCC-FASD (AUC 1.0) and accepted phone replays; we rebuilt the training pipeline over versions v2 to v5.");

  // 11 --------------------------------------------------------------- XAI
  s = pres.addSlide({ masterName: "Content", sectionTitle: SEC.design });
  s.addText("Every decision explains itself", { placeholder: "title" });
  await fitImage(s, path.join(FIG, "gradcam_examples.png"), 0.6, 1.3, 5.6, 5.6);
  text(s, [
    { text: "Grad-CAM on layer4 of both branches", options: { bullet: true, breakLine: true } },
    { text: "Branch attribution: spatial vs frequency evidence", options: { bullet: true, breakLine: true } },
    { text: "Radial spectrum and high-frequency energy against live faces", options: { bullet: true, breakLine: true } },
    { text: "Fractal dimension (box counting) – shown, never decides", options: { bullet: true, breakLine: true } },
    { text: "Liveness timeline and plain-language reasons", options: { bullet: true } }],
    { x: 6.6, y: 1.5, w: 6.1, h: 3.3, fontSize: 17, paraSpaceAfter: 10 });
  card(s, 6.6, 5.0, 6.1, 1.6, C.text1);
  text(s, "The explanations exposed a \"blurry = spoof\" bias that rejected backlit real faces – and pointed to the retraining that fixed it.",
    { x: 6.85, y: 5.2, w: 5.6, h: 1.2, fontSize: 16, color: C.background1 });
  notes(s, "LCC-FASD images, not team faces. Everything is computed locally; the unused language-model wrapper was removed.");

  // 12 --------------------------------------------------------------- template
  s = pres.addSlide({ masterName: "Content", sectionTitle: SEC.design });
  s.addText("The face is never stored – only a revocable template", { placeholder: "title" });
  await fitImage(s, path.join(FIG, "template_pipeline.png"), 0.6, 1.3, 12.1, 2.75);
  const t = face.template;
  stat(s, 0.8, 4.4, 2.8, t.raw_vs_protected_corr.toFixed(3), "correlation of raw vs protected scores");
  stat(s, 3.9, 4.4, 2.8, t.same_face_two_keys.mean.toFixed(3), "same face under two keys (unlinkable)");
  stat(s, 7.0, 4.4, 2.8, `${t.revoked_template_scores.accepted} / ${t.revoked_template_scores.n}`, "old templates matched after re-keying");
  stat(s, 10.1, 4.4, 2.6, `${t.match_ms.toFixed(1)} ms`, "per match; 1,024 bytes per user");
  notes(s, "A logistic-map key schedule – this is where the fractal geometry of the title lives – drives a 512-to-256 orthonormal projection. Accuracy is reported with the key known to the matcher, following the BioHashing critique.");

  // 13 --------------------------------------------------------------- OTP
  s = pres.addSlide({ masterName: "Content", sectionTitle: SEC.design });
  s.addText("Random-walk OTP: a code for this transfer only", { placeholder: "title" });
  await fitImage(s, path.join(FIG, "otp_pipeline.png"), 0.6, 1.3, 8.2, 2.7);
  await fitImage(s, path.join(EVF, "otp_graph_walk.png"), 9.1, 1.25, 3.6, 3.6);
  card(s, 0.6, 4.3, 8.2, 1.95, "FBE9E6");
  text(s, "Version 1 defect, found by measuring", { x: 0.85, y: 4.45, w: 7.7, h: 0.4, fontSize: 18, bold: true, color: C.accent3 });
  text(s, "Truncating raw path bytes saw only two node IDs: 20,000 secrets gave just 768 distinct codes (≈ 400 guesses for a 50% break). Version 2 hashes the whole path; Python and JavaScript produce identical codes on 12 test vectors.",
    { x: 0.85, y: 4.9, w: 7.7, h: 1.6, fontSize: 15, color: C.text1 });
  text(s, "64-node small-world graph, start + 16 steps; seeded by HMAC-SHA256(K, time step ‖ hash of transfer)",
    { x: 9.1, y: 4.95, w: 3.6, h: 1.5, fontSize: 13, color: C.text2 });
  notes(s, "This is the Review-1 idea, corrected and made transaction-bound. Codes last 30 s with a 10 s grace window; a used time step cannot be replayed.");

  // 14 --------------------------------------------------------------- demo 1
  pres.addSection({ title: SEC.demo });
  s = pres.addSlide({ masterName: "Content", sectionTitle: SEC.demo });
  s.addText("Demo: sign-in with a live face check", { placeholder: "title" });
  await fitImage(s, path.join(FIG, "ui_signin_liveness.png"), 0.6, 1.35, 6.0, 5.3);
  await fitImage(s, path.join(FIG, "ui_signin_result.png"), 6.85, 1.35, 5.85, 3.9);
  text(s, "Evidence card: 2/2 challenges, anti-spoofing 0.83, face match 0.49 – each with its threshold",
    { x: 6.85, y: 5.45, w: 5.85, h: 0.8, fontSize: 15, color: C.text2 });
  notes(s, "Screenshots from the 10 Oct recording; face pixelated, e-mails blurred. If time permits, show the live demo instead.");

  // 15 --------------------------------------------------------------- demo 2
  s = pres.addSlide({ masterName: "Content", sectionTitle: SEC.demo });
  s.addText("Demo: step-up transfer approved on the phone", { placeholder: "title" });
  await fitImage(s, path.join(FIG, "ui_verify_qr.png"), 0.6, 1.35, 7.4, 5.2);
  await fitImage(s, path.join(FIG, "ui_phone_page.png"), 8.3, 1.35, 4.4, 4.2);
  text(s, "If the laptop's address changes, the phone explains why it has no key; re-pairing needs a fresh face check.",
    { x: 8.3, y: 5.7, w: 4.4, h: 0.9, fontSize: 14, color: C.text2 });
  notes(s, "The transfer QR carries reference, amount and payee. The phone shows them, and reveals the six-digit code only after Approve.");

  // 16 --------------------------------------------------------------- method
  pres.addSection({ title: SEC.results });
  s = pres.addSlide({ masterName: "Content", sectionTitle: SEC.results });
  s.addText("Evaluation: three components, five kinds of attempt", { placeholder: "title" });
  const comps = [["user", "A", "ArcFace on the template"], ["eye", "L", "Liveness + continuity"], ["wave", "F", "Spatial-frequency CNN"]];
  comps.forEach(([ic, k, d], i) => {
    const y = 1.6 + i * 1.3;
    circleIcon(s, ic, 0.7, y, 0.75);
    text(s, k, { x: 1.65, y: y - 0.02, w: 0.8, h: 0.8, fontSize: 34, bold: true, color: C.accent1, fontFace: "Cambria" });
    text(s, d, { x: 2.35, y: y + 0.15, w: 3.6, h: 0.5, fontSize: 17 });
  });
  const cats = [["Genuine", "enrolled person, live", HEX.accent4], ["Impostor", "different live person", HEX.accent3], ["Photo", "still of the right person", HEX.accent3],
    ["Replay", "video on a phone", HEX.accent3], ["Swap", "photo, then a live attacker", HEX.accent3]];
  cats.forEach(([a, b, col], i) => {
    const y = 1.5 + i * 0.86;
    card(s, 6.4, y, 6.3, 0.72);
    s.addShape(pres.shapes.OVAL, { x: 6.6, y: y + 0.22, w: 0.28, h: 0.28, fill: { color: col }, line: { color: col, width: 0 } });
    text(s, a, { x: 7.1, y: y + 0.17, w: 1.7, h: 0.4, fontSize: 17, bold: true });
    text(s, b, { x: 8.8, y: y + 0.19, w: 3.8, h: 0.4, fontSize: 15, color: C.text2 });
  });
  text(s, "Rule: anti-spoofing is only scored on people it never saw in training. Combinations use AND fusion; population of 1,000 attempts, 50% genuine.",
    { x: 0.6, y: 5.95, w: 12.1, h: 0.7, fontSize: 15, color: C.text2 });
  notes(s, `Data: ${face.identities} identities for face recognition; held-out LCC-FASD subjects plus one unseen webcam person for anti-spoofing; 5 webcam videos and ${live.field.genuine_attempts} field attempts for liveness.`);

  // 17 --------------------------------------------------------------- A results
  s = pres.addSlide({ masterName: "Content", sectionTitle: SEC.results });
  s.addText("ArcFace recognises people – including in photos", { placeholder: "title" });
  stat(s, 0.7, 1.6, 3.6, pct(face.protected.EER, 2), "equal error rate on the protected template");
  stat(s, 0.7, 3.25, 3.6, "0", `false accepts in ${face.pairs_impostor.toLocaleString("en-US")} impostor pairs`);
  stat(s, 0.7, 4.9, 3.6, pct(face.attacks_vs_own_template.rate, 1), "photo / replay attacks of the right person accepted", C.accent3);
  s.addChart(pres.charts.BAR, [{ name: "Accepted by ArcFace alone (%)", labels: ["Impostor (different person)", "Genuine attempt", "Photo / replay of the user"],
    values: [100 * face.protected.FAR, 100 * face.attempt_level_protected.recall, 100 * face.attacks_vs_own_template.rate] }],
    { x: 4.8, y: 1.4, w: 7.9, h: 5.3, barDir: "bar", chartColors: [HEX.accent3, HEX.accent4, HEX.accent3], ...axis, showValue: true,
      dataLabelPosition: "outEnd", dataLabelFormatCode: "0.0", valAxisMaxVal: 110, valAxisMinVal: 0, showLegend: false, showTitle: true,
      title: "Accepted by ArcFace alone (%)", catAxisOrientation: "maxMin", varyColors: true });
  notes(s, "Recognition is accurate, but on its own it is not security: it happily matches a photo of the account holder. That is why L and F exist.");

  // 18 --------------------------------------------------------------- L results
  s = pres.addSlide({ masterName: "Content", sectionTitle: SEC.results });
  s.addText("Random challenges stop replays that fool blink-only checks", { placeholder: "title" });
  const lv = [["Replay, blink-only", live.replay_blink_only.rate], ["Replay, random pair", live.pairs.replay.rate],
    ["Photo held still", live.photo.still_pairs.rate], ["Photo tilted", live.photo.tilted_pairs.rate],
    ["Swap, no continuity", sys.l_rates_before_fix.swap / sys.l_rates.genuine], ["Swap, continuity", sys.swap_continuity_pass_given_challenges]];
  s.addChart(pres.charts.BAR, [{ name: "Attacks passing liveness (%)", labels: lv.map((x) => x[0]), values: lv.map((x) => 100 * x[1]) }],
    { x: 0.6, y: 1.4, w: 8.0, h: 5.3, barDir: "col", chartColors: [HEX.accent3, HEX.accent4, HEX.accent4, HEX.accent4, HEX.accent3, HEX.accent2],
      varyColors: true, ...axis, showValue: true, dataLabelPosition: "outEnd", dataLabelFormatCode: "0", valAxisMaxVal: 110, valAxisMinVal: 0,
      showLegend: false, showTitle: true, title: "Attacks passing liveness (%)" });
  card(s, 8.95, 1.5, 3.75, 5.1);
  text(s, "Why it works", { x: 9.2, y: 1.7, w: 3.3, h: 0.4, fontSize: 18, bold: true, color: C.accent1 });
  text(s, [
    { text: `Replays blinked in ${pct(live.achievability.replay.BLINK.rate, 0)} of windows – but never turned, smiled or looked up`, options: { bullet: true, breakLine: true } },
    { text: `0 of ${live.pairs.replay.n} random pairs passed`, options: { bullet: true, breakLine: true } },
    { text: "Quick, aligned swaps pass the motion rules – the identity check on challenge frames stops them", options: { bullet: true, breakLine: true } },
    { text: `Field trial: ${pct(live.field.liveness_pass_rate, 0)} of genuine users passed first time`, options: { bullet: true } }],
    { x: 9.2, y: 2.2, w: 3.3, h: 4.2, fontSize: 14, paraSpaceAfter: 8 });
  notes(s, "Swap bars are for splices whose live part completed the challenges. In the field, most genuine failures were turns or blinks that timed out on 9 Oct while one user was still learning the system.");

  // 19 --------------------------------------------------------------- F results
  s = pres.addSlide({ masterName: "Content", sectionTitle: SEC.results });
  s.addText("Anti-spoofing on unseen people: spatial generalises better", { placeholder: "title" });
  const V = fas.variants;
  s.addChart(pres.charts.BAR, [
    { name: "Spatial only", labels: ["LCC-FASD (12 unseen subjects)", "Webcam (unseen person)"], values: [V.spatial.lcc.AUC, V.spatial.webcam_unseen_person.AUC] },
    { name: "Spatial + frequency", labels: ["LCC-FASD (12 unseen subjects)", "Webcam (unseen person)"], values: [V.fused.lcc.AUC, V.fused.webcam_unseen_person.AUC] }],
    { x: 0.6, y: 1.4, w: 7.4, h: 5.3, barDir: "col", barGrouping: "clustered", chartColors: [HEX.accent1, HEX.dk2], ...axis, showValue: true,
      dataLabelPosition: "outEnd", dataLabelFormatCode: "0.000", valAxisMinVal: 0.5, valAxisMaxVal: 1.0, showLegend: true, legendPos: "b",
      showTitle: true, title: "AUC on held-out data (higher is better)" });
  card(s, 8.3, 1.5, 4.4, 5.1);
  text(s, "What we learned", { x: 8.55, y: 1.7, w: 4, h: 0.4, fontSize: 18, bold: true, color: C.accent1 });
  text(s, [
    { text: `On LCC-FASD the fused model wins (AUC ${V.fused.lcc.AUC.toFixed(2)}, EER ${pct(V.fused.lcc.EER, 0)}) – comparable to published MobileNetV3 (0.92, 16%)`, options: { bullet: true, breakLine: true } },
    { text: "On a new person the frequency branch hurts: it learns camera-specific spectra", options: { bullet: true, breakLine: true } },
    { text: `Unseen person, per attempt: all phone attacks blocked, but ${pct(V.fused.attempt_webcam.BPCER, 0)} of genuine attempts rejected`, options: { bullet: true, breakLine: true } },
    { text: "Fractal dimension alone: AUC ≈ 0.48 (chance)", options: { bullet: true } }],
    { x: 8.55, y: 2.2, w: 3.95, h: 4.3, fontSize: 14, paraSpaceAfter: 8 });
  notes(s, "Honest generalisation result: our webcam data covers only two people. That is the main limitation and the main item of future work.");

  // 20 --------------------------------------------------------------- combinations chart
  s = pres.addSlide({ masterName: "Content", sectionTitle: SEC.results });
  s.addText("Combining components: each one covers another's blind spot", { placeholder: "title" });
  const combos = ["A", "L", "F", "A+L", "A+F", "L+F", "A+L+F"];
  s.addChart(pres.charts.BAR, ["accuracy", "precision", "recall", "f1"].map((k, i) => ({
    name: ["Accuracy", "Precision", "Recall", "F1"][i], labels: combos, values: combos.map((c) => 100 * T[c][k]) })),
    { x: 0.6, y: 1.35, w: 12.1, h: 5.4, barDir: "col", barGrouping: "clustered", chartColors: [HEX.dk1, HEX.accent1, HEX.accent4, HEX.accent2],
      ...axis, valAxisMinVal: 0, valAxisMaxVal: 100, showLegend: true, legendPos: "t", showTitle: false, barGapWidthPct: 60 });
  notes(s, `A alone: accuracy ${pct(T.A.accuracy)}. A+L: accuracy ${pct(T["A+L"].accuracy)}, F1 ${T["A+L"].f1.toFixed(3)}. A+L+F: accuracy ${pct(T["A+L+F"].accuracy)}, precision ${pct(T["A+L+F"].precision)}. Genuine = positive class; 500 genuine + 500 attacks.`);

  // 21 --------------------------------------------------------------- acceptance table
  s = pres.addSlide({ masterName: "Content", sectionTitle: SEC.results });
  s.addText("Who gets through: acceptance by attempt type", { placeholder: "title" });
  const catsK = ["genuine", "impostor", "photo", "replay", "swap"];
  const shade = (v, k) => k === "genuine" ? (v > 0.7 ? "DDF2E6" : "FFF4D6") : (v < 0.01 ? "DDF2E6" : v < 0.3 ? "FFF4D6" : "F9DCD6");
  const head = ["Combination", "Genuine ↑", "Impostor ↓", "Photo ↓", "Replay ↓", "Swap ↓"].map((h) => ({ text: h, options: { ...hdr, fontSize: 15, align: "center" } }));
  const rowsT = combos.map((c) => [{ text: c, options: { bold: true, fontSize: 16, color: HEX.dk1, align: "center" } }]
    .concat(catsK.map((k) => ({ text: (100 * T[c].acceptance[k]).toFixed(1) + "%", options: { fontSize: 16, color: HEX.dk1, align: "center",
      fill: { color: shade(T[c].acceptance[k], k) }, bold: c === "A+L+F" } }))));
  s.addTable([head, ...rowsT], { x: 0.6, y: 1.45, w: 8.3, colW: [1.8, 1.3, 1.3, 1.3, 1.3, 1.3], rowH: 0.58,
    border: { type: "solid", pt: 0.75, color: "FFFFFF" }, valign: "middle" });
  card(s, 9.25, 1.45, 3.45, 4.65, C.text1);
  text(s, "Reading it", { x: 9.5, y: 1.65, w: 3, h: 0.4, fontSize: 18, bold: true, color: C.accent2 });
  text(s, [
    { text: "A stops impostors, not photos", options: { bullet: true, breakLine: true } },
    { text: "L stops photos and replays, not impostors", options: { bullet: true, breakLine: true } },
    { text: "A+L+F: no attack type gets through", options: { bullet: true, breakLine: true } },
    { text: `Cost: genuine acceptance ${pct(T["A+L+F"].recall, 0)} on the first try; about ${pct(1 - Math.pow(1 - T["A+L+F"].recall, 3), 0)} within 3 tries`, options: { bullet: true } }],
    { x: 9.5, y: 2.15, w: 3.0, h: 3.8, fontSize: 15, color: C.background1, paraSpaceAfter: 8 });
  text(s, `If liveness were bypassed (a video that responds to prompts), A+F still blocks ${pct(1 - T["A+F"].acceptance.photo, 0)} of re-imaged faces – F is the defence in depth.`,
    { x: 0.6, y: 6.25, w: 12.1, h: 0.5, fontSize: 15, italic: true, color: C.text2 });
  notes(s, "On our measured attacks A+L already blocks everything and has the best F1; F costs some recall on unseen people but protects against attacks that can perform the challenges.");

  // 22 --------------------------------------------------------------- OTP results
  s = pres.addSlide({ masterName: "Content", sectionTitle: SEC.results });
  s.addText("OTP codes: as uniform as TOTP, bound to the payment", { placeholder: "title" });
  stat(s, 0.7, 1.5, 3.7, otp.distinct.walk_v2.toLocaleString("en-US"), `distinct codes from 20,000 secrets (ideal ${Math.round(otp.distinct.ideal_expected).toLocaleString("en-US")}; v1: 768)`);
  stat(s, 0.7, 3.2, 3.7, otp.uniformity.buckets_100.p_value.toFixed(2), "χ² p-value over 200,000 codes (uniform)");
  stat(s, 0.7, 4.9, 3.7, `0 / ${otp.binding.trials.toLocaleString("en-US")}`, "codes unchanged after a 1-cent edit to the amount");
  await fitImage(s, path.join(EVF, "otp_uniformity.png"), 4.7, 1.45, 8.0, 3.6);
  text(s, `3 guesses per transfer → 3 in a million chance · replayed time steps refused · ${(otp.latency_ms.walk_generate_cached_graph * 1000).toFixed(0)} µs per code with a cached graph`,
    { x: 4.7, y: 5.4, w: 8.0, h: 0.9, fontSize: 15, color: C.text2 });
  notes(s, `Changing one key bit, the time step, the amount, the payee or the reference changed ${otp.binding.mean_digits_changed.amount_1c.toFixed(1)} of 6 digits on average (5.4 for independent codes).`);

  // 23 --------------------------------------------------------------- latency
  s = pres.addSlide({ masterName: "Content", sectionTitle: SEC.results });
  s.addText("Where the seconds go", { placeholder: "title" });
  const st = lat.verify_presence_stages;
  const parts = Object.entries(st).filter(([k]) => k !== "total" && st[k].mean > 1).sort((a, b) => b[1].mean - a[1].mean);
  s.addChart(pres.charts.DOUGHNUT, [{ name: "ms", labels: parts.map(([k]) => k), values: parts.map(([, v]) => Math.round(v.mean)) }],
    { x: 0.6, y: 1.35, w: 6.6, h: 5.4, holeSize: 55, chartColors: [HEX.accent1, HEX.accent2, HEX.accent5, HEX.dk2, HEX.accent6],
      showPercent: true, showValue: false, showLegend: true, legendPos: "b", legendFontFace: "+mn-lt", legendFontSize: 12,
      dataLabelColor: "FFFFFF", dataLabelFontFace: "+mn-lt", dataLabelFontSize: 12, showTitle: false });
  stat(s, 7.6, 1.6, 5, `${lat.mains_reference.verify_min_s}–${lat.mains_reference.verify_mean_s} s`, "verification on mains power (13 Oct)");
  stat(s, 7.6, 3.25, 5, `${lat.unit["liveness_per_frame_ms (landmarks + overlay)"].toFixed(0)} ms`, "per camera frame – live feedback at 15 fps");
  text(s, `ArcFace face detection dominates (≈ ${Math.round(100 * st["ArcFace (detect+align+embed)"].mean / st.total.mean)}% of the time). Pie measured on battery power (${(st.total.mean / 1000).toFixed(1)} s total); cropping faces before ArcFace is the next optimisation.`,
    { x: 7.6, y: 5.0, w: 5.1, h: 1.6, fontSize: 15, color: C.text2 });
  notes(s, "The user's own time is about 8-14 s for the face step: calibration plus two prompts plus verification.");

  // 24 --------------------------------------------------------------- comparison
  s = pres.addSlide({ masterName: "Content", sectionTitle: SEC.results });
  s.addText("How VaultTrust compares with common designs", { placeholder: "title" });
  const yes = { text: "✓", options: { color: HEX.accent4, bold: true, fontSize: 18, align: "center" } };
  const no = { text: "✗", options: { color: HEX.accent3, bold: true, fontSize: 18, align: "center" } };
  const part = { text: "partly", options: { color: "6B7280", fontSize: 14, align: "center" } };
  const na = { text: "–", options: { color: "6B7280", fontSize: 14, align: "center" } };
  const cmp = [
    ["Proves presence at transfer time", no, no, part, part, yes],
    ["Resists photo / replay", na, na, no, part, yes],
    ["Resists swap attacks", na, na, no, no, yes],
    ["Code bound to amount and payee", part, no, na, na, yes],
    ["Biometric template revocable", na, na, no, no, yes],
    ["Explains its decisions", no, no, no, no, yes]];
  const ch2 = ["Property", "Password + SMS", "TOTP app", "Face login", "Face + blink", "VaultTrust"].map((h, i) => ({ text: h, options: { ...hdr, fontSize: 15, align: i ? "center" : "left", fill: { color: i === 5 ? HEX.accent1 : HEX.dk2 } } }));
  s.addTable([ch2, ...cmp.map((r, i) => [{ text: r[0], options: { fontSize: 15, color: HEX.dk1 } }, ...r.slice(1)].map((c) => ({ ...c, options: { ...c.options, fill: { color: i % 2 ? "FFFFFF" : HEX.lt2 } } })))],
    { x: 0.6, y: 1.45, w: 12.1, colW: [3.9, 1.7, 1.5, 1.6, 1.6, 1.8], rowH: 0.62, border: { type: "solid", pt: 0.5, color: "D1D9E0" }, valign: "middle" });
  text(s, `On LCC-FASD our fused CNN (AUC ${V.fused.lcc.AUC.toFixed(2)}) sits in the range of published lightweight models (0.87–0.92); ArcFace's own benchmark is 99.83% on LFW.`,
    { x: 0.6, y: 6.0, w: 12.1, h: 0.6, fontSize: 15, italic: true, color: C.text2 });
  notes(s, "Mechanism-level and dataset-level comparisons are detailed in Chapter 7.8 of the report.");

  // 25 --------------------------------------------------------------- conclusion
  pres.addSection({ title: SEC.close });
  s = pres.addSlide({ masterName: "Title Dark", sectionTitle: SEC.close });
  text(s, "Conclusion", { x: 0.8, y: 0.55, w: 11.7, h: 0.8, fontSize: 36, bold: true, color: C.background1, fontFace: "Cambria" });
  const concl = [["check", `A+L+F let no attack type through; precision ${pct(T["A+L+F"].precision, 0)}`],
    ["check", "A swap attack we found ourselves is closed by face continuity"],
    ["check", "Templates are unlinkable and revocable; OTP codes are uniform and transaction-bound"],
    ["check", "Every decision is explained: Grad-CAM, spectra, liveness timeline, reasons"]];
  concl.forEach(([ic, tx], i) => {
    circleIcon(s, ic, 0.85, 1.65 + i * 0.75, 0.5, C.accent4);
    text(s, tx, { x: 1.6, y: 1.7 + i * 0.75, w: 6.3, h: 0.5, fontSize: 17, color: C.background1 });
  });
  card(s, 8.3, 1.55, 4.3, 3.15, C.text2);
  text(s, "Next steps", { x: 8.55, y: 1.75, w: 3.8, h: 0.4, fontSize: 18, bold: true, color: C.accent2 });
  text(s, [
    { text: "Data from 10+ people and more attack media", options: { bullet: true, breakLine: true } },
    { text: "Domain-generalising anti-spoofing; spatial-first", options: { bullet: true, breakLine: true } },
    { text: "Liveness in the browser; HTTPS and secure key storage", options: { bullet: true, breakLine: true } },
    { text: "Detect deepfake / virtual-camera injection", options: { bullet: true } }],
    { x: 8.55, y: 2.2, w: 3.85, h: 2.4, fontSize: 15, color: C.background1, paraSpaceAfter: 6 });
  text(s, "Thank you  ·  Questions?", { x: 0.8, y: 5.4, w: 11.7, h: 0.9, fontSize: 32, bold: true, color: C.accent2, fontFace: "Cambria" });
  text(s, "105 automated tests · full report: VaultTrust_Final_Report.pdf", { x: 0.8, y: 6.3, w: 11.7, h: 0.4, fontSize: 14, color: "B8C4CE" });
  notes(s, "Close on the main lesson: no single component is enough, and attacks are found by attacking your own system.");

  await pres.writeFile({ fileName: OUT });
  const { applyTheme } = require(process.env.PPTX_SKILL + "/scripts/apply_theme.js");
  await applyTheme(OUT, THEME);
  console.log("saved", OUT);
})().catch((e) => { console.error(e); process.exit(1); });
