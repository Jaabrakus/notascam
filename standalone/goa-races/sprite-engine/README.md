# GOA Sprite Converter

Import existing sprites, prepare a redraw against the approved six-race GOA style,
have Codex perform the AI redraw in the current chat, then pack the result as a
transparent sprite atlas. This is the chat workflow selected by the user; there
is no API key, external AI server, or automatic model call in this application.

## Open

Double-click **Dungeon Master Sample / Launch GOA Sprite Converter.command**.
It starts a local-only Python server and opens the converter in your browser.
Keep the launcher running while working. Python 3 is the only runtime dependency.
The launcher uses port 8876, or an available port if that port is already occupied.

Alternatively open **Dungeon Master Sample / GOA Sprite Converter.html** directly.
The standalone HTML supports import, DMI decoding, conversion ZIP downloads,
finished-redraw import, and atlas export. Automatic job saving and result detection
use the launcher.

## Workflow

1. Drop in a PNG, DMI, WebP or JPG. A DMI's state names, frame dimensions,
   directions and frame counts are detected. Choose the animation state to redraw.
   A plain image starts as a single frame; expand **Source sheet layout** to
   describe a sheet. Supported direction counts are 1, 4, 8 and 16.
2. Choose character, armor overlay, weapon/prop, or spell/effect, and the finished
   frame size (32, 64 or 128). Add any identity or alignment requirements.
3. Click **Prepare redraw for Codex**. With the launcher, the job is saved under
   `jobs/<id>/`. Copy its generated message into the current Codex chat.
   Without the launcher, attach the downloaded conversion ZIP to the message.
4. Codex inspects the input and reference, uses the built-in image generation
   tool, reviews the generated sheet and saves `result.png` in the job folder.
   The running converter detects that file. For a ZIP-based job, import the
   finished redraw using **Import finished redraw**.
5. Compare source and result by direction and animation frame. Export a ZIP
   containing `sprites.png`, `atlas.json` and `redraw-request.json`.

The source sheet is arranged as direction columns and consecutive animation rows
for a redraw. Its request retains the original source cell rectangles and order.
The input sheet and approved reference always travel together. Input animation
delays are retained in the manifest, in BYOND deciseconds where provided by DMI.
The viewer plays at a fixed inspection speed; it is not the game animation player.

## What matching means

The AI receives the same reference and a category-specific specification for
compact GOA proportions, readable pixel clusters, dark outlines and material
shading, while preserving identity, facing and pose. It redraws the artwork;
resizing and palette changes alone do not produce this style.

The app does **not** redraw by itself, guarantee identical anatomy across frames,
create missing animation poses, produce 16 body directions from four inputs, or
automatically register equipment overlays to every race. Visual review remains
necessary. Source grid bounds and result transparency are checked, but neither proves
that the model preserved the poses or kept every sprite inside its cell.

The approved reference is an enlarged generated visual draft rather than a
finished 32-pixel atlas. The export step mechanically resizes each returned cell
using nearest-neighbor sampling. Choosing 32-pixel output does not guarantee
hand-authored 32-pixel shading or perfect animation; inspect the packed result.

Returned cell boundaries may fall between source pixels when an AI image has an
odd dimension. The packer samples equal fractional source rectangles rather than
rejecting a valid grid solely because its image dimensions are not divisible by
the number of columns or rows. Always inspect alignment against the source poses.

## Files and reusable engine

- `sprite-engine.js`: browser library exposed as `SpriteEngine`. DMI PNG metadata
  decoding, frame selection/reordering, request specifications, transparent PNG
  atlas packing, manifest generation and a dependency-free ZIP writer.
- `workshop.js`: import/review UI, local job persistence, result polling and export.
- `workshop.template.html`: editable UI source.
- `build.py`: embeds the reference, example DMI and JavaScript in standalone HTML.
- `serve.py`: local job service; binds only to the loopback interface. It reads
  only the converter page and recognized job files, and writes only job inputs
  and results. It makes no external network requests.
- `jobs/`: persistent conversion folders. Inputs remain unchanged. PNG/DMI input
  bytes are retained; JPG/WebP are decoded to a lossless PNG for the job.
- `verify_workshop.py`: local browser integration checks, no image AI calls.

`SpriteEngine.inspect(file)` reads a sprite file. `prepare(input, config)` extracts
selected frames. `specification(input, prepared, options)` creates a redraw job.
`pack(resultImage, specification)` packs the returned grid at the target cell size;
`manifest(specification)` describes the atlas. The library is separate from the
workshop so other project tools can reuse it. It is not yet connected to a C# game.

## Build and check

From the project root:

```sh
python3 standalone/goa-races/sprite-engine/build.py
python3 standalone/goa-races/sprite-engine/serve.py
```

With that server running, browser verification uses the already-installed
Playwright and Google Chrome:

```sh
python3 standalone/goa-races/sprite-engine/verify_workshop.py
```

It checks real compressed DMI metadata, frame ordering, animation inspection,
invalid layout handling, ZIP integrity, transparency, PNG/JSON export, saved jobs,
result detection and restoring jobs. Synthetic result fixtures test the plumbing
and are deleted; they are never presented as AI-converted art.

The approved race reference remains in `../goa-races-lotr-v1.png`. Its original
generation prompt and provenance are in the parent folder. Existing game sprites
and the earlier gear-fitting tool are preserved.
