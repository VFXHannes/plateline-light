"""Shared functionality for both editions: settings, import, reorder."""

import math
import os
import re

import bpy
from bpy.props import (
    BoolProperty,
    CollectionProperty,
    EnumProperty,
    FloatProperty,
    IntProperty,
    StringProperty,
)
from bpy.types import Operator, PropertyGroup
from bpy_extras.io_utils import ImportHelper

MOVIE_EXTENSIONS = (
    '.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v', '.mpg', '.mpeg', '.m2v',
    '.mts', '.m2ts', '.ogv', '.flv', '.wmv', '.divx', '.dv', '.mxf',
)
IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.exr', '.tif', '.tiff', '.dpx', '.tga', '.cin')

DEFAULT_IMAGE_DURATION = 100

# A run of numbered files is treated as one sequence only if it is reasonably
# dense. Real sequences are contiguous (0001..0100) even with a few frames
# missing; unrelated stills that happen to end in digits (SH010, SH020, SH030)
# are not, and must stay separate shots.
SEQUENCE_MIN_DENSITY = 0.5

# Written on import so the Pro edition can still find the original plate after
# the background has been swapped to a proxy sequence. Harmless in Light, and
# it means a Light scene upgrades to Pro cleanly.
SOURCE_PATH_KEY = "plateline_source_path"
# Scenes built with the pre-rename 2.x/3.0 add-on used this key.
LEGACY_SOURCE_PATH_KEYS = ("batch_source_path",)

# Everything the lens reader found, recorded on the camera so the panel can
# report it and an artist can tell at a glance where a lens came from.
FOCAL_SOURCE_KEY = "plateline_focal_source"
LENS_MODEL_KEY = "plateline_lens_model"
LENS_NOTE_KEY = "plateline_lens_note"
FOCUS_DISTANCE_KEY = "plateline_focus_distance"
FOCAL_RANGE_KEY = "plateline_focal_range"

_SEQUENCE_NUMBER_RE = re.compile(r'^(.*?)(\d+)$')

# A code is a short optional letter prefix followed by digits: 0010, SQ010, v002.
_CODE_RE = re.compile(r'^[A-Za-z]{0,4}\d{2,4}$')


def sequence_shot_codes(name):
    """(sequence, shot) read from a name, or None.

    Splits on the usual separators and keeps the tokens that look like codes, so
    a show prefix (`ABC_0010_0020`) and a trailing suffix (`0010_0020_plate_v2`)
    are both ignored -- the first two codes are the sequence and the shot.
    Names carrying only one code, like `SH010_plate`, yield nothing.
    """
    codes = [tok for tok in re.split(r'[_\-.\s]+', name) if _CODE_RE.match(tok)]
    return (codes[0], codes[1]) if len(codes) >= 2 else None

# Pro plugs its metadata parser in here. Light registers nothing, so `read_lens`
# always returns None and every camera falls back to the panel value -- no
# conditional imports and no dead code in the Light build.
_lens_readers = []
_lens_cache = {}


def register_lens_reader(func):
    if func not in _lens_readers:
        _lens_readers.append(func)


def unregister_lens_reader(func):
    if func in _lens_readers:
        _lens_readers.remove(func)
    _lens_cache.clear()


def has_lens_readers():
    return bool(_lens_readers)


# Pro's recursive scanner registers here, so a dropped *folder* can be expanded
# without core needing to know how. Light leaves it empty and skips folders.
_folder_scanner = []


def register_folder_scanner(func):
    if func not in _folder_scanner:
        _folder_scanner.append(func)


def unregister_folder_scanner(func):
    if func in _folder_scanner:
        _folder_scanner.remove(func)


def scan_folder(path, recursive=True, naming='AUTO'):
    """Items inside a folder, or [] when no scanner is registered (Light)."""
    for scanner in _folder_scanner:
        try:
            return scanner(path, recursive, naming)
        except Exception as exc:
            print(f"[Plateline] Folder scan failed for {path}: {exc}")
    return []


