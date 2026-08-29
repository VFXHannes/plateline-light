# Changelog

## 3.0.0

First release of the split editions. This is a substantial rewrite of the 2.x
add-on, with a modular codebase, a full automated test suite, and verified
support for the current LTS releases.

### New — image sequences
- Selected frames are grouped into the sequences they belong to. Selecting all
  500 files of five shots now produces five cameras, not five hundred.
- Any frame of a sequence anchors to the first frame with the full duration, so
  it no longer matters which one you click.
- Frame numbers are stripped from camera names: `0010_0010.0001` → `0010_0010`.
- Inconsistent zero padding (`shot_1` … `shot_12`) is handled as one shot.
- Sequence duration is the frame span, so a sequence with dropped frames still
  occupies its full length on the timeline.
- Unrelated stills that merely end in digits (`SH010.png`, `SH020.png`) stay
  separate shots.

### New — drag and drop
- Plates can be dropped straight into the 3D Viewport. The dropped files are
  imported with the settings already in the panel, without a second trip through
  the file browser.
- Folders cannot be dropped — Blender routes a drop by file extension, so a
  directory matches no handler in any add-on. Pro gains an **Or paste folder
  path(s)** field instead, which accepts Explorer's *Copy as path* output and
  several `;`-separated paths at once.

### New — sequence-aware naming
- The name pattern gains an `@` token for the sequence number alongside `#` for
  the shot. The new default `@@@@_####` produces `0010_0010`, `0010_0020` …
  and rolls over to `0020_0010` at the next sequence.
- Sequence numbering has its own Start and Step, shown only when the pattern
  uses `@`.
- The panel previews the names the current settings will produce, including the
  roll-over into the second sequence.
- Sequences are detected from the file names themselves, so plates named the
  production way group correctly even in one flat folder, with pipeline prefixes
  and suffixes ignored. Detection requires every file in the batch to carry a
  pair of codes, so a partial match never half-applies.
- Sequences are numbered in order of first appearance, so interleaved plates do
  not invent extra sequences.

### New — Pro
- **Import Folder**: recursive scan of a folder tree, one camera per movie or
  image sequence, with Auto / File / Folder naming. `Proxy` folders are skipped.
- **Lens from metadata**: focal length and sensor width read from OpenEXR
  (`pinholeFocalLength`, `nominalFocalLength`, `effectiveFocalLength`, plus
  common vendor spellings) and from JPEG/TIFF EXIF. Falls back to the panel
  value when a plate carries none.

### Changed — proxy generation
- Proxies are now built with Blender's video sequencer instead of a generated
  3D scene rendered through EEVEE. Measured on the same plates: **17-18x
  faster** (a 45-frame 1080p movie went from 8.2s to 0.46s). Output layout,
  naming and behaviour are unchanged, so existing proxies still work.
- **The FFmpeg backend is gone.** With the sequencer doing the work there was
  nothing left for an external encoder to be faster at, so the preference page,
  the executable path and the subprocess call have all been removed. Proxies
  now have no external dependency and no setup step at all.
- Generate Proxies runs modally: a progress bar, Esc to cancel, and Blender
  stays responsive across a long batch.

### Fixed
- Proxy generation failed silently on Blender 4.2–4.5: the EEVEE render engine
  identifier changed between 4.x and 5.x. The engine is now detected at runtime.
- Reordering cameras created duplicate timeline markers, because import and
  reorder used different marker naming. Markers are now matched by their bound
  camera.
- Proxy generation from image-sequence plates produced nothing, because an image
  datablock set to `SEQUENCE` reports a size of 0×0.
- Switching an image-sequence camera back to Original forced it to a movie clip.
- Re-applying a proxy leaked a new image datablock each time.
- Image sequences were given a hardcoded 100-frame duration.
- Import ordering was plain alphabetical, so `Shot_10` sorted before `Shot_2`.

### Changed
- Requires Blender 4.5 LTS or newer. Verified on 4.5 LTS, 5.0 and 5.2 LTS.
- Installs as an extension; the manifest is the single source of version truth.
- Wider format support: `.m4v`, `.mpg`, `.mpeg`, `.mts`, `.m2ts`, `.ogv`,
  `.flv`, `.wmv`, `.dv`, `.mxf`, `.cin`, plus case-insensitive extensions.
- Failures are reported instead of silently swallowed.

## 2.3.1
- Previous single-edition release.
