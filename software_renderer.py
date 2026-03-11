#!/usr/bin/env python3
"""software_renderer - 3D software renderer (wireframe + filled triangles, z-buffer).

Usage: python software_renderer.py [--width W] [--height H] [--wireframe]
"""
import sys, math

class Vec3:
    __slots__ = ('x','y','z')
    def __init__(self, x=0, y=0, z=0): self.x=x; self.y=y; self.z=z
    def __add__(s, o): return Vec3(s.x+o.x, s.y+o.y, s.z+o.z)
    def __sub__(s, o): return Vec3(s.x-o.x, s.y-o.y, s.z-o.z)
    def __mul__(s, t): return Vec3(s.x*t, s.y*t, s.z*t)
    def dot(s, o): return s.x*o.x+s.y*o.y+s.z*o.z
    def cross(s, o): return Vec3(s.y*o.z-s.z*o.y, s.z*o.x-s.x*o.z, s.x*o.y-s.y*o.x)
    def norm(s): l=math.sqrt(s.dot(s)); return Vec3(s.x/l,s.y/l,s.z/l) if l>1e-10 else Vec3()
    def __repr__(s): return f"({s.x:.2f},{s.y:.2f},{s.z:.2f})"

def mat4_perspective(fov, aspect, near, far):
    f = 1/math.tan(fov/2)
    return [[f/aspect,0,0,0],[0,f,0,0],[0,0,(far+near)/(near-far),-1],
            [0,0,2*far*near/(near-far),0]]

def mat4_lookat(eye, center, up):
    f = (center-eye).norm(); s = f.cross(up).norm(); u = s.cross(f)
    return [[s.x,u.x,-f.x,0],[s.y,u.y,-f.y,0],[s.z,u.z,-f.z,0],
            [-s.dot(eye),-u.dot(eye),f.dot(eye),1]]

def mat_mul(a, b):
    r = [[0]*4 for _ in range(4)]
    for i in range(4):
        for j in range(4):
            for k in range(4):
                r[i][j] += a[i][k]*b[k][j]
    return r

def transform(m, v):
    x=m[0][0]*v.x+m[1][0]*v.y+m[2][0]*v.z+m[3][0]
    y=m[0][1]*v.x+m[1][1]*v.y+m[2][1]*v.z+m[3][1]
    z=m[0][2]*v.x+m[1][2]*v.y+m[2][2]*v.z+m[3][2]
    w=m[0][3]*v.x+m[1][3]*v.y+m[2][3]*v.z+m[3][3]
    if abs(w) > 1e-10: x/=w; y/=w; z/=w
    return Vec3(x, y, z)

class Framebuffer:
    def __init__(self, w, h):
        self.w=w; self.h=h
        self.color = [[' ']*w for _ in range(h)]
        self.zbuf = [[float('inf')]*w for _ in range(h)]
        self.shades = " .:-=+*#%@"

    def set_pixel(self, x, y, z, shade=1.0):
        ix, iy = int(x), int(y)
        if 0<=ix<self.w and 0<=iy<self.h and z < self.zbuf[iy][ix]:
            self.zbuf[iy][ix] = z
            idx = max(0, min(len(self.shades)-1, int(shade*(len(self.shades)-1))))
            self.color[iy][ix] = self.shades[idx]

    def line(self, x0, y0, z0, x1, y1, z1, shade=0.8):
        dx=abs(x1-x0); dy=abs(y1-y0)
        steps=max(int(max(dx,dy)),1)
        for i in range(steps+1):
            t=i/steps
            x=x0+(x1-x0)*t; y=y0+(y1-y0)*t; z=z0+(z1-z0)*t
            self.set_pixel(x, y, z, shade)

    def triangle(self, v0, v1, v2, shade=0.7):
        """Rasterize filled triangle with scanline."""
        pts = sorted([(v0.x,v0.y,v0.z),(v1.x,v1.y,v1.z),(v2.x,v2.y,v2.z)], key=lambda p:p[1])
        for y in range(max(0,int(pts[0][1])), min(self.h, int(pts[2][1])+1)):
            xs = []
            for i in range(3):
                j=(i+1)%3
                y0,y1=pts[i][1],pts[j][1]
                if (y0<=y<y1) or (y1<=y<y0):
                    t=(y-y0)/(y1-y0) if abs(y1-y0)>1e-10 else 0
                    x=pts[i][0]+(pts[j][0]-pts[i][0])*t
                    z=pts[i][2]+(pts[j][2]-pts[i][2])*t
                    xs.append((x,z))
            if len(xs)>=2:
                xs.sort()
                for x in range(max(0,int(xs[0][0])), min(self.w, int(xs[-1][0])+1)):
                    t=(x-xs[0][0])/(xs[-1][0]-xs[0][0]) if abs(xs[-1][0]-xs[0][0])>1e-10 else 0
                    z=xs[0][1]+(xs[-1][1]-xs[0][1])*t
                    self.set_pixel(x, y, z, shade)

    def render(self):
        return "\n".join("".join(row) for row in self.color)

