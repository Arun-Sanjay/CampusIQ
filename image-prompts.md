# CampusIQ Landing — Image Generation Prompts

Paste each block into ChatGPT (Image generation / GPT-Image). Save the resulting transparent PNG at the path listed under **drop file at**, and the landing will pick it up automatically (the placeholder slots are wired by `data-img` attributes — see "DOM slot" for each).

There is one **shared style preamble** every prompt opens with so all renders share the same dark / violet / cyan aesthetic. After saving each PNG, just refresh `/` — no code changes needed.

---

## Shared style preamble

> Ultra-realistic 3D product render, transparent PNG background (no environment, no floor), studio lighting from above-left and above-right, soft rim light in violet (#A78BFA) and cyan (#22D3EE), faint volumetric fog, glassmorphism on all surfaces with subtle frosted highlights, soft purple-to-cyan emissive glow, a few floating bokeh particles, clean octane-style materials, sharp focus, no text, no logos, no watermarks. Style language: futuristic SaaS hero artwork.

---

## 1. Bento — AI Note Assistant (large tile)

- **DOM slot:** `data-img="bento-note-assistant"`
- **Drop file at:** `frontend/public/img/bento-note-assistant.png`
- **Aspect:** 4:3 (request 1024×768 or larger)

Prompt:

> [shared style preamble]. Subject: a glassy floating book opening into a stream of paper sheets that morph into a glowing chat bubble. The chat bubble is a translucent violet-to-cyan gradient with soft inner glow. Two thin neon-cyan glyph lines float above the pages, suggesting cited document chunks. Centered composition, slight 3/4 angle, transparent background.

---

## 2. Bento — CollegeGPT (small tile)

- **DOM slot:** `data-img="bento-college-gpt"`
- **Drop file at:** `frontend/public/img/bento-college-gpt.png`
- **Aspect:** 1:1 (request 1024×1024)

Prompt:

> [shared style preamble]. Subject: a stylized 3D campus building (modern academic block with rooftop lantern) rendered in dark frosted glass with violet-cyan rim light, with a single translucent speech bubble floating above its roof. The bubble has a soft cyan emissive interior. Centered composition, transparent background.

---

## 3. Bento — Adaptive Quizzes (small tile)

- **DOM slot:** `data-img="bento-adaptive-quiz"`
- **Drop file at:** `frontend/public/img/bento-adaptive-quiz.png`
- **Aspect:** 1:1 (request 1024×1024)

Prompt:

> [shared style preamble]. Subject: three floating glassy quiz answer cards stacked at slight angles, the front card has a glowing cyan checkmark ring and a violet bar indicating progress. Each card is dark frosted glass with a thin violet-cyan border. Slight motion-blur trail on the rear card to suggest difficulty adapting. Transparent background.

---

## 4. Bento — Smart Resume + ATS (small tile)

- **DOM slot:** `data-img="bento-smart-resume"`
- **Drop file at:** `frontend/public/img/bento-smart-resume.png`
- **Aspect:** 1:1 (request 1024×1024)

Prompt:

> [shared style preamble]. Subject: a single glassy resume sheet floating vertically (no readable text on it — only abstract horizontal stripes hinting at lines), with a circular ATS-score gauge ring orbiting around it; the ring is violet at the top filling toward cyan at the bottom, with a single bright filament glow at the meter tip. Transparent background.

---

## 5. Bento — Job Tracker + Fit Scores (small tile)

- **DOM slot:** `data-img="bento-job-tracker"`
- **Drop file at:** `frontend/public/img/bento-job-tracker.png`
- **Aspect:** 1:1 (request 1024×1024)

Prompt:

> [shared style preamble]. Subject: three translucent kanban cards floating in a slight zig-zag column, each card a dark frosted glass tile with a small cyan-to-violet fit-score gauge in the corner. The middle card glows a touch brighter than the others. Faint vertical column lines behind suggesting a board, but no readable text. Transparent background.

---

## 6. Bento — Voice Mock Interview (wide tile, 3:1 aspect)

- **DOM slot:** `data-img="bento-voice-interview"`
- **Drop file at:** `frontend/public/img/bento-voice-interview.png`
- **Aspect:** 16:9 or wider, request **1536×1024**

Prompt:

> [shared style preamble]. Subject: a horizontal row of five glossy spherical AI voice orbs, each a different subtle hue progression from violet (left) through indigo / blue / teal to cyan (right). A continuous neon waveform ribbon arcs across all five orbs like an audio graph, glowing white-cyan at the peaks and violet in the troughs. Faint dotted timeline beneath the orbs. Wide cinematic composition, transparent background.

---

## 7. Showcase — Adaptive Learning Engine (skill graph)

- **DOM slot:** `data-img="adaptive-skill-graph"`
- **Drop file at:** `frontend/public/img/adaptive-skill-graph.png`
- **Aspect:** 4:3, request **1024×768** or larger

Prompt:

> [shared style preamble]. Subject: a stylized 3D directed skill graph — about 10 glowing spherical nodes connected by translucent neon edges. One specific path threading through 4 nodes is highlighted brighter (violet-to-cyan emissive glow) showing the shortest learning path. Smaller nodes are softer violet, the active path is brighter cyan-white. Subtle dotted iso-grid floor for depth. Slight 3/4 perspective, transparent background.

---

## 8. Showcase — Voice Interview Personas

- **DOM slot:** `data-img="interview-personas"`
- **Drop file at:** `frontend/public/img/interview-personas.png`
- **Aspect:** 4:3, request **1024×768** or larger

Prompt:

> [shared style preamble]. Subject: five spherical AI persona avatars arranged in a horizontal row, each one a different metallic translucent finish — round 1 warm violet, round 2 deep navy with an analytical edge highlight, round 3 architectural teal, round 4 amber-violet, round 5 confident cyan. Each orb has a subtle ring around it labeled by tiny tick marks (no readable text). One long progress filament threads horizontally beneath them, glowing brightest at the third orb. Transparent background.

---

## 9. Open Graph image (social share preview)

- **Drop file at:** `frontend/public/og-image.png`
- **Aspect:** 1.91:1, request **1536×1024** then crop to 1200×630, OR request 1024×1024 then expand
- **Then add** `<meta property="og:image" content="/og-image.png" />` to `frontend/index.html` (currently the og:image meta line is intentionally left out — wire it after this asset lands).

Prompt:

> [shared style preamble]. Subject: a wide cinematic hero composition. Center-left: a glassy translucent diamond-orbit emblem (concentric rings, a small violet-cyan core). Center-right: a soft constellation of feature glyphs floating loosely (a tiny chat bubble, a sound wave, a graph node, a resume sheet, a kanban card). Below all of it, three thin horizontal scan-lines in violet-cyan gradient. Pure dark backdrop OK (this one is NOT transparent — fill the canvas with #06070A). Cinematic, premium, no text.

---

## Optional 10. Replacement favicon mark

If you want a more elaborate brand mark than the SVG that's shipped at `frontend/public/favicon.svg`, generate this and convert to a 64×64 PNG/ICO:

- **Drop file at:** `frontend/public/favicon.png` (and update the link tag in `index.html` if you want to swap)
- **Aspect:** 1:1, request **1024×1024**

Prompt:

> Minimalist SaaS app icon, 1:1, rounded-square dark base (#0F1116) with subtle radial violet glow at center. Inside: two concentric thin rings (#A78BFA on the outer, #22D3EE on the inner), a tiny violet-cyan gradient orb dead-center, and two small accent dots at 3 o'clock (cyan) and 9 o'clock (violet). No text. Clean, geometric, scalable. Solid dark background (not transparent).

---

## Wiring the dropped images

The marketing components currently render a soft gradient placeholder inside each slot via the `.img-slot` rule in `frontend/src/pages/marketing/landing.css`. Once your PNGs land, swap the placeholder to a real `<img>` by editing `FeatureBento.tsx`, `AdaptiveShowcase.tsx`, and `InterviewShowcase.tsx` — replace each `<div className="img-slot" data-img="..." ...>` with:

```tsx
<img
  src="/img/bento-note-assistant.png"
  alt=""
  className="img-slot"
  style={{ objectFit: 'cover', width: '100%', height: '100%' }}
/>
```

(Or just add a `background-image: url(...)` rule in `landing.css` keyed to each `data-img` attribute — that route requires zero JSX changes. Up to you.)

The `data-img` attribute is the join key so a future automation could swap them in bulk.
