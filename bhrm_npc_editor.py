# To run this script, install the required packages with:
# pip install pyvista pyvistaqt numpy matplotlib PySide6

# =============================================================================
# Black Hawk Rescue Mission NPC Point Visualizer & Editor
#
# Features:
# - Loads NPC spawn points from a text file (default: bot_spawn_commands.txt).
# - 3D visualization of all NPC points using PyVista.
# - Color-coded by NPC type, with a clean legend (one entry per type).
# - Tree-based organization by path (folders).
# - Select/deselect points or groups in the tree to control visibility.
# - Double-click a point in the tree or 3D view to edit its properties.
# - Live preview of edits in the 3D view.
# - Camera controls: view/edit/copy/paste camera position, focal point, and up vector.
# - Orientation marker (UP/NORTH) can be moved, hidden, shown, and is saved to workspace.
# - Copy visible or selected points to clipboard.
# - Add NPCs from clipboard (they are appended at the end, with no path).
# - Open/select/load other NPC map files.
# - Save/load workspace files (.json) that store:
#     - Absolute map file path
#     - Camera position, focal point, and up vector
#     - Current selection
#     - Orientation marker visibility and offset
# - All edits are reflected in the visualization and saved back to the text file.
# - "Save Workspace" button is always visible.
# - On startup, loads workspace.json if it exists.
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

positions = []
DATA_FILENAME = "bot_spawn_commands.txt"

def get_all_folder_paths(self):
    paths = []
    def walk(item, path):
        if item.data(0, Qt.UserRole) is None:  # It's a folder
            new_path = path + [item.text(0)]
            paths.append(new_path)
            for i in range(item.childCount()):
                walk(item.child(i), new_path)
    root = self.area_tree.invisibleRootItem()
    for i in range(root.childCount()):
        walk(root.child(i), [])
    return paths

def save_positions_to_file(filename, folder_paths=None):
    def path_split(path):
        return [p for p in path.split("/") if p]
    sorted_positions = sorted(positions, key=lambda p: (path_split(p.get("path", "")), p.get("order", 0)))
    with open(filename, "w", encoding="utf-8") as f:
        last_path = []
        if folder_paths:
            for folder_path in sorted(folder_paths, key=lambda x: (len(x), x)):
                for i in range(len(folder_path)):
                    if last_path[:i+1] != folder_path[:i+1]:
                        f.write("#" * (i + 1) + " " + folder_path[i] + "\n")
                last_path = list(folder_path)
        for p in sorted_positions:
            path_parts = path_split(p.get("path", ""))
            common = 0
            for a, b in zip(last_path, path_parts):
                if a == b:
                    common += 1
                else:
                    break
            for i in range(common, len(path_parts)):
                f.write("#" * (i + 1) + " " + path_parts[i] + "\n")
            last_path = path_parts
            if p.get("command") == "bot spawn":
                line = f"bot spawn 1 {p['type']} {p['roblox_x']} {p['roblox_y']} {p['roblox_z']} {p.get('orientation', 0)}\n"
            elif p.get("command") == "spawn":
                line = f"spawn 1 {p['type']} {p['roblox_x']} {p['roblox_y']} {p['roblox_z']} {p.get('rot_x', 0)} {p.get('rot_y', 0)} {p.get('rot_z', 0)}\n"
            else:
                continue
            f.write(line)