class wait_cursor:
    """Busy cursor that degrades quietly when there is no window.

    `context.window` is None when an operator is driven from a startup script or
    a headless pipeline, where a busy cursor is meaningless anyway -- but the
    unguarded call raised AttributeError and killed the import.
    """

    def __init__(self, context):
        self.window = getattr(context, 'window', None)

    def __enter__(self):
        if self.window is not None:
            self.window.cursor_modal_set('WAIT')
        return self

    def __exit__(self, *exc_info):
        if self.window is not None:
            self.window.cursor_modal_restore()
        return False


def read_lens(filepath):
    """First lens reading any registered reader can supply, or None."""
    if not _lens_readers or not filepath:
        return None
    key = os.path.normcase(filepath)
    if key in _lens_cache:
        return _lens_cache[key]

    # Prefer a reader that produced a usable focal length, but keep a partial
    # finding (lens model, zoom range, focus distance) so the panel can still
    # report what the plate contained and why nothing was applied.
    result = None
    for reader in _lens_readers:
        try:
            candidate = reader(filepath)
        except Exception as exc:
            print(f"[Plateline] Lens reader failed on {filepath}: {exc}")
            continue
        if not candidate:
            continue
        if candidate.get('focal_length'):
            result = candidate
            break
        if result is None:
            result = candidate

    _lens_cache[key] = result
    return result


def clear_lens_cache():
    _lens_cache.clear()


# --- paths & naming ---

def get_absolute_path(path):
    if not path:
        return None
    try:
        return os.path.abspath(bpy.path.abspath(path))
    except Exception:
        return None


def is_movie(filename):
    return filename.lower().endswith(MOVIE_EXTENSIONS)


def apply_name_pattern(pattern, position, start=10, step=10,
                       sequence_position=0, sequence_start=10, sequence_step=10):
    """Substitute `#` runs with the shot number and `@` runs with the sequence.

    Classic film numbering starts at 0010 and steps by 10 so inserts can be
    slotted in later, which a plain 1,2,3 counter cannot express. `@@@@_####`
    gives 0010_0010, 0010_0020 ... then 0020_0010 when the sequence changes.
    """
    shot = start + position * step
    sequence = sequence_start + sequence_position * sequence_step

    def replace_shot(match):
        return f"{shot:0{len(match.group(0))}d}"

    def replace_sequence(match):
        return f"{sequence:0{len(match.group(0))}d}"

    out = re.sub(r'@+', replace_sequence, pattern)
    return re.sub(r'#+', replace_shot, out)


def preview_names(settings, count=3):
    """Example names for the current pattern, for the panel to show.

    Reading `@@@@_####` cold tells you nothing; seeing `0010_0010, 0010_0020,
    0020_0010` tells you everything.
    """
    pattern = settings.name_pattern
    has_sequence = "@" in pattern
    out = []
    for i in range(count):
        # once the shot column is shown, roll the last example into sequence two
        seq = 1 if (has_sequence and i == count - 1) else 0
        shot = 0 if (has_sequence and i == count - 1) else i
        out.append(apply_name_pattern(
            pattern, shot, settings.number_start, settings.number_step,
            seq, settings.sequence_start, settings.sequence_step))
    return out


def natural_key(text):
    """Sort key where SH2 comes before SH10, unlike plain alphabetical.

    Digit runs sort ahead of text, matching Explorer's ordering so a folder
    like `2024_01_15` lands before `Shots` rather than after everything.
    """
    return tuple(
        (0, int(part), '') if part.isdigit() else (1, 0, part.lower())
        for part in re.split(r'(\d+)', text) if part
    )


def path_sort_key(relative_path):
    """Natural sort applied per path component, so folders group correctly."""
    return tuple(natural_key(part) for part in relative_path.replace("\\", "/").split("/"))


