import cv2
import moderngl
from PIL import Image
import numpy as np

class MediaLoader:
    def __init__(self, ctx):
        self.ctx = ctx

    def load_image(self, path):
        img = Image.open(path).convert('RGB')
        # Ensure no PBO is bound (Dear PyGui might leave one bound)
        self.ctx.pixel_unpack_buffer = None
        # Use alignment=1 for safety
        texture = self.ctx.texture(img.size, 3, img.tobytes(), alignment=1)
        texture.build_mipmaps()
        return texture

    def load_video(self, path):
        return VideoTexture(self.ctx, path)

class VideoTexture:
    def __init__(self, ctx, path):
        self.ctx = ctx
        self.cap = cv2.VideoCapture(path)
        self.width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Ensure no PBO is bound
        self.ctx.pixel_unpack_buffer = None
        
        self.texture = self.ctx.texture((self.width, self.height), 3)
        self.texture.repeat_x = False
        self.texture.repeat_y = False

    def update(self):
        ret, frame = self.cap.read()
        if not ret:
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
        
        if ret:
            # OpenCV is BGR, OpenGL is RGB
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            self.texture.write(frame.tobytes())

    def use(self, location=0):
        self.update()
        self.texture.use(location=location)
