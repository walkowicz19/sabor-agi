---
version: 1
slug: "index-html"
primary_target: "index.html"
related_targets: []
---

# Counter desk

Operate. One shift at the parts counter: sign on, read a bin, open a requisition, approve or refuse.

## Audience and job

A clerk requests a quantity. A manager is the only person who sees unit cost and the only person who can throw the approve lever. Success is a requisition that cannot drive on-hand below zero.

## Direction

Gauge board, seed 33440cdb, composition dial-first. Approved comp: `.impeccable/mocks/decision/assigned.webp`.

The memorable moment is the needle. It shows the requested quantity. Signal red starts at on-hand and is the mark the needle must not pass. Status is a stamped plate, not a hue.

## Do not literalize

The comp's Portuguese subtitle. Product copy is English. Duplicate tick numerals in the generated dial are a defect; each value is drawn once. "Limit" is the on-hand mark, shown by the red wedge, not a second caption.

## Read from the comp

Corners are full circles for dials and shallow 2px rectangles for plates. The bezel is a heavy black ring, not a 1px grid. Elevation is a soft shadow down and to the right. Display type is condensed gothic, tight, heavy. Body type is a workhorse sans. Palette: aluminum `#C9CDC8`, dial face `#F7F8F4`, ink `#1C1F1E`, signal `#D23B2E` only on the live limit.

## Inventory

| Ingredient | Medium | Commitment |
|---|---|---|
| Panel | Generated raster `public/panel.webp` | Brushed aluminum, full bleed |
| Dials, ticks, needle, red wedge | SVG | Needle snaps to the quantity; red starts at on-hand |
| Approve lever | HTML button | On the lead bezel, manager, pending only |
| Plates | HTML on the panel texture | Pending, Approved, Refused, synthetic fixture, unit cost |
| Title | HTML, Barlow Condensed | Oficina Leme, then Parts counter |
| Find, quantity, sign-off | HTML and Lucide | User-specified icon set |
| Portuguese line | Accepted omission | English product copy |

## Unresolved

None in this slice. The server session lasts 30 minutes. Fixture passwords stay in server configuration and out of this bundle.
