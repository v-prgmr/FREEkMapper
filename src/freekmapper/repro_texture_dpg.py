import moderngl
import glfw
import dearpygui.dearpygui as dpg
from PIL import Image
import os

def main():
    if not glfw.init():
        return
    
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    
    window = glfw.create_window(1280, 720, "Repro DPG", None, None)
    glfw.make_context_current(window)
    
    ctx = moderngl.create_context()
    
    dpg.create_context()
    dpg.create_viewport(title='Controls', width=400, height=600)
    dpg.setup_dearpygui()
    
    path = "/home/vrazer/.gemini/antigravity/scratch/projection_mapper/apre ski projection mapping/Generated Image November 14, 2025 - 11_38PM.png"

    def load_callback():
        print(f"Loading {path}")
        try:
            img = Image.open(path).convert('RGB')
            print(f"Image size: {img.size}")
            texture = ctx.texture(img.size, 3, img.tobytes())
            print("Texture created successfully")
        except Exception as e:
            print(f"Error: {e}")

    with dpg.window(label="Test"):
        dpg.add_button(label="Load", callback=load_callback)

    dpg.show_viewport()

    # Auto-trigger for testing
    # We can't easily auto-click DPG button from script without running the loop.
    # But we can call the callback directly to simulate it happening during the loop?
    # No, we want it to happen inside the loop context if possible, or just call it.
    
    # Let's run a few frames and call it.
    
    frame_count = 0
    while not glfw.window_should_close(window):
        glfw.poll_events()
        
        ctx.clear(0.1, 0.1, 0.1)
        
        if frame_count == 10:
            load_callback()
            break # Exit after test
            
        dpg.render_dearpygui_frame()
        glfw.swap_buffers(window)
        frame_count += 1

    dpg.destroy_context()
    glfw.terminate()

if __name__ == "__main__":
    main()