def split_frame_number(stem):
    """('SH010_plate_', '0001') for 'SH010_plate_0001', else (stem, None)."""
    match = _SEQUENCE_NUMBER_RE.match(stem)
    if not match:
        return stem, None
    return match.group(1), match.group(2)


def scan_sequence(filepath):
    """Resolve `filepath` to the sequence it belongs to.

    Returns (first_frame_path, duration, is_sequence). Any frame of a sequence
    resolves to the same first frame, which is what lets a selection of 500
    files collapse to the handful of shots it actually represents.

    Frame numbers are matched at any width, so a shot exported without zero
    padding (shot_1 ... shot_12) stays one sequence instead of splitting at the
    digit-count boundary.
    """
    directory, filename = os.path.split(filepath)
    stem, ext = os.path.splitext(filename)
    prefix, digits = split_frame_number(stem)
    if digits is None or not os.path.isdir(directory):
        return filepath, DEFAULT_IMAGE_DURATION, False

    pattern = re.compile(
        r'^' + re.escape(prefix) + r'(\d+)' + re.escape(ext) + r'$', re.IGNORECASE,
    )
    try:
        found = [(int(m.group(1)), m.group(0))
                 for m in (pattern.match(f) for f in os.listdir(directory)) if m]
    except OSError:
        return filepath, DEFAULT_IMAGE_DURATION, False

    if len(found) < 2:
        return filepath, DEFAULT_IMAGE_DURATION, False

    numbers = [n for n, _ in found]
    span = max(numbers) - min(numbers) + 1
    if len(found) / span < SEQUENCE_MIN_DENSITY:
        # Sparse -- these are separate stills that merely end in digits.
        return filepath, DEFAULT_IMAGE_DURATION, False

    # Use the real filename of the lowest frame rather than reformatting the
    # number, so mixed padding cannot produce a path that does not exist.
    first_name = min(found, key=lambda pair: pair[0])[1]
    # Duration is the span, not the file count: a sequence missing a few frames
    # still occupies its full length on the timeline.
    return os.path.join(directory, first_name), span, True


def count_sequence_frames(filepath):
    """Frames in the numbered image sequence that `filepath` belongs to."""
    return scan_sequence(filepath)[1]


def sequence_display_name(first_path, is_sequence):
    """Camera name for a plate: 'SH010_plate_0001' -> 'SH010_plate'."""
    stem = os.path.splitext(os.path.basename(first_path))[0]
    if not is_sequence:
        return stem
    prefix, digits = split_frame_number(stem)
    if digits is None:
        return stem
    return prefix.rstrip('_-. ') or stem


# --- background image access ---

def get_background(camera):
    if not camera or camera.type != 'CAMERA' or not camera.data.background_images:
        return None
    return camera.data.background_images[0]


def get_bg_duration(bg, default=DEFAULT_IMAGE_DURATION):
    if bg is None:
        return default
    if bg.source == 'MOVIE_CLIP' and bg.clip:
        return int(bg.clip.frame_duration)
    if bg.source == 'IMAGE':
        return int(bg.image_user.frame_duration)
    return default


def sequence_frame_offset(image):
    """Offset that makes a sequence resolve to its own first file.

    Blender picks the frame to show as `scene_frame - frame_start + 1 +
    frame_offset`. With an offset of 0 that asks for frame 1, so a sequence
    whose files are numbered from 1001 sends Blender looking for `plate.0001`,
    which does not exist -- and a missing frame draws nothing at all. The
    background looks correctly configured and stays empty.
    """
    if image is None or image.source != 'SEQUENCE':
        return 0
    stem = os.path.splitext(os.path.basename(image.filepath))[0]
    _prefix, digits = split_frame_number(stem)
    return int(digits) - 1 if digits else 0


def get_bg_start(bg, default=0):
    if bg is None:
        return default
    if bg.source == 'MOVIE_CLIP' and bg.clip:
        return int(bg.clip.frame_start)
    if bg.source == 'IMAGE':
        return int(bg.image_user.frame_start)
    return default


