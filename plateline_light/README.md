# Plateline Light

**Plateline** is a workflow accelerator for Layout Artists, Matchmovers, and Animators. It automates the tedious part of setting up one camera per video plate and laying those shots out on the timeline.

> **Light edition — free.** Recursive folder import, lens metadata, and proxy generation live in **Plateline Pro**.

## Features

### Batch Import
* **Drag and drop** — drop plates straight into the 3D Viewport. Select fifty files in Explorer or Finder, drag them in, and they import with the current settings; no file browser, no second selection.
* **Smart Placement** — choose how new clips join the timeline:
    * **Append** — finds the end of the current sequence and places new clips after the last one.
    * **Cursor** — starts exactly at the playhead.
    * **Manual** — starts at a fixed frame number.
* **Into a Collection** — new cameras go into their own collection ("Plates" by default), nested under whichever collection is active. Importing again reuses it rather than making a second one, so the whole shot list stays selectable and hideable in one click. Switch it off to drop the cameras straight into the active collection.
* **Auto Setup** — creates a camera per clip and configures the background image reference (opacity, depth, focal length, height).
* **Gap Control** — insert handle frames between clips automatically.

### Image Sequences
* **One camera per shot, not per frame.** Select all 500 frames of five sequences and you get five cameras — the add-on groups numbered files into the sequences they belong to.
* **Any frame will do.** Pick frame 0087 and the camera still anchors to frame 0001 with the full duration.
* **Clean names.** `0010_0010.0001.exr` becomes a camera called `0010_0010`.
* **Stills stay separate.** Files like `SH010.png`, `SH020.png`, `SH030.png` are recognised as three shots rather than one gap-riddled sequence.
* **Padding doesn't have to be consistent.** `shot_1` … `shot_12` is still one shot.
* **Sequences recognised from the names themselves.** Plates already named the production way — `0010_0010`, `0010_0020`, `0020_0010` — are grouped into the sequences they say they belong to, even when they all sit side by side in one folder. Prefixes and suffixes are ignored, so `PROD_0010_0020_plate_v003.mov` still reads as sequence `0010`, shot `0020`.

### Intelligent Naming
* **Token Pattern** — two tokens, the classic VFX convention:
    * `#` runs become the **shot** number,
    * `@` runs become the **sequence** number.

  The default `@@@@_####` gives `0010_0010`, `0010_0020`, `0010_0030` … and rolls over to `0020_0010` when a second sequence is found. Use `####` alone if you only want shot numbers.
* **Start and Step for each** — separate **Shot numbering** and **Sequence numbering** rows. 10/10 is the film convention, leaving room for inserts. The **Sequence numbering** row only appears when the pattern actually contains `@`.
* **Live preview** — the panel shows **Cameras will be named** with the first names your current settings produce, including the roll-over into the second sequence, so you can read the result instead of decoding the pattern.
* **Search & Replace** — clean up filenames on import (e.g. strip a `_plate` suffix).
* **Keep Filename** — use the video file's name verbatim.

### Maintenance
* **Reorder Selected** (the **Tools** box) — re-stacks the selected cameras on the timeline in name order, starting at the **Start Frame** set just above the button, and spacing them by each plate's own length plus the **Gap**. Their markers and plate offsets move with them, and the scene end frame follows.
  Use it after deleting a shot, renaming to change the order, or importing a second batch you want folded into the existing run.
* **Marker Binding** — every camera gets a bound timeline marker, so scrubbing switches cameras automatically.

## Installation

Requires **Blender 4.5 LTS or newer** (tested on 4.5 LTS, 5.0 and 5.2 LTS).

1. Download `plateline_light-3.0.0.zip`.
2. Drag the zip into the Blender window — or go to **Edit ▸ Preferences ▸ Add-ons ▸ Install from Disk**.
3. Enable **Plateline Light**.

Light and Pro share the same operators and panel, so install only one of them at a time.

## Usage

### Import
1. In the 3D Viewport press **N** to open the sidebar, then pick the **Plateline** tab.
2. Choose a **Placement** mode (Append is the usual choice).
3. Choose a **Naming** mode (e.g. Pattern `@@@@_####`) and check the **Cameras will be named** preview.
4. Either **drag your plates into the 3D Viewport**, or click **Import Files** and select them in the browser.

Dragged files use the settings already in the panel, so set the pattern before you drop.

**Video:** `.mp4` `.mov` `.avi` `.mkv` `.webm` `.m4v` `.mpg` `.mpeg` `.mts` `.m2ts` `.ogv` `.flv` `.wmv` `.dv` `.mxf` — anything Blender's FFmpeg can open. **Images:** `.png` `.jpg` `.exr` `.tif` `.dpx` `.tga` `.cin`, as stills or numbered sequences. Extensions are matched case-insensitively, so `.MOV` and `.PNG` are fine.

Odd file names are handled: spaces, non-ASCII and CJK characters, `&`, `+`, `#`, `'`, `[]`, `()`, dots as separators, leading digits, missing separators (`plate0001.png`), and sequences that start at any number (`hero_1001`).

### Reorder
1. Select the cameras to fix, in the 3D View or the Outliner.
2. In the **Tools** box, set the **Start Frame**.
3. Click **Reorder Selected**.

## Upgrading to Pro

Pro adds three things Light does not have:

| | Light | Pro |
|---|---|---|
| Import selected files, sequence grouping, naming, markers, reorder | ✅ | ✅ |
| **Import Folder** — scan a whole tree, one camera per shot | — | ✅ |
| **Lens from metadata** — focal length + sensor from EXR / EXIF | — | ✅ |
| **Proxy pipeline** — JPG proxies, resolution switcher | — | ✅ |

## Known limitations

* **Version numbers at the end of a file name look like frame numbers.**
  `plate_0001_v1.png`, `plate_0001_v2.png`, `plate_0001_v3.png` are read as one
  three-frame sequence, because the trailing `1/2/3` is indistinguishable from
  frame numbering. Put the version before the frame number
  (`plate_v1_0001.png`) or in its own folder.
* **Sequences missing more than half their frames** are treated as unrelated
  stills rather than one shot. This is deliberate — it is what keeps
  `SH010.png`, `SH020.png`, `SH030.png` from collapsing into a single camera.
* **A lone numbered frame** (`solo_0001.png` with no siblings) is treated as a
  still: held for 100 frames, and it keeps the number in its name.
* **Focal length is the panel value** and is applied to every camera. Reading it
  from the plate is a Pro feature.

## License

GPL v3 or later.
