# FREEkMapper

A powerful projection mapping application built with Python, Tkinter, and OpenGL. Designed for live performance and installation art, FREEkMapper allows you to map video and images onto physical surfaces with advanced sequencing and live control capabilities.

## Features

- **Quad Surface Mapping**: Create and map multiple quad surfaces to physical objects.
- **Media Support**: Load videos and images onto individual surfaces.
- **Advanced Playback Modes**:
    - **Concurrent**: All surfaces play their media simultaneously (looping).
    - **Sequential**: Define a playlist of steps where surfaces play one after another.
- **Continuous Surfaces**: Designate specific surfaces to keep playing (e.g., background loops) regardless of the current sequence step.
- **Live Control Panel**: A separate window for triggering saved configurations and managing shows live.
- **Fullscreen Output**: High-performance OpenGL output window for the projector.
- **Configuration Persistence**: Save and load your entire mapping setup and sequence.

## Installation

```bash
pip install freekmapper
```

## Usage

To start the application:

```bash
freekmapper
```

## Workflow Guide

### 1. Mapping Surfaces
1.  **Add Surface**: Click "Add Quad Surface" to create a new mapping area.
2.  **Adjust Geometry**:
    - In the **Embedded Preview** (Right Panel), drag the corners of the surface to match your physical object.
    - Use **Shortcuts**: `r` / `R` to rotate the surface points if the orientation is wrong.
3.  **Load Media**: Select a surface in the list and click "Load Video" or "Load Image".

### 2. Sequencing & Playback
The application supports two playback modes:

-   **Concurrent (All Play)**: Default mode. All surfaces play their assigned media in a loop.
-   **Sequential (One by One)**: Plays a defined playlist of cues.

#### Setting up a Sequence
1.  Click **⚙ Setup Sequence** to open the Sequence Editor.
2.  **Add Steps**: Select a surface and media file, then click "Add to Playlist".
3.  **Order**: Use "Move Up" / "Move Down" to arrange the playback order.
4.  **Continuous Surfaces**: Check the boxes on the right for surfaces that should *always* be visible (e.g., a background layer), even when other steps are playing.
5.  **Apply**: Saves the sequence.

### 3. Live Performance
For live shows, use the **Live Control Panel**:

1.  Click **🎛 Live Control Panel**.
2.  **Slots**: You have 5 slots to assign different saved configurations (`.npy` files).
    -   Click **Assign** to choose a config file.
    -   Click **GO** to instantly load that configuration.
3.  **Looping**:
    -   Check the boxes next to the slots you want to include in a loop.
    -   Set the **Loop Duration** (in seconds).
    -   Click **Start Loop** to cycle through the selected configs automatically.
4.  **Blackout**: Click **Disable Show** to instantly blackout the projector output. Click again to resume.

### 4. Fullscreen Output
When you are ready to project:

1.  Select the target **Display** from the dropdown.
2.  Click **▶ Fullscreen Output**.
3.  **Fullscreen Shortcuts**:
    -   `ESC`: Exit fullscreen.
    -   `E`: Toggle **Edit Mode** (shows/hides corner handles).
    -   `H`: Hide/show control overlays.
    -   `R`: Rotate the selected surface.
    -   **Drag Corners**: You can fine-tune the mapping directly in the fullscreen window.

## Requirements

-   Python 3.8+
-   OpenGL 3.3+ compatible graphics card
-   Dependencies: `moderngl`, `glfw`, `dearpygui`, `opencv-python`, `numpy`, `Pillow`
