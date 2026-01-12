import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os

class SequenceEditorDialog(tk.Toplevel):
    def __init__(self, parent, surfaces, sequence_steps, continuous_surfaces, on_apply):
        super().__init__(parent)
        self.title("Sequence Editor (Playlist)")
        self.geometry("600x600")
        self.transient(parent)
        self.grab_set()
        
        self.surfaces = surfaces
        # sequence_steps: list of {"surface_index": int, "media_path": str, "media_type": str}
        self.sequence_steps = list(sequence_steps) 
        self.continuous_surfaces = set(continuous_surfaces)
        self.on_apply = on_apply
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main Layout: Left (Sequence), Right (Controls/Continuous)
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # --- LEFT: SEQUENCE LIST ---
        seq_frame = ttk.LabelFrame(main_frame, text="Playback Sequence (Playlist)", padding=5)
        seq_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Listbox with Scrollbar
        self.seq_listbox = tk.Listbox(seq_frame, selectmode=tk.SINGLE)
        scrollbar = ttk.Scrollbar(seq_frame, orient="vertical", command=self.seq_listbox.yview)
        self.seq_listbox.config(yscrollcommand=scrollbar.set)
        
        self.seq_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.refresh_sequence_list()
        
        # --- RIGHT: CONTROLS ---
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        
        # Add Step Section
        add_frame = ttk.LabelFrame(right_frame, text="Add Step", padding=5)
        add_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(add_frame, text="Surface:").pack(anchor=tk.W)
        self.surface_var = tk.StringVar()
        surface_options = [s["name"] for s in self.surfaces]
        self.surface_cb = ttk.Combobox(add_frame, textvariable=self.surface_var, values=surface_options, state="readonly")
        if surface_options: self.surface_cb.current(0)
        self.surface_cb.pack(fill=tk.X, pady=2)
        
        ttk.Button(add_frame, text="Select Media...", command=self.browse_media).pack(fill=tk.X, pady=2)
        self.selected_media_path = None
        self.media_lbl = ttk.Label(add_frame, text="No media selected", foreground="gray", wraplength=150)
        self.media_lbl.pack(pady=2)
        
        ttk.Button(add_frame, text="Add to Playlist", command=self.add_step).pack(fill=tk.X, pady=5)
        
        # Edit Sequence Section
        edit_frame = ttk.LabelFrame(right_frame, text="Edit Playlist", padding=5)
        edit_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Button(edit_frame, text="Move Up", command=self.move_up).pack(fill=tk.X, pady=2)
        ttk.Button(edit_frame, text="Move Down", command=self.move_down).pack(fill=tk.X, pady=2)
        ttk.Button(edit_frame, text="Remove Step", command=self.remove_step).pack(fill=tk.X, pady=2)
        
        # Continuous Section
        cont_frame = ttk.LabelFrame(right_frame, text="Continuous Surfaces", padding=5)
        cont_frame.pack(fill=tk.BOTH, expand=True)
        
        self.cont_vars = []
        for i, surface in enumerate(self.surfaces):
            var = tk.BooleanVar(value=(i in self.continuous_surfaces))
            self.cont_vars.append(var)
            ttk.Checkbutton(cont_frame, text=surface["name"], variable=var).pack(anchor=tk.W)
            
        # Bottom Buttons
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, pady=10, padx=10)
        
        ttk.Button(btn_frame, text="Apply", command=self.apply).pack(side=tk.RIGHT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        
    def browse_media(self):
        filename = filedialog.askopenfilename(
            title="Select Media",
            filetypes=[("Media files", "*.mp4 *.avi *.mov *.mkv *.jpg *.png"), ("All files", "*.*")],
            parent=self
        )
        if filename:
            self.selected_media_path = filename
            self.media_lbl.config(text=os.path.basename(filename), foreground="black")
            
    def add_step(self):
        idx = self.surface_cb.current()
        if idx < 0:
            messagebox.showwarning("Error", "Select a surface")
            return
        
        if not self.selected_media_path:
            messagebox.showwarning("Error", "Select media file")
            return
            
        media_type = "video"
        if self.selected_media_path.lower().endswith(('.jpg', '.jpeg', '.png', '.bmp')):
            media_type = "image"
            
        step = {
            "surface_index": idx,
            "media_path": self.selected_media_path,
            "media_type": media_type
        }
        self.sequence_steps.append(step)
        self.refresh_sequence_list()
        
    def refresh_sequence_list(self):
        self.seq_listbox.delete(0, tk.END)
        for i, step in enumerate(self.sequence_steps):
            s_idx = step["surface_index"]
            s_name = self.surfaces[s_idx]["name"] if 0 <= s_idx < len(self.surfaces) else "Unknown"
            m_name = os.path.basename(step["media_path"])
            self.seq_listbox.insert(tk.END, f"{i+1}. {s_name} - {m_name}")
            
    def move_up(self):
        sel = self.seq_listbox.curselection()
        if not sel: return
        idx = sel[0]
        if idx > 0:
            self.sequence_steps[idx], self.sequence_steps[idx-1] = self.sequence_steps[idx-1], self.sequence_steps[idx]
            self.refresh_sequence_list()
            self.seq_listbox.selection_set(idx-1)
            
    def move_down(self):
        sel = self.seq_listbox.curselection()
        if not sel: return
        idx = sel[0]
        if idx < len(self.sequence_steps) - 1:
            self.sequence_steps[idx], self.sequence_steps[idx+1] = self.sequence_steps[idx+1], self.sequence_steps[idx]
            self.refresh_sequence_list()
            self.seq_listbox.selection_set(idx+1)
            
    def remove_step(self):
        sel = self.seq_listbox.curselection()
        if not sel: return
        idx = sel[0]
        self.sequence_steps.pop(idx)
        self.refresh_sequence_list()
        
    def apply(self):
        # Update continuous set
        new_continuous = set()
        for i, var in enumerate(self.cont_vars):
            if var.get():
                new_continuous.add(i)
                
        self.on_apply(self.sequence_steps, new_continuous)
        self.destroy()
