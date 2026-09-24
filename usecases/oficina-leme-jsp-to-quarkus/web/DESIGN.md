---
name: Oficina Leme Parts Counter
description: Dial-first gauge board for issuing spare parts against a job.
colors:
  signal: "#D23B2E"
  aluminum: "#C9CDC8"
  face: "#F7F8F4"
  ink: "#1C1F1E"
  plate: "#B7BDB6"
  plate-ghost: "#C5CAC3"
  plate-edge: "#4E554F"
typography:
  display:
    fontFamily: "Barlow Condensed, Arial Narrow, sans-serif"
    fontSize: "clamp(3rem, 5.2vw, 4.75rem)"
    fontWeight: 700
    lineHeight: 0.82
    letterSpacing: "-0.035em"
  title:
    fontFamily: "Barlow Condensed, sans-serif"
    fontSize: "1.15rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "0.16em"
  body:
    fontFamily: "Barlow, Segoe UI, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.35
    letterSpacing: "normal"
  label:
    fontFamily: "Barlow Condensed, sans-serif"
    fontSize: "0.85rem"
    fontWeight: 600
    lineHeight: 1.2
    letterSpacing: "0.1em"
  numeral:
    fontFamily: "Barlow Condensed, Arial Narrow, sans-serif"
    fontSize: "11px"
    fontWeight: 700
    lineHeight: 1
    letterSpacing: "normal"
rounded:
  plate: "2px"
  dial: "9999px"
  lever: "0.55rem"
  lever-knob: "0.2rem"
spacing:
  xs: "0.35rem"
  sm: "0.45rem"
  md: "0.85rem"
  lg: "1.05rem"
  xl: "1.5rem"
components:
  plate:
    backgroundColor: "{colors.plate}"
    textColor: "{colors.ink}"
    rounded: "{rounded.plate}"
    padding: "0.45rem 0.9rem"
    typography: "{typography.label}"
  plate-ghost:
    backgroundColor: "{colors.plate-ghost}"
    textColor: "{colors.ink}"
    rounded: "{rounded.plate}"
    padding: "0.45rem 0.9rem"
  plate-icon:
    backgroundColor: "{colors.plate}"
    textColor: "{colors.ink}"
    rounded: "{rounded.plate}"
    padding: "0.45rem"
    size: "2.6rem"
  plate-status:
    backgroundColor: "{colors.plate}"
    textColor: "{colors.ink}"
    rounded: "{rounded.plate}"
    padding: "0.45rem 0.9rem"
    width: "7.5rem"
  lever-approve:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.face}"
    rounded: "{rounded.lever}"
    padding: "0.7rem 0.35rem 0.75rem"
    width: "5.6rem"
  input-field:
    backgroundColor: "{colors.face}"
    textColor: "{colors.ink}"
    rounded: "{rounded.plate}"
    padding: "0.4rem 0.55rem"
  dial-lead:
    backgroundColor: "{colors.face}"
    textColor: "{colors.ink}"
    rounded: "{rounded.dial}"
    width: "min(23rem, 42vw)"
  dial-queue:
    backgroundColor: "{colors.face}"
    textColor: "{colors.ink}"
    rounded: "{rounded.dial}"
    width: "8.25rem"
---

# Design System: Oficina Leme Parts Counter

## Overview

**Creative North Star: "The Gauge Board"**

Oficina Leme’s counter is a brushed aluminum instrument panel, not an admin console. On-hand is the red limit on an enamel dial; the requested quantity is the needle that must not pass it. The desk reads as hardware: black bezels, condensed gothic numerals, stamped metal plates with four corner fasteners, and a single approve lever on the lead dial’s bezel.

Density is dial-first and spare. One large live dial leads the viewport; smaller queue dials and named plates support it. Status is stamped language—Pending, Approved, Refused—never a hue chip. Signal red appears only on the live limit wedge. The world refuses the admin shell of sidebar, cards, and status chips.

