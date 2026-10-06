# Neon Candy on a Clean White Lab Table - Style Guide

## Concept
A bold, high-energy, modern visual system built on pure white backgrounds, subtle dot grids, and glassmorphism layered with hyper-saturated neon and soft pastel colors. Designed to feel playful, futuristic, and highly energetic.

## 1. Backgrounds
- **Base:** `#FFFFFF` everywhere. No grays.
- **Texture:** A subtle 24px dot grid `radial-gradient(circle, rgba(10,10,10,0.14) 1px, transparent 1.2px)`.
- **Blobs:** Large, blurred `filter: blur(80px)` neon/pastel blobs placed fixed in the background for glass elements to refract.

## 2. Colors
- **Text:** `#0A0A0A` (primary), `#52525B` (secondary). Never use neon for text (WCAG contrast).
- **Neon Accents:** 
  - Pink: `#FF2E97`
  - Cyan: `#00E5FF`
  - Lime: `#B6FF00`
  - Violet: `#7A5CFF`
  - Orange: `#FF6B00`
  - Yellow: `#FFE600`
- **Pastel Fills (Cards, alerts):**
  - Pink: `#FFD6E8`
  - Sky: `#D6F0FF`
  - Mint: `#D9FFE3`
  - Butter: `#FFF4C2`
  - Lavender: `#E6DBFF`
  - Peach: `#FFE3D1`
- **Rainbow System:** A sweeping `linear-gradient(90deg, ...)` used on primary CTA buttons, active states, and focus rings.

## 3. Liquid Glass
- **Surface:** `rgba(255,255,255,0.45)` with `backdrop-filter: blur(20px) saturate(180%)`.
- **Border:** `1px solid rgba(255,255,255,0.7)`.
- **Inner Glow:** `inset 0 1px 0 rgba(255,255,255,0.9)`.
- **Radii:** Pill shapes (32px) for buttons, large rounded corners (16-24px) for cards and modals.

## 4. Shadows
- **Base Shadows:** Light, wide ambient spread starting at `rgba(10,10,10,0.05)` (sm) and moving to `rgba(10,10,10,0.15)` (xl).
- **Colored Shadows:** Colored blooms on primary neon elements (e.g., `rgba(255,46,151,0.45)`).
- **Hover States:** Elements lift (`translateY(-2px)`) and shadows expand to the next size up.

## 5. Typography
- **Headings & Display:** `Space Grotesk`, tight tracking (`-0.03em`), heavy weights. Display titles use gradient text clips.
- **Body & UI:** `Inter`. Clean, highly readable.
- **Data, Code, IDs:** `Geist Mono`. Used for metrics, node IDs, and OTP digits.

## 6. Motion & Animations
- **Springs/Easings:** `cubic-bezier(0.22, 1, 0.36, 1)` for snappy, bouncy interactions.
- **Hover:** Buttons get a background-size shift for the gradient, lift, and shadow bloom. Active press scales down slightly (`0.97`).
- **Page Load:** Staggered `fadeUp` animations on layout elements (opacity + translateY).
- **Drawings:** Canvas lines animate smoothly, nodes pulse brightly with their active states.

## Streamlit Implementation
Since this is a Streamlit stack, these tokens and styles have been heavily baked into a custom `style.css` which targets Streamlit's internal classes (`.stButton`, `.stTextInput`, `[data-testid="stAlert"]`, etc.) using CSS descendant combinators to aggressively override defaults while maintaining the required business logic.
