# TradeTown UI/UX Bible

**Status:** Canonical. Every visual and interaction rule below is either
(a) already implemented and cited to its real file/class, or (b) marked
*(rule, not yet fully enforced)* where the codebase has a known gap. New
UI work should match this document; if a new pattern is genuinely needed,
this document gets updated in the same change, not silently diverged
from.

The one-sentence brief for all of it: **TradeTown should read like a
modern management-sim HUD wrapped around a cozy pixel-art world** — dense
enough to feel like real company data, never so dense it stops being
readable in two seconds (`DESIGN_BIBLE.md`'s "Readable Information"
pillar).

---

## Color Palette

Defined once, in `frontend/tailwind.config.js`, and used nowhere else as
raw hex in component code (component code should always reference the
named token):

| Token | Hex | Used for |
|---|---|---|
| `parchment` | `#f4e6c9` | Primary text on dark panels; background fill for paper-like surfaces (whiteboards, Company Memory, Newspaper). |
| `ink` | `#241c14` | Primary text on light/parchment surfaces; whiteboard body text. |
| `panel` | `#2b2118` | Base background for HUD panels and modals (Pause Menu, Brain Room HUD container). |
| `panelLight` | `#3a2c1f` | Buttons, secondary surfaces, input backgrounds — one step lighter than `panel` for a subtle depth cue without a drop shadow. |
| `gold` | `#d9a441` | Accent — headings, active/hover states, the one color reserved for "this is important or interactive." |
| `bullish` | `#4caf6a` | Positive numbers only (watchlist gains, completed-task status). Never used decoratively. |
| `bearish` | `#d1495b` | Negative numbers only (watchlist losses). Never used decoratively. |

Rules:

- **`gold` is scarce on purpose.** If everything is gold, nothing reads
  as "pay attention here." It's reserved for headings, the currently
  active/hover UI element, and confidence-bar fills.
- **`bullish`/`bearish` never appear together as a generic
  positive/negative pair outside financial numbers.** They are not a
  general-purpose success/error color scheme — a validation error, for
  instance, should not borrow `bearish` red; it isn't a market number.
- **Rooms get their own accent tint**, independent of the UI palette —
  see `LobbyScene.ts`'s `DOORS` array (`0x9be7b0` Scout Office,
  `0xffe08a` CEO Office, `0xc9a3ff` Brain Room, `0xffb4a8` Meeting Room,
  `0xffd9a0` Break Room) and each agent's own tint in `AgentProfiles.ts`.
  These are Phaser-space hex ints, not Tailwind tokens, and are allowed
  to be more varied than the UI palette because they're wayfinding, not
  chrome.

## Fonts

One font family, everywhere: `fontFamily.pixel` = `["Courier New",
ui-monospace, monospace]` (`tailwind.config.js`), applied via the
`font-pixel` utility class. In-world Phaser text objects
(`Whiteboard.ts`, name tags, badges) use `fontFamily: "monospace"`
directly since Phaser doesn't read Tailwind config — the intent is the
same font family, kept in sync manually (there is no shared constant
between the two today; see `KNOWN_LIMITATIONS.md`).

- **Base UI text size is `text-[11px]`** across every modal (Pause,
  Settings, Company Memory, Newspaper). This is intentional and small —
  it reinforces the "terminal/monospace readout" feel appropriate to an
  investment company's internal tooling, without tipping into an
  unreadably dense Bloomberg-terminal density (see `DESIGN_BIBLE.md`'s
  "Bloomberg Terminal" inspiration note: tone and vocabulary only, not
  interaction density).
- **In-world text is smaller still** (`fontSize: "6px"`–`"10px"` in
  Phaser) because it's rendered at high camera zoom (2.5×–5.7×
  depending on room size — see Camera Behavior below), so the effective
  on-screen size is comparable to the UI's 11px despite the raw font-size
  number looking tiny.
- **No second font, ever.** A second typeface would immediately break
  the "one company, one house style" read. If a future feature seems to
  need a different font (a "handwritten" journal effect for Company
  Memory, say), the answer is a different *treatment* of the same
  monospace font (letter-spacing, color, italics via CSS), not a new
  font file.

## Pixel Art Rules

- **Single source of truth**: every sprite comes from
  `assets/cute-fantasy-rpg/` via `scripts/generate-assets.mjs`'s
  generated manifest. No hand-placed image paths anywhere in game code —
  everything goes through `AssetLoader.get(id)`. This is enforced by
  convention today, not by a lint rule (see `KNOWN_LIMITATIONS.md`).