**Key Characteristics:**
- Dial-first gauge board on full-bleed brushed aluminum (`public/panel.webp`)
- Barlow Condensed for display and plate stamps; Barlow for body
- Signal red only on the live on-hand limit; black hub with light lettering
- Stamped plates with four corner fasteners for actions and status
- Approve lever on the lead bezel; Lucide for search, sign-off, and quantity steppers

## Colors

Cool industrial enamel on brushed metal: aluminum field, pale dial face, near-black ink, and one signal red reserved for the live limit.

### Primary
- **Signal Red** (`#D23B2E`): The live on-hand limit wedge on the lead dial only. Also fault alert text on the enamel plate. Never fills buttons, plates, or status stamps.

### Neutral
- **Brushed Aluminum** (`#C9CDC8`): Full-bleed panel field behind `panel.webp`.
- **Enamel Face** (`#F7F8F4`): Dial faces, input fills, selection invert text, hub lettering.
- **Instrument Ink** (`#1C1F1E`): Bezel, ticks, needle, hub fill, body copy, focus ring, approve lever body.
- **Stamped Plate** (`#B7BDB6`): Default plate fill over the panel texture.
- **Ghost Plate** (`#C5CAC3`): Quieter plate fill for sign-off and match rows; also the sign-on plate base.
- **Plate Edge** (`#4E554F`): 1px plate and sign-plate border.

### Named Rules
**The Live Limit Rule.** Signal red appears only on the live dial’s on-hand wedge (and fault text). Status never borrows the hue.

**The Ink Bezel Rule.** Dials sit in a heavy black ring. Light lettering lives on the black hub; dark numerals live on the enamel face.

## Typography

**Display Font:** Barlow Condensed (with Arial Narrow)
**Body Font:** Barlow (with Segoe UI)

**Character:** Condensed gothic stamps for the brand and plates; a workhorse sans for readable counter copy. All plate and lever labels are uppercase with open tracking.

### Hierarchy
- **Display** (700, `clamp(3rem, 5.2vw, 4.75rem)`, line-height 0.82, tracking `-0.035em`): “Oficina Leme” upper left. Uppercase.
- **Title** (600, `1.15rem`, tracking `0.16em`): “Parts counter” under the brand. Uppercase.
- **Body** (400, `16px`, line-height 1.35): Root copy and inherited controls.
- **Label** (600, `0.85rem`, tracking `0.1em`, uppercase): Field labels, lock note, waiting copy, plate stamps.
- **Numeral** (700, `11px`): Dial face ticks. Hub code ~`8.5px`; hub name ~`7px` / 600, both in enamel on ink.

### Named Rules
**The Stamp Case Rule.** Plates, levers, labels, and the brand lockup are uppercase condensed stamps. Do not mix sentence-case UI chrome into the board.

## Layout

Two-column desk grid on wide viewports: lead dial and issue stack on the left (`~1.15fr`), finder and queue dials on the right (`~0.85fr`, min `16rem`). Brand row spans full width upper left / sign-off upper right. Gap `0.35rem 1rem`; padding `1.05rem 1.5rem 0.9rem`. The approve lever stacks absolutely on the lead bezel (`top: 20%`, offset right). Fixture plate sits under the large dial. At `760px` and below, the grid collapses to a single column, lead dial shrinks to `min(100%, 20rem)`, queue dials scroll horizontally, and the lever aligns to the start edge.

## Elevation & Depth

Depth is hardware cast, not UI card lift: soft shadows fall down and to the right under dials, plates, and the lever. Plates also carry inset enamel highlights. The aluminum panel texture provides ambient grain; no floating glass or multi-layer purple glow.

### Shadow Vocabulary
- **Lead dial** (`filter: drop-shadow(8px 16px 10px rgba(28, 31, 30, 0.28))`): Primary instrument presence.
- **Queue dial** (`filter: drop-shadow(4px 8px 6px rgba(28, 31, 30, 0.24))`): Secondary instruments.
- **Plate cast** (`0 8px 12px rgba(28, 31, 30, 0.16)` plus inset highlights): Stamped metal.
- **Lever cast** (`6px 12px 14px rgba(28, 31, 30, 0.3)`): Physical throw control.
- **Sign-on plate** (`0 16px 22px rgba(28, 31, 30, 0.18)`): Heavier dock for credentials.

