#version 330

uniform sampler2D texture0;

in vec2 v_texcoord;
out vec4 f_color;

void main() {
    f_color = texture(texture0, v_texcoord);
}
