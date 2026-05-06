# Framework templates

## Framework colors - Quick WCAG contrast notes (using your text colors)
The following is a guide on how to use colors for proper WCAG contrast in the `source/scss/* files.

## Primary base colors
**Light mode examples** (background → text)
- $c_primary_default (or subtle) → $c_text_primary → passes AA (~7–12:1)
- $c_primary_strong ← deeper, more saturated blue — good for pressed/hover states or accents on white/light surfaces
  - $c_primary_strong → $c_text_inverse → passes AA (~9:1+)
  - $c_primary_strong → white ($c_text_inverse) → very safe
- $c_primary_subtle ← very light tint — excellent subtle background / surface

**Dark mode examples**
- $c_primary_default--dark ← noticeably lighter & more vivid than your original suggestion — better visibility and pop on dark surfaces
  - dark surfaces (#12151a–#1e2227) → $c_primary_default--dark → ~4.8–5.5:1 (passes AA normal text)
- $c_primary_strong--dark ← strong, vibrant highlight — good contrast against near-black/dark grays
  - $c_primary_subtle--dark → $c_text_primary--dark → ~11–13:1 (excellent)
  - $c_primary_strong--dark → $c_text_inverse--dark → ~5.2:1 (passes AA normal text)
- $c_primary_subtle--dark ← deep muted blue-gray — subtle surface / card background in dark mode

---

## Secondary base colors
**Light mode examples** (background → text)  
- $c_secondary_default or subtle → $c_text_primary → passes AA easily (10+:1)
  - $c_secondary_default ← your base — bright, friendly accent (excellent contrast on white/light surfaces with dark text: ~10.8:1) 
- $c_secondary_strong → $c_text_inverse → passes AA (~8–10:1)  
  - $c_secondary_strong ← deeper, richer orange-brown for pressed/hover/strong accents (~7–9:1 with white text)
- $c_secondary_subtle ← very soft peachy cream — perfect for subtle backgrounds, cards, or highlights (~12+:1 with primary text)

**Dark mode examples** (background → text)  
- $c_secondary_default--dark → ~5.0–5.8:1 with $c_text_primary--dark (passes AA normal text)
  - $c_secondary_default--dark ← vibrant warm orange — good pop and visibility on dark surfaces (~5.0–5.8:1 with light text on typical dark bg)  
- $c_secondary_subtle--dark → $c_text_primary--dark → excellent (~10+:1) 
  - $c_secondary_strong--dark ← brighter/lighter variant for emphasis — strong contrast (~6+:1 with dark text on near-black)
- $c_secondary_strong--dark → $c_text_inverse--dark → ~5.5+:1 (passes AA normal text)
  - $c_secondary_subtle--dark ← muted deep terracotta-brown — ideal subtle surface/card bg in dark mode (~9–12:1 with light text)

---

## Tertiary base colors
**Light mode examples**  
- $c_tertiary_default ← your base — cheerful & energetic accent (~7.0:1 on white with dark text — solid AA)  
  - $c_tertiary_default or subtle → $c_text_primary → passes AA comfortably (7–12+:1)  
- $c_tertiary_strong ← deeper coral-red for emphasis, pressed/hover states (~4.8–5.2:1 with white text — passes AA normal/large text)  
  - $c_tertiary_strong → $c_text_inverse → passes AA (~4.8+:1 normal text, higher for large text)  
- $c_tertiary_subtle ← soft peachy blush — great for subtle backgrounds, tags, or highlights (~11+:1 with primary text)

**Dark mode examples**  
- $c_tertiary_default--dark ← brightened & slightly desaturated coral — excellent visibility & pop on dark surfaces (~4.9–5.6:1 with light text on typical dark bg)  
  - $c_tertiary_default--dark → ~4.9–5.6:1 with $c_text_primary--dark (passes AA normal text)  
- $c_tertiary_strong--dark ← vivid lighter coral for strong accents — strong contrast (~5.8+:1 with dark text on near-black)  
  - $c_tertiary_strong--dark → $c_text_inverse--dark → ~5.5–6+:1 (passes AA normal text)
- $c_tertiary_subtle--dark ← muted deep terracotta — ideal subtle card/surface background in dark mode (~8–10:1 with light text)
  - $c_tertiary_subtle--dark → $c_text_primary--dark → very good (~9+:1)

---

## Action / CTAs
**Light mode Actions / CTAs**  
- Default/Hover/Pressed surfaces → $c_text_primary (or $c_action_default_text / $c_action_pressed_text) → 5.5–11+:1 (excellent AA, often AAA)  
- Use white text only on very saturated pressed states if needed — but dark text works better here for accessibility & readability  
- Disabled → muted text (gray) → passes AA large text / UI components  

**Dark mode Actions / CTAs**  
- Primary default/hover/pressed → white text ($c_text_primary--dark or explicit white) → 4.6–7+:1 (solid AA normal text)  
- Secondary/Tertiary default/hover/pressed → dark text (26,26,26) → 4.8–6.5:1 on those brighter warm tones (passes AA)  
- Disabled → light gray text on dark muted bg → ~7–10:1 (very readable)  

**General tips**  
- Primary for main CTAs — highest visibility  
- Secondary for alternate/prominent actions  
- Tertiary for destructive/attention-grabbing (e.g., delete, warning) or tertiary choices  
- Always pair with your existing $c_text_ variables for non-CTA text on surfaces
