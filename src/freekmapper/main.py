import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import cv2
import numpy as np
import threading
import time
import os
import glfw

from .video_source import VideoSource
from .renderers import GLTkRenderer, GLFullscreenRenderer
from .control_panel import LiveControlPanel
from .sequence_setup import SequenceEditorDialog

class ProjectionMapper:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Projection Mapper (PyOpenGL)")
        self.root.geometry("1400x800")

        # State
        self.video_sources: dict[str, VideoSource] = {}
        self.surfaces = []
        self.selected_surface = None
        self.selected_point = None

        # Background video thread
        self.video_thread = None
        self.stop_thread = False
        self.target_fps = 30

        # Display info
        self.displays = self.detect_displays()
        
        # Virtual Canvas Resolution
        self.canvas_width = 1920
        self.canvas_height = 1080

        # UI elements
        self.opengl_view = None
        self.fps_label = None
        self.media_label = None
        self.surface_listbox = None
        self.quality_var = tk.StringVar(value="low")
        self.display_var = tk.StringVar()
        
        # Fullscreen State
        self.fullscreen_window = None
        self.fullscreen_renderer = None
        
        # Sequencing State
        self.playback_mode = tk.StringVar(value="concurrent") # 'concurrent' or 'sequential'
        self.sequence_steps = [] # List of {"surface_index": int, "media_path": str, "media_type": str}
        self.continuous_surfaces = set() # Set of surface indices
        self.current_sequence_index = 0
        self.sequence_active = False
        
        # Image Duration State
        self.current_clip_start_time = 0
        self.image_duration = 5.0 # Seconds

        self.setup_ui()
        
        # Apply Modern Theme
        try:
            import sv_ttk
            sv_ttk.set_theme("dark")
        except ImportError:
            pass
            
        self.start_video_thread()

    # --------- UI SETUP --------- #
    def setup_ui(self):
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # LEFT PANEL
        left_container = ttk.Frame(main_frame, width=280)
        left_container.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_container.pack_propagate(False)

        left_canvas = tk.Canvas(left_container, width=260, highlightthickness=0)
        scrollbar = ttk.Scrollbar(left_container, orient="vertical", command=left_canvas.yview)

        left_panel = ttk.Frame(left_canvas)
        left_canvas.create_window((0, 0), window=left_panel, anchor="nw")
        left_canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        def on_configure(event):
            left_canvas.configure(scrollregion=left_canvas.bbox("all"))

        left_panel.bind("<Configure>", on_configure)

        def on_mousewheel(event):
            left_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        def on_linux_scroll_up(event):
            left_canvas.yview_scroll(-1, "units")

        def on_linux_scroll_down(event):
            left_canvas.yview_scroll(1, "units")

        left_canvas.bind_all("<MouseWheel>", on_mousewheel)
        left_canvas.bind_all("<Button-4>", on_linux_scroll_up)
        left_canvas.bind_all("<Button-5>", on_linux_scroll_down)

        # Title
        ttk.Label(left_panel, text="Projection Mapper", font=("Arial", 14, "bold")).pack(pady=10)

        # Surface frame
        surface_frame = ttk.LabelFrame(left_panel, text="Surfaces", padding=10)
        surface_frame.pack(fill=tk.X, pady=5)

        ttk.Button(surface_frame, text="Add Quad Surface", command=self.add_quad_surface).pack(
            fill=tk.X, pady=2
        )
        ttk.Button(surface_frame, text="Delete Surface", command=self.delete_surface).pack(
            fill=tk.X, pady=2
        )

        list_frame = ttk.Frame(surface_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        list_scrollbar = ttk.Scrollbar(list_frame)
        list_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.surface_listbox = tk.Listbox(list_frame, yscrollcommand=list_scrollbar.set, height=6)
        self.surface_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        list_scrollbar.config(command=self.surface_listbox.yview)
        self.surface_listbox.bind("<<ListboxSelect>>", self.on_surface_select)

        # Media frame
        media_frame = ttk.LabelFrame(left_panel, text="Surface Media", padding=10)
        media_frame.pack(fill=tk.X, pady=5)

        ttk.Label(media_frame, text="Selected Surface Media:").pack()
        ttk.Button(media_frame, text="Load Video", command=self.load_video_to_surface).pack(
            fill=tk.X, pady=2
        )
        ttk.Button(media_frame, text="Load Image", command=self.load_image_to_surface).pack(
            fill=tk.X, pady=2
        )

        self.media_label = ttk.Label(media_frame, text="No media", foreground="gray")
        self.media_label.pack(pady=5)

        # Transform frame
        transform_frame = ttk.LabelFrame(left_panel, text="Transform", padding=10)
        transform_frame.pack(fill=tk.X, pady=5)

        ttk.Label(transform_frame, text="Opacity:").pack()
        self.opacity_scale = ttk.Scale(
            transform_frame,
            from_=0,
            to=100,
            orient=tk.HORIZONTAL,
            command=self.update_opacity,
        )
        self.opacity_scale.set(100)
        self.opacity_scale.pack(fill=tk.X, pady=2)

        ttk.Label(transform_frame, text="Rotation:").pack(pady=(10, 0))
        rotation_buttons = ttk.Frame(transform_frame)
        rotation_buttons.pack(fill=tk.X, pady=2)

        ttk.Button(rotation_buttons, text="↻ CW", command=self.rotate_surface_cw).pack(
            side=tk.LEFT, expand=True, padx=1
        )
        ttk.Button(rotation_buttons, text="↺ CCW", command=self.rotate_surface_ccw).pack(
            side=tk.LEFT, expand=True, padx=1
        )
        
        # Sequencing Frame
        seq_frame = ttk.LabelFrame(left_panel, text="Playback Sequencing", padding=10)
        seq_frame.pack(fill=tk.X, pady=5)
        
        ttk.Radiobutton(seq_frame, text="Concurrent (All Play)", variable=self.playback_mode, value="concurrent", command=self.reset_playback).pack(anchor=tk.W)
        ttk.Radiobutton(seq_frame, text="Sequential (One by One)", variable=self.playback_mode, value="sequential", command=self.reset_playback).pack(anchor=tk.W)
        
        ttk.Button(seq_frame, text="⚙ Setup Sequence", command=self.open_sequence_setup).pack(fill=tk.X, pady=2)
        ttk.Button(seq_frame, text="Reset / Restart Sequence", command=self.restart_sequence).pack(fill=tk.X, pady=2)

        # Performance frame
        perf_frame = ttk.LabelFrame(left_panel, text="Performance", padding=10)
        perf_frame.pack(fill=tk.X, pady=5)

        ttk.Label(perf_frame, text="Quality:").pack(anchor=tk.W)
        self.quality_var.set("low")
        ttk.Radiobutton(
            perf_frame, text="Low (Fast)", variable=self.quality_var, value="low"
        ).pack(anchor=tk.W)
        ttk.Radiobutton(
            perf_frame, text="Medium", variable=self.quality_var, value="medium"
        ).pack(anchor=tk.W)

        self.fps_label = ttk.Label(perf_frame, text="FPS: --")
        self.fps_label.pack(pady=2)

        # Output frame
        output_frame = ttk.LabelFrame(left_panel, text="Output", padding=10)
        output_frame.pack(fill=tk.X, pady=5)

        ttk.Label(output_frame, text="Display:").pack(anchor=tk.W)

        display_options = [
            f"Display {i + 1} ({w}x{h})" for i, (_, _, w, h) in enumerate(self.displays)
        ]
        self.display_var.set(display_options[0] if display_options else "Display 1")

        display_dropdown = ttk.Combobox(
            output_frame,
            textvariable=self.display_var,
            values=display_options,
            state="readonly",
            width=23,
        )
        display_dropdown.pack(fill=tk.X, pady=2)

        ttk.Button(output_frame, text="▶ Fullscreen Output", command=self.fullscreen_output).pack(
            fill=tk.X, pady=5
        )
        ttk.Button(output_frame, text="Save Config", command=self.save_config).pack(
            fill=tk.X, pady=2
        )
        ttk.Button(output_frame, text="Load Config", command=self.load_config).pack(
            fill=tk.X, pady=2
        )
        ttk.Button(output_frame, text="🎛 Live Control Panel", command=self.launch_control_panel).pack(
            fill=tk.X, pady=5
        )

        self.status_label = ttk.Label(
            output_frame, text="Ready", foreground="green", font=("Arial", 8)
        )
        self.status_label.pack(pady=2)

        # Info / shortcuts
        info_frame = ttk.LabelFrame(left_panel, text="Shortcuts", padding=10)
        info_frame.pack(fill=tk.BOTH, expand=True, pady=5)

        instructions = (
            "Embedded Preview:\n"
            "• Drag corners to adjust\n"
            "• r/R: Rotate CW/CCW\n\n"
            "Fullscreen (GLFW):\n"
            "• ESC: Exit fullscreen\n"
            "• E: Toggle edit mode\n"
            "• H: Hide/show controls\n"
            "• R: Rotate selected surface\n"
            "• Drag corners: adjust mapping\n"
        )
        ttk.Label(info_frame, text=instructions, justify=tk.LEFT, font=("Arial", 8)).pack(
            anchor=tk.W
        )

        # RIGHT PANEL (OpenGL preview)
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        def fps_callback(fps):
            self.fps_label.config(text=f"FPS: {fps:.1f}")

        self.opengl_view = GLTkRenderer(
            master=right_panel,
            surfaces=self.surfaces,
            get_frame_callback=self.get_surface_frame,
            fps_callback=fps_callback,
            width=800,
            height=600,
            canvas_width=self.canvas_width,
            canvas_height=self.canvas_height,
        )
        self.opengl_view.pack(fill=tk.BOTH, expand=True)

        # Keep GL widget size in sync
        self.opengl_view.bind("<Configure>", self.opengl_view.set_size)

        # Start a simple animation loop for OpenGL preview
        def gl_step():
            # 0. Update Playback Logic
            self.update_playback_logic()
            
            # 1. Update Preview
            self.opengl_view.redraw()
            
            # 2. Update Fullscreen (if active)
            if self.fullscreen_window:
                if glfw.window_should_close(self.fullscreen_window):
                    self.close_fullscreen()
                else:
                    glfw.make_context_current(self.fullscreen_window)
                    w_fb, h_fb = glfw.get_framebuffer_size(self.fullscreen_window)
                    self.fullscreen_renderer.draw(w_fb, h_fb)
                    glfw.swap_buffers(self.fullscreen_window)
                    glfw.poll_events()
                    
                    # Restore Tkinter context implicitly handled by redraw's tkMakeCurrent next frame,
                    # but good to be safe if we do other things.
                    # self.opengl_view.tkMakeCurrent() # redraw does this now.

            self.opengl_view.after(16, gl_step)  # ~60 FPS

        # Delay start of GL loop to ensure window is mapped and context is ready
        self.root.after(100, gl_step)

        # Mouse events on OpenGL widget
        self.opengl_view.bind("<Button-1>", self.on_gl_click)
        self.opengl_view.bind("<B1-Motion>", self.on_gl_drag)
        self.opengl_view.bind("<ButtonRelease-1>", self.on_gl_release)

        # Keyboard shortcuts
        self.root.bind("<r>", lambda e: self.rotate_surface_cw())
        self.root.bind("<R>", lambda e: self.rotate_surface_ccw())

    # --------- DISPLAY DETECTION --------- #
    def detect_displays(self):
        displays = []
        try:
            import subprocess
            import platform

            if platform.system() == "Linux":
                try:
                    result = subprocess.run(
                        ["xrandr", "--query"], capture_output=True, text=True, timeout=2
                    )
                    for line in result.stdout.splitlines():
                        if " connected" in line:
                            parts = line.split()
                            for part in parts:
                                if "x" in part and "+" in part:
                                    res_pos = part.split("+")
                                    w, h = map(int, res_pos[0].split("x"))
                                    x = int(res_pos[1]) if len(res_pos) > 1 else 0
                                    y = int(res_pos[2]) if len(res_pos) > 2 else 0
                                    displays.append((x, y, w, h))
                                    break
                except Exception:
                    pass
        except Exception:
            pass

        if not displays:
            try:
                w = self.root.winfo_screenwidth()
                h = self.root.winfo_screenheight()
                displays.append((0, 0, w, h))
            except Exception:
                displays.append((0, 0, 1920, 1080))

        return displays

    def get_selected_display(self):
        try:
            txt = self.display_var.get()
            idx = int(txt.split()[1]) - 1
            if 0 <= idx < len(self.displays):
                return self.displays[idx]
        except Exception:
            pass
        return self.displays[0] if self.displays else (0, 0, 1920, 1080)

    # --------- GLFW MONITOR MATCHING --------- #
    def get_glfw_monitors(self):
        mons = []
        for m in glfw.get_monitors():
            mode = glfw.get_video_mode(m)
            x, y = glfw.get_monitor_pos(m)
            mons.append(
                {
                    "monitor": m,
                    "x": x,
                    "y": y,
                    "width": mode.size.width,
                    "height": mode.size.height,
                }
            )
        return mons

    def find_matching_monitor(self, target_display):
        tx, ty, tw, th = target_display
        mons = self.get_glfw_monitors()
        if not mons:
            return None

        best = None
        for m in mons:
            if (
                m["x"] == tx
                and m["y"] == ty
                and m["width"] == tw
                and m["height"] == th
            ):
                return m
            if m["width"] == tw and m["height"] == th:
                best = m

        return best or mons[0]

    # --------- VIDEO THREAD --------- #
    def start_video_thread(self):
        if self.video_thread and self.video_thread.is_alive():
            return
        self.stop_thread = False
        self.video_thread = threading.Thread(target=self.video_reader_thread, daemon=True)
        self.video_thread.start()

    def stop_video_thread(self):
        self.stop_thread = True
        if self.video_thread and self.video_thread.is_alive():
            self.video_thread.join(timeout=0.5)

    def video_reader_thread(self):
        sleep_time = 1.0 / max(self.target_fps, 1)
        while not self.stop_thread:
            for vs in list(self.video_sources.values()):
                vs.read_frame()
            time.sleep(sleep_time)

    # --------- SURFACES --------- #
    def add_quad_surface(self):
        # Use Virtual Canvas Size
        w = self.canvas_width
        h = self.canvas_height
        margin = min(w, h) // 4

        points = np.array(
            [
                [margin, margin],
                [w - margin, margin],
                [w - margin, h - margin],
                [margin, h - margin],
            ],
            dtype=np.float32,
        )

        surface = {
            "points": points,
            "opacity": 1.0,
            "name": f"Surface {len(self.surfaces) + 1}",
            "video_id": None,
            "media_type": None,
            "media_path": None, # Store path for config
            "static_frame": None,
        }

        self.surfaces.append(surface)
        # self.sequence_steps.append(...) # Don't auto-add to playlist
        self.surface_listbox.insert(tk.END, surface["name"])
        self.surface_listbox.selection_clear(0, tk.END)
        self.surface_listbox.selection_set(tk.END)
        self.selected_surface = len(self.surfaces) - 1
        self.opengl_view.selected_surface_index = self.selected_surface
        self.update_media_label()

    def delete_surface(self):
        if self.selected_surface is None:
            return
        idx = self.selected_surface
        if not (0 <= idx < len(self.surfaces)):
            return

        surface = self.surfaces[idx]
        vid = surface.get("video_id")
        if vid and vid in self.video_sources:
            self.video_sources[vid].release()
            del self.video_sources[vid]

        self.surfaces.pop(idx)
        # Update sequence steps - remove steps referencing this surface
        self.sequence_steps = [s for s in self.sequence_steps if s["surface_index"] != idx]
        # Shift indices greater than idx
        for step in self.sequence_steps:
            if step["surface_index"] > idx:
                step["surface_index"] -= 1
        
        self.surface_listbox.delete(idx)
        self.selected_surface = None
        self.opengl_view.selected_surface_index = None
        self.media_label.config(text="No media", foreground="gray")

    def on_surface_select(self, event):
        selection = self.surface_listbox.curselection()
        if not selection:
            return
        self.selected_surface = selection[0]
        self.opengl_view.selected_surface_index = self.selected_surface
        surface = self.surfaces[self.selected_surface]
        self.opacity_scale.set(surface["opacity"] * 100)
        self.update_media_label()

    def update_media_label(self):
        if self.selected_surface is None:
            self.media_label.config(text="No surface selected", foreground="gray")
            return
        surface = self.surfaces[self.selected_surface]
        if surface["media_type"] == "video":
            self.media_label.config(text="Video loaded", foreground="green")
        elif surface["media_type"] == "image":
            self.media_label.config(text="Image loaded", foreground="blue")
        else:
            self.media_label.config(text="No media", foreground="gray")

    # --------- MEDIA LOADING --------- #
    def load_video_to_surface(self):
        if self.selected_surface is None:
            messagebox.showwarning("No Surface", "Please select a surface first")
            return

        filename = filedialog.askopenfilename(
            title="Select Video",
            filetypes=[("Video files", "*.mp4 *.avi *.mov *.mkv"), ("All files", "*.*")],
        )
        if not filename:
            return

        surface = self.surfaces[self.selected_surface]
        old_vid = surface.get("video_id")
        if old_vid and old_vid in self.video_sources:
            self.video_sources[old_vid].release()
            del self.video_sources[old_vid]

        video_id = f"video_{len(self.video_sources)}_{time.time()}"
        # If sequential, disable loop by default? Or keep it? 
        # User said "continue playing them as and when they finish".
        # So sequential videos should NOT loop individually.
        # But concurrent ones might.
        # Let's default to loop=True, but override in playback logic.
        self.video_sources[video_id] = VideoSource(filename, loop=True)

        surface["video_id"] = video_id
        surface["media_type"] = "video"
        surface["media_path"] = filename
        surface["static_frame"] = None

        self.media_label.config(text=f"Video: {os.path.basename(filename)}", foreground="green")
        self.reset_playback() # Restart sequence logic when media changes

    def load_image_to_surface(self):
        if self.selected_surface is None:
            messagebox.showwarning("No Surface", "Please select a surface first")
            return

        filename = filedialog.askopenfilename(
            title="Select Image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp"), ("All files", "*.*")],
        )
        if not filename:
            return

        surface = self.surfaces[self.selected_surface]
        old_vid = surface.get("video_id")
        if old_vid and old_vid in self.video_sources:
            self.video_sources[old_vid].release()
            del self.video_sources[old_vid]

        img = cv2.imread(filename)
        if img is None:
            messagebox.showerror("Error", "Failed to load image")
            return

        h, w = img.shape[:2]
        max_size = 1280
        if w > max_size or h > max_size:
            scale = max_size / max(w, h)
            new_w, new_h = int(w * scale), int(h * scale)
            img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

        static_frame = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)

        surface["video_id"] = None
        surface["media_type"] = "image"
        surface["media_path"] = filename
        surface["static_frame"] = static_frame

        self.media_label.config(text=f"Image: {os.path.basename(filename)}", foreground="blue")

    # --------- TRANSFORM CONTROLS --------- #
    def update_opacity(self, value):
        if self.selected_surface is None:
            return
        idx = self.selected_surface
        if 0 <= idx < len(self.surfaces):
            self.surfaces[idx]["opacity"] = float(value) / 100.0

    def rotate_surface_cw(self):
        if self.selected_surface is None:
            return
        s = self.surfaces[self.selected_surface]
        s["points"] = np.roll(s["points"], 1, axis=0)

    def rotate_surface_ccw(self):
        if self.selected_surface is None:
            return
        s = self.surfaces[self.selected_surface]
        s["points"] = np.roll(s["points"], -1, axis=0)

    # --------- OPENGL PREVIEW INPUT --------- #
    def on_gl_click(self, event):
        if self.selected_surface is None:
            return

        # Convert Tk coords to Canvas coords
        # Viewport: self.opengl_view.width x height
        # Canvas: self.canvas_width x height
        # Scale factor:
        scale_x = self.canvas_width / self.opengl_view.width
        scale_y = self.canvas_height / self.opengl_view.height
        
        # Mouse in Canvas Coords
        cx = event.x * scale_x
        cy = event.y * scale_y
        
        # GL Y is inverted relative to Canvas Top-Left?
        # In draw_surface we used: self.canvas_height - pts[0][1]
        # So points are stored in Top-Left coords.
        # Mouse event is Top-Left.
        # So we can compare directly.
        
        surface = self.surfaces[self.selected_surface]
        pts = surface["points"]

        min_dist = float("inf")
        closest = None
        # Threshold in canvas pixels (e.g. 50px)
        threshold = 50.0 
        
        for i, (px, py) in enumerate(pts):
            d = np.hypot(cx - px, cy - py)
            if d < threshold and d < min_dist:
                min_dist = d
                closest = i

        self.selected_point = closest

    def on_gl_drag(self, event):
        if self.selected_surface is None or self.selected_point is None:
            return

        scale_x = self.canvas_width / self.opengl_view.width
        scale_y = self.canvas_height / self.opengl_view.height
        
        cx = event.x * scale_x
        cy = event.y * scale_y

        s = self.surfaces[self.selected_surface]
        s["points"][self.selected_point] = [cx, cy]

    def on_gl_release(self, event):
        self.selected_point = None

    # --------- FRAME ACCESS --------- #
    def get_surface_frame(self, surface, idx=None):
        # Sequential Mode Visibility Logic
        if self.playback_mode.get() == "sequential":
            if idx is None:
                try:
                    idx = self.surfaces.index(surface)
                except ValueError:
                    pass
            
            if idx is not None:
                # If continuous, always show
                if idx in self.continuous_surfaces:
                    pass # Allow through
                else:
                    # Determine active surface index
                    active_idx = -1
                    if self.sequence_steps and self.current_sequence_index < len(self.sequence_steps):
                        active_idx = self.sequence_steps[self.current_sequence_index]["surface_index"]
                    
                    # Strict check: If this surface is not the active one, hide it.
                    if idx != active_idx:
                        return None

        if surface["media_type"] == "video":
            vid = surface.get("video_id")
            if vid and vid in self.video_sources:
                return self.video_sources[vid].get_current_frame()
        elif surface["media_type"] == "image":
            return surface.get("static_frame")
        return None

    # --------- FULLSCREEN OUTPUT (GLFW) --------- #
    def fullscreen_output(self):
        if self.fullscreen_window:
            messagebox.showinfo("Info", "Fullscreen window already open")
            return

        if not self.surfaces or all(s.get("media_type") is None for s in self.surfaces):
            messagebox.showwarning("No Media", "Load media on at least one surface first")
            return

        if not any(self.get_surface_frame(s) is not None for s in self.surfaces):
            messagebox.showwarning("No Media", "Waiting for media to load. Try again.")
            return

        if not glfw.init():
            messagebox.showerror("GLFW Error", "Failed to initialize GLFW")
            return

        target_display = self.get_selected_display()
        monitor_info = self.find_matching_monitor(target_display)
        if monitor_info is None:
            monitor = glfw.get_primary_monitor()
            mode = glfw.get_video_mode(monitor)
            width, height = mode.size.width, mode.size.height
        else:
            monitor = monitor_info["monitor"]
            width = monitor_info["width"]
            height = monitor_info["height"]

        glfw.window_hint(glfw.AUTO_ICONIFY, glfw.FALSE)

        self.fullscreen_window = glfw.create_window(
            width,
            height,
            "Projection Mapper Fullscreen",
            monitor,  # choose monitor here
            None,
        )

        if not self.fullscreen_window:
            glfw.terminate()
            messagebox.showerror("GLFW Error", "Failed to create fullscreen window")
            return

        glfw.make_context_current(self.fullscreen_window)
        glfw.swap_interval(1)

        self.fullscreen_renderer = GLFullscreenRenderer(
            self.surfaces,
            self.get_surface_frame,
            selected_index=self.selected_surface,
            canvas_width=self.canvas_width,
            canvas_height=self.canvas_height,
        )

        drag_state = {"surface_idx": None, "point_idx": None}

        def key_callback(win, key, scancode, action, mods):
            if action != glfw.PRESS:
                return
            if key == glfw.KEY_ESCAPE:
                glfw.set_window_should_close(win, True)
            elif key == glfw.KEY_E:
                self.fullscreen_renderer.edit_mode = not self.fullscreen_renderer.edit_mode
            elif key == glfw.KEY_H:
                self.fullscreen_renderer.show_controls = not self.fullscreen_renderer.show_controls
            elif key == glfw.KEY_R:
                idx = self.fullscreen_renderer.selected_surface_index
                if idx is not None and 0 <= idx < len(self.surfaces):
                    s = self.surfaces[idx]
                    s["points"] = np.roll(s["points"], 1, axis=0)

        def mouse_button_callback(win, button, action, mods):
            if button != glfw.MOUSE_BUTTON_LEFT:
                return
            x, y = glfw.get_cursor_pos(win)
            
            # Scale to Canvas
            w_win, h_win = glfw.get_window_size(win)
            # Avoid div by zero
            if w_win == 0 or h_win == 0: return
            
            sx = self.canvas_width / w_win
            sy = self.canvas_height / h_win
            
            cx = x * sx
            cy = y * sy

            if action == glfw.PRESS and self.fullscreen_renderer.edit_mode:
                for i, s in enumerate(self.surfaces):
                    pts = s["points"]
                    for j, p in enumerate(pts):
                        # Threshold also scaled? Or just check distance in canvas units.
                        # 30px on canvas is reasonable.
                        if np.hypot(cx - p[0], cy - p[1]) < 30:
                            drag_state["surface_idx"] = i
                            drag_state["point_idx"] = j
                            self.fullscreen_renderer.selected_surface_index = i
                            break
            elif action == glfw.RELEASE:
                drag_state["surface_idx"] = None
                drag_state["point_idx"] = None

        def cursor_pos_callback(win, x, y):
            i = drag_state["surface_idx"]
            j = drag_state["point_idx"]
            if i is not None and j is not None and self.fullscreen_renderer.edit_mode:
                w_win, h_win = glfw.get_window_size(win)
                if w_win == 0 or h_win == 0: return
                
                sx = self.canvas_width / w_win
                sy = self.canvas_height / h_win
                
                cx = x * sx
                cy = y * sy
                
                self.surfaces[i]["points"][j] = [cx, cy]

        glfw.set_key_callback(self.fullscreen_window, key_callback)
        glfw.set_mouse_button_callback(self.fullscreen_window, mouse_button_callback)
        glfw.set_cursor_pos_callback(self.fullscreen_window, cursor_pos_callback)
        
        # Note: We do NOT run the loop here anymore. It's handled in gl_step.

    def close_fullscreen(self):
        if self.fullscreen_window:
            glfw.destroy_window(self.fullscreen_window)
            self.fullscreen_window = None
            self.fullscreen_renderer = None
            # Do NOT terminate glfw, as we might want to open it again.
            # glfw.terminate()

    def toggle_blackout(self, enabled):
        if self.fullscreen_renderer:
            self.fullscreen_renderer.blackout = enabled

    # --------- PLAYBACK LOGIC --------- #
    def reset_playback(self):
        self.current_sequence_index = 0
        self.sequence_active = True
        
        mode = self.playback_mode.get()
        
        for i, surface in enumerate(self.surfaces):
            vid = surface.get("video_id")
            if vid and vid in self.video_sources:
                vs = self.video_sources[vid]
                if mode == "concurrent":
                    vs.loop = True
                    vs.play()
                else:
                    if i in self.continuous_surfaces:
                        vs.loop = True
                        vs.play()
                    else:
                        vs.loop = False
                        vs.stop() # Stop all initially for sequential

        if mode == "sequential" and self.surfaces:
             # Start first one
             # Start first one
             self.play_next_in_sequence()

    def open_sequence_setup(self):
        SequenceEditorDialog(
            self.root, 
            self.surfaces, 
            self.sequence_steps, 
            self.continuous_surfaces, 
            self.apply_sequence_setup
        )

    def apply_sequence_setup(self, new_steps, new_continuous):
        self.sequence_steps = new_steps
        self.continuous_surfaces = new_continuous
        self.reset_playback()


    def restart_sequence(self):
        self.reset_playback()

    def play_next_in_sequence(self):
        # Find next valid step
        while self.current_sequence_index < len(self.sequence_steps):
            step = self.sequence_steps[self.current_sequence_index]
            idx = step["surface_index"]
            path = step["media_path"]
            
            if 0 <= idx < len(self.surfaces):
                surface = self.surfaces[idx]
                
                # Check if we need to load media
                current_path = surface.get("media_path")
                if current_path != path:
                    # Load new media
                    if step["media_type"] == "video":
                        old_vid = surface.get("video_id")
                        if old_vid and old_vid in self.video_sources:
                            self.video_sources[old_vid].release()
                            del self.video_sources[old_vid]
                            
                        video_id = f"video_{len(self.video_sources)}_{time.time()}_{idx}"
                        self.video_sources[video_id] = VideoSource(path, loop=False) # Sequential = No Loop
                        surface["video_id"] = video_id
                        surface["media_type"] = "video"
                        surface["media_path"] = path
                        surface["static_frame"] = None
                        
                    elif step["media_type"] == "image":
                        img = cv2.imread(path)
                        if img is not None:
                            h, w = img.shape[:2]
                            max_size = 1280
                            if w > max_size or h > max_size:
                                scale = max_size / max(w, h)
                                new_w, new_h = int(w * scale), int(h * scale)
                                img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                            surface["static_frame"] = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                            surface["media_type"] = "image"
                            surface["media_path"] = path
                            surface["video_id"] = None

                # Play
                vid = surface.get("video_id")
                if vid and vid in self.video_sources:
                    vs = self.video_sources[vid]
                    vs.loop = False
                    vs.play()
                    self.current_clip_start_time = time.time()
                    return # Started
            
                # If it's an image, we also "start" it by setting time
                if surface["media_type"] == "image":
                    self.current_clip_start_time = time.time()
                    return
            
            # If invalid, skip
            self.current_sequence_index += 1
            
        # Sequence finished -> Loop
        self.current_sequence_index = 0
        self.play_next_in_sequence()

    def update_playback_logic(self):
        if self.playback_mode.get() == "sequential":
            # Check if current playing video is finished
            if self.current_sequence_index < len(self.sequence_steps):
                step = self.sequence_steps[self.current_sequence_index]
                idx = step["surface_index"]
                if 0 <= idx < len(self.surfaces):
                    surface = self.surfaces[idx]
                    vid = surface.get("video_id")
                    if vid and vid in self.video_sources:
                        vs = self.video_sources[vid]
                        if vs.is_finished():
                            self.current_sequence_index += 1
                            self.play_next_in_sequence()
                    elif surface["media_type"] == "image":
                        # Check duration
                        if time.time() - self.current_clip_start_time > self.image_duration:
                            self.current_sequence_index += 1
                            self.play_next_in_sequence()

    # --------- SAVE CONFIG --------- #
    def save_config(self):
        filename = filedialog.asksaveasfilename(
            title="Save Configuration",
            defaultextension=".npy",
            filetypes=[("NumPy files", "*.npy"), ("All files", "*.*")],
        )
        if not filename:
            return

        config = {
            "surfaces": [
                {
                    "points": s["points"].tolist(), 
                    "opacity": s["opacity"], 
                    "name": s["name"],
                    "media_path": s.get("media_path")
                }
                for s in self.surfaces
            ],
            "playback_mode": self.playback_mode.get(),
            "playback_mode": self.playback_mode.get(),
            "sequence_steps": self.sequence_steps,
            "continuous_surfaces": list(self.continuous_surfaces)
        }
        np.save(filename, config)
        messagebox.showinfo("Saved", "Configuration saved successfully")

    def load_config(self):
        filename = filedialog.askopenfilename(
            title="Load Configuration",
            filetypes=[("NumPy files", "*.npy"), ("All files", "*.*")],
        )
        if filename:
            self.load_config_from_file(filename)

    def load_config_from_file(self, filename, silent=False):
        try:
            config = np.load(filename, allow_pickle=True).item()
            if "surfaces" not in config:
                messagebox.showerror("Error", "Invalid configuration file")
                return

            # Clear existing surfaces
            self.surfaces.clear()
            self.surface_listbox.delete(0, tk.END)
            self.selected_surface = None
            self.opengl_view.selected_surface_index = None
            self.sequence_order = []
            
            # Release existing videos
            for vs in list(self.video_sources.values()):
                vs.release()
            self.video_sources.clear()

            # Load new surfaces
            for i, s_data in enumerate(config["surfaces"]):
                surface = {
                    "points": np.array(s_data["points"], dtype=np.float32),
                    "opacity": s_data["opacity"],
                    "name": s_data["name"],
                    "video_id": None,
                    "media_type": None,
                    "media_path": s_data.get("media_path"),
                    "static_frame": None,
                }
                
                # Load Media if path exists
                path = surface["media_path"]
                if path and os.path.exists(path):
                    if path.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                        video_id = f"video_{len(self.video_sources)}_{time.time()}_{i}"
                        self.video_sources[video_id] = VideoSource(path, loop=True)
                        surface["video_id"] = video_id
                        surface["media_type"] = "video"
                    elif path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
                        img = cv2.imread(path)
                        if img is not None:
                            h, w = img.shape[:2]
                            max_size = 1280
                            if w > max_size or h > max_size:
                                scale = max_size / max(w, h)
                                new_w, new_h = int(w * scale), int(h * scale)
                                img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
                            surface["static_frame"] = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
                            surface["media_type"] = "image"

                self.surfaces.append(surface)
                self.surface_listbox.insert(tk.END, surface["name"])
                
            # Load settings
            if "playback_mode" in config:
                self.playback_mode.set(config["playback_mode"])
            if "sequence_steps" in config:
                self.sequence_steps = config["sequence_steps"]
            elif "sequence_order" in config:
                # Migrate old format
                self.sequence_steps = []
                for idx in config["sequence_order"]:
                    if 0 <= idx < len(self.surfaces):
                        s = self.surfaces[idx]
                        if s["media_path"]:
                            self.sequence_steps.append({
                                "surface_index": idx,
                                "media_path": s["media_path"],
                                "media_type": s["media_type"]
                            })
            else:
                self.sequence_steps = []
            
            if "continuous_surfaces" in config:
                self.continuous_surfaces = set(config["continuous_surfaces"])
            else:
                self.continuous_surfaces = set()

            self.reset_playback()
            if not silent:
                messagebox.showinfo("Loaded", "Configuration loaded successfully")
            
        except Exception as e:
            if not silent:
                messagebox.showerror("Error", f"Failed to load config: {e}")
            else:
                print(f"Error loading config: {e}")

    def launch_control_panel(self):
        LiveControlPanel(self.root, self.load_config_from_file, self.toggle_blackout)

    # --------- CLEANUP --------- #
    def shutdown(self):
        self.stop_video_thread()
        for vs in list(self.video_sources.values()):
            vs.release()
        self.video_sources.clear()

    def __del__(self):
        try:
            self.shutdown()
        except Exception:
            pass


# ==========================
# Entry Point
# ==========================
def main():
    root = tk.Tk()
    app = ProjectionMapper(root)

    def on_close():
        app.shutdown()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()

if __name__ == "__main__":
    main()
