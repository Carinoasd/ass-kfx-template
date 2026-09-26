# ass-kfx-template

[繁體中文](README.md) ｜ [简体中文](README.zh-CN.md) ｜ **English**

> A Claude skill that turns a plain ASS lyrics file into **karaoke effect subtitles (KFX)** for anime insert songs, OPs and EDs.
> Claude reads the lyrics, looks at the footage, designs the effects, applies the template on its own, checks the result with screenshots, and hands you three things: the template, the finished subtitles and a preview video.

| Drop-and-bounce + theme shapes (strawberry) | Outline preview (Yutils) | Dissolve into particles (Yutils) |
|---|---|---|
| ![drop](docs/images/berry.gif) | ![ghost outline](docs/images/ghost.gif) | ![particles](docs/images/dust.gif) |

---

## What is it?

An analogy first:

- An **ASS subtitle file** is a list of "where each line goes and what color it is".
- An **Aegisub karaoke template** is a script of moves. Write "each character drops in from above, squashes on landing and bounces" once, and it generates that animation for every character of every line in the song.
- **This skill** teaches Claude to be an effects artist who writes those scripts. It knows how to write a template, rehearse it outside Aegisub, screenshot the result to catch problems, and it remembers what users corrected in the past.

Hand Claude a lyrics `.ass` (ideally with the video too), say "make effects for this song", and you get subtitles ready to burn into the video.

## What can it do?

### 1. Effects that are actually designed

Claude understands the song before touching any code:

- It reads the whole lyrics and picks out the mood (for example, "the little things will be forgotten").
- It grabs a frame from the middle of every line to see which objects and colors are on screen (for example, the characters making strawberry jam).
- It finds the scene cuts and lands each effect's climax on the cut frame.
- It comes up with one core idea that ties the lyrics to the picture.

The skill ships with a full worked example, "Jam Jar". Jam is a way of preserving strawberries, and the lyrics say small things get forgotten, so the song stores one strawberry per line in a jar. The jar fills up from empty, and on the cut to the finished jar it gets a red-and-white gingham cloth and a bow.

### 2. A starter template in one command

```bash
python ass-kfx-template/assets/starter_build.py lyrics.ass out_template.ass --main JP --sub CN --theme berry --yutils
```

The generated template already works. It includes:

| Part | Effect |
|---|---|
| Main line (large text) | Characters drop in quickly one after another, squash on landing, bounce back, and fade from a flash color to their own color |
| Sub line (translation) | Pops up from below, one character at a time, on the exact frame the first main character lands |
| Theme shapes | Strawberry, flower, heart or star. They **only appear on entrance and exit** and never sit around the text |
| Entrances | 5 variants: fly in from the sides, bounce up from below, slam down from above, sweep along the edges, outline preview |
| Exits | 5 variants: pop out and rise, burst from the center, sweep across the top, fall away, dissolve into particles |
| No visible repetition | Two neighbouring lines never use the same variant, and count, size and angle are randomized slightly |
| Short lines | Decorations are compressed proportionally, but never below half length |
| Last line | Its own finale: a theme shape glides along the top of the text, leaving a trail of sparkles |

Every parameter (colors, timings, heights…) lives in the `C` and `P` tables on the template's first line, so you can tweak them directly in Aegisub.

### 3. Glyph-aware effects with Yutils

