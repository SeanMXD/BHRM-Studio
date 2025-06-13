# BHRM Studio

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
- `bhrm_studio.py`: Main application logic, GUI, and 3D plotting.
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
pyinstaller bhrm_studio.spec

## Project File Overview

### Main Application Files

- **bhrm_studio.py**  
  The main Python application. Provides a Qt-based GUI and a 3D PyVista visualization for editing and managing NPC spawn points for Black Hawk Rescue Mission. Handles file I/O, workspace management, clipboard operations, and all user interactions.

- **bhrm_studio.spec**  
  PyInstaller specification file for building a standalone executable of the editor. Lists hidden imports and resources needed for packaging.

- **bot_spawn_commands.txt**  
  The default text file containing all NPC spawn points and commands. This is the main data file loaded and saved by the editor.

- **README.md**  
  Project documentation, including features, usage, data model, and developer notes.

- **RBRM5_-_Logo_of_PLATINUM_FIVE.ico**  
  Application icon used for the executable.

### Automation Scripts

- **bhrm_copy_command.ahk**  
  AutoHotkey script.  
  - **Purpose:** When you press `Ctrl+Shift+C`, it copies the line under your mouse cursor in Roblox and pastes it into Notepad (if Notepad is the next window in Alt+Tab order).  
  - **Usage:** Useful for quickly transferring spawn commands from Roblox to your text file.

- **bhrm_paste_command.ahk**  
  AutoHotkey script.  
  - **Purpose:** When you press `Ctrl+Shift+V`, it pastes and presses Enter for each line in your clipboard, one line at a time (useful for pasting multiple commands into Roblox or another app).  
  - **Escape:** Hold the Enter key to abort/escape the paste loop.

### Build Output

- **/build, /dist**  
  Output folders created by PyInstaller when building the executable.  
  - `dist/bhrm_studio.exe`: The compiled standalone application.

### Other Files

- **compile_py.cmd**  
  Batch script for building the Python application or running PyInstaller.

- **.gitignore**  
  Git ignore file for excluding build artifacts and other non-source files.

- **workspace.json**  
  (If present) Stores the last used workspace, including camera, selection, and marker state.

---

### **AHK Script Hotkeys Summary**

- **Ctrl+Shift+C**: Copy a line from Roblox under your mouse to Notepad (if Notepad is next in Alt+Tab).
- **Ctrl+Shift+V**: Paste and press Enter for each line in your clipboard, one at a time.
- **Escape for paste**: Hold the Enter key to abort the paste loop.

---

> For more details on each file's purpose, see the in-code comments or the README sections above.

## Suggestions & Future Improvements

Here are some ideas to further enhance BHRM Studio:

### Undo/Redo Support
- Implement undo/redo for point edits, deletions, and moves to help recover from mistakes.

### Error Handling & Validation
- Add user-friendly error messages and input validation (e.g., prevent non-numeric input in coordinate fields).
- Highlight or focus fields with invalid input.

### Performance for Large Maps
- For large numbers of points, consider:
  - Only updating/redrawing visible/changed points.
  - Using a background thread for file I/O or heavy parsing.

### Export/Import Enhancements
- Support exporting to other formats (CSV, JSON, etc.).
- Allow importing from other formats or merging files.

### UI/UX Improvements
- Add tooltips to buttons and fields for clarity.
- Add a status bar for quick feedback (e.g., “Saved”, “Loaded”, “Copied”).
- Allow multi-select and batch editing of points.

### Settings Persistence
- Remember window size/position, last opened files, and UI preferences between sessions.

### Documentation
- Add screenshots or GIFs to this README.
- Document keyboard shortcuts and power-user features.

### Testing
- Add unit tests for parsing, saving, and coordinate conversion functions.

### Accessibility
- Ensure keyboard navigation works for all controls.
- Add high-contrast or colorblind-friendly color schemes.

### Wireframe/Solid Mode UI Elements & Workspace Persistence

A planned feature is to allow users to toggle between wireframe and solid rendering modes directly from the application's UI, and to have this preference saved as part of the workspace file. This would ensure that when a workspace is loaded, the chosen rendering mode (wireframe or solid) is automatically restored, providing a consistent visual experience across sessions. While PyVista supports toggling these modes via keyboard shortcuts (`W` for wireframe, `S` for solid), integrating this functionality into the GUI and workspace persistence would make the workflow more intuitive and user-friendly. Implementation challenges include keeping the UI state synchronized with PyVista's internal representation, especially when the mode is changed outside the UI (e.g., via keyboard shortcuts).  One day there might also be the ability to toggle or persist wireframe/solid for individual objects.

### Developer Note: Wireframe/Solid Mode Persistence

When updating or re-plotting points, the code spot-checks the representation mode (wireframe or solid) of the first actor and applies it to all new actors. This ensures that if the user toggles wireframe/solid mode in the PyVista window (e.g., by pressing `W` or `S`), the chosen mode persists across re-renders.

**Technical note:**  
PyVista/VTK does not provide a global "representation mode" for the entire window; the mode is stored per actor. The code checks the first actor as a proxy for the current mode. If you want full UI synchronization (e.g., a toggle button that always matches the PyVista state), consider polling the first actor's representation and updating the UI accordingly.

---

*If you have suggestions or want to contribute, feel free to open an issue or pull request!*