def set_bg_start(bg, frame):
    if bg is None:
        return
    if bg.source == 'MOVIE_CLIP' and bg.clip:
        bg.clip.frame_start = frame
    elif bg.source == 'IMAGE':
        bg.image_user.frame_start = frame
        bg.image_user.frame_offset = sequence_frame_offset(bg.image)


# --- timeline markers ---

def find_marker_for_camera(scene, camera):
    """Locate the marker bound to `camera`.

    The binding is checked before the name because older scenes were written
    with two different schemes -- import used "<cam>", reorder used "M_<cam>" --
    which is why reordering an imported camera used to create a duplicate.
    """
    for marker in scene.timeline_markers:
        if marker.camera == camera:
            return marker
    for name in (camera.name, f"M_{camera.name}"):
        marker = scene.timeline_markers.get(name)
        if marker is not None:
            return marker
    return None


def place_marker(scene, camera, frame):
    marker = find_marker_for_camera(scene, camera)
    if marker is None:
        marker = scene.timeline_markers.new(camera.name, frame=frame)
    marker.frame = frame
    marker.camera = camera
    return marker


def iter_areas(context):
    """Areas of the current screen, or nothing.

    `context.screen` is None when an operator runs from a startup script or a
    headless pipeline, where there is no UI to update.
    """
    screen = getattr(context, 'screen', None)
    return screen.areas if screen is not None else ()


def force_timeline_view_all(context):
    for area in iter_areas(context):
        if area.type not in ('TIMELINE', 'DOPESHEET_EDITOR', 'GRAPH_EDITOR'):
            continue
        region = next((r for r in area.regions if r.type == 'WINDOW'), None)
        if region is None:
            continue
        try:
            with context.temp_override(area=area, region=region):
                if area.type == 'TIMELINE':
                    bpy.ops.time.view_all()
                elif area.type == 'DOPESHEET_EDITOR':
                    bpy.ops.action.view_all()
                else:
                    bpy.ops.graph.view_all()
        except Exception:
            pass


def infer_groups_from_names(items):
    """Derive the sequence from file names when the folders did not say.

    A flat delivery is often named to the shot list already -- 0010_0010,
    0010_0020, 0020_0010 -- and that first field is the sequence.

    Deliberately conservative: it only applies when *every* name fits the
    pattern and the set contains more than one sequence. A single mismatch, or
    only one sequence, means nothing is inferred rather than half the shots
    being regrouped on a guess.
    """
    if not items or any(item.group is not None for item in items):
        return False

    keys = []
    for item in items:
        codes = sequence_shot_codes(item.name)
        if codes is None:
            return False
        keys.append(codes[0])

    if len(set(keys)) < 2:
        return False

    for item, key in zip(items, keys):
        item.group = key
    return True


def get_source_path(camera):
    """Original plate path recorded at import time, if it still resolves."""
    if not camera or camera.type != 'CAMERA':
        return None
    stored = camera.data.get(SOURCE_PATH_KEY)
    if not stored:
        # Scenes made before the rename still carry the old key.
        for legacy in LEGACY_SOURCE_PATH_KEYS:
            stored = camera.data.get(legacy)
            if stored:
                camera.data[SOURCE_PATH_KEY] = stored
                break
    if not stored:
        return None
    resolved = get_absolute_path(stored)
    return resolved if resolved and os.path.exists(resolved) else None


# --- settings ---

