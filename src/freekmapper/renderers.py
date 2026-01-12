from pyopengltk import OpenGLFrame
from OpenGL.GL import *
import time
import glfw
import numpy as np

# ==========================
# Embedded OpenGL Preview (Tkinter + pyopengltk)
# ==========================
class GLTkRenderer(OpenGLFrame):
    def __init__(self, master, surfaces, get_frame_callback, fps_callback=None, canvas_width=1920, canvas_height=1080, **kwargs):
        self.surfaces = surfaces
        self.get_frame = get_frame_callback
        self.fps_callback = fps_callback
        self.textures = {}  # id -> texture
        self.selected_surface_index = None
        self.last_time = time.time()
        # default size if not provided
        self.width = kwargs.get("width", 800)
        self.height = kwargs.get("height", 600)
        
        # Virtual Canvas Size (Target Resolution)
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        
        self.canvas_height = canvas_height
        
        self.context_ready = False
        
        super().__init__(master, **kwargs)

    def initgl(self):
        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glClearColor(0.0, 0.0, 0.0, 1.0)
        self.context_ready = True

    def set_size(self, event):
        # Keep track of widget size for viewport and Y-flip mapping
        self.width = max(event.width, 1)
        self.height = max(event.height, 1)

    def upload_texture(self, surface, frame):
        """Upload RGB frame to GPU."""
        video_id = surface.get("video_id") or id(surface)
        h, w = frame.shape[:2]

        if video_id not in self.textures:
            self.textures[video_id] = glGenTextures(1)

        tex = self.textures[video_id]
        glBindTexture(GL_TEXTURE_2D, tex)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        # Use pixel store to handle alignment if needed, but usually default is 4. 
        # If we have issues we can set GL_UNPACK_ALIGNMENT to 1.
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGB,
            w,
            h,
            0,
            GL_RGB,
            GL_UNSIGNED_BYTE,
            frame,
        )
        return tex

    def draw_surface(self, surface, tex, width, height, is_selected=False):
        pts = surface["points"]
        opacity = surface["opacity"]

        # If texture is present, draw textured quad
        if tex:
            glColor4f(1.0, 1.0, 1.0, opacity)
            glBindTexture(GL_TEXTURE_2D, tex)
            glEnable(GL_TEXTURE_2D)
            
            glBegin(GL_QUADS)
            # OpenGL origin bottom-left, Tk origin top-left → flip Y via (height - y)
            # Note: We are now using Canvas Coordinates for points.
            # glOrtho is set to Canvas Size.
            # So we don't need to flip Y relative to widget height, but relative to Canvas Height if points are top-left.
            # Let's assume points are stored in Top-Left Canvas Coords (0,0 is top-left of 1920x1080).
            # So GL Y = CanvasHeight - PointY.
            
            glTexCoord2f(0, 0)
            glVertex2f(pts[0][0], self.canvas_height - pts[0][1])
            glTexCoord2f(1, 0)
            glVertex2f(pts[1][0], self.canvas_height - pts[1][1])
            glTexCoord2f(1, 1)
            glVertex2f(pts[2][0], self.canvas_height - pts[2][1])
            glTexCoord2f(0, 1)
            glVertex2f(pts[3][0], self.canvas_height - pts[3][1])
            glEnd()
        else:
            # Draw placeholder wireframe
            glDisable(GL_TEXTURE_2D)
            glColor4f(0.5, 0.5, 0.5, 0.5)
            glBegin(GL_QUADS)
            glVertex2f(pts[0][0], self.canvas_height - pts[0][1])
            glVertex2f(pts[1][0], self.canvas_height - pts[1][1])
            glVertex2f(pts[2][0], self.canvas_height - pts[2][1])
            glVertex2f(pts[3][0], self.canvas_height - pts[3][1])
            glEnd()

        # Draw Selection / Controls
        if is_selected:
            glDisable(GL_TEXTURE_2D)
            glLineWidth(2.0)
            glColor3f(0.0, 1.0, 0.0)
            glBegin(GL_LINE_LOOP)
            for p in pts:
                glVertex2f(p[0], self.canvas_height - p[1])
            glEnd()

            glPointSize(8.0)
            glBegin(GL_POINTS)
            glColor3f(1.0, 1.0, 0.0)
            for p in pts:
                glVertex2f(p[0], self.canvas_height - p[1])
            glEnd()
            glEnable(GL_TEXTURE_2D)

    def redraw(self):
        if not self.context_ready:
            return

        # Ensure Tkinter GL context is current
        self.tkMakeCurrent()
        
        w, h = self.width, self.height
        glViewport(0, 0, w, h)
        glClear(GL_COLOR_BUFFER_BIT)

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        # Scale: Map Canvas Size (1920x1080) to Viewport (w x h)
        # We want to see the whole canvas.
        # glOrtho(left, right, bottom, top, near, far)
        # We map 0..CanvasWidth to 0..ViewportWidth
        glOrtho(0, self.canvas_width, 0, self.canvas_height, -1, 1)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        for i, surface in enumerate(self.surfaces):
            frame = self.get_frame(surface, i)
            tex = None
            if frame is not None:
                tex = self.upload_texture(surface, frame)
            
            self.draw_surface(surface, tex, w, h, i == self.selected_surface_index)

        # FPS callback
        now = time.time()
        dt = now - self.last_time
        if dt > 0.0:
            fps = 1.0 / dt
            if self.fps_callback:
                self.fps_callback(fps)
        self.last_time = now
        
        # Swap buffers!
        self.tkSwapBuffers()