def cube_mesh():
    v = [Vec3(-1,-1,-1),Vec3(1,-1,-1),Vec3(1,1,-1),Vec3(-1,1,-1),
         Vec3(-1,-1,1),Vec3(1,-1,1),Vec3(1,1,1),Vec3(-1,1,1)]
    faces = [(0,1,2,3),(4,5,6,7),(0,1,5,4),(2,3,7,6),(0,3,7,4),(1,2,6,5)]
    tris = []
    for f in faces:
        tris.append((f[0],f[1],f[2]))
        tris.append((f[0],f[2],f[3]))
    return v, tris

def main():
    w, h, wireframe = 70, 30, False
    for i,a in enumerate(sys.argv[1:]):
        if a=="--width" and i+2<=len(sys.argv[1:]): w=int(sys.argv[i+2])
        if a=="--height" and i+2<=len(sys.argv[1:]): h=int(sys.argv[i+2])
        if a=="--wireframe": wireframe=True

    print(f"=== 3D Software Renderer ({w}x{h}) ===\n")
    fb = Framebuffer(w, h)
    verts, tris = cube_mesh()

    # Rotate cube
    angle = 0.7
    ca, sa = math.cos(angle), math.sin(angle)
    rot_verts = []
    for v in verts:
        x = v.x*ca - v.z*sa; z = v.x*sa + v.z*ca
        y = v.y*math.cos(0.4) - z*math.sin(0.4)
        z2 = v.y*math.sin(0.4) + z*math.cos(0.4)
        rot_verts.append(Vec3(x, y, z2))

    view = mat4_lookat(Vec3(0,0,5), Vec3(0,0,0), Vec3(0,1,0))
    proj = mat4_perspective(math.pi/4, w/h, 0.1, 100)
    mvp = mat_mul(view, proj)

    # Project vertices
    screen = []
    for v in rot_verts:
        p = transform(mvp, v)
        sx = (p.x+1)*w/2; sy = (1-p.y)*h/2
        screen.append(Vec3(sx, sy, p.z))

    light = Vec3(0.5, 1, 0.8).norm()
    for i0,i1,i2 in tris:
        v0,v1,v2 = rot_verts[i0],rot_verts[i1],rot_verts[i2]
        normal = (v1-v0).cross(v2-v0).norm()
        ndotl = max(0.1, normal.dot(light))
        s0,s1,s2 = screen[i0],screen[i1],screen[i2]
        if wireframe:
            fb.line(s0.x,s0.y,s0.z,s1.x,s1.y,s1.z,ndotl)
            fb.line(s1.x,s1.y,s1.z,s2.x,s2.y,s2.z,ndotl)
            fb.line(s2.x,s2.y,s2.z,s0.x,s0.y,s0.z,ndotl)
        else:
            fb.triangle(s0,s1,s2,ndotl)
    print(fb.render())

if __name__ == "__main__":
    main()