- **`pixelArt: true`** is set once, globally, in `GameManager.ts`'s
  Phaser config — this disables texture smoothing so scaled pixel art
  stays crisp at any zoom level. Any new Phaser game instance or texture
  must inherit this setting, never override it locally.
- **No new art assets without a licensing check.** The pack's license
  terms live in `assets/cute-fantasy-rpg/read_me.txt` (free pack) and `PREMIUM_PACK_LICENSE.txt` (premium pack), and `README.md`
  carries a license note. A new visual need should first be satisfied by
  recoloring/retinting an existing asset (see NPC tint/badge strategy
  below) before adding new art.
- **Palette-swapped sprite + badge for character variety.** The player
  uses `characters/player/player`; each of the nine agents uses its own
  `characters/player/player-<id>` — a palette-swapped copy with
  hair/shirt/pants hue-shifted to that agent's identity color (generated
  by a one-off PIL script, not hand-drawn; see
  animation-config.json's `_comment_agent_variants`). This replaced an
  earlier `sprite.setTint(profile.tint)`-only approach, which washed the
  *whole* sprite one color instead of reading as different clothes. Each
  agent also keeps a small always-visible emoji/glyph badge above its head
  (`AgentProfiles.ts`'s `badge` field) for shape-based identification at a
  glance. Giving the premium pack's modular character rig (separate
  Player_Base/Hair/Chest/Legs layers) a try first, but its animation-row
  layout didn't match this project's verified convention and reverse-
  engineering it reliably wasn't feasible without risking a broken walk
  cycle — the palette-swap approach reuses the *already-verified* frame
  layout, so there's no risk of a broken animation. This is the standing
  pattern for any *new* character-like entity, including every planned
  agent in `AI_AGENT_BIBLE.md`.
- **Right-facing movement mirrors the left-facing animation** rather
  than using a dedicated row, because the sheet only ships one horizontal
  direction (`AnimatedActor.ts`'s `playAnim()`, documented in
  `docs/Architecture.md`'s "Sprite sheet notes").

## Animations & Transitions

- **Scene transitions**: a 250ms camera fade-out, then `scene.start()`,
  handled uniformly by `SceneManager.goTo()` — no scene ever transitions
  without this fade. A fresh scene fades in over 300ms
  (`CameraManager.fadeIn()`). These numbers are deliberately fast (game
  UI convention: transitions under ~300ms read as responsive, not
  sluggish) and are not currently configurable per-scene — they should
  stay uniform unless a specific room has a strong narrative reason not
  to (there isn't one yet).
- **HUD bars animate, never snap.** Confidence and research-progress
  bars in the Brain Room HUD (`ConfidenceBar` in `BrainRoomHud.tsx`) use
  `transition-all duration-500 ease-out` on a width-percentage `<div>` —
  a real CSS transition, not a canvas-drawn bar, specifically so a tick
  update (server pushes every 2s by default) *visibly moves* rather than
  jumping. This is the reference implementation for any future numeric
  readout that updates on a tick cadence (Risk Engine's v0.9 panels
  should follow the same pattern).
- **In-world ambient motion is continuous, not event-triggered**: the
  Brain Room's holographic core (`BrainRoomScene.ts`'s
  `buildHolographicCore`) uses looping Phaser tweens (pulsing rings,
  rotation, a breathing core) purely as atmosphere — it never reacts to
  game state. Monitor-desk screens flicker on independent random-offset
  timers for the same reason: a roomful of identically-timed animations
  reads as artificial in a way slightly desynced ones don't.
- **Name tags and badges follow the sprite every frame**, converting a
  fixed *screen-space* pixel gap into the correct *world-space* offset
  for the room's current camera zoom (`screenGapToWorld()` in
  `AnimatedActor.ts`) — this is why the gap looks visually consistent in
  a tiny room at 5.7× zoom and a large room at 2.5× zoom, and any new
  always-visible in-world UI element (a future agent's status icon, for
  instance) must use the same helper rather than a hardcoded world-space
  offset.

## Menus, HUD, and Window Layouts

Two distinct UI layers exist and should never be confused:

1. **Persistent chrome** — always visible during gameplay:
   `TopStatusBar` (top-left clock + connection status, top-center agent
   roster dots, top-right connection light), `BottomToolbar` (Save /
   Load / Memory / Settings / Pause, bottom-center), and the Brain Room
   HUD (only visible while `currentScene === "BrainRoomScene"`, docked
   top-right).
