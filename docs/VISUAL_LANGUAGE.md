# Agent OS Visual Language

## Direction
The interface combines two complementary visual systems:

1. **Original Line Art Vector** for brand marks, system illustrations, diagrams and lightweight SVG assets.
2. **ReactBits-inspired interaction patterns** for subtle motion, responsive hover states, reveal transitions, ambient particles and interactive surfaces.

ReactBits is a design reference, not a required runtime dependency. The current implementation uses original inline SVG and CSS motion to keep the first visual layer lightweight and self-contained.

## Implemented
- Custom SVG line-art brand mark and hero illustration.
- Animated SVG stroke reveal and slow orbit motion.
- Ambient gradient field and restrained particle motion.
- Hover/focus/active feedback for navigation, modules, metrics and integration cards.
- Page entrance transitions and chat composer focus feedback.
- Arabic RTL as the document default; runtime language switch remains supported.
- prefers-reduced-motion support to minimize non-essential movement.

## Design constraints
- Preserve the existing dark navy / blue / mint palette.
- Prefer SVG/CSS over large raster assets for interface illustration.
- Avoid heavy WebGL/canvas effects in the default dashboard.
- Motion must communicate state or affordance, not distract from work.
- Keep keyboard focus and reduced-motion behavior usable.
- Do not introduce ReactBits dependencies until a specific component requires one and its bundle/runtime cost is justified.

## Reference
- ReactBits: https://reactbits.dev/
