# To run this script, install the required packages with:
# pip install pyvista pyvistaqt numpy matplotlib PySide6

# =============================================================================
# Black Hawk Rescue Mission NPC Point Visualizer & Editor
#
# Features:
# - Loads NPC spawn points from a text file (default: npc-commands.txt).
# - 3D visualization of all NPC points using PyVista.
# - Color-coded by NPC type, with a clean legend (one entry per type).
# - Unlimited tree-based organization by area, subsection, and type.
# - Select/deselect points or groups in the tree to control visibility.
# - Double-click a point in the tree or in the 3D view to:
#     - Edit its type, position, orientation, area, and subsection.
#     - Preview changes live in the 3D view (point moves and is highlighted).
#     - Move the camera to this point's perspective or set the focal point.
#     - Copy the "bot spawn" line for this point to the clipboard.
#     - Copy the point's coordinates as a JSON array (camera paste compatible).
#     - Save changes to the file (or cancel to revert).
# - Double-click a parent/group node to rename it (updates all child NPCs).
# - Copy all visible points' "bot spawn" lines to the clipboard.
# - Copy or load the current selection (indices) to/from the clipboard.
# - Add NPCs from clipboard (paste lines in bot spawn format).
# - Open/select/load other NPC map files.
# - Save/load workspace files (.json) that store:
#     - Relative map file path
#     - Camera position, focal point, and up vector
#     - Current selection
#     - Orientation marker visibility and offset
# - Camera controls: view/edit/copy/paste camera position, focal point, and up vector.
# - Orientation marker (UP/NORTH) can be moved, hidden, shown, and is saved to workspace.
# - All edits are reflected in the visualization and saved back to the text file.
# =============================================================================

import re
import numpy as np
import pyvista as pv
import matplotlib.pyplot as plt
from pyvistaqt import BackgroundPlotter
from qtpy.QtWidgets import (
    QWidget, QVBoxLayout, QCheckBox, QLabel, QPushButton, QLineEdit,
    QGroupBox, QApplication, QScrollArea, QTreeWidget, QTreeWidgetItem, QSplitter,
    QHBoxLayout, QToolButton, QDialog, QFormLayout, QDialogButtonBox, QMessageBox, QComboBox,
    QFileDialog
)
from qtpy.QtCore import Qt, QObject
import sys
import json
import time
import os

# --- Data Parsing ---
positions = []
area = None
subsection = None

DATA_FILENAME = "npc-commands.txt"

with open(DATA_FILENAME, "r", encoding="utf-8") as f:
    for line in f:
        line = line.strip()
        if line.startswith("## "):
            subsection = line[3:].strip()
        elif line.startswith("# "):
            area = line[2:].strip()
            subsection = None
        elif line.startswith("bot spawn"):
            m = re.match(r"bot spawn \d+ (\S+) ([\-\d\.]+) ([\-\d\.]+) ([\-\d\.]+)(?: ([\-\d\.]+))?", line)
            if m:
                bot_type = m.group(1)
                roblox_x = float(m.group(2))
                roblox_y = float(m.group(3))
                roblox_z = float(m.group(4))
                orientation = float(m.group(5)) if m.lastindex >= 5 and m.group(5) else 0
                positions.append({
                    "area": area,
                    "subsection": subsection,
                    "type": bot_type,
                    "roblox_x": roblox_x,
                    "roblox_y": roblox_y,
                    "roblox_z": roblox_z,
                    "orientation": orientation
                })

# For PyVista: x = roblox_x, y = roblox_z, z = roblox_y
xs = np.array([p["roblox_x"] for p in positions])
ys = np.array([p["roblox_z"] for p in positions])
zs = np.array([p["roblox_y"] for p in positions])
types = [p["type"] for p in positions]
unique_types = sorted(set(types))

color_list = plt.get_cmap('tab10').colors
type_colors = {t: color_list[i % len(color_list)] for i, t in enumerate(unique_types)}

plotter = BackgroundPlotter(show=True, title="BHRM NPC Point Positions (PyVista)")

type_actors = {}
point_actors = []
arrow_actors = []
label_actors = []

orientation_marker_visible = True
orientation_marker_offset = [0, 0, 0]

def orientation_to_vector(orientation_deg):
    angle_rad = np.deg2rad(orientation_deg)
    return np.array([
        np.sin(angle_rad),
        -np.cos(angle_rad),
        0
    ])

def plot_points(selected_point_indices):
    plotter.clear()
    point_actors.clear()
    arrow_actors.clear()
    label_actors.clear()

    type_to_indices = {}
    for idx in selected_point_indices:
        t = positions[idx]["type"]
        type_to_indices.setdefault(t, []).append(idx)

    cone_height = 15
    cone_radius = 4
    for t, indices in type_to_indices.items():
        for idx in indices:
            p = positions[idx]
            pos = np.array([p["roblox_x"], p["roblox_z"], p["roblox_y"]])
            orientation = float(p.get("orientation", 0))
            direction = orientation_to_vector(orientation)
            cone = pv.Cone(center=pos, direction=direction, height=cone_height, radius=cone_radius, resolution=24)
            actor = plotter.add_mesh(cone, color=type_colors[t], name=f"point_{idx}")
            point_actors.append(actor)

    if orientation_marker_visible and len(xs) > 0:
        min_x, min_y, min_z = xs.min(), ys.min(), zs.min()
        ox, oy, oz = orientation_marker_offset
        marker_base = np.array([min_x + ox, min_y + oy, min_z + oz])
        up_len = (zs.max() - min_z) * 0.2 if (zs.max() - min_z) > 0 else 10
        north_len = (ys.max() - min_y) * 0.12 if (ys.max() - min_y) > 0 else 6

        up_arrow = plotter.add_arrows(marker_base[None, :], np.array([[0, 0, up_len]]), color='red', mag=1, label='UP')
        up_label = plotter.add_point_labels(np.array([[marker_base[0], marker_base[1], marker_base[2] + up_len * 1.15]]), ["UP"], point_color='red', font_size=20)
        arrow_actors.append(up_arrow)
        label_actors.append(up_label)

        north_arrow = plotter.add_arrows(marker_base[None, :], np.array([[0, north_len, 0]]), color='blue', mag=1, label='N')
        north_label = plotter.add_point_labels(np.array([[marker_base[0], marker_base[1] + north_len * 1.15, marker_base[2]]]), ["N"], point_color='blue', font_size=20)
        arrow_actors.append(north_arrow)
        label_actors.append(north_label)

    legend_entries = []
    for t in type_to_indices:
        legend_entries.append([t, type_colors[t]])
    if orientation_marker_visible:
        legend_entries.append(["UP", "red"])
        legend_entries.append(["N", "blue"])
    plotter.remove_legend()
    plotter.add_legend(legend_entries)
    plotter.render()