With `--yutils`, the template loads [Yutils](https://github.com/Youka/Yutils) at run time and turns each character into its real outline:

- **Outline preview**: before a character drops in, a hollow outline of it lights up where it will land, then fades as the character falls into it. It reads as "a character is about to appear here".
- **Dissolve into particles**: on exit, each character breaks into dozens of tiny squares that follow its actual strokes. They take off left to right, drift upward, shrink and vanish. From a distance it still looks like the character, and then it scatters. This is great for songs about loss, memories or starry skies.

The reference docs describe more glyph-based recipes, such as "light running along the outline".

### 4. Apply and preview without opening Aegisub

| Tool | What it does |
|---|---|
| `kt_apply.py` | Runs Aegisub's own `kara-templater.lua` directly. The result matches "Apply karaoke template" inside Aegisub |
| `render.py` | Renders any timestamp with libass (ffmpeg) into an image, with frame sequences and zoomed crops |
| `review.py` | Grabs entrance, middle and exit frames of every line and tiles them into one overview sheet |

For every version, Claude goes through the screenshots itself to check sync, alignment and readability on both bright and dark footage, and fixes problems before showing you anything.

### 5. Missing glyph handling

`glyph_check.py` runs first and lists any characters the font lacks. For a missing character, `glyph2ass.py` can **build it out of strokes from the same font** (for example, reusing parts of 别 and 気) or borrow it from another font, so the lyrics don't have to change.

### 6. It evolves itself

The skill gets better every time it's used on a song:

1. **It takes notes.** After each delivery, the user's feedback is sorted and written back into the skill. "Too plain" goes into the design lessons; "that effect looks great" goes into the recipe library.
2. **Guard rails.** `selftest.py` runs a 31-check smoke test: every theme and every entrance and exit variant is applied for real, the templater must report 0 errors, and a libass screenshot is rendered at the end.
3. **Version and package.** `evolve.py` runs the tests first and **refuses to bump the version or package if they fail**. Only after they pass does it increment the version, add an entry to `CHANGELOG.md` and build a new `.skill`.

## Installation

### As a Claude skill (recommended)

1. Zip the `ass-kfx-template/` folder and rename the file to `.skill` (a plain `.zip` also works).
2. Upload it under Skills in Claude's settings.
3. Ask Claude something like "make karaoke effects for this insert song" and it will use the skill automatically.

### Running the scripts yourself

You'll need:

- Python 3 plus `pip install lupa fonttools pillow numpy`
- ffmpeg built with libass
- Aegisub (`kt_apply.py` uses its `automation/autoload/kara-templater.lua`)

> 💡 On Windows, run `kt_apply.py` with the **Windows Python** so text widths match Aegisub exactly. WSL/Linux also work, but may be off by a fraction of a pixel, so treat that output as a preview only.

### When Yutils is used

To re-apply a `--yutils` template inside Aegisub, copy `ass-kfx-template/scripts/Yutils.lua` into one of these folders. If you use DependencyControl, it is usually there already.

- `<Aegisub install dir>\automation\include\`
- `%APPDATA%\Aegisub\automation\include\`

## Quick start (manual workflow)

```bash
cd ass-kfx-template

# 1. Check for missing glyphs
python scripts/glyph_check.py lyrics.ass

# 2. Generate a starter template
python assets/starter_build.py lyrics.ass song_template.ass --main JP --sub CN --theme berry --yutils

# 3. Apply it (the templater must report 0 errors)
python scripts/kt_apply.py song_template.ass song_fx.ass --aegisub "C:\Program Files\Aegisub"

# 4. Review screenshots (entrance / middle / exit of every line)
python scripts/review.py song_fx.ass check --video source.mp4 --style JP

# 5. Render a preview video
ffmpeg -ss START -to END -copyts -i source.mp4 -vf "subtitles=song_fx.ass" -c:a aac -ss START preview.mp4
```

One rule for the lyrics: **each line starts with a single `{\k1}` and its Effect field is `karaoke`**. `starter_build.py` rewrites your lyrics this way automatically.

## Layout

```
ass-kfx-template/
├── SKILL.md                  Instructions for Claude (workflow, delivery rules, self-evolution)
├── CHANGELOG.md              What changed in each version, plus ideas not done yet
├── requirements.txt
├── assets/
│   ├── starter_build.py      Starter template generator (themes, 5 entrances, 5 exits)
│   ├── shapes.py             Theme shapes (strawberry, flower, heart, star…)
│   └── examples/jam_jar/     Code of the full "Jam Jar" example (read-only reference)
├── scripts/
│   ├── kt_apply.py / mock.lua  Run kara-templater outside Aegisub
│   ├── render.py / review.py   libass screenshots and per-line overview
│   ├── glyph_check.py / glyph2ass.py / fontfind.py   Missing glyphs, glyph-to-drawing, glyph assembly
│   ├── Yutils.lua            Yutils library (MIT)
│   ├── selftest.py           Smoke test
│   └── evolve.py             Test → bump version → package
├── references/
│   ├── design-lessons.md     Real user feedback (read before starting)
│   ├── showcase-jam-jar.md   Walkthrough of the target quality level
│   ├── effect-recipes.md     Recipe library A–N (drop, typewriter, ink spread, particles…)
│   ├── templater-cookbook.md Templater handbook (including Yutils usage)
│   └── missing-glyphs.md     How to fill in missing glyphs
└── tests/smoke_song.ass      Lyrics used by the smoke test
```

Note: the skill's internal docs (`SKILL.md`, `references/`) are written in Simplified Chinese.

## Limitations

- Only **libass** is supported (mpv, ffmpeg encoding, MPC-HC in libass mode). VSFilter doesn't handle the bounding-box lock trick, so multi-layer shapes end up misaligned.
- "Dissolve into particles" adds roughly 600 events for a 10-character line. That's fine for encoding. If real-time playback struggles, raise `YP.step` or lower `YP.max`.
- The Windows path where Yutils reads glyph outlines through GDI hasn't been run through `selftest.py` on a real Windows machine yet (see "ideas not done yet" in `CHANGELOG.md`).

## License

MIT © Carinoasd. `scripts/Yutils.lua` comes from [Youka/Yutils](https://github.com/Youka/Yutils), also MIT licensed, with its original copyright notice kept at the top of the file.
