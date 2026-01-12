import moderngl
import glfw
from PIL import Image
import os

def main():
    if not glfw.init():
        return
    
    glfw.window_hint(glfw.CONTEXT_VERSION_MAJOR, 3)
    glfw.window_hint(glfw.CONTEXT_VERSION_MINOR, 3)
    glfw.window_hint(glfw.OPENGL_PROFILE, glfw.OPENGL_CORE_PROFILE)
    # create hidden window
    window = glfw.create_window(100, 100, "Hidden", None, None)
    glfw.make_context_current(window)
    
    ctx = moderngl.create_context()
    
    path = "/home/vrazer/.gemini/antigravity/scratch/projection_mapper/apre ski projection mapping/Generated Image November 14, 2025 - 11_38PM.png"
    
    print(f"Loading {path}")
    try:
        img = Image.open(path).convert('RGB')
        print(f"Image size: {img.size}")
        print(f"Image mode: {img.mode}")
        print(f"Data length: {len(img.tobytes())}")
        
        texture = ctx.texture(img.size, 3, img.tobytes())
        print("Texture created successfully")
    except Exception as e:
        print(f"Error: {e}")
        # Check max texture size
        print(f"Max texture size: {ctx.info['GL_MAX_TEXTURE_SIZE']}")

    glfw.terminate()

if __name__ == "__main__":
    main()