class PointPicker(QObject):
    def __init__(self, plotter, positions, control_panel):
        super().__init__()
        self.plotter = plotter
        self.positions = positions
        self.control_panel = control_panel
        self.last_picked = None
        self.last_time = None
        self.plotter.track_click_position(self.on_pick, side='left')

    def on_pick(self, picked):
        if picked is None:
            return
        min_dist = float('inf')
        min_idx = None
        for idx, p in enumerate(self.positions):
            pos = np.array([p["roblox_x"], p["roblox_z"], p["roblox_y"]])
            dist = np.linalg.norm(pos - np.array(picked))
            if dist < min_dist:
                min_dist = dist
                min_idx = idx
        if min_idx is None or min_dist > 2:
            return

        now = time.time()
        if self.last_picked == min_idx and self.last_time and (now - self.last_time) < 0.5:
            self.control_panel.open_point_details_popup(min_idx)
            self.last_picked = None
            self.last_time = None
        else:
            self.last_picked = min_idx
            self.last_time = now

def build_tree_structure(positions):
    tree = {}
    for idx, p in enumerate(positions):
        path = []
        if p["area"]:
            path.append(p["area"])
        if p["subsection"]:
            path.append(p["subsection"])
        path.append(p["type"])
        node = tree
        for part in path:
            if part not in node:
                node[part] = {}
            node = node[part]
        if "_points" not in node:
            node["_points"] = []
        node["_points"].append(idx)
    return tree

def fill_tree_widget(parent_item, node):
    for key, child in node.items():
        if key == "_points":
            for point_idx in child:
                point = positions[point_idx]
                label = f"{point['type']} ({point['roblox_x']:.1f}, {point['roblox_z']:.1f}, {point['roblox_y']:.1f})"
                point_item = QTreeWidgetItem([label])
                point_item.setFlags(point_item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsSelectable)
                point_item.setCheckState(0, Qt.Unchecked)
                point_item.setData(0, Qt.UserRole, point_idx)
                parent_item.addChild(point_item)
        else:
            item = QTreeWidgetItem([key])
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEditable)
            item.setCheckState(0, Qt.Unchecked)
            fill_tree_widget(item, child)
            parent_item.addChild(item)

class PointEditDialog(QDialog):
    def __init__(self, point, parent=None, goto_point_callback=None, set_focal_callback=None, preview_callback=None, highlight_callback=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Point")
        self.point = point.copy()
        self.goto_point_callback = goto_point_callback
        self.set_focal_callback = set_focal_callback
        self.preview_callback = preview_callback
        self.highlight_callback = highlight_callback
        layout = QFormLayout(self)

        self.type_edit = QComboBox()
        self.type_edit.setEditable(True)
        self.type_edit.addItems(unique_types)
        self.type_edit.setCurrentText(point["type"])
        layout.addRow("Type", self.type_edit)

        self.x_edit = QLineEdit(str(point["roblox_x"]))
        layout.addRow("X", self.x_edit)
        self.y_edit = QLineEdit(str(point["roblox_y"]))
        layout.addRow("Y", self.y_edit)
        self.z_edit = QLineEdit(str(point["roblox_z"]))
        layout.addRow("Z", self.z_edit)
        self.orientation_edit = QLineEdit(str(point.get("orientation", 0)))
        layout.addRow("Orientation", self.orientation_edit)

        self.area_edit = QLineEdit(point.get("area") or "")
        layout.addRow("Area", self.area_edit)
        self.subsection_edit = QLineEdit(point.get("subsection") or "")
        layout.addRow("Subsection", self.subsection_edit)

        btn_layout = QHBoxLayout()
        goto_btn = QPushButton("Go To Perspective")
        focal_btn = QPushButton("Set Focal Here")
        copy_line_btn = QPushButton("Copy Line")
        copy_coords_btn = QPushButton("Copy Coordinates")
        btn_layout.addWidget(goto_btn)
        btn_layout.addWidget(focal_btn)
        btn_layout.addWidget(copy_line_btn)
        btn_layout.addWidget(copy_coords_btn)
        layout.addRow(btn_layout)

        goto_btn.clicked.connect(self.goto_point)
        focal_btn.clicked.connect(self.set_focal)
        copy_line_btn.clicked.connect(self.copy_line_to_clipboard)
        copy_coords_btn.clicked.connect(self.copy_coords_to_clipboard)

        for edit in [self.type_edit.lineEdit(), self.x_edit, self.y_edit, self.z_edit, self.orientation_edit, self.area_edit, self.subsection_edit]:
            edit.textChanged.connect(self.preview)
        self.type_edit.currentTextChanged.connect(self.preview)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)
        self._original_values = self.get_values()

    def get_values(self):
        return {
            "type": self.type_edit.currentText(),
            "roblox_x": float(self.x_edit.text()),
            "roblox_y": float(self.y_edit.text()),
            "roblox_z": float(self.z_edit.text()),
            "orientation": float(self.orientation_edit.text()),
            "area": self.area_edit.text() or None,
            "subsection": self.subsection_edit.text() or None
        }

    def goto_point(self):
        if self.goto_point_callback:
            self.goto_point_callback(self.get_values())

    def set_focal(self):
        if self.set_focal_callback:
            self.set_focal_callback(self.get_values())

    def preview(self):
        if self.preview_callback:
            self.preview_callback(self.get_values())
        if self.highlight_callback:
            self.highlight_callback(self.get_values())

    def copy_line_to_clipboard(self):
        point = self.get_values()
        line = f"bot spawn 1 {point['type']} {point['roblox_x']} {point['roblox_y']} {point['roblox_z']} {point['orientation']}"
        clipboard = QApplication.clipboard()
        clipboard.setText(line)
        QMessageBox.information(self, "Copied", "Point line copied to clipboard.")

    def copy_coords_to_clipboard(self):
        point = self.get_values()
        coords = json.dumps([point['roblox_x'], point['roblox_y'], point['roblox_z']])
        clipboard = QApplication.clipboard()
        clipboard.setText(coords)
        QMessageBox.information(self, "Copied", "Coordinates copied to clipboard (camera paste compatible).")

    def reject(self):
        if self.preview_callback:
            self.preview_callback(self._original_values)
        if self.highlight_callback:
            self.highlight_callback(self._original_values)
        super().reject()