class PlatelineSettings(PropertyGroup):
    placement_mode: EnumProperty(
        name="Placement",
        description="Where new clips start on the timeline",
        items=[
            ('MANUAL', "Manual", "Start strictly at the frame set below"),
            ('APPEND', "Append", "Start after the last existing clip"),
            ('CURSOR', "Cursor", "Start at the playhead"),
        ],
        default='APPEND',
    )
    start_frame: IntProperty(
        name="Start Frame",
        description="Frame the first clip starts on. Used by Manual placement, "
                    "and as the starting point when the timeline is empty",
        default=1001,
    )
    clip_gap: IntProperty(
        name="Gap",
        description="Blank frames left between one clip and the next, for handles",
        default=0, min=0,
    )
    cam_height: FloatProperty(
        name="Height",
        description="Height above the origin at which each camera is placed",
        default=1.0,
    )
    focal_length: FloatProperty(
        name="Focal Length",
        description="Focal length to use when the plate carries no lens data, "
                    "or when Lens is set to Manual",
        default=35.0, min=1.0,
    )
    focal_source: EnumProperty(
        name="Focal Length",
        description="Where each camera's focal length comes from",
        items=[
            ('METADATA', "From Metadata", "Read the lens from the plate when it carries one, otherwise use the value below"),
            ('MANUAL', "Manual", "Always use the value below"),
        ],
        default='METADATA',
    )
    bg_opacity: FloatProperty(
        name="Opacity",
        description="How strongly the background plate is drawn in the viewport",
        default=0.5, min=0.0, max=1.0,
    )
    bg_depth: EnumProperty(
        name="Depth",
        description="Whether the plate draws over the scene or behind it",
        items=[('FRONT', "Front", "Draw the plate in front of the scene"),
               ('BACK', "Back", "Draw the plate behind the scene")],
        default='FRONT',
    )
    naming_mode: EnumProperty(
        name="Mode",
        description="How each camera's name is derived from its plate",
        items=[
            ('FILENAME', "Filename", "Use the file name as-is, minus the frame number"),
            ('REPLACE', "Replace", "Search and replace within the file name"),
            ('PATTERN', "Pattern",
             "Numbered pattern: # runs become the shot number, @ runs the sequence"),
        ],
        default='FILENAME',
    )
    find_str: StringProperty(
        name="Find",
        description="Text to look for in the file name, for Replace naming",
        default="_plate",
    )
    replace_str: StringProperty(
        name="Replace",
        description="Text to put in its place. Leave empty to strip the Find text out",
        default="",
    )
    name_pattern: StringProperty(
        name="Pattern",
        description=("# runs become the shot number, @ runs the sequence. "
                     "e.g. @@@@_#### gives 0010_0010, 0010_0020, then 0020_0010"),
        default="@@@@_####",
    )
    number_start: IntProperty(
        name="Start",
        description="Number given to the first shot",
        default=10, min=0,
    )
    number_step: IntProperty(
        name="Step",
        description="Increment between shots. 10 is the film convention, leaving room for inserts",
        default=10, min=1,
    )
    sequence_start: IntProperty(
        name="Seq Start",
        description="Number given to the first sequence, for the @ token",
        default=10, min=0,
    )
    sequence_step: IntProperty(
        name="Seq Step",
        description="Increment between sequences, for the @ token",
        default=10, min=1,
    )


# --- collecting plates ---

class ImportItem:
    """One camera's worth of source: a movie, a still, or a whole sequence."""

    __slots__ = ("path", "name", "duration", "is_movie", "sort_key", "group",
                 "is_sequence")

    def __init__(self, path, name, duration, is_movie, sort_key, group=None,
                 is_sequence=False):
        self.path = path
        self.name = name
        self.duration = duration
        self.is_movie = is_movie
        self.sort_key = sort_key
        # A lone still must not be loaded as a SEQUENCE: Blender would then look
        # for a different numbered file on every frame of the hold and draw
        # nothing after the first.
        self.is_sequence = is_sequence
        # Which sequence this shot belongs to; drives the `@` counter. None
        # keeps everything in one sequence, which is right for a flat selection.
        self.group = group


def make_item(filepath, sort_key):
    if is_movie(filepath):
        try:
            clip = bpy.data.movieclips.load(filepath, check_existing=True)
            duration = int(clip.frame_duration)
        except Exception as exc:
            print(f"[Plateline] Could not read {filepath}: {exc}")
            return None
        name = os.path.splitext(os.path.basename(filepath))[0]
        return ImportItem(filepath, name, duration, True, sort_key)

    first, duration, is_seq = scan_sequence(filepath)
    return ImportItem(first, sequence_display_name(first, is_seq), duration,
                      False, sort_key, is_sequence=is_seq)