2. **Modal overlays** — full-screen `bg-black/60` backdrop, centered
   content box, one focused task at a time: Pause Menu, Settings, Company
   Memory, Newspaper, Dialogue Box. **Exactly one of these should be
   meaningfully interactive at once** — see the "Interaction Rules"
   section below for the current gap here and its fix.

Modal box styling is consistent across all of them: `rounded` corners
(small radius, not pill-shaped — this is a management-sim aesthetic, not
a mobile-app one), `shadow-pixel` (`4px 4px 0 rgba(0,0,0,0.6)`, a hard
pixel-art-style drop shadow, never a soft/blurred CSS shadow — blur reads
as photographic and breaks the pixel-art register), and either a `panel`
(dark, e.g. Pause/Settings) or `parchment` (light/paper, e.g. Company
Memory/Newspaper/whiteboards) background depending on whether the surface
represents "a UI panel" or "an in-world paper document."

**Z-index layering** (highest wins): Company Memory / Settings / Dialogue
(`z-50`) sit above Pause Menu (`z-40`), which sits above the Brain Room
HUD and persistent chrome (no explicit `z-*`, effectively `z-0`/document
order). This layering exists so a modal opened *from* the Pause Menu
(Settings) visually sits on top of it rather than behind.

## Notification Style

TradeTown has no toast/snackbar system today — "notifications" are
entirely in-world and in-panel:

- **News items** (`NewsItem`) surface only inside the Newspaper modal and
  the Brain Room HUD's "Recent Discoveries"/"Market Status" sections —
  never as a popup interrupting play. This is a deliberate consequence of
  "No Clutter": an AI company generating a discovery every few ticks
  would produce a toast storm if notifications were push-based instead
  of pull-based (the player opens the newspaper; the newspaper doesn't
  open itself).
- **The "Meeting in progress" pill** in `TopStatusBar` (visible in the
  in-progress screenshots throughout `CHANGELOG.md`) is the one exception
  — a small, persistent, non-blocking status chip, not a dismissible
  toast. This is the reference pattern for any future ambient status
  indicator: a small always-visible chip in the status bar, not an
  interrupting popup.
- **Save status** (`Saving…` / `Saved` / error) renders inline on the
  Save button itself in `BottomToolbar` — again, no popup. The rule
  going forward: *if a status can live next to the control that caused
  it, it should*, rather than becoming a floating notification.

## Dialogue Boxes