def parse_bot_file(filename):
    positions = []
    folder_stack = []
    folder_counters = {}
    with open(filename, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("//"):
                continue
            m_folder = re.match(r"^(#+)\s*(.*)", line)
            if m_folder:
                level = len(m_folder.group(1))
                name = m_folder.group(2).strip()
                if not name:
                    continue
                folder_stack = folder_stack[:level-1]
                folder_stack.append(name)
                continue
            m_bot = re.match(r"bot spawn \d+ (\S+) ([\-\d\.]+) ([\-\d\.]+) ([\-\d\.]+)(?: ([\-\d\.]+))?", line)
            if m_bot:
                bot_type = m_bot.group(1)
                roblox_x = float(m_bot.group(2))
                roblox_y = float(m_bot.group(3))
                roblox_z = float(m_bot.group(4))
                orientation = float(m_bot.group(5)) if m_bot.lastindex >= 5 and m_bot.group(5) else 0
                path = "/".join(folder_stack)
                order = folder_counters.get(path, 0)
                folder_counters[path] = order + 1
                positions.append({
                    "command": "bot spawn",
                    "type": bot_type,
                    "roblox_x": roblox_x,
                    "roblox_y": roblox_y,
                    "roblox_z": roblox_z,
                    "orientation": orientation,
                    "path": path,
                    "order": order
                })
                continue
            m_prop = re.match(r"spawn \d+ (\S+) ([\-\d\.]+) ([\-\d\.]+) ([\-\d\.]+) ([\-\d\.]+) ([\-\d\.]+) ([\-\d\.]+)", line)
            if m_prop:
                prop_type = m_prop.group(1)
                roblox_x = float(m_prop.group(2))
                roblox_y = float(m_prop.group(3))
                roblox_z = float(m_prop.group(4))
                rot_x = float(m_prop.group(5))
                rot_y = float(m_prop.group(6))
                rot_z = float(m_prop.group(7))
                path = "/".join(folder_stack)
                order = folder_counters.get(path, 0)
                folder_counters[path] = order + 1
                positions.append({
                    "command": "spawn",
                    "type": prop_type,
                    "roblox_x": roblox_x,
                    "roblox_y": roblox_y,
                    "roblox_z": roblox_z,
                    "rot_x": rot_x,
                    "rot_y": rot_y,
                    "rot_z": rot_z,
                    "path": path,
                    "order": order
                })
    return positions

def orientation_to_vector(orientation_deg):
    angle_rad = np.deg2rad(orientation_deg)
    return np.array([
        np.sin(angle_rad),
        -np.cos(angle_rad),
        0
    ])

def prop_rot_to_vector(rot_x, rot_y, rot_z):
    angle_rad = np.deg2rad(rot_y)
    return np.array([
        np.sin(angle_rad),
        -np.cos(angle_rad),
        0
    ])

def build_tree_structure(positions):
    tree = {}
    for idx, p in enumerate(positions):
        path = p.get("path", "")
        parts = [part for part in path.strip("/").split("/") if part] if path else []
        node = tree
        for part in parts:
            if part not in node:
                node[part] = {}
            node = node[part]
        if "_points" not in node:
            node["_points"] = []
        node["_points"].append((p.get("order", 0), idx))
    return tree

def fill_tree_widget(parent_item, tree_struct):
    def add_nodes(node, parent):
        for key in sorted(k for k in node.keys() if k != "_points"):
            folder_item = QTreeWidgetItem([key])
            folder_item.setFlags(
                folder_item.flags()
                | Qt.ItemIsUserCheckable
                | Qt.ItemIsDragEnabled
                | Qt.ItemIsDropEnabled
                | Qt.ItemIsEditable
            )
            folder_item.setCheckState(0, Qt.Unchecked)
            folder_item._old_name = key  # Track old name for rename logic
            add_nodes(node[key], folder_item)
            parent.addChild(folder_item)
        if "_points" in node:
            for order, idx in sorted(node["_points"]):
                point = positions[idx]
                label = f"{point['type']} ({point['roblox_x']:.1f}, {point['roblox_z']:.1f}, {point['roblox_y']:.1f})"
                point_item = QTreeWidgetItem([label])
                point_item.setFlags(
                    point_item.flags()
                    | Qt.ItemIsUserCheckable
                    | Qt.ItemIsSelectable
                    | Qt.ItemIsDragEnabled
                )
                point_item.setCheckState(0, Qt.Unchecked)
                point_item.setData(0, Qt.UserRole, idx)
                parent.addChild(point_item)
    add_nodes(tree_struct, parent_item)

def get_transformed_positions():
    return np.array([[-p["roblox_x"], p["roblox_z"], p["roblox_y"]] for p in positions])

def get_types():
    return [p["type"] for p in positions]

def get_unique_types():
    return sorted(set(get_types()))

def get_type_colors():
    color_list = plt.get_cmap('tab10').colors
    unique_types = get_unique_types()
    return {t: color_list[i % len(color_list)] for i, t in enumerate(unique_types)}

plotter = BackgroundPlotter(show=True, title="BHRM NPC Point Positions (PyVista)")

type_actors = {}
point_actors = []
arrow_actors = []
label_actors = []

orientation_marker_visible = True
orientation_marker_offset = [0, 0, 0]

def plot_points(selected_point_indices):
    global xs, ys, zs, types, unique_types, type_colors
    transformed_positions = get_transformed_positions()
    xs, ys, zs = transformed_positions[:, 0], transformed_positions[:, 1], transformed_positions[:, 2]
    types = get_types()
    unique_types = get_unique_types()
    type_colors = get_type_colors()

    plotter.clear()
    point_actors.clear()
    arrow_actors.clear()
    label_actors.clear()

    checked_types = set()
    if hasattr(plot_points, "panel") and hasattr(plot_points.panel, "type_checkboxes"):
        checked_types = {t for t, cb in plot_points.panel.type_checkboxes.items() if cb.isChecked()}
    else:
        checked_types = set(unique_types)

    type_to_indices = {}
    for idx in selected_point_indices:
        t = positions[idx]["type"]
        if t in checked_types:
            type_to_indices.setdefault(t, []).append(idx)

    cone_height = 15
    cone_radius = 4
    wedge_length = 15
    wedge_width = 8
    wedge_height = 6

    for t, indices in type_to_indices.items():
        for idx in indices:
            p = positions[idx]
            pos = transformed_positions[idx]
            if p.get("command") == "bot spawn":
                orientation = float(p.get("orientation", 0))
                direction = orientation_to_vector(orientation)
                # Draw NPC as cone
                cone = pv.Cone(center=pos, direction=direction, height=cone_height, radius=cone_radius, resolution=24)
                actor = plotter.add_mesh(cone, color=type_colors[t], name=f"point_{idx}")
                point_actors.append(actor)
            elif p.get("command") == "spawn":
                # Draw prop as wedge (triangular prism)
                # Compute orientation from rot_y (yaw), rot_x (pitch), rot_z (roll)
                yaw = np.deg2rad(p.get("rot_z", 0))                    # Y and Z swapped
                pitch = np.deg2rad(-p.get("rot_x", 0))                 # X inverted
                roll = np.deg2rad(p.get("rot_y", 0))                   # Y and Z swapped

                # Local wedge vertices (centered at origin, pointing +Y)
                # Triangle base at -length/2, rectangle at +length/2
                v = np.array([
                    [0, wedge_length/2, 0],  # tip
                    [-wedge_width/2, -wedge_length/2, -wedge_height/2],  # base left bottom
                    [wedge_width/2, -wedge_length/2, -wedge_height/2],   # base right bottom
                    [wedge_width/2, -wedge_length/2, wedge_height/2],    # base right top
                    [-wedge_width/2, -wedge_length/2, wedge_height/2],   # base left top
                ])
                # Faces: tip, base, sides
                faces = [
                    3, 0, 1, 2,  # bottom triangle
                    3, 0, 2, 3,  # right triangle
                    3, 0, 3, 4,  # top triangle
                    3, 0, 4, 1,  # left triangle
                    4, 1, 2, 3, 4  # base quad
                ]
                # Rotation matrix: R = Rz(roll) @ Rx(pitch) @ Ry(yaw)
                def rotmat(yaw, pitch, roll):
                    cy, sy = np.cos(yaw), np.sin(yaw)
                    cp, sp = np.cos(pitch), np.sin(pitch)
                    cr, sr = np.cos(roll), np.sin(roll)
                    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
                    Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
                    Rz = np.array([[cr, -sr, 0], [sr, cr, 0], [0, 0, 1]])
                    return Rz @ Rx @ Ry
                R = rotmat(yaw, pitch, roll)
                v_rot = (R @ v.T).T
                v_final = v_rot + pos
                wedge = pv.PolyData(v_final, faces)
                actor = plotter.add_mesh(wedge, color=type_colors[t], name=f"point_{idx}")
                point_actors.append(actor)
            else:
                # fallback: draw a small sphere
                sphere = pv.Sphere(radius=3, center=pos)
                actor = plotter.add_mesh(sphere, color=type_colors[t], name=f"point_{idx}")
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
        transformed_positions = get_transformed_positions()
        min_dist = float('inf')
        min_idx = None
        for idx, p in enumerate(self.positions):
            pos = transformed_positions[idx]
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

        unique_types = get_unique_types()

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

        self.orientation_edit = None
        self.rot_x_edit = None
        self.rot_y_edit = None
        self.rot_z_edit = None

        if point.get("command") == "bot spawn" or ("orientation" in point and "rot_x" not in point):
            self.orientation_edit = QLineEdit(str(point.get("orientation", 0)))
            layout.addRow("Orientation", self.orientation_edit)
        elif point.get("command") == "spawn" or ("rot_x" in point):
            self.rot_x_edit = QLineEdit(str(point.get("rot_x", 0)))
            self.rot_y_edit = QLineEdit(str(point.get("rot_y", 0)))
            self.rot_z_edit = QLineEdit(str(point.get("rot_z", 0)))
            layout.addRow("Rot X", self.rot_x_edit)
            layout.addRow("Rot Y", self.rot_y_edit)
            layout.addRow("Rot Z", self.rot_z_edit)

        self.path_edit = QLineEdit(point.get("path", ""))
        layout.addRow("Path", self.path_edit)
        self.order_edit = QLineEdit(str(point.get("order", 0)))
        self.order_edit.setReadOnly(True)
        layout.addRow("Order", self.order_edit)

        btn_layout = QHBoxLayout()
        goto_btn = QPushButton("Go To Perspective")
        focal_btn = QPushButton("Set Focal Here")
        copy_line_btn = QPushButton("Copy Line")
        copy_coords_btn = QPushButton("Copy Coordinates")
        move_up_btn = QPushButton("Move Up")
        move_down_btn = QPushButton("Move Down")
        preview_btn = QPushButton("Preview")
        stop_preview_btn = QPushButton("Stop Preview")
        self.stop_preview_btn = stop_preview_btn
        btn_layout.addWidget(goto_btn)
        btn_layout.addWidget(focal_btn)
        btn_layout.addWidget(copy_line_btn)
        btn_layout.addWidget(copy_coords_btn)
        btn_layout.addWidget(move_up_btn)
        btn_layout.addWidget(move_down_btn)
        btn_layout.addWidget(preview_btn)
        btn_layout.addWidget(stop_preview_btn)
        layout.addRow(btn_layout)

        goto_btn.clicked.connect(self.goto_point)
        focal_btn.clicked.connect(self.set_focal)
        copy_line_btn.clicked.connect(self.copy_line_to_clipboard)
        copy_coords_btn.clicked.connect(self.copy_coords_to_clipboard)
        move_up_btn.clicked.connect(lambda: self.move_point(-1))
        move_down_btn.clicked.connect(lambda: self.move_point(1))
        preview_btn.clicked.connect(self.preview)
        stop_preview_btn.clicked.connect(self.stop_preview)


        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)
        self._original_values = self.get_values()
        self._point_idx = point.get("_idx", None)
        self._previewing = False

    def get_values(self):
        base = {
            "type": self.type_edit.currentText(),
            "roblox_x": float(self.x_edit.text()),
            "roblox_y": float(self.y_edit.text()),
            "roblox_z": float(self.z_edit.text()),
            "path": self.path_edit.text(),
            "order": int(self.order_edit.text())
        }
        if self.orientation_edit is not None:
            base["orientation"] = float(self.orientation_edit.text())
            base["command"] = "bot spawn"
        elif self.rot_x_edit is not None:
            base["rot_x"] = float(self.rot_x_edit.text())
            base["rot_y"] = float(self.rot_y_edit.text())
            base["rot_z"] = float(self.rot_z_edit.text())
            base["command"] = "spawn"
        return base

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
        self._previewing = True

    def stop_preview(self):
        if self.preview_callback:
            self.preview_callback(self._original_values)
        if self.highlight_callback:
            self.highlight_callback(self._original_values)
        self._previewing = False

    def copy_line_to_clipboard(self):
        point = self.get_values()
        if point.get("command") == "bot spawn":
            line = f"bot spawn 1 {point['type']} {point['roblox_x']} {point['roblox_y']} {point['roblox_z']} {point.get('orientation', 0)}"
        elif point.get("command") == "spawn":
            line = f"spawn 1 {point['type']} {point['roblox_x']} {point['roblox_y']} {point['roblox_z']} {point.get('rot_x', 0)} {point.get('rot_y', 0)} {point.get('rot_z', 0)}"
        else:
            line = ""
        clipboard = QApplication.clipboard()
        clipboard.setText(line)
        QMessageBox.information(self, "Copied", "Point line copied to clipboard.")

    def copy_coords_to_clipboard(self):
        point = self.get_values()
        coords = json.dumps([point['roblox_x'], point['roblox_y'], point['roblox_z']])
        clipboard = QApplication.clipboard()
        clipboard.setText(coords)
        QMessageBox.information(self, "Copied", "Coordinates copied to clipboard (camera paste compatible).")

    def move_point(self, direction):
        if self._point_idx is None:
            return
        current = positions[self._point_idx]
        folder = current.get("path", "")
        same_folder = [i for i, p in enumerate(positions) if p.get("path", "") == folder]
        same_folder_sorted = sorted(same_folder, key=lambda idx: positions[idx]["order"])
        idx_in_folder = next((i for i, idx in enumerate(same_folder_sorted) if idx == self._point_idx), None)
        if idx_in_folder is None:
            return
        swap_with = idx_in_folder + direction
        if 0 <= swap_with < len(same_folder_sorted):
            idx_a = same_folder_sorted[idx_in_folder]
            idx_b = same_folder_sorted[swap_with]
            positions[idx_a]["order"], positions[idx_b]["order"] = positions[idx_b]["order"], positions[idx_a]["order"]
            save_positions_to_file(DATA_FILENAME)
            if self.parent() and hasattr(self.parent(), "reload_positions"):
                self.parent().reload_positions()
            self.order_edit.setText(str(positions[self._point_idx]["order"]))

    def reject(self):
        self.stop_preview()
        super().reject()