def is_supported(filename):
    return filename.lower().endswith(MOVIE_EXTENSIONS + IMAGE_EXTENSIONS)


def collect_from_files(directory, filenames, recursive=True, naming='AUTO'):
    """Items for an explicit selection, collapsing sequences to one each.

    Entries that are folders are scanned rather than skipped, so dropping a
    mixture of clips and folders behaves the way dropping either alone does.
    """
    items = {}
    for filename in filenames:
        abs_path = get_absolute_path(os.path.join(directory, filename))
        if not abs_path or not os.path.exists(abs_path):
            continue

        if os.path.isdir(abs_path):
            dropped = os.path.basename(abs_path.rstrip(os.sep)) or filename
            for item in scan_folder(abs_path, recursive, naming):
                if item.path not in items:
                    # keep the folder's own order after the entries before it
                    item.sort_key = path_sort_key(filename) + item.sort_key
                    # Scanning a folder makes it the root, so the sequence level
                    # sits above it and goes unseen. Dropping SQ010 and SQ020
                    # plainly means two sequences, so name them after the folder
                    # unless the tree below already said otherwise.
                    if item.group is None:
                        item.group = dropped
                    items[item.path] = item
            continue

        if not is_supported(filename):
            continue
        item = make_item(abs_path, path_sort_key(filename))
        # Every frame of a sequence resolves to the same first frame, so this
        # is what turns a 500-file selection into the shots it represents.
        if item is not None and item.path not in items:
            items[item.path] = item
    return sorted(items.values(), key=lambda i: i.sort_key)


def apply_lens(cam_data, item, settings):
    """Set the lens from plate metadata when available, else the panel value.

    Sensor width matters as much as focal length -- the same 35mm lens frames
    very differently on Super 35 than on full frame -- so it is applied whenever
    the metadata supplies it.
    """
    lens = read_lens(item.path) if settings.focal_source == 'METADATA' else None

    # Everything found is recorded even when nothing is applied, so the panel can
    # explain *why* a camera kept the fallback value.
    if lens:
        if lens.get('lens_model'):
            cam_data[LENS_MODEL_KEY] = lens['lens_model']
        if lens.get('focus_distance'):
            cam_data[FOCUS_DISTANCE_KEY] = round(float(lens['focus_distance']), 4)
        if lens.get('focal_range'):
            lo, hi = lens['focal_range']
            cam_data[FOCAL_RANGE_KEY] = f"{lo:g}-{hi:g}"
        if lens.get('note'):
            cam_data[LENS_NOTE_KEY] = lens['note']

    if lens and lens.get('focal_length'):
        cam_data.lens = lens['focal_length']
        if lens.get('sensor_width'):
            cam_data.sensor_width = lens['sensor_width']
        source = lens.get('source') or "metadata"
        if lens.get('confidence') == 'assumed':
            source += " (assumed)"
        cam_data[FOCAL_SOURCE_KEY] = source
        return True

    cam_data.lens = settings.focal_length
    cam_data[FOCAL_SOURCE_KEY] = "manual" if lens is None else "manual (no focal length in file)"
    return False