`DialogueBox.tsx` is the single interact UI for talking to an agent —
there is deliberately no separate in-world speech bubble (removed during
the v0.2 build specifically because it duplicated `DialogueBox`, see
`CHANGELOG.md`'s v0.2 "Fixed" section). Rules:

- Bottom-center placement, `pointer-events-none` container with a
  `pointer-events-auto` inner box, so it never blocks clicking the rest
  of the screen outside its own bounds.
- Advances on **Space, Enter, `E`, or a direct click** — all four are
  wired to the same `gameStore.advanceDialogue()` call, so there is no
  "wrong" key for a player used to any one convention.
- Speaker name in `gold`, line text in `parchment`, on a `panel/95`
  (95% opacity) background with a `gold` border — the only modal-style
  surface with a colored (not plain dark) border, marking it as
  distinctly conversational rather than a system menu.
- Lines come from `DialogueManager.ts`'s per-agent, per-task-string
  arrays (`AGENT_TASK_LINES`) plus a greeting (`AGENT_GREETINGS`) — never
  generated at interact-time. This keeps dialogue content server-simple
  (no LLM call in the interact path today) and instantly responsive.

## Camera Behavior

Defined once in `CameraManager.ts`, applied identically by every room
scene via `RoomScene`'s shared `create()`:

- **Base zoom is 2.5×.** Any room smaller than the viewport at that zoom
  is zoomed in further, "cover-fit" style (`Math.max(BASE_ZOOM,
  viewportW/roomW, viewportH/roomH)`) so the room always fully fills the
  screen — no letterboxing, ever, matching CSS `background-size: cover`
  by design.
- **Camera follows the player** with `startFollow(target, true, 0.12,
  0.12)` — smoothed (lerped), not a hard snap, and a 32×24px deadzone so
  small movements don't constantly nudge the camera.
- **Bounds always clamp to the room's own dimensions** — the camera can
  never show area outside the room, including above/below a short room's
  top/bottom edge once the player is near a wall (this is why a prop
  placed too close to a room's top wall can end up outside the visible
  camera range even though it's inside the room's own coordinate space —
  see the whiteboard-placement fix in `CHANGELOG.md` for a concrete
  case).
- **The Lobby is the one "outdoor" scene** with substantially more room
  than any interior — its zoom stays at `BASE_ZOOM` (2.5×) rather than
  being cover-fit-forced higher, giving it a deliberately more spacious
  feel than the tight interior offices.

## Accessibility

Honest current-state assessment, not aspirational:

- **Keyboard-first movement (WASD) has no remapping UI today.** A
  settings-level key-remap option is a real, tracked gap — see
  `TASK_BACKLOG.md`'s UI category.
- **No colorblind-safe mode for `bullish`/`bearish`.** Green/red is the
  conventional financial-data pairing but is the single worst color pair
  for the most common form of color blindness (deuteranopia). A
  shape/icon-based supplement (▲/▼ prefix, already partially present via
  the `+`/`-` sign text) is a near-term fix candidate — see
  `KNOWN_LIMITATIONS.md`.
- **Text size is fixed at 11px/6px** with no in-game scaling option.
  This is a real accessibility gap, tracked in `TASK_BACKLOG.md`.
- **No screen-reader support.** The game canvas is inherently
  non-semantic (a `<canvas>` element); even the React-rendered UI layer
  currently has no `aria-*` attributes. This is an honest limitation, not
  a solved problem — see `KNOWN_LIMITATIONS.md`.
- **What *is* handled well today**: every interactive button has a
  visible hover state (`hover:bg-gold hover:text-ink` or
  `hover:brightness-110`), dialogue can be advanced via three different
  input methods (see Dialogue Boxes above), and no gameplay-critical
  information is conveyed by color alone *except* `bullish`/`bearish`
  (flagged above as the one exception needing a fix).

## Visual Hierarchy

The reading order for any new panel, top to bottom, most to least
urgent — this is the literal order the Brain Room HUD's sections follow
today (`BrainRoomHud.tsx`) and should be the default for any new panel:

1. **What time is it / is the system live** (Market Clock, connection
   status) — orientation before content.
2. **Company-wide summary** (Company Status: X of Y agents working,
   average mood/energy) — the one-glance answer to "how's it going."
3. **Per-agent detail** (Agent Status) — one line each, name in `gold`,
   location in muted text, task on its own indented line below.
4. **Active work in progress** (Research Queue, with animated confidence
   bars) — what's actually changing right now.
5. **Reference data** (Watchlist) — slower-changing, still important.
6. **Recent history** (Current Tasks, Recent Discoveries, Market Status)
   — the past, scrollable, least urgent.

A new panel that doesn't fit this "now → summary → detail → history"
shape should be reconsidered before being added — it's a strong signal
the panel is trying to do two jobs at once.

## Interaction Rules

- **One verb set in the world**: WASD to move, `E` to interact
  (dialogue, doors, the newspaper stand), `Escape`/pause-key to pause.
  No context-sensitive verb menu, ever — matching "No Clutter."
- **`E`'s priority order when multiple things overlap**: door-exit beats
  starting a new dialogue beats nothing (`RoomScene.update()`'s
  `interacted && !nearDoor` / `nearDoor && interacted` split, fixed
  during v0.2 specifically because both firing off the same press could
  leave a dialogue box stuck open across a scene transition — see
  `CHANGELOG.md`). Any new interactable added to a room must be checked
  against this same priority chain, not bolted on independently.
- **Rule, not yet fully enforced: only one full-screen modal open at a
  time.** Newspaper and Company Memory are mutually exclusive as of the
  v0.3.1 fix (`gameStore.ts` — opening one now closes the other), but
  Settings and Pause are *intentionally* allowed to coexist (Settings is
  reachable from inside the Pause Menu) — that specific pairing is a
  deliberate exception to the "one modal" rule, not an oversight, and
  should remain the *only* exception. Any new modal must close every
  *other* modal on open except Pause↔Settings.
- **No modal closes on outside-click or `Escape` today.** Every modal's
  only close affordance is its own "Close" button. This is a real,
  tracked gap (see `TASK_BACKLOG.md`'s UI category) — the fix, when it
  lands, should be a single shared hook (e.g. a `useModalEscape(close)`)
  rather than each modal re-implementing its own key listener, to avoid
  the kind of drift that caused the newspaper/memory stacking bug in the
  first place.
- **The player never loses control mid-simulation.** Pausing
  (`GameManager.togglePause()`) pauses every active Phaser scene but does
  *not* pause the backend simulation — NEXUS keeps ticking server-side
  while the client is paused, matching `DESIGN_BIBLE.md`'s "the company
  keeps working without you" pillar even at the moment-to-moment level,
  not just across sessions.
