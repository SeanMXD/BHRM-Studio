# Black Hawk Rescue Mission NPC Point Visualizer & Editor

## Purpose
Visualizes and edits NPC spawn points for a Roblox game, using a 3D PyVista window and a Qt-based GUI.

## Main Features
- **Loads** NPC spawn points from a text file (`bot_spawn_commands.txt` by default).
- **3D Visualization:** All points are shown in a PyVista window, color-coded by type.
- **Tree View:** Points are organized in a tree by folder/path, with checkboxes for visibility.
- **Editing:** Double-click a point (in tree or 3D) to edit its properties in a popup dialog.
- **Clipboard:** Copy/paste points and camera positions/focals.
- **Workspace:** Save/load workspace files (`.json`) that store camera, selection, marker, and file info.
- **Orientation Marker:** Shows UP/NORTH in the 3D view, can be moved/hidden.
- **Supports unknown/plaintext commands:** These are editable as raw text.

## Key Files
- `bhrm_npc_editor.py`: Main application logic, GUI, and 3D plotting.
- `bot_spawn_commands.txt`: Default data file for NPC spawn points.

## Data Model
- `positions`: List of dicts, each representing a point or command.
    - `"command"`: `"bot spawn"`, `"spawn"`, or `"raw"`
    - `"type"`: NPC type (if not raw)
    - `"roblox_x"`, `"roblox_y"`, `"roblox_z"`: Coordinates (if not raw)
    - `"orientation"` or `"rot_x"`, `"rot_y"`, `"rot_z"`: Orientation (if not raw)
    - `"path"`: Folder path as string
    - `"order"`: Order within folder

## GUI Structure
- **Tree Widget:** Shows folders and points, supports drag/drop, selection, and editing.
- **Type Checkboxes:** Show/hide types in the 3D view.
- **Camera Controls:** View/edit/copy/paste camera position, focal point, up vector.
- **Orientation Marker Controls:** Show/hide and move the marker.
- **Workspace Controls:** Save/load workspace files.

## Editing Points
- **Popup dialog:** Edits all properties for a point, or raw text for unknown commands.
- **Live preview:** Changes are shown in the 3D view before saving.

## Plotting
- `plot_points`: Draws all checked points in 3D, color-coded by type.
- **Orientation marker:** Drawn as arrows labeled UP/N.

## File I/O
- `parse_bot_file`: Reads the text file and populates `positions`.
- `save_positions_to_file`: Writes all points back to the text file, preserving folder structure.

## Clipboard
- **Copy/paste:** Points, camera, and selection can be copied to/pasted from the clipboard.

## Workspace
- **Save/load:** Stores current file, camera, selection, and marker state in a `.json` file.

## Extensibility
- **Unknown commands:** Any line not matching known patterns is stored as `"raw"` and editable as plain text.

## Requirements

- Python 3.8+
- numpy
- matplotlib
- pyvista
- pyvistaqt
- qtpy

Install dependencies with:
pip install numpy matplotlib pyvista pyvistaqt qtpy

## Usage

Run the editor with:

## Building an Executable

You can use PyInstaller to build a standalone executable:
pyinstaller bhrm_npc_editor.spec

---

> If you need to remember how to add new point types, change the file format, or extend the GUI, look for the relevant parsing, plotting, and dialog code.