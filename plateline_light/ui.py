"""Sidebar panel. Pro injects its proxy section through `register_section`."""

import bpy
from bpy.types import Panel

from . import core

# Populated by the Pro-only modules. Keeping the panel extension-driven is what
# lets core stay free of any awareness of proxies, folder scanning or metadata.
_sections = []          # extra boxes, appended after the Camera box
_import_extras = []     # (draw_button, draw_options) pairs inside the Import box
HAS_LENS_METADATA = False


def register_section(func):
    if func not in _sections:
        _sections.append(func)


def unregister_section(func):
    if func in _sections:
        _sections.remove(func)


def register_import_extra(draw_button, draw_options=None):
    entry = (draw_button, draw_options)
    if entry not in _import_extras:
        _import_extras.append(entry)


def unregister_import_extra(draw_button, draw_options=None):
    entry = (draw_button, draw_options)
    if entry in _import_extras:
        _import_extras.remove(entry)


class PT_PlatelinePanel(Panel):
    bl_label = "Plateline"
    bl_idname = "VIEW3D_PT_plateline"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Plateline'

    def draw(self, context):
        layout = self.layout
        settings = context.scene.plateline_settings

        box = layout.box()
        box.label(text="Import", icon='IMPORT')
        box.prop(settings, "placement_mode", text="")
        if settings.placement_mode == 'MANUAL':
            box.prop(settings, "start_frame")
        box.prop(settings, "clip_gap")
        box.separator()
        box.prop(settings, "naming_mode", text="")
        if settings.naming_mode == 'REPLACE':
            box.prop(settings, "find_str")
            box.prop(settings, "replace_str")
        elif settings.naming_mode == 'PATTERN':
            column = box.column(align=True)
            column.prop(settings, "name_pattern", text="")

            # Two fields per row is the most a sidebar column fits: adding a
            # third element squeezed both labels down to "St...".
            grid = box.column(align=True)
            grid.label(text="Shot numbering")
            row = grid.row(align=True)
            row.prop(settings, "number_start", text="Start")
            row.prop(settings, "number_step", text="Step")
            if "@" in settings.name_pattern:
                grid.separator()
                grid.label(text="Sequence numbering")
                row = grid.row(align=True)
                row.prop(settings, "sequence_start", text="Start")
                row.prop(settings, "sequence_step", text="Step")

            # what the current settings actually produce
            preview = box.column(align=True)
            preview.label(text="Cameras will be named")
            body = preview.column(align=True)
            body.scale_y = 0.8
            for line in core.preview_names(settings):
                body.label(text="    " + line)

        row = box.row(align=True)
        row.operator("plateline.import_files",
                     text="Files" if _import_extras else "Import Files", icon='FILE_MOVIE')
        for draw_button, _ in _import_extras:
            draw_button(row, context)
        for _, draw_options in _import_extras:
            if draw_options is not None:
                draw_options(box, context)

        layout.separator()
        box = layout.box()
        box.label(text="Camera", icon='CAMERA_DATA')
        box.prop(settings, "cam_height")
        if HAS_LENS_METADATA:
            box.prop(settings, "focal_source", text="Lens")
            box.prop(settings, "focal_length",
                     text="Fallback" if settings.focal_source == 'METADATA' else "Focal Length")
        else:
            box.prop(settings, "focal_length")
        row = box.row(align=True)
        row.prop(settings, "bg_depth", text="")
        row.prop(settings, "bg_opacity", slider=True)

        for section in _sections:
            layout.separator()
            section(layout, context)

        layout.separator()
        box = layout.box()
        box.label(text="Tools", icon='TOOL_SETTINGS')
        box.prop(settings, "start_frame")
        box.operator("plateline.reorder_cameras", text="Reorder Selected", icon='SORTALPHA')


classes = (
    PT_PlatelinePanel,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