### Named Rules
**The Cast Shadow Rule.** Shadows are soft, directional, and attached to instruments and plates—never hard offset outlines or floating card stacks.

## Shapes

Full circles for dials and dial hit targets. Shallow 2px rectangles for plates, inputs, faults, and the sign-on plate. The approve lever is a taller rounded block (`0.55rem`) with a rounded handle and square-ish knob. Plate corners carry four fastener dots (radial gradients at 7px inset). Borders are 1px plate-edge, not hairline UI grids.

### Named Rules
**The Fastener Plate Rule.** Interactive chrome is a stamped plate with four corner fasteners on the panel texture—not a bordered card or pill chip.

## Components

### Plates
Stamped metal controls: plate fill, panel texture, four fasteners, uppercase condensed label.
- **Shape:** Shallow rectangle (`2px` radius), border `{colors.plate-edge}`
- **Default / action:** `{colors.plate}` fill; action tracking `0.14em`
- **Ghost:** `{colors.plate-ghost}` for sign-off and match rows
- **Icon:** Min width `2.6rem`; Lucide at `1.05rem`, stroke-width `2` (search, ± quantity, sign-off)
- **Status:** Min width `7.5rem` (narrows on mobile); stamps Pending / Approved / Refused / unit cost / fixture note
- **Disabled:** Opacity `0.55`, wait cursor

### Approve Lever
Manager-only throw on the lead bezel for pending requisitions.
- **Shape:** `5.6rem` wide, ink body, face lettering, rounded `0.55rem`
- **Handle:** Dark graphite column with inset shade and top knob
- **Word:** “Approve” in condensed uppercase; Refuse remains a separate action plate below

### Dials
SVG enamel instruments. Lead ~`min(23rem, 42vw)`; queue `8.25rem` (`6.35rem` on mobile).
- **Bezel:** Ink ring; selected queue hit darkens to `#111413`
- **Face:** Enamel; ticks and condensed numerals in ink
- **Live limit:** Signal wedge from on-hand outward; needle tracks requested quantity when live
- **Hub:** Ink disk with enamel part code and name
- **Motion:** Needle `420ms` cubic-bezier `(0.16, 0.84, 0.24, 1)`; none when `prefers-reduced-motion`

### Inputs / Fields
- **Style:** Enamel fill, ink 1px border, `2px` radius, tabular nums, padding `0.4rem 0.55rem`
- **Focus:** `2px` ink outline, `3px` offset (`:focus-visible`)
- **Stepper value:** Condensed 700 at `1.35rem`, centered in `3.4rem` width

### Sign-on plate
Credential dock on the same aluminum world: ghost plate fill, panel texture, heavier cast shadow, stacked labels and a Lucide-backed Sign on plate action.

### Navigation
No sidebar. Brand lockup upper left; sign-off plate upper right; finder on the right column. Composition stays dial-first.

## Do's and Don'ts

### Do:
- **Do** lead with one large live dial and put the approve lever on its bezel.
- **Do** keep signal red on the live limit (and fault text) only.
- **Do** stamp status as Pending, Approved, or Refused on fastener plates.
- **Do** use Barlow Condensed for brand, plates, dials; Barlow for body; Lucide for search, sign-off, and quantity steppers.
- **Do** ground the board on `public/panel.webp` brushed aluminum with enamel faces and black bezels.

### Don't:
- **Don't** introduce an admin shell: sidebar, content cards, or status chips.
- **Don't** paint plates, levers, or status stamps with signal red.
- **Don't** replace stamped plates with pill chips, soft UI cards, or glyph-only chrome without the plate.
- **Don't** put marketing kickers, eyebrow labels, or Portuguese subtitle lines on the board—product copy stays English counter voice.
- **Don't** draw duplicate tick numerals on a dial; each scale value appears once.
