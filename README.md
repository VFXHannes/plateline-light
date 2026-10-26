# Plateline Light

**One camera per plate. Automatically.**

Plateline turns a folder of plates into a laid-out timeline of cameras -- one
per shot, background images configured, timeline markers bound -- for layout,
matchmove and previs work in Blender.

This repository holds the **Light** edition, which is free and always will be.

## Install

Download the latest `plateline_light-*.zip` from
[Releases](../../releases), then drag it into Blender, or use
**Edit > Preferences > Add-ons > Install from Disk**.

Requires **Blender 4.5 LTS or newer**. Verified on 4.5 LTS and 5.2 LTS.

## What it does

- **One camera per shot, not per frame.** Select all 500 frames of five
  sequences and you get five cameras.
- **Any frame will do.** Pick frame 0087 and the camera still anchors to the
  first frame with the full duration.
- **Drag and drop.** Drop plates straight into the 3D viewport.
- **Names that match your shot list.** `@@@@_####` gives `0010_0010`,
  `0010_0020` ... and rolls over to `0020_0010` at the next sequence.
- **Awkward names survive.** Spaces, non-ASCII, CJK, `&`, `+`, `#`, dots as
  separators, missing separators, inconsistent zero padding, sequences starting
  at any number.
- **Markers bound to cameras**, so scrubbing cuts between shots.

Full manual: [`README.md`](plateline_light/README.md) inside the add-on folder.

## Reporting a problem

Open an [issue](../../issues). Plateline is mostly about file names and folder
structure, so please include a few real file names and the folder layout -- that
usually identifies the cause immediately.

## Plateline Pro

Light covers the import: one camera per shot, sequence grouping, naming,
markers. Pro is for when a whole delivery lands at once:

- **Folder import.** Point it at the plates folder and it walks the tree.
  Format and version folders (`exr/`, `v003/`) are skipped when naming.
- **Lens from metadata.** Focal length and sensor width read from EXR headers
  and JPEG/TIFF EXIF, so forty cameras do not need the same number typed in.
- **Proxies.** JPG proxies at 25 to 100 percent, built with Blender's own
  sequencer, switchable per camera. 4K EXR plates scrub again.
- **The rest of the EXR header** (ISO, shutter, timecode, camera, reel) stored
  on each camera.

Pro is $19 on [Superhive](https://superhivemarket.com/products/plateline-pro).
It shares its core with Light, so a scene built in Light opens in Pro unchanged.
Its source is not in this repository, but bug reports for shared behaviour are
welcome here.

If Light saved you an afternoon, a rating on
[extensions.blender.org](https://extensions.blender.org/add-ons/plateline-light/)
helps other people find it.

## Licence

GPL-3.0-or-later. See [LICENSE.txt](LICENSE.txt).