# ==========================
# Fullscreen OpenGL Renderer (GLFW)
# ==========================
class GLFullscreenRenderer:
    def __init__(self, surfaces, get_frame_callback, selected_index=None, canvas_width=1920, canvas_height=1080):
        self.surfaces = surfaces
        self.get_frame = get_frame_callback
        self.textures = {}
        self.selected_surface_index = selected_index
        self.edit_mode = True
        self.show_controls = True
        self.blackout = False
        
        # Virtual Canvas Size
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height

    def upload_texture(self, surface, frame):
        vid = surface.get("video_id") or id(surface)
        h, w = frame.shape[:2]

        if vid not in self.textures:
            self.textures[vid] = glGenTextures(1)

        tex = self.textures[vid]
        glBindTexture(GL_TEXTURE_2D, tex)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        
        glPixelStorei(GL_UNPACK_ALIGNMENT, 1)

        glTexImage2D(
            GL_TEXTURE_2D,
            0,
            GL_RGB,
            w,
            h,
            0,
            GL_RGB,
            GL_UNSIGNED_BYTE,
            frame,
        )
        return tex

    def draw(self, width, height):
        glViewport(0, 0, width, height)
        glClearColor(0, 0, 0, 1)
        glClear(GL_COLOR_BUFFER_BIT)
        
        if self.blackout:
            return

        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        # Scale Canvas to Window
        glOrtho(0, self.canvas_width, 0, self.canvas_height, -1, 1)

        glMatrixMode(GL_MODELVIEW)
        glLoadIdentity()

        glEnable(GL_TEXTURE_2D)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        for i, surface in enumerate(self.surfaces):
            frame = self.get_frame(surface, i)
            tex = None
            if frame is not None:
                tex = self.upload_texture(surface, frame)

            pts = surface["points"]
            opacity = surface["opacity"]
            is_selected = (i == self.selected_surface_index)

            if tex:
                glColor4f(1, 1, 1, opacity)
                glBindTexture(GL_TEXTURE_2D, tex)
                glEnable(GL_TEXTURE_2D)

                glBegin(GL_QUADS)
                glTexCoord2f(0, 0)
                glVertex2f(pts[0][0], self.canvas_height - pts[0][1])
                glTexCoord2f(1, 0)
                glVertex2f(pts[1][0], self.canvas_height - pts[1][1])
                glTexCoord2f(1, 1)
                glVertex2f(pts[2][0], self.canvas_height - pts[2][1])
                glTexCoord2f(0, 1)
                glVertex2f(pts[3][0], self.canvas_height - pts[3][1])
                glEnd()
            # else:
            #     # In Fullscreen, we don't show the placeholder grey quad
            #     # to ensure "hidden" surfaces are truly invisible (transparent).
            #     pass

            if self.edit_mode and self.show_controls:
                glDisable(GL_TEXTURE_2D)

                # Outline
                glLineWidth(2.0)
                if is_selected:
                    glColor3f(0.0, 1.0, 0.0)
                else:
                    glColor3f(0.0, 1.0, 1.0)

                glBegin(GL_LINE_LOOP)
                for p in pts:
                    glVertex2f(p[0], self.canvas_height - p[1])
                glEnd()

                # Handles
                glPointSize(10.0 if is_selected else 7.0)
                glBegin(GL_POINTS)
                glColor3f(1.0, 1.0, 0.0)
                for p in pts:
                    glVertex2f(p[0], self.canvas_height - p[1])
                glEnd()

                glEnable(GL_TEXTURE_2D)
