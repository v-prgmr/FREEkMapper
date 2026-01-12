import moderngl
from .surface import Surface

class Engine:
    def __init__(self, ctx):
        self.ctx = ctx
        self.surfaces = []
        self.active_surface = None

    def add_surface(self):
        surface = Surface(self.ctx)
        self.surfaces.append(surface)
        self.active_surface = surface

    def set_active_surface(self, index):
        if 0 <= index < len(self.surfaces):
            self.active_surface = self.surfaces[index]

    def render(self, draw_overlays=True):
        self.ctx.clear(0.0, 0.0, 0.0)
        # Render surfaces
        for surface in self.surfaces:
            surface.render(None)
            
        # Draw control points if requested (Editor only)
        if draw_overlays and self.active_surface:
            # We could draw small quads or points at corners here
            # For now, let's just keep it simple. 
            # If we had visual helpers, we would skip them here.
            pass

    def handle_mouse_drag(self, x, y, width, height):
        # Convert screen coordinates to NDC
        ndc_x = (x / width) * 2 - 1
        ndc_y = -((y / height) * 2 - 1) # Flip Y for OpenGL

        if self.active_surface:
            if not hasattr(self, 'dragging_corner'):
                self.dragging_corner = None
            
            if self.dragging_corner is not None:
                self.active_surface.set_corner(self.dragging_corner, ndc_x, ndc_y)
            
    def handle_mouse_down(self, x, y, width, height):
        ndc_x = (x / width) * 2 - 1
        ndc_y = -((y / height) * 2 - 1)
        
        if self.active_surface:
            corner = self.active_surface.get_closest_corner(ndc_x, ndc_y)
            if corner is not None:
                self.dragging_corner = corner

    def handle_mouse_up(self):
        self.dragging_corner = None
