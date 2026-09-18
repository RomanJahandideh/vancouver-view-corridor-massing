"""
A Python-rendered static preview of the view-corridor-trimmed massing,
for documentation. This is a matplotlib illustration of the same
geometry written to the .3dm file, not a screenshot from Rhino (this
environment doesn't have Rhino/Grasshopper installed to render from).
Run with: python preview_render.py  (requires matplotlib)
"""
import rhino3dm
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

m = rhino3dm.File3dm.Read("vancouver_viewcone_massing.3dm")

fig = plt.figure(figsize=(11, 8), facecolor="#0b0d10")
ax = fig.add_subplot(111, projection="3d")
ax.set_facecolor("#0b0d10")

for obj in m.Objects:
    geo = obj.Geometry
    if geo.ObjectType == rhino3dm.ObjectType.Mesh:
        verts = [(v.X, v.Y, v.Z) for v in geo.Vertices]
        faces = []
        for f in geo.Faces:
            if len(f) == 4 and f[2] != f[3]:
                faces.append([verts[f[0]], verts[f[1]], verts[f[2]], verts[f[3]]])
            else:
                faces.append([verts[f[0]], verts[f[1]], verts[f[2]]])
        pc = Poly3DCollection(faces, facecolor="#e0d8d0", edgecolor="#2a2320", linewidths=0.3, alpha=0.95)
        ax.add_collection3d(pc)
    elif geo.ObjectType == rhino3dm.ObjectType.Curve:
        pts = geo.ToNurbsCurve()
        n = 60
        xs, ys, zs = [], [], []
        for i in range(n + 1):
            t = pts.Domain.T0 + (pts.Domain.T1 - pts.Domain.T0) * i / n
            p = pts.PointAt(t)
            xs.append(p.X); ys.append(p.Y); zs.append(p.Z)
        ax.plot(xs, ys, zs, color="#e07b5a", linewidth=1.2)

all_x = [v.X for o in m.Objects for v in (o.Geometry.Vertices if o.Geometry.ObjectType == rhino3dm.ObjectType.Mesh else [])]
all_y = [v.Y for o in m.Objects for v in (o.Geometry.Vertices if o.Geometry.ObjectType == rhino3dm.ObjectType.Mesh else [])]
all_z = [v.Z for o in m.Objects for v in (o.Geometry.Vertices if o.Geometry.ObjectType == rhino3dm.ObjectType.Mesh else [])]
ax.set_xlim(min(all_x) - 30, max(all_x) + 30)
ax.set_ylim(min(all_y) - 30, max(all_y) + 60)
ax.set_zlim(0, max(all_z) + 20)
ax.set_box_aspect([1, 1, 0.7])
ax.view_init(elev=22, azim=-58)
ax.set_axis_off()

fig.savefig("preview.png", dpi=150, facecolor="#0b0d10", bbox_inches="tight")
print("Wrote preview.png")