def update_point_in_file(point_idx, new_point, filename=DATA_FILENAME):
    with open(filename, "r", encoding="utf-8") as f:
        lines = f.readlines()
    point = positions[point_idx]
    orig_pattern = re.compile(
        rf"bot spawn \d+ {re.escape(point['type'])} {point['roblox_x']} {point['roblox_y']} {point['roblox_z']}(?: {point.get('orientation', 0)})?"
    )
    new_line = f"bot spawn 1 {new_point['type']} {new_point['roblox_x']} {new_point['roblox_y']} {new_point['roblox_z']} {new_point['orientation']}\n"
    replaced = False
    for i, line in enumerate(lines):
        if orig_pattern.match(line.strip()):
            lines[i] = new_line
            replaced = True
            break
    if not replaced:
        raise Exception("Could not find the original point line in the file.")
    with open(filename, "w", encoding="utf-8") as f:
        f.writelines(lines)

class ControlPanel(QWidget):
    def __init__(self, plotter):
        super().__init__()
        self.plotter = plotter
        self.highlight_actor = None
        self.current_map_file = DATA_FILENAME
        self.workspace_path = None
        self.init_ui()
        self.plotter.add_callback(self.on_camera_changed, 100)

    def _get_parent_names(self, item):
        names = []
        while item is not None and item.parent() is not None:
            names.insert(0, item.text(0))
            item = item.parent()
        return names

    def on_camera_changed(self):
        cam = self.plotter.camera
        pos = cam.position
        focal = cam.focal_point
        up = cam.up
        for i, val in enumerate(pos):
            self.pos_labels[i].setText(f"{val:.2f}")
        for i, val in enumerate(focal):
            self.focal_labels[i].setText(f"{val:.2f}")
        for i, val in enumerate(up):
            self.up_labels[i].setText(f"{val:.2f}")

    def open_point_details_popup(self, point_idx):
        orig_point = positions[point_idx].copy()

        def goto_point(point):
            pos = np.array([point["roblox_x"], point["roblox_z"], point["roblox_y"]])
            orientation = float(point.get("orientation", 0))
            angle_rad = np.deg2rad(orientation)
            offset = np.array([
                -10 * np.sin(angle_rad),
                10 * np.cos(angle_rad),
                3
            ])
            cam_pos = pos + offset
            up = np.array([0, 0, 1])
            self.plotter.camera_position = [cam_pos.tolist(), pos.tolist(), up.tolist()]
            self.plotter.render()

        def set_focal(point):
            cam = self.plotter.camera
            pos = np.array([point["roblox_x"], point["roblox_z"], point["roblox_y"]])
            self.plotter.camera_position = [list(cam.position), pos.tolist(), list(cam.up)]
            self.plotter.render()

        def preview(point):
            xs[point_idx] = point["roblox_x"]
            ys[point_idx] = point["roblox_z"]
            zs[point_idx] = point["roblox_y"]
            types[point_idx] = point["type"]
            self.update_plot()

        def highlight(point):
            if self.highlight_actor is not None:
                try:
                    plotter.remove_actor(self.highlight_actor)
                except Exception:
                    pass
                self.highlight_actor = None
            pt = np.array([[point["roblox_x"], point["roblox_z"], point["roblox_y"]]])
            self.highlight_actor = plotter.add_points(
                pt, color='magenta', point_size=25, render_points_as_spheres=True
            )
            plotter.render()

        dlg = PointEditDialog(
            orig_point, self,
            goto_point_callback=goto_point,
            set_focal_callback=set_focal,
            preview_callback=preview,
            highlight_callback=highlight
        )

        prev_selection = self.get_current_selection_indices()

        result = dlg.exec_()
        if result == QDialog.Accepted:
            new_point = dlg.get_values()
            try:
                update_point_in_file(point_idx, new_point)
            except Exception as e:
                QMessageBox.warning(self, "Save Failed", f"Could not save point: {e}")
                xs[point_idx] = orig_point["roblox_x"]
                ys[point_idx] = orig_point["roblox_z"]
                zs[point_idx] = orig_point["roblox_y"]
                types[point_idx] = orig_point["type"]
                self.update_plot()
                self.set_selection_indices(prev_selection)
                return
            positions[point_idx].update(new_point)
            xs[point_idx] = new_point["roblox_x"]
            ys[point_idx] = new_point["roblox_z"]
            zs[point_idx] = new_point["roblox_y"]
            types[point_idx] = new_point["type"]
            self.area_tree.clear()
            tree_struct = build_tree_structure(positions)
            fill_tree_widget(self.area_tree.invisibleRootItem(), tree_struct)
            self.update_plot()
            self.set_selection_indices(prev_selection)
            QMessageBox.information(self, "Point Updated", "Point updated and saved to file.")
        else:
            xs[point_idx] = orig_point["roblox_x"]
            ys[point_idx] = orig_point["roblox_z"]
            zs[point_idx] = orig_point["roblox_y"]
            types[point_idx] = orig_point["type"]
            self.update_plot()
            self.set_selection_indices(prev_selection)

    def update_plot(self):
        selected_point_indices = set()
        def collect_checked(item):
            point_idx = item.data(0, Qt.UserRole)
            if point_idx is not None:
                if item.checkState(0) == Qt.Checked:
                    selected_point_indices.add(point_idx)
            else:
                for i in range(item.childCount()):
                    collect_checked(item.child(i))
        root = self.area_tree.invisibleRootItem()
        for i in range(root.childCount()):
            collect_checked(root.child(i))
        plot_points(selected_point_indices)

    def select_all_tree(self, value=True):
        state = Qt.Checked if value else Qt.Unchecked
        root = self.area_tree.invisibleRootItem()
        self.area_tree.blockSignals(True)
        def set_all(item):
            item.setCheckState(0, state)
            for i in range(item.childCount()):
                set_all(item.child(i))
        for i in range(root.childCount()):
            set_all(root.child(i))
        self.area_tree.blockSignals(False)
        self.update_plot()

    def on_tree_item_changed(self, item, column):
        state = item.checkState(0)
        self.area_tree.blockSignals(True)
        def set_children(item, state):
            for i in range(item.childCount()):
                child = item.child(i)
                child.setCheckState(0, state)
                set_children(child, state)
        set_children(item, state)
        point_idx = item.data(0, Qt.UserRole)
        renamed = False
        if point_idx is None and item.childCount() > 0:
            def update_descendants(itm, parent_names):
                for i in range(itm.childCount()):
                    child = itm.child(i)
                    child_idx = child.data(0, Qt.UserRole)
                    if child_idx is not None:
                        # Only update the field corresponding to the current depth
                        depth = len(parent_names)
                        if depth == 1:
                            if positions[child_idx]["area"] != parent_names[0]:
                                positions[child_idx]["area"] = parent_names[0]
                                renamed = True
                        elif depth == 2:
                            if positions[child_idx]["subsection"] != parent_names[1]:
                                positions[child_idx]["subsection"] = parent_names[1]
                                renamed = True
                        elif depth == 3:
                            if positions[child_idx]["type"] != parent_names[2]:
                                positions[child_idx]["type"] = parent_names[2]
                                renamed = True
                    else:
                        update_descendants(child, parent_names + [child.text(0)])
            update_descendants(item, self._get_parent_names(item))
        self.area_tree.blockSignals(False)
        self.update_plot()
        # --- Save file if any renaming occurred ---
        if renamed:
            try:
                with open(self.current_map_file, "w", encoding="utf-8") as f:
                    last_area = None
                    last_subsection = None
                    for p in positions:
                        if p["area"] != last_area:
                            last_area = p["area"]
                            f.write(f"# {last_area}\n")
                            last_subsection = None
                        if p["subsection"] != last_subsection and p["subsection"]:
                            last_subsection = p["subsection"]
                            f.write(f"## {last_subsection}\n")
                        line = f"bot spawn 1 {p['type']} {p['roblox_x']} {p['roblox_y']} {p['roblox_z']} {p['orientation']}\n"
                        f.write(line)
            except Exception as e:
                QMessageBox.warning(self, "Save Failed", f"Could not save file after renaming: {e}")

    def on_tree_item_selected(self):
        if self.highlight_actor is not None:
            try:
                plotter.remove_actor(self.highlight_actor)
            except Exception:
                pass
            self.highlight_actor = None

        selected_items = self.area_tree.selectedItems()
        if not selected_items:
            return
        item = selected_items[0]
        point_idx = item.data(0, Qt.UserRole)
        if point_idx is not None:
            p = positions[point_idx]
            pt = np.array([[p["roblox_x"], p["roblox_z"], p["roblox_y"]]])
            self.highlight_actor = plotter.add_points(
                pt, color='magenta', point_size=25, render_points_as_spheres=True
            )
            plotter.render()

    def on_tree_item_double_clicked(self, item, column):
        point_idx = item.data(0, Qt.UserRole)
        if point_idx is not None:
            self.open_point_details_popup(point_idx)
        else:
            self.area_tree.editItem(item, 0)

    def copy_selection_to_clipboard(self):
        selected_point_indices = set()
        def collect_all_indices(item, checked_parent=False):
            point_idx = item.data(0, Qt.UserRole)
            checked = item.checkState(0) == Qt.Checked
            if point_idx is not None:
                if checked or checked_parent:
                    selected_point_indices.add(point_idx)
            else:
                for i in range(item.childCount()):
                    collect_all_indices(item.child(i), checked_parent=checked or checked_parent)
        root = self.area_tree.invisibleRootItem()
        for i in range(root.childCount()):
            collect_all_indices(root.child(i))
        clipboard = QApplication.clipboard()
        clipboard.setText(",".join(str(idx) for idx in sorted(selected_point_indices)))
        QMessageBox.information(self, "Copied", f"Copied {len(selected_point_indices)} selected indices to clipboard.")

    def load_selection_from_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        try:
            indices = set(int(idx) for idx in text.split(",") if idx.strip().isdigit())
        except Exception:
            QMessageBox.warning(self, "Error", "Clipboard does not contain valid indices.")
            return
        def set_checked(item):
            point_idx = item.data(0, Qt.UserRole)
            if point_idx is not None:
                item.setCheckState(0, Qt.Checked if point_idx in indices else Qt.Unchecked)
            else:
                all_checked = True
                for i in range(item.childCount()):
                    set_checked(item.child(i))
                    if item.child(i).checkState(0) != Qt.Checked:
                        all_checked = False
                item.setCheckState(0, Qt.Checked if all_checked and item.childCount() > 0 else Qt.Unchecked)
        root = self.area_tree.invisibleRootItem()
        self.area_tree.blockSignals(True)
        for i in range(root.childCount()):
            set_checked(root.child(i))
        self.area_tree.blockSignals(False)
        self.update_plot()

    def add_npcs_from_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text()
        new_points = []
        area = None
        subsection = None
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("## "):
                subsection = line[3:].strip()
            elif line.startswith("# "):
                area = line[2:].strip()
                subsection = None
            elif line.startswith("bot spawn"):
                m = re.match(r"bot spawn \d+ (\S+) ([\-\d\.]+) ([\-\d\.]+) ([\-\d\.]+)(?: ([\-\d\.]+))?", line)
                if m:
                    bot_type = m.group(1)
                    roblox_x = float(m.group(2))
                    roblox_y = float(m.group(3))
                    roblox_z = float(m.group(4))
                    orientation = float(m.group(5)) if m.lastindex >= 5 and m.group(5) else 0
                    new_points.append({
                        "area": area,
                        "subsection": subsection,
                        "type": bot_type,
                        "roblox_x": roblox_x,
                        "roblox_y": roblox_y,
                        "roblox_z": roblox_z,
                        "orientation": orientation
                    })
        if not new_points:
            QMessageBox.warning(self, "No NPCs Found", "Clipboard does not contain valid NPC lines.")
            return
        with open(self.current_map_file, "a", encoding="utf-8") as f:
            for p in new_points:
                line = f"bot spawn 1 {p['type']} {p['roblox_x']} {p['roblox_y']} {p['roblox_z']} {p['orientation']}\n"
                f.write(line)
        positions.extend(new_points)
        self.reload_positions()
        QMessageBox.information(self, "NPCs Added", f"Added {len(new_points)} NPCs from clipboard.")

    def reload_positions(self):
        global xs, ys, zs, types, unique_types, type_colors
        xs = np.array([p["roblox_x"] for p in positions])
        ys = np.array([p["roblox_z"] for p in positions])
        zs = np.array([p["roblox_y"] for p in positions])
        types[:] = [p["type"] for p in positions]
        unique_types[:] = sorted(set(types))
        type_colors.clear()
        color_list = plt.get_cmap('tab10').colors
        for i, t in enumerate(unique_types):
            type_colors[t] = color_list[i % len(color_list)]
        self.area_tree.clear()
        tree_struct = build_tree_structure(positions)
        fill_tree_widget(self.area_tree.invisibleRootItem(), tree_struct)
        self.update_plot()

    def select_and_load_file(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Open NPC Map File", "", "Text Files (*.txt);;All Files (*)")
        if fname:
            self.load_map_file(fname)

    def open_other_file(self):
        global positions
        positions.clear()
        self.area_tree.clear()
        self.update_plot()
        self.select_and_load_file()
            
    def load_map_file(self, fname):
        global positions, xs, ys, zs, types, unique_types, type_colors, DATA_FILENAME
        DATA_FILENAME = fname
        self.current_map_file = fname
        positions.clear()
        area = None
        subsection = None
        with open(fname, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("## "):
                    subsection = line[3:].strip()
                elif line.startswith("# "):
                    area = line[2:].strip()
                    subsection = None
                elif line.startswith("bot spawn"):
                    m = re.match(r"bot spawn \d+ (\S+) ([\-\d\.]+) ([\-\d\.]+) ([\-\d\.]+)(?: ([\-\d\.]+))?", line)
                    if m:
                        bot_type = m.group(1)
                        roblox_x = float(m.group(2))
                        roblox_y = float(m.group(3))
                        roblox_z = float(m.group(4))
                        orientation = float(m.group(5)) if m.lastindex >= 5 and m.group(5) else 0
                        positions.append({
                            "area": area,
                            "subsection": subsection,
                            "type": bot_type,
                            "roblox_x": roblox_x,
                            "roblox_y": roblox_y,
                            "roblox_z": roblox_z,
                            "orientation": orientation
                        })
        self.reload_positions()
        QMessageBox.information(self, "Loaded", f"Loaded {len(positions)} NPCs from {os.path.basename(fname)}.")

    def save_workspace_as_file(self):
        fname, _ = QFileDialog.getSaveFileName(self, "Save Workspace", "", "Workspace Files (*.json);;All Files (*)")
        if not fname:
            return
        cam = self.plotter.camera
        rel_map = os.path.relpath(self.current_map_file, os.path.dirname(fname))
        selection = self.get_current_selection_indices()
        workspace = {
            "map_file": rel_map,
            "camera": {
                "position": list(cam.position),
                "focal": list(cam.focal_point),
                "up": list(cam.up)
            },
            "selection": selection,
            "orientation_marker": {
                "visible": orientation_marker_visible,
                "offset": orientation_marker_offset
            }
        }
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(workspace, f, indent=2)
        QMessageBox.information(self, "Saved", f"Workspace saved to {fname}")

    def load_workspace_file(self):
        global orientation_marker_visible, orientation_marker_offset
        fname, _ = QFileDialog.getOpenFileName(self, "Load Workspace", "", "Workspace Files (*.json);;All Files (*)")
        if not fname:
            return
        with open(fname, "r", encoding="utf-8") as f:
            workspace = json.load(f)
        map_file = os.path.join(os.path.dirname(fname), workspace["map_file"])
        self.load_map_file(map_file)
        cam = workspace.get("camera", {})
        if cam:
            self.plotter.camera_position = [cam["position"], cam["focal"], cam["up"]]
            self.plotter.render()
        selection = workspace.get("selection", [])
        self.set_selection_indices(selection)
        marker = workspace.get("orientation_marker", {})
        orientation_marker_visible = marker.get("visible", True)
        orientation_marker_offset = marker.get("offset", [0, 0, 0])
        self.marker_show_btn.setChecked(orientation_marker_visible)
        self.marker_show_btn.setText("Show Marker" if not orientation_marker_visible else "Hide Marker")
        self.marker_move_x.setText(str(orientation_marker_offset[0]))
        self.marker_move_y.setText(str(orientation_marker_offset[1]))
        self.marker_move_z.setText(str(orientation_marker_offset[2]))
        self.update_plot()
        QMessageBox.information(self, "Loaded", f"Workspace loaded from {fname}")

    def get_current_selection_indices(self):
        indices = []
        def collect_checked(item):
            point_idx = item.data(0, Qt.UserRole)
            if point_idx is not None:
                if item.checkState(0) == Qt.Checked:
                    indices.append(point_idx)
            else:
                for i in range(item.childCount()):
                    collect_checked(item.child(i))
        root = self.area_tree.invisibleRootItem()
        for i in range(root.childCount()):
            collect_checked(root.child(i))
        return indices

    def set_selection_indices(self, indices):
        indices = set(indices)
        def set_checked(item):
            point_idx = item.data(0, Qt.UserRole)
            if point_idx is not None:
                item.setCheckState(0, Qt.Checked if point_idx in indices else Qt.Unchecked)
            else:
                all_checked = True
                for i in range(item.childCount()):
                    set_checked(item.child(i))
                    if item.child(i).checkState(0) != Qt.Checked:
                        all_checked = False
                item.setCheckState(0, Qt.Checked if all_checked and item.childCount() > 0 else Qt.Unchecked)
        root = self.area_tree.invisibleRootItem()
        self.area_tree.blockSignals(True)
        for i in range(root.childCount()):
            set_checked(root.child(i))
        self.area_tree.blockSignals(False)
        self.update_plot()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        splitter = QSplitter()
        splitter.setOrientation(Qt.Vertical)

        area_group = QGroupBox("Sections & Subsections")
        area_vbox = QVBoxLayout()
        self.area_tree = QTreeWidget()
        self.area_tree.setHeaderHidden(True)
        self.area_tree.itemChanged.connect(self.on_tree_item_changed)
        self.area_tree.itemSelectionChanged.connect(self.on_tree_item_selected)
        self.area_tree.itemDoubleClicked.connect(self.on_tree_item_double_clicked)
        tree_struct = build_tree_structure(positions)
        fill_tree_widget(self.area_tree.invisibleRootItem(), tree_struct)
        area_vbox.addWidget(self.area_tree)
        tree_btn_layout = QVBoxLayout()
        tree_select_all = QPushButton("Select All")
        tree_select_all.clicked.connect(lambda: self.select_all_tree(True))
        tree_deselect_all = QPushButton("Deselect All")
        tree_deselect_all.clicked.connect(lambda: self.select_all_tree(False))
        copy_visible_btn = QPushButton("Copy Visible Points")
        copy_visible_btn.clicked.connect(self.copy_visible_points_to_clipboard)
        copy_selection_btn = QPushButton("Copy Selection To Clipboard")
        copy_selection_btn.clicked.connect(self.copy_selection_to_clipboard)
        load_selection_btn = QPushButton("Load Selection From Clipboard")
        load_selection_btn.clicked.connect(self.load_selection_from_clipboard)
        add_npcs_btn = QPushButton("Add NPCs From Clipboard")
        add_npcs_btn.clicked.connect(self.add_npcs_from_clipboard)
        open_file_btn = QPushButton("Open NPC File")
        open_file_btn.clicked.connect(self.open_other_file)
        save_ws_btn = QPushButton("Save Workspace As...")
        save_ws_btn.clicked.connect(self.save_workspace_as_file)
        load_ws_btn = QPushButton("Load Workspace...")
        load_ws_btn.clicked.connect(self.load_workspace_file)
        tree_btn_layout.addWidget(tree_select_all)
        tree_btn_layout.addWidget(tree_deselect_all)
        tree_btn_layout.addWidget(copy_visible_btn)
        tree_btn_layout.addWidget(copy_selection_btn)
        tree_btn_layout.addWidget(load_selection_btn)
        tree_btn_layout.addWidget(add_npcs_btn)
        tree_btn_layout.addWidget(open_file_btn)
        tree_btn_layout.addWidget(save_ws_btn)
        tree_btn_layout.addWidget(load_ws_btn)
        area_vbox.addLayout(tree_btn_layout)
        area_group.setLayout(area_vbox)

        group = QGroupBox("NPC Types")
        vbox = QVBoxLayout()
        self.type_checkboxes = {}
        for t in unique_types:
            cb = QCheckBox(t)
            cb.setChecked(False)
            cb.stateChanged.connect(self.update_plot)
            self.type_checkboxes[t] = cb
            vbox.addWidget(cb)
        type_btn_layout = QVBoxLayout()
        type_select_all = QPushButton("Select All")
        type_select_all.clicked.connect(lambda: self.select_all_types(True))
        type_deselect_all = QPushButton("Deselect All")
        type_deselect_all.clicked.connect(lambda: self.select_all_types(False))
        type_btn_layout.addWidget(type_select_all)
        type_btn_layout.addWidget(type_deselect_all)
        vbox.addLayout(type_btn_layout)
        group.setLayout(vbox)

        cam_group = QGroupBox("Camera Controls")
        cam_layout = QVBoxLayout()
        cam_layout.addWidget(QLabel("Camera Position:"))
        self.pos_labels = []
        self.pos_edits = []
        pos_layout = QHBoxLayout()
        for i, label in enumerate(["X", "Y", "Z"]):
            lbl = QLabel("0.00")
            self.pos_labels.append(lbl)
            edit = QLineEdit()
            edit.setFixedWidth(70)
            edit.setPlaceholderText("Set...")
            edit.returnPressed.connect(lambda i=i: self.set_camera("pos", i))
            self.pos_edits.append(edit)
            pos_layout.addWidget(QLabel(label))
            pos_layout.addWidget(lbl)
            pos_layout.addWidget(edit)
            up_btn = QToolButton()
            up_btn.setText("▲")
            up_btn.clicked.connect(lambda _, idx=i: self.adjust_value(self.pos_edits, idx, 0.01, "pos"))
            down_btn = QToolButton()
            down_btn.setText("▼")
            down_btn.clicked.connect(lambda _, idx=i: self.adjust_value(self.pos_edits, idx, -0.01, "pos"))
            pos_layout.addWidget(up_btn)
            pos_layout.addWidget(down_btn)
        pos_cp_layout = QVBoxLayout()
        pos_copy_btn = QPushButton("Copy Position")
        pos_copy_btn.setFixedWidth(110)
        pos_copy_btn.clicked.connect(self.copy_position_to_clipboard)
        pos_paste_btn = QPushButton("Paste Position")
        pos_paste_btn.setFixedWidth(110)
        pos_paste_btn.clicked.connect(self.paste_position_from_clipboard)
        pos_cp_layout.addWidget(pos_copy_btn)
        pos_cp_layout.addWidget(pos_paste_btn)
        pos_layout.addLayout(pos_cp_layout)
        cam_layout.addLayout(pos_layout)

        cam_layout.addWidget(QLabel("Focal Point:"))
        self.focal_labels = []
        self.focal_edits = []
        focal_layout = QHBoxLayout()
        for i, label in enumerate(["X", "Y", "Z"]):
            lbl = QLabel("0.00")
            self.focal_labels.append(lbl)
            edit = QLineEdit()
            edit.setFixedWidth(70)
            edit.setPlaceholderText("Set...")
            edit.returnPressed.connect(lambda i=i: self.set_camera("focal", i))
            self.focal_edits.append(edit)
            focal_layout.addWidget(QLabel(label))
            focal_layout.addWidget(lbl)
            focal_layout.addWidget(edit)
            up_btn = QToolButton()
            up_btn.setText("▲")
            up_btn.clicked.connect(lambda _, idx=i: self.adjust_value(self.focal_edits, idx, 0.01, "focal"))
            down_btn = QToolButton()
            down_btn.setText("▼")
            down_btn.clicked.connect(lambda _, idx=i: self.adjust_value(self.focal_edits, idx, -0.01, "focal"))
            focal_layout.addWidget(up_btn)
            focal_layout.addWidget(down_btn)
        focal_cp_layout = QVBoxLayout()
        focal_copy_btn = QPushButton("Copy Focal")
        focal_copy_btn.setFixedWidth(110)
        focal_copy_btn.clicked.connect(self.copy_focal_to_clipboard)
        focal_paste_btn = QPushButton("Paste Focal")
        focal_paste_btn.setFixedWidth(110)
        focal_paste_btn.clicked.connect(self.paste_focal_from_clipboard)
        focal_cp_layout.addWidget(focal_copy_btn)
        focal_cp_layout.addWidget(focal_paste_btn)
        focal_layout.addLayout(focal_cp_layout)
        cam_layout.addLayout(focal_layout)

        cam_layout.addWidget(QLabel("View Up Vector:"))
        self.up_labels = []
        self.up_edits = []
        up_layout = QHBoxLayout()
        for i, label in enumerate(["X", "Y", "Z"]):
            lbl = QLabel("0.00")
            self.up_labels.append(lbl)
            edit = QLineEdit()
            edit.setFixedWidth(70)
            edit.setPlaceholderText("Set...")
            edit.returnPressed.connect(lambda i=i: self.set_camera("up", i))
            self.up_edits.append(edit)
            up_layout.addWidget(QLabel(label))
            up_layout.addWidget(lbl)
            up_layout.addWidget(edit)
            up_btn = QToolButton()
            up_btn.setText("▲")
            up_btn.clicked.connect(lambda _, idx=i: self.adjust_value(self.up_edits, idx, 0.01, "up"))
            down_btn = QToolButton()
            down_btn.setText("▼")
            down_btn.clicked.connect(lambda _, idx=i: self.adjust_value(self.up_edits, idx, -0.01, "up"))
            up_layout.addWidget(up_btn)
            up_layout.addWidget(down_btn)
        cam_layout.addLayout(up_layout)

        clipboard_layout = QHBoxLayout()
        copy_btn = QPushButton("Copy Camera To Clipboard")
        copy_btn.clicked.connect(self.copy_camera_to_clipboard)
        paste_btn = QPushButton("Load Camera From Clipboard")
        paste_btn.clicked.connect(self.load_camera_from_clipboard)
        clipboard_layout.addWidget(copy_btn)
        clipboard_layout.addWidget(paste_btn)
        cam_layout.addLayout(clipboard_layout)

        cam_btn = QPushButton("Set All Camera")
        cam_btn.clicked.connect(self.set_camera)
        cam_layout.addWidget(cam_btn)
        cam_group.setLayout(cam_layout)

        marker_group = QGroupBox("Orientation Marker")
        marker_layout = QHBoxLayout()
        self.marker_show_btn = QPushButton("Show Marker" if not orientation_marker_visible else "Hide Marker")
        self.marker_show_btn.setCheckable(True)
        self.marker_show_btn.setChecked(orientation_marker_visible)
        self.marker_show_btn.clicked.connect(self.toggle_orientation_marker)
        marker_layout.addWidget(self.marker_show_btn)

        self.marker_move_x = QLineEdit(str(orientation_marker_offset[0]))
        self.marker_move_y = QLineEdit(str(orientation_marker_offset[1]))
        self.marker_move_z = QLineEdit(str(orientation_marker_offset[2]))
        for edit in [self.marker_move_x, self.marker_move_y, self.marker_move_z]:
            edit.setFixedWidth(50)
            edit.editingFinished.connect(self.move_orientation_marker)
        marker_layout.addWidget(QLabel("X:"))
        marker_layout.addWidget(self.marker_move_x)
        marker_layout.addWidget(QLabel("Y:"))
        marker_layout.addWidget(self.marker_move_y)
        marker_layout.addWidget(QLabel("Z:"))
        marker_layout.addWidget(self.marker_move_z)
        marker_group.setLayout(marker_layout)
        cam_layout.addWidget(marker_group)

        splitter.addWidget(area_group)
        splitter.addWidget(group)
        splitter.addWidget(cam_group)
        splitter.setSizes([200, 100, 100])

        scroll_layout.addWidget(splitter)
        scroll_content.setLayout(scroll_layout)
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        self.setLayout(main_layout)
        self.update_plot()

    def select_all_types(self, value=True):
        for cb in self.type_checkboxes.values():
            cb.setChecked(value)
        self.update_plot()

    def copy_camera_to_clipboard(self):
        cam = self.plotter.camera
        data = {
            "position": list(cam.position),
            "focal": list(cam.focal_point),
            "up": list(cam.up)
        }
        clipboard = QApplication.clipboard()
        clipboard.setText(json.dumps(data, indent=2))

    def load_camera_from_clipboard(self):
        clipboard = QApplication.clipboard()
        try:
            data = json.loads(clipboard.text())
            pos = data["position"]
            focal = data["focal"]
            up = data["up"]
            self.plotter.camera_position = [pos, focal, up]
            self.plotter.render()
            for i in range(3):
                self.pos_edits[i].setText(f"{pos[i]:.2f}")
                self.focal_edits[i].setText(f"{focal[i]:.2f}")
                self.up_edits[i].setText(f"{up[i]:.2f}")
        except Exception as e:
            print("Clipboard does not contain valid camera data:", e)

    def copy_position_to_clipboard(self):
        cam = self.plotter.camera
        clipboard = QApplication.clipboard()
        clipboard.setText(json.dumps(list(cam.position)))

    def paste_position_from_clipboard(self):
        clipboard = QApplication.clipboard()
        try:
            pos = json.loads(clipboard.text())
            if isinstance(pos, list) and len(pos) == 3:
                cam = self.plotter.camera
                self.plotter.camera_position = [pos, list(cam.focal_point), list(cam.up)]
                self.plotter.render()
                for i in range(3):
                    self.pos_edits[i].setText(f"{pos[i]:.2f}")
        except Exception as e:
            print("Clipboard does not contain valid position:", e)

    def copy_focal_to_clipboard(self):
        cam = self.plotter.camera
        clipboard = QApplication.clipboard()
        clipboard.setText(json.dumps(list(cam.focal_point)))

    def paste_focal_from_clipboard(self):
        clipboard = QApplication.clipboard()
        try:
            focal = json.loads(clipboard.text())
            if isinstance(focal, list) and len(focal) == 3:
                cam = self.plotter.camera
                self.plotter.camera_position = [list(cam.position), focal, list(cam.up)]
                self.plotter.render()
                for i in range(3):
                    self.focal_edits[i].setText(f"{focal[i]:.2f}")
        except Exception as e:
            print("Clipboard does not contain valid focal point:", e)

    def copy_visible_points_to_clipboard(self):
        selected_point_indices = set()
        def collect_checked(item):
            point_idx = item.data(0, Qt.UserRole)
            if point_idx is not None:
                if item.checkState(0) == Qt.Checked:
                    selected_point_indices.add(point_idx)
            else:
                for i in range(item.childCount()):
                    collect_checked(item.child(i))
        root = self.area_tree.invisibleRootItem()
        for i in range(root.childCount()):
            collect_checked(root.child(i))

        with open(DATA_FILENAME, "r", encoding="utf-8") as f:
            lines = f.readlines()

        visible_points = set()
        for idx in selected_point_indices:
            point = positions[idx]
            visible_points.add((
                point["type"],
                point["roblox_x"],
                point["roblox_y"],
                point["roblox_z"],
                point.get("orientation", 0)
            ))

        output_lines = []
        for line in lines:
            m = re.match(r"bot spawn \d+ (\S+) ([\-\d\.]+) ([\-\d\.]+) ([\-\d\.]+)(?: ([\-\d\.]+))?", line.strip())
            if m:
                t = m.group(1)
                x = float(m.group(2))
                y = float(m.group(3))
                z = float(m.group(4))
                orientation = float(m.group(5)) if m.lastindex >= 5 and m.group(5) else 0
                if (t, x, y, z, orientation) in visible_points:
                    output_lines.append(line.rstrip())
        clipboard = QApplication.clipboard()
        clipboard.setText("\n".join(output_lines))
        QMessageBox.information(self, "Copied", f"Copied {len(output_lines)} lines to clipboard.")

    def adjust_value(self, edits, idx, delta, which):
        try:
            cam = self.plotter.camera
            if edits[idx].text().strip() == "":
                if which == "pos":
                    val = cam.position[idx]
                elif which == "focal":
                    val = cam.focal_point[idx]
                elif which == "up":
                    val = cam.up[idx]
            else:
                val = float(edits[idx].text())
            new_val = val + delta
            edits[idx].setText(f"{new_val:.2f}")
            self.set_camera(which, idx)
            cam = self.plotter.camera
            if which == "pos":
                edits[idx].setText(f"{cam.position[idx]:.2f}")
            elif which == "focal":
                edits[idx].setText(f"{cam.focal_point[idx]:.2f}")
            elif which == "up":
                edits[idx].setText(f"{cam.up[idx]:.2f}")
        except Exception:
            pass

    def set_camera(self, which=None, idx=None):
        try:
            cam = self.plotter.camera
            pos = list(cam.position)
            focal = list(cam.focal_point)
            up = list(cam.up)
            if which is not None and idx is not None:
                if which == "pos":
                    val = self.pos_edits[idx].text()
                    if val.strip() != "":
                        pos[idx] = float(val)
                elif which == "focal":
                    val = self.focal_edits[idx].text()
                    if val.strip() != "":
                        focal[idx] = float(val)
                elif which == "up":
                    val = self.up_edits[idx].text()
                    if val.strip() != "":
                        up[idx] = float(val)
            else:
                for i, edit in enumerate(self.pos_edits):
                    val = edit.text()
                    if val.strip() != "":
                        pos[i] = float(val)
                for i, edit in enumerate(self.focal_edits):
                    val = edit.text()
                    if val.strip() != "":
                        focal[i] = float(val)
                for i, edit in enumerate(self.up_edits):
                    val = edit.text()
                    if val.strip() != "":
                        up[i] = float(val)
            self.plotter.camera_position = [pos, focal, up]
            self.plotter.render()
        except Exception as e:
            print("Invalid camera input:", e)

    def toggle_orientation_marker(self):
        global orientation_marker_visible
        orientation_marker_visible = not orientation_marker_visible
        self.marker_show_btn.setText("Show Marker" if not orientation_marker_visible else "Hide Marker")
        self.marker_show_btn.setChecked(orientation_marker_visible)
        self.update_plot()

    def move_orientation_marker(self):
        global orientation_marker_offset
        try:
            x = float(self.marker_move_x.text())
            y = float(self.marker_move_y.text())
            z = float(self.marker_move_z.text())
            orientation_marker_offset = [x, y, z]
            self.update_plot()
        except Exception:
            pass

picker = None
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)
panel = ControlPanel(plotter)
picker = PointPicker(plotter, positions, panel)
panel.show()
app.exec()