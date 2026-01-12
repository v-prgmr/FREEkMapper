import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os

class LiveControlPanel(tk.Toplevel):
    def __init__(self, master, load_config_callback, toggle_blackout_callback=None):
        super().__init__(master)
        self.title("Live Control Panel")
        self.geometry("400x500")
        self.load_config_callback = load_config_callback
        self.toggle_blackout_callback = toggle_blackout_callback
        
        self.config_slots = [None] * 5 # Paths for slots 1-5
        self.loop_active = False
        self.current_loop_index = 0
        self.loop_slots = [] # Indices of slots to loop
        
        self.setup_ui()
        
    def setup_ui(self):
        ttk.Label(self, text="Live Config Switcher", font=("Arial", 12, "bold")).pack(pady=10)
        
        self.slot_frames = []
        self.slot_btns = [] # Track buttons to disable/enable
        self.loop_vars = []
        
        for i in range(5):
            frame = ttk.Frame(self)
            frame.pack(fill=tk.X, padx=10, pady=5)
            
            # Loop Checkbox
            loop_var = tk.BooleanVar()
            self.loop_vars.append(loop_var)
            ttk.Checkbutton(frame, variable=loop_var).pack(side=tk.LEFT)
            
            # Slot Label
            lbl = ttk.Label(frame, text=f"Slot {i+1}: Empty", width=20)
            lbl.pack(side=tk.LEFT, padx=5)
            
            # Assign Button
            btn_assign = ttk.Button(frame, text="Assign", width=6, command=lambda idx=i: self.assign_slot(idx))
            btn_assign.pack(side=tk.LEFT, padx=2)
            self.slot_btns.append(btn_assign)
            
            # Trigger Button
            btn_go = ttk.Button(frame, text="GO", width=4, command=lambda idx=i: self.trigger_slot(idx))
            btn_go.pack(side=tk.LEFT, padx=2)
            self.slot_btns.append(btn_go)
            
            self.slot_frames.append(lbl)
            
        ttk.Separator(self, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # Loop Controls
        loop_frame = ttk.LabelFrame(self, text="Loop Control", padding=10)
        loop_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(loop_frame, text="Loop Duration (sec):").pack(side=tk.LEFT)
        self.duration_entry = ttk.Entry(loop_frame, width=5)
        self.duration_entry.insert(0, "10")
        self.duration_entry.pack(side=tk.LEFT, padx=5)
        
        self.loop_btn = ttk.Button(loop_frame, text="Start Loop", command=self.toggle_loop)
        self.loop_btn.pack(side=tk.RIGHT)
        
        # Show Control
        self.show_enabled = True
        self.show_btn = ttk.Button(self, text="Disable Show", command=self.toggle_show)
        self.show_btn.pack(pady=5)
        
        self.status_lbl = ttk.Label(self, text="Ready", foreground="gray")
        self.status_lbl.pack(pady=10)

    def toggle_show(self):
        self.show_enabled = not self.show_enabled
        
        # Toggle Blackout in Main App
        # We need access to main app instance or a callback. 
        # Currently we only have load_config_callback.
        # We should probably pass a blackout callback or access master.app?
        # master is root. app is ProjectionMapper instance?
        # Usually master is root. We can try to access app via a new callback or assume structure.
        # Let's assume we need to pass a callback.
        # But for now, let's try to access it via master if possible, or update main to pass it.
        # Actually, let's update main.py to pass the callback.
        # But I can't update main.py easily now without another step.
        # Wait, I can use self.master.winfo_toplevel() or similar?
        # No, ProjectionMapper is a class, not a widget.
        # I'll assume the user will update main.py to pass the callback, OR I can add it to main.py in the next step.
        # Let's assume I'll update main.py to pass 'toggle_blackout_callback' to constructor.
        if hasattr(self, 'toggle_blackout_callback'):
            self.toggle_blackout_callback(not self.show_enabled)
            
        if self.show_enabled:
            self.show_btn.config(text="Disable Show")
            self.status_lbl.config(text="Show Enabled", foreground="green")
            # Enable controls
            self.loop_btn.state(["!disabled"])
            for btn in self.slot_btns: # Need to track buttons
                btn.state(["!disabled"])
        else:
            self.show_btn.config(text="Enable Show")
            self.status_lbl.config(text="Show Disabled (Blackout)", foreground="red")
            # Disable controls
            if self.loop_active:
                self.toggle_loop() # Stop loop
            
            self.loop_btn.state(["disabled"])
            for btn in self.slot_btns:
                btn.state(["disabled"])

    def assign_slot(self, idx):
        if not self.show_enabled: return
        filename = filedialog.askopenfilename(
            title=f"Assign Config to Slot {idx+1}",
            filetypes=[("NumPy files", "*.npy"), ("All files", "*.*")],
        )
        if filename:
            self.config_slots[idx] = filename
            self.slot_frames[idx].config(text=f"Slot {idx+1}: {os.path.basename(filename)}")

    def trigger_slot(self, idx):
        if not self.show_enabled: return
        path = self.config_slots[idx]
        if path:
            # Use silent mode to avoid popups
            self.load_config_callback(path, silent=True)
            self.status_lbl.config(text=f"Loaded Slot {idx+1}", foreground="green")
        else:
            messagebox.showwarning("Empty Slot", f"Slot {idx+1} is empty")

    def toggle_loop(self):
        if not self.show_enabled: return
        
        if self.loop_active:
            self.loop_active = False
            self.loop_btn.config(text="Start Loop")
            self.status_lbl.config(text="Loop Stopped", foreground="red")
        else:
            # Gather slots
            self.loop_slots = [i for i, var in enumerate(self.loop_vars) if var.get() and self.config_slots[i]]
            if not self.loop_slots:
                messagebox.showwarning("No Slots", "Select at least one assigned slot to loop")
                return
            
            try:
                self.loop_duration = float(self.duration_entry.get()) * 1000 # ms
            except:
                self.loop_duration = 10000
            
            self.loop_active = True
            self.current_loop_index = 0 # Always start from first slot
            self.loop_btn.config(text="Stop Loop")
            self.status_lbl.config(text="Loop Running...", foreground="green")
            self.run_loop_step()

    def run_loop_step(self):
        if not self.loop_active:
            return
        
        idx = self.loop_slots[self.current_loop_index]
        self.trigger_slot(idx)
        
        self.current_loop_index = (self.current_loop_index + 1) % len(self.loop_slots)
        
        self.after(int(self.loop_duration), self.run_loop_step)
