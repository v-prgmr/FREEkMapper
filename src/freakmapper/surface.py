import moderngl
import numpy as np

class Surface:
    def __init__(self, ctx):
        self.ctx = ctx
        self.texture = None
        # Initial corners (NDC)
        self.corners = np.array([
            [-0.5, -0.5], # Bottom-Left
            [ 0.5, -0.5], # Bottom-Right
            [-0.5,  0.5], # Top-Left
            [ 0.5,  0.5], # Top-Right
        ], dtype='f4')

        # Texture coordinates
        self.tex_coords = np.array([
            [0.0, 0.0],
            [1.0, 0.0],
            [0.0, 1.0],
            [1.0, 1.0],
        ], dtype='f4')

        try:
            self.prog = self.ctx.program(
                vertex_shader=open('shaders/vertex.glsl').read(),
                fragment_shader=open('shaders/fragment.glsl').read(),
            )
        except moderngl.Error as e:
            print("Shader compilation error:", e)
            # Print shader source for debugging
            print("Vertex Shader:")
            print(open('shaders/vertex.glsl').read())
            print("Fragment Shader:")
            print(open('shaders/fragment.glsl').read())
            raise e

        self.vbo = self.ctx.buffer(reserve=self.corners.nbytes + self.tex_coords.nbytes)
        self._update_buffer()

        self.vao = self.ctx.vertex_array(
            self.prog,
            [
                (self.vbo, '2f 2f', 'in_vert', 'in_texcoord'),
            ],
        )

    def _update_buffer(self):
        # Interleave or just concatenate? 
        # The VAO format is '2f 2f', implying interleaved or separate attributes?
        # My previous code used a single array. Let's stick to interleaved for simplicity in one buffer.
        # Vertices: x, y, u, v
        data = np.hstack([self.corners, self.tex_coords]).astype('f4')
        self.vbo.write(data.tobytes())

    def set_corner(self, index, x, y):
        # index: 0=BL, 1=BR, 2=TL, 3=TR
        self.corners[index] = [x, y]
        self._update_buffer()

    def get_closest_corner(self, x, y, threshold=0.1):
        # Find the corner closest to (x, y) in NDC
        dists = np.linalg.norm(self.corners - np.array([x, y]), axis=1)
        min_idx = np.argmin(dists)
        if dists[min_idx] < threshold:
            return min_idx
        return None

    def render(self, texture):
        tex = texture if texture else self.texture
        if tex:
            tex.use(location=0)
        self.vao.render(moderngl.TRIANGLE_STRIP)