def create_camera(context, item, name, frame, settings):
    if item.is_movie:
        asset = bpy.data.movieclips.load(item.path, check_existing=True)
    else:
        asset = bpy.data.images.load(item.path, check_existing=True)
        asset.source = 'SEQUENCE' if item.is_sequence else 'FILE'

    cam_data = bpy.data.cameras.new(name)
    cam_obj = bpy.data.objects.new(name, cam_data)
    context.collection.objects.link(cam_obj)

    cam_obj.location = (0.0, 0.0, settings.cam_height)
    cam_obj.rotation_euler = (math.radians(90.0), 0.0, 0.0)
    cam_data[SOURCE_PATH_KEY] = item.path
    cam_data.show_background_images = True
    apply_lens(cam_data, item, settings)

    bg = cam_data.background_images.new()
    bg.alpha = settings.bg_opacity
    bg.display_depth = settings.bg_depth
    if item.is_movie:
        bg.source = 'MOVIE_CLIP'
        bg.clip = asset
        asset.frame_start = frame
    else:
        bg.source = 'IMAGE'
        bg.image = asset
        bg.image_user.frame_duration = item.duration
        bg.image_user.frame_start = frame
        bg.image_user.frame_offset = sequence_frame_offset(asset)
        bg.image_user.use_auto_refresh = True

    place_marker(context.scene, cam_obj, frame)
    return cam_obj


def create_cameras(context, items, settings):
    """Lay `items` out on the timeline. Returns (created, skipped_names, from_metadata)."""
    scene = context.scene
    frame = resolve_start_frame(scene, settings)
    if not scene.timeline_markers:
        scene.frame_start = frame

    clear_lens_cache()
    # Folder structure wins; names are the fallback for a flat delivery.
    if settings.naming_mode == 'PATTERN':
        infer_groups_from_names(items)
    created = 0
    from_metadata = 0
    skipped = []
    # Shot numbering restarts inside each sequence, so 0010_0010, 0010_0020 is
    # followed by 0020_0010. Sequences are indexed by first appearance and shots
    # counted per sequence -- incrementing on every *change* of group would
    # invent a new sequence each time the order interleaved two of them.
    sequence_order = {}
    shot_counters = {}
    for entry in items:
        if entry.group not in sequence_order:
            sequence_order[entry.group] = len(sequence_order)
            shot_counters[entry.group] = 0

    for item in items:
        sequence_index = sequence_order.get(item.group, 0)
        shot_index = shot_counters.get(item.group, 0)

        name = item.name
        if settings.naming_mode == 'REPLACE':
            name = name.replace(settings.find_str, settings.replace_str).strip("_") or item.name
        elif settings.naming_mode == 'PATTERN':
            name = apply_name_pattern(
                settings.name_pattern, shot_index,
                settings.number_start, settings.number_step,
                sequence_index, settings.sequence_start, settings.sequence_step,
            )

        try:
            cam_obj = create_camera(context, item, name, frame, settings)
        except Exception as exc:
            print(f"[Plateline] Skipped {item.path}: {exc}")
            skipped.append(os.path.basename(item.path))
            continue

        if cam_obj.data.get(FOCAL_SOURCE_KEY, "manual") != "manual":
            from_metadata += 1
        frame += item.duration + settings.clip_gap
        created += 1
        shot_counters[item.group] = shot_index + 1

    scene.frame_end = frame
    context.view_layer.update()
    force_timeline_view_all(context)
    return created, skipped, from_metadata


# --- operators ---

def resolve_start_frame(scene, settings):
    if settings.placement_mode == 'MANUAL':
        return settings.start_frame
    if settings.placement_mode == 'CURSOR':
        return scene.frame_current
    if not scene.timeline_markers:
        return settings.start_frame

    last = max(scene.timeline_markers, key=lambda m: m.frame)
    duration = DEFAULT_IMAGE_DURATION
    if last.camera:
        duration = get_bg_duration(get_background(last.camera))
    return last.frame + duration + settings.clip_gap


def _report_result(operator, created, skipped, from_metadata, noun):
    lens = f" ({from_metadata} lens from metadata)" if from_metadata else ""
    if skipped:
        operator.report(
            {'WARNING'},
            f"Imported {created} {noun}{lens}, skipped {len(skipped)}: {', '.join(skipped[:3])}",
        )
    elif created:
        operator.report({'INFO'}, f"Imported {created} {noun}{lens}.")
    else:
        operator.report({'WARNING'}, "Nothing importable found.")