def update_point_in_file(point_idx, new_point, filename=DATA_FILENAME):
    positions[point_idx].update(new_point)
    save_positions_to_file(filename)

class ControlPanel(QWidget):
    def __init__(self, plotter):
        super().__init__()
        self.plotter = plotter
        self.highlight_actor = None
        self.current_map_file = DATA_FILENAME
        self.workspace_loaded_path = None
        self.init_ui()
        self.plotter.add_callback(self.on_camera_changed, 100)
        ControlPanel.get_all_folder_paths = get_all_folder_paths
    def rebuild_type_checkboxes(self):
        # Remove old checkboxes
        for cb in getattr(self, "type_checkboxes", {}).values():
            cb.setParent(None)
        self.type_checkboxes = {}
        for t in get_unique_types():
            cb = QCheckBox(t)
            cb.setChecked(True)
            cb.stateChanged.connect(self.update_plot)
            self.type_checkboxes[t] = cb
            self.type_vbox.addWidget(cb)
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

    def get_tree_state(self):
        expanded = set()
        checked = set()
        selected = set()
        def walk(item, path):
            text = item.text(0)
            this_path = path + (text,)
            if item.isExpanded():
                expanded.add(this_path)
            if item.checkState(0) == Qt.Checked:
                checked.add(this_path)
            if item.isSelected():
                selected.add(this_path)
            for i in range(item.childCount()):
                walk(item.child(i), this_path)
        root = self.area_tree.invisibleRootItem()
        for i in range(root.childCount()):
            walk(root.child(i), ())
        return {"expanded": expanded, "checked": checked, "selected": selected}

    def set_tree_state(self, state):
        expanded = state.get("expanded", set())
        checked = state.get("checked", set())
        selected = state.get("selected", set())
        def walk(item, path):
            text = item.text(0)
            this_path = path + (text,)
            if this_path in expanded:
                item.setExpanded(True)
            if this_path in checked:
                item.setCheckState(0, Qt.Checked)
            if this_path in selected:
                item.setSelected(True)
            for i in range(item.childCount()):
                walk(item.child(i), this_path)
        root = self.area_tree.invisibleRootItem()
        for i in range(root.childCount()):
            walk(root.child(i), ())

    def open_point_details_popup(self, point_idx):
        tree_state = self.get_tree_state()
        orig_point = positions[point_idx].copy()
        orig_point["_idx"] = point_idx

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
            self._preview_backup = positions[point_idx].copy()
            positions[point_idx].update(point)
            self.update_plot()

        def stop_preview(point=None):
            if hasattr(self, "_preview_backup"):
                positions[point_idx].update(self._preview_backup)
                self.update_plot()
                del self._preview_backup

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

        dlg.stop_preview_btn.clicked.disconnect()
        dlg.stop_preview_btn.clicked.connect(lambda: stop_preview())

        prev_selection = self.get_current_selection_indices()

        result = dlg.exec_()
        # Always restore original if not accepted
        if result == QDialog.Accepted:
            new_point = dlg.get_values()
            try:
                update_point_in_file(point_idx, new_point)
            except Exception as e:
                QMessageBox.warning(self, "Save Failed", f"Could not save point: {e}")
                self.update_plot()
                self.set_selection_indices(prev_selection)
                return
            positions[point_idx].update(new_point)
            self.area_tree.clear()
            tree_struct = build_tree_structure(positions)
            fill_tree_widget(self.area_tree.invisibleRootItem(), tree_struct)
            self.set_tree_state(tree_state)
            self.update_plot()
            self.set_selection_indices(prev_selection)
            QMessageBox.information(self, "Point Updated", "Point updated and saved to file.")
        else:
            stop_preview()
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
        if selected_point_indices:
            plot_points.panel = self
            plot_points(selected_point_indices)
        else:
            plotter.clear()
            plotter.render()

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
        # If it's a point, propagate check state up to parents
        if item.data(0, Qt.UserRole) is not None:
            self.area_tree.blockSignals(True)
            parent = item.parent()
            while parent:
                all_checked = all(parent.child(i).checkState(0) == Qt.Checked for i in range(parent.childCount()))
                any_checked = any(parent.child(i).checkState(0) == Qt.Checked for i in range(parent.childCount()))
                if all_checked:
                    parent.setCheckState(0, Qt.Checked)
                elif any_checked:
                    parent.setCheckState(0, Qt.PartiallyChecked)
                else:
                    parent.setCheckState(0, Qt.Unchecked)
                parent = parent.parent()
            self.area_tree.blockSignals(False)
            self.update_plot()
            return

        # If it's a folder, propagate check state to all children
        state = item.checkState(0)
        self.area_tree.blockSignals(True)
        def set_children(item, state):
            for i in range(item.childCount()):
                child = item.child(i)
                child.setCheckState(0, state)
                set_children(child, state)
        set_children(item, state)
        self.area_tree.blockSignals(False)
        self.update_plot()

        # Folder rename logic
        old_name = getattr(item, "_old_name", item.text(0))
        new_name = item.text(0)
        if old_name != new_name and new_name.strip():
            path = []
            parent = item.parent()
            while parent:
                path.insert(0, parent.text(0))
                parent = parent.parent()
            old_path = path + [old_name]
            new_path = path + [new_name]
            for p in positions:
                parts = [part for part in p.get("path", "").split("/") if part]
                if parts[:len(old_path)] == old_path:
                    parts = new_path + parts[len(old_path):]
                    p["path"] = "/".join(parts)
            item._old_name = new_name
            folder_paths = self.get_all_folder_paths()
            save_positions_to_file(self.current_map_file, folder_paths=folder_paths)
            self.reload_positions()

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
            transformed_positions = get_transformed_positions()
            pt = transformed_positions[point_idx:point_idx + 1]
            self.highlight_actor = plotter.add_points(
                pt, color='magenta', point_size=25, render_points_as_spheres=True
            )
            plotter.render()

    def on_tree_item_double_clicked(self, item, column):
        point_idx = item.data(0, Qt.UserRole)
        if point_idx is not None:
            self.open_point_details_popup(point_idx)

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
        root_order = sum(1 for p in positions if p.get("path", "") == "")
        for i, line in enumerate(text.splitlines()):
            line = line.strip()
            # Support both NPCs and props
            if line.startswith("bot spawn"):
                m = re.match(r"bot spawn \d+ (\S+) ([\-\d\.]+) ([\-\d\.]+) ([\-\d\.]+)(?: ([\-\d\.]+))?", line)
                if m:
                    bot_type = m.group(1)
                    roblox_x = float(m.group(2))
                    roblox_y = float(m.group(3))
                    roblox_z = float(m.group(4))
                    orientation = float(m.group(5)) if m.lastindex >= 5 and m.group(5) else 0
                    new_points.append({
                        "command": "bot spawn",
                        "type": bot_type,
                        "roblox_x": roblox_x,
                        "roblox_y": roblox_y,
                        "roblox_z": roblox_z,
                        "orientation": orientation,
                        "path": "",
                        "order": root_order + len(new_points)
                    })
            elif line.startswith("spawn"):
                m = re.match(r"spawn \d+ (\S+) ([\-\d\.]+) ([\-\d\.]+) ([\-\d\.]+) ([\-\d\.]+) ([\-\d\.]+) ([\-\d\.]+)", line)
                if m:
                    prop_type = m.group(1)
                    roblox_x = float(m.group(2))
                    roblox_y = float(m.group(3))
                    roblox_z = float(m.group(4))
                    rot_x = float(m.group(5))
                    rot_y = float(m.group(6))
                    rot_z = float(m.group(7))
                    new_points.append({
                        "command": "spawn",
                        "type": prop_type,
                        "roblox_x": roblox_x,
                        "roblox_y": roblox_y,
                        "roblox_z": roblox_z,
                        "rot_x": rot_x,
                        "rot_y": rot_y,
                        "rot_z": rot_z,
                        "path": "",
                        "order": root_order + len(new_points)
                    })
        if not new_points:
            QMessageBox.warning(self, "No Points Found", "Clipboard does not contain valid NPC or prop lines.")
            return
        with open(self.current_map_file, "a", encoding="utf-8") as f:
            for p in new_points:
                if p.get("command") == "bot spawn":
                    line = f"bot spawn 1 {p['type']} {p['roblox_x']} {p['roblox_y']} {p['roblox_z']} {p['orientation']}\n"
                elif p.get("command") == "spawn":
                    line = f"spawn 1 {p['type']} {p['roblox_x']} {p['roblox_y']} {p['roblox_z']} {p['rot_x']} {p['rot_y']} {p['rot_z']}\n"
                else:
                    continue
                f.write(line)
        positions.extend(new_points)
        folder_paths = self.get_all_folder_paths()
        save_positions_to_file(self.current_map_file, folder_paths=folder_paths)
        self.reload_positions()
        QMessageBox.information(self, "Points Added", f"Added {len(new_points)} points from clipboard.")

    def reload_positions(self):
        tree_state = self.get_tree_state()
        self.area_tree.clear()
        tree_struct = build_tree_structure(positions)
        fill_tree_widget(self.area_tree.invisibleRootItem(), tree_struct)
        self.set_tree_state(tree_state)
        self.rebuild_type_checkboxes()
        self.update_plot()
        folder_paths = self.get_all_folder_paths()
        save_positions_to_file(self.current_map_file, folder_paths=folder_paths)

    def select_and_load_file(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Open Game File", "", "Text Files (*.txt);;All Files (*)")
        if fname:
            self.load_map_file(fname)

    def open_other_file(self):
        global positions
        positions.clear()
        self.area_tree.clear()
        self.update_plot()
        self.select_and_load_file()
            
    def load_map_file(self, fname):
        global positions, DATA_FILENAME
        DATA_FILENAME = fname
        self.current_map_file = fname
        positions.clear()
        positions.extend(parse_bot_file(fname))
        self.reload_positions()
        self.rebuild_type_checkboxes()
        self.update_plot()
        QMessageBox.information(self, "Loaded", f"Loaded {len(positions)} points from {os.path.basename(fname)}.")

    def save_workspace_as_file(self):
        fname, _ = QFileDialog.getSaveFileName(self, "Save Workspace", "", "Workspace Files (*.json);;All Files (*)")
        if not fname:
            return
        cam = self.plotter.camera
        abs_map = os.path.abspath(self.current_map_file)
        selection = self.get_current_selection_indices()
        workspace = {
            "map_file": abs_map,
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
        self.workspace_loaded_path = fname
        with open(fname, "r", encoding="utf-8") as f:
            workspace = json.load(f)
        map_file = workspace["map_file"]
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

    def save_workspace_to_loaded_path(self):
        if not self.workspace_loaded_path:
            QMessageBox.warning(self, "No Workspace", "No workspace file loaded.")
            return
        cam = self.plotter.camera
        abs_map = os.path.abspath(self.current_map_file)
        selection = self.get_current_selection_indices()
        workspace = {
            "map_file": abs_map,
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
        with open(self.workspace_loaded_path, "w", encoding="utf-8") as f:
            json.dump(workspace, f, indent=2)
        QMessageBox.information(self, "Saved", f"Workspace saved to {self.workspace_loaded_path}")

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

        area_group = QGroupBox("Paths")
        area_vbox = QVBoxLayout()
        self.area_tree = DeletableTreeWidget(self)
        self.area_tree.setHeaderHidden(True)
        self.area_tree.setDragDropMode(QTreeWidget.InternalMove)
        self.area_tree.setDefaultDropAction(Qt.MoveAction)
        self.area_tree.dropEvent = self.on_tree_drop_event
        self.area_tree.itemChanged.connect(self.on_tree_item_changed)
        self.area_tree.itemSelectionChanged.connect(self.on_tree_item_selected)
        self.area_tree.itemDoubleClicked.connect(self.on_tree_item_double_clicked)
        self.area_tree.setSelectionMode(QTreeWidget.ExtendedSelection)
        tree_struct = build_tree_structure(positions)
        fill_tree_widget(self.area_tree.invisibleRootItem(), tree_struct)
        area_vbox.addWidget(self.area_tree)
        tree_btn_layout = QVBoxLayout()
        tree_select_all = QPushButton("Select All")
        tree_select_all.clicked.connect(lambda: self.select_all_tree(True))
        tree_deselect_all = QPushButton("Deselect All")
        tree_deselect_all.clicked.connect(lambda: self.select_all_tree(False))
        copy_selection_btn = QPushButton("Copy Selection To Clipboard")
        copy_selection_btn.clicked.connect(self.copy_selection_to_clipboard)
        load_selection_btn = QPushButton("Load Selection From Clipboard")
        load_selection_btn.clicked.connect(self.load_selection_from_clipboard)
        add_npcs_btn = QPushButton("Add NPCs From Clipboard")
        add_npcs_btn.clicked.connect(self.add_npcs_from_clipboard)
        open_file_btn = QPushButton("Open Game File")
        open_file_btn.clicked.connect(self.open_other_file)
        copy_visible_btn = QPushButton("Copy Visible Points To Clipboard")
        copy_visible_btn.clicked.connect(self.copy_visible_points_to_clipboard)

        ws_btn_group = QGroupBox("Workspace")
        ws_btn_layout = QVBoxLayout()
        self.simple_save_ws_btn = QPushButton("Save Workspace")
        self.simple_save_ws_btn.clicked.connect(self.save_workspace_to_loaded_path)
        save_ws_btn = QPushButton("Save Workspace As...")
        save_ws_btn.clicked.connect(self.save_workspace_as_file)
        load_ws_btn = QPushButton("Load Workspace...")
        load_ws_btn.clicked.connect(self.load_workspace_file)
        ws_btn_layout.addWidget(self.simple_save_ws_btn)
        ws_btn_layout.addWidget(save_ws_btn)
        ws_btn_layout.addWidget(load_ws_btn)
        ws_btn_group.setLayout(ws_btn_layout)

        tree_btn_layout.addWidget(tree_select_all)
        tree_btn_layout.addWidget(tree_deselect_all)
        tree_btn_layout.addWidget(copy_selection_btn)
        tree_btn_layout.addWidget(load_selection_btn)
        tree_btn_layout.addWidget(add_npcs_btn)
        tree_btn_layout.addWidget(open_file_btn)
        tree_btn_layout.addWidget(copy_visible_btn)
        tree_btn_layout.addWidget(ws_btn_group)
        area_vbox.addLayout(tree_btn_layout)
        area_group.setLayout(area_vbox)

        group = QGroupBox("NPC Types")
        self.type_vbox = QVBoxLayout()
        self.type_checkboxes = {}
        for t in get_unique_types():
            cb = QCheckBox(t)
            cb.setChecked(True)
            cb.stateChanged.connect(self.update_plot)
            self.type_checkboxes[t] = cb
            self.type_vbox.addWidget(cb)
        type_btn_layout = QVBoxLayout()
        type_select_all = QPushButton("Select All")
        type_select_all.clicked.connect(lambda: self.select_all_types(True))
        type_deselect_all = QPushButton("Deselect All")
        type_deselect_all.clicked.connect(lambda: self.select_all_types(False))
        type_btn_layout.addWidget(type_select_all)
        type_btn_layout.addWidget(type_deselect_all)
        self.type_vbox.addLayout(type_btn_layout)
        group.setLayout(self.type_vbox)


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

    def on_tree_drop_event(self, event):
        tree_state = self.get_tree_state()
        selected_items = self.area_tree.selectedItems()
        selected_indices = [item.data(0, Qt.UserRole) for item in selected_items if item.data(0, Qt.UserRole) is not None]

        QTreeWidget.dropEvent(self.area_tree, event)
        self.update_orders_from_tree()
        folder_paths = self.get_all_folder_paths()
        save_positions_to_file(self.current_map_file, folder_paths=folder_paths)
        self.reload_positions()

        def select_by_indices(item):
            point_idx = item.data(0, Qt.UserRole)
            if point_idx is not None and point_idx in selected_indices:
                item.setSelected(True)
            for i in range(item.childCount()):
                select_by_indices(item.child(i))
        root = self.area_tree.invisibleRootItem()
        for i in range(root.childCount()):
            select_by_indices(root.child(i))
        self.set_tree_state(tree_state)

    def update_orders_from_tree(self):
        def update_orders(item, path):
            order = 0
            for i in range(item.childCount()):
                child = item.child(i)
                point_idx = child.data(0, Qt.UserRole)
                if point_idx is not None:
                    positions[point_idx]["order"] = order
                    positions[point_idx]["path"] = "/".join(path)
                    order += 1
                else:
                    update_orders(child, path + [child.text(0)])
        root = self.area_tree.invisibleRootItem()
        for i in range(root.childCount()):
            update_orders(root.child(i), [root.child(i).text(0)])

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

    def copy_visible_points_to_clipboard(self):
        visible_indices = set()
        def collect_checked(item):
            point_idx = item.data(0, Qt.UserRole)
            if point_idx is not None:
                if item.checkState(0) == Qt.Checked:
                    visible_indices.add(point_idx)
            else:
                for i in range(item.childCount()):
                    collect_checked(item.child(i))
        root = self.area_tree.invisibleRootItem()
        for i in range(root.childCount()):
            collect_checked(root.child(i))
        lines = []
        for idx in sorted(visible_indices):
            p = positions[idx]
            lines.append(f"bot spawn 1 {p['type']} {p['roblox_x']} {p['roblox_y']} {p['roblox_z']} {p['orientation']}")
        clipboard = QApplication.clipboard()
        clipboard.setText("\n".join(lines))
        QMessageBox.information(self, "Copied", f"Copied {len(lines)} visible points to clipboard.")

    def delete_selected_points(self):
        selected_items = self.area_tree.selectedItems()
        if not selected_items:
            return
        # Only delete points, not folders
        indices_to_delete = []
        for item in selected_items:
            idx = item.data(0, Qt.UserRole)
            if idx is not None:
                indices_to_delete.append(idx)
        if not indices_to_delete:
            return
        indices_to_delete = sorted(set(indices_to_delete), reverse=True)
        reply = QMessageBox.question(
            self, "Delete Points",
            f"Delete {len(indices_to_delete)} selected point(s)?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            for idx in indices_to_delete:
                del positions[idx]
            folder_paths = self.get_all_folder_paths()
            save_positions_to_file(self.current_map_file, folder_paths=folder_paths)
            self.reload_positions()

class DeletableTreeWidget(QTreeWidget):
    def __init__(self, parent_panel):
        super().__init__()
        self.parent_panel = parent_panel

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            self.parent_panel.delete_selected_points()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            # Open point editor if a point is selected
            selected_items = self.selectedItems()
            if selected_items:
                item = selected_items[0]
                idx = item.data(0, Qt.UserRole)
                if idx is not None:
                    self.parent_panel.open_point_details_popup(idx)
        else:
            super().keyPressEvent(event)

if __name__ == "__main__":
    picker = None
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    panel = ControlPanel(plotter)
    picker = PointPicker(plotter, positions, panel)

    workspace_path = os.path.join(os.path.dirname(__file__), "workspace.json")
    if os.path.exists(workspace_path):
        panel.load_workspace_file = panel.load_workspace_file.__get__(panel)
        with open(workspace_path, "r", encoding="utf-8") as f:
            workspace = json.load(f)
        map_file = workspace["map_file"]
        panel.load_map_file(map_file)
        cam = workspace.get("camera", {})
        if cam:
            panel.plotter.camera_position = [cam["position"], cam["focal"], cam["up"]]
            panel.plotter.render()
        selection = workspace.get("selection", [])
        panel.set_selection_indices(selection)
        marker = workspace.get("orientation_marker", {})
        orientation_marker_visible = marker.get("visible", True)
        orientation_marker_offset = marker.get("offset", [0, 0, 0])
        panel.marker_show_btn.setChecked(orientation_marker_visible)
        panel.marker_show_btn.setText("Show Marker" if not orientation_marker_visible else "Hide Marker")
        panel.marker_move_x.setText(str(orientation_marker_offset[0]))
        panel.marker_move_y.setText(str(orientation_marker_offset[1]))
        panel.marker_move_z.setText(str(orientation_marker_offset[2]))
        panel.update_plot()

    panel.show()
    app.exec()