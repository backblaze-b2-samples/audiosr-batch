# Product

## Register

product

## Users

Podcast networks, oral-history archives, and music-production teams (and the engineers
who serve them) who need to restore and upscale large libraries of degraded audio to
48 kHz. Their context: they have terabytes of low-quality source recordings and want a
batch pipeline that reconstructs high-frequency content on-device and keeps every
artifact — original, enhanced rendition, and provenance sidecar — durably in cloud
storage.

## Product Purpose

A batch audio super-resolution pipeline (Next.js 16 + React 19 + Tailwind v4 +
shadcn/ui frontend, FastAPI backend) with Backblaze B2 as the single storage layer. It
ingests audio, runs the local `versatile_audio_super_resolution` (AudioSR) model to
upscale it to 48 kHz, and writes the enhanced WAV + a JSON sidecar back to B2 — a
concrete demonstration of write amplification at scale (a 1 TB archive becomes 5–10 TB).
Success = a user can ingest a clip, enhance it, hear the difference, and see the
storage-amplification story as a live metric — with every screen production-grade.

## Brand Personality

Confident, precise, quietly professional. Voice is direct and free of hype
("Restore your archive, at scale"). The interface should feel like a modern developer
tool — considered, calm, trustworthy — not a marketing showpiece. The design carries
craft through restraint, letting the audio and the amplification metrics be the story.

## Anti-references

- **Generic AI/SaaS slop.** No gradient text, hero-metric templates, identical
  icon-card grids, tracked uppercase eyebrows, or decorative glassmorphism. These are
  the exact 2026 AI tells this kit exists to help builders avoid.
- **Over-branded / loud.** No heavy brand-color drenching, decorative motion, or flashy
  effects. It is scaffolding to be rebranded, not a hero page.
- **Toy / prototype feel.** No missing states, inconsistent components, or placeholder
  polish. Must read as production-grade.
- **Enterprise-drab.** No Bootstrap-era gray boxes or dense-but-lifeless admin-panel
  look. Considered, like modern dev tools (Linear, GitHub Primer, Stripe).

## Design Principles

- **Practice what you preach.** The kit itself must model the production quality it
  asks agents to produce. Slop here propagates into every project built on it.
- **Neutral foundation, easy to rebrand.** Identity lives in tokens (`globals.css`) and
  one config file. Screens are built from the shared UI kit so a rebrand is a token
  swap, not a rewrite.
- **Earned familiarity over novelty.** Use standard, trusted affordances (top bar +
  side nav, command palette, data tables). The tool disappears into the task.
- **Every state is designed.** Default, hover, focus, active, disabled, loading (skeleton),
  empty (teaches the interface), and error (says what's wrong + offers retry) — never
  half-shipped.
- **Consistency is the feature.** One button vocabulary, one form-control set, one icon
  style across every screen. Divergence is a bug.

## Accessibility & Inclusion

Target **WCAG 2.1 AA**. Body text ≥ 4.5:1, large/bold text ≥ 3:1, visible focus
indicators on every interactive element, full keyboard navigation, correct semantic
landmarks and heading order, labelled form controls, and a `prefers-reduced-motion`
alternative for every animation. Full light and dark theme parity.