class OT_ImportFiles(Operator, ImportHelper):
    bl_idname = "plateline.import_files"
    # Short: this is the file browser's confirm button, which clips a long
    # label. The tooltip carries the detail.
    bl_label = "Import"
    bl_description = "Import selected plates. Frames of one sequence become a single camera"
    bl_options = {'REGISTER', 'UNDO'}

    # SKIP_SAVE matters for drag-and-drop: without it a previous drop's file
    # list is reused, and the second drop imports the first drop's files.
    files: CollectionProperty(type=bpy.types.OperatorFileListElement,
                              options={'SKIP_SAVE', 'HIDDEN'})
    directory: StringProperty(subtype='DIR_PATH', options={'SKIP_SAVE', 'HIDDEN'})
    filter_glob: StringProperty(
        default="*.mp4;*.mov;*.avi;*.mkv;*.webm;*.png;*.jpg;*.jpeg;*.exr;*.tif;*.tiff;*.dpx;*.tga",
        options={'HIDDEN'},
    )

    def invoke(self, context, event):
        """Drag-and-drop already supplies the files; only browse when it hasn't.

        ImportHelper's own invoke always opens the file browser, which made a
        drop ask the user to pick the very files they had just dropped.
        """
        if self.directory and self.files:
            return self.execute(context)
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        if not self.files:
            return {'CANCELLED'}

        settings = context.scene.plateline_settings
        try:
            folder_settings = getattr(context.scene, "plateline_folder", None)
            recursive = getattr(folder_settings, "scan_recursive", True)
            naming = getattr(folder_settings, "folder_naming", 'AUTO')
            with wait_cursor(context):
                items = collect_from_files(
                    self.directory, [f.name for f in self.files], recursive, naming)
                created, skipped, from_metadata = create_cameras(context, items, settings)
        except Exception as exc:
            self.report({'ERROR'}, str(exc))
            return {'CANCELLED'}

        _report_result(self, created, skipped, from_metadata, "clips")
        return {'FINISHED'}


class FH_DropPlates(bpy.types.FileHandler):
    """Drop plates straight into the 3D Viewport.

    Reuses the ordinary file-select operator, so a drop and a browse behave
    identically -- sequences still collapse to one camera per shot.
    """

    bl_idname = "PLATELINE_FH_drop_plates"
    bl_label = "Drop plates to build cameras"
    bl_import_operator = "plateline.import_files"
    bl_file_extensions = ";".join(MOVIE_EXTENSIONS + IMAGE_EXTENSIONS)

    @classmethod
    def poll_drop(cls, context):
        return context.area is not None and context.area.type == 'VIEW_3D'


class OT_ReorderSelectedCameras(Operator):
    bl_idname = "plateline.reorder_cameras"
    bl_label = "Reorder Selected"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return any(o.type == 'CAMERA' for o in context.selected_objects)

    def execute(self, context):
        cameras = sorted(
            (o for o in context.selected_objects if o.type == 'CAMERA'),
            key=lambda o: o.name,
        )
        if not cameras:
            return {'CANCELLED'}

        scene = context.scene
        settings = scene.plateline_settings
        frame = settings.start_frame
        for camera in cameras:
            bg = get_background(camera)
            duration = get_bg_duration(bg)
            set_bg_start(bg, frame)
            place_marker(scene, camera, frame)
            frame += duration + settings.clip_gap

        scene.frame_end = frame
        force_timeline_view_all(context)
        self.report({'INFO'}, f"Reordered {len(cameras)} cameras.")
        return {'FINISHED'}


classes = (
    PlatelineSettings,
    OT_ImportFiles,
    FH_DropPlates,
    OT_ReorderSelectedCameras,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.plateline_settings = bpy.props.PointerProperty(type=PlatelineSettings)


def unregister():
    if hasattr(bpy.types.Scene, "plateline_settings"):
        del bpy.types.Scene.plateline_settings
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
