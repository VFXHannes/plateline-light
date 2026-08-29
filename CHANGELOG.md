# Changelog

## 3.0.0 — first release

Plateline builds one camera per plate and lays the shots out on the timeline,
for layout, matchmove and previs work.

### Import

- **One camera per shot, not per frame.** Select all 500 frames of five image
  sequences and you get five cameras. Any frame anchors to the first with the
  full duration, so it does not matter which one you click.
- **Drag and drop.** Drop plates into the 3D viewport and they import with the
  settings already on screen.
- **Awkward names survive.** Spaces, non-ASCII and CJK characters, `&`, `+`,
  `#`, brackets, dots as separators, no separator at all, inconsistent zero
  padding, and sequences starting at any number.
- **Unrelated stills stay separate.** `SH010.png`, `SH020.png`, `SH030.png` are
  three shots, not one gap-riddled sequence.
- **Sequences keep their length**, gaps included.
- **Placement modes** — append after the last clip, start at the playhead, or at
  a fixed frame, with optional handle frames between clips.
- **Cameras land in their own collection**, reused across imports, so a whole
  shot list can be selected or hidden at once.

### Naming

- **Two tokens.** `#` runs become the shot number, `@` runs the sequence. The
  default `@@@@_####` gives `0010_0010`, `0010_0020` … and rolls over to
  `0020_0010` at the next sequence.
- Separate **start and step** for shot and sequence numbering.
- The panel **previews the names** before you import.
- Sequences are read from the plates themselves — from a folder per sequence, or
  from the shot codes in the file names, ignoring pipeline prefixes and suffixes.

### Cameras and timeline

- Background image, opacity, depth and height configured per camera.
- A timeline marker bound to every camera, so scrubbing cuts between shots.
- **Reorder Selected** re-stacks cameras and moves their markers with them.

### Pro

- **Recursive folder import** — point it at a tree and it finds every movie and
  image sequence. Format and version folders are skipped when naming, so the
  camera takes the shot's name. `Proxy` folders are ignored.
- **Lens from metadata** — focal length and sensor width read from OpenEXR
  headers or JPEG/TIFF EXIF. Findings are graded, and only those whose unit the
  format actually fixes are applied; a zoom lens is reported, never guessed at.
- **Proxy pipeline** — JPG proxies at 25/50/75/100 % with a one-click resolution
  switcher. Built with Blender's own video sequencer, so there is nothing to
  install. A progress bar runs while it works, and Esc cancels.

### Known limitations

Documented rather than hidden — see `limitations.md`:

- A version suffix after the frame number (`plate_0001_v1.png`) reads as frame
  numbering.
- Sequences missing more than half their frames are treated as separate stills.
- Folders cannot be dragged into Blender; use the Folder button or paste the
  path. Blender routes drops by file extension, so a directory matches nothing.
- Lens metadata is read from images, not from movie containers.

### Requirements

Blender 4.5 LTS or newer. Verified on 4.5 LTS and 5.2 LTS. Windows, macOS and
Linux. GPL-3.0-or-later.
