"""
Grasshopper Python 3 Script component: view-corridor-constrained massing.

Paste this into a GhPython / "Script" component in Grasshopper (Rhino 8,
Python 3 mode). It shares the exact same core algorithm as
view_corridor_massing.py in this repo (half-plane clipping, axis
derivation, per-floor sloped-ceiling trim), verified standalone with
rhino3dm before being adapted here, so the geometric logic is not
being trusted for the first time inside the GH canvas.

Inputs (add as component input parameters, matching these names):
  corridor_poly   Point3d list  - the view corridor's real polygon vertices,
                                   already in local project coordinates
                                   (e.g. from the City's Open Data GeoJSON,
                                   reprojected upstream of this component)
  site_poly       Point3d list  - the candidate site boundary
  setback         Number        - uniform setback distance (m)
  base_elev       Number        - PLACEHOLDER geodetic elevation at the
                                   corridor apex (m); confirm the real
                                   figure with the City for an actual site
  slope           Number        - PLACEHOLDER rate of ceiling rise per
                                   meter of distance from the apex
  floor_height    Number        - floor-to-floor height (m)
  max_floors      Integer       - candidate ceiling on floor count from
                                   zoning alone, before the corridor is applied

Outputs:
  floor_breps     Brep list     - one extruded solid per buildable floor
  floor_count     Integer       - number of floors actually built
  apex_pt         Point3d       - the derived corridor apex, for a sanity check
"""

import math
import Rhino.Geometry as rg
import ghpythonlib.treehelpers as th


def clip_halfplane(poly, ox, oy, nx, ny):
    if not poly:
        return []
    out = []
    n = len(poly)
    for i in range(n):
        curr, prev = poly[i], poly[i - 1]
        curr_in = (curr[0] - ox) * nx + (curr[1] - oy) * ny >= -1e-9
        prev_in = (prev[0] - ox) * nx + (prev[1] - oy) * ny >= -1e-9
        if curr_in:
            if not prev_in:
                out.append(_intersect(prev, curr, ox, oy, nx, ny))
            out.append(curr)
        elif prev_in:
            out.append(_intersect(prev, curr, ox, oy, nx, ny))
    return out


def _intersect(p1, p2, ox, oy, nx, ny):
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    denom = dx * nx + dy * ny
    t = ((ox - p1[0]) * nx + (oy - p1[1]) * ny) / denom if denom != 0 else 0.0
    t = max(0.0, min(1.0, t))
    return (p1[0] + dx * t, p1[1] + dy * t)


def _signed_area(poly):
    a = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return a / 2


def offset_polygon_inward(poly, setback):
    inward_sign = 1 if _signed_area(poly) < 0 else -1
    current = list(poly)
    n = len(poly)
    for i in range(n):
        if not current:
            break
        a, b = poly[i], poly[(i + 1) % n]
        dx, dy = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dy)
        if length < 1e-9:
            continue
        dx, dy = dx / length, dy / length
        nx, ny = inward_sign * dy, -inward_sign * dx
        ox, oy = a[0] + nx * setback, a[1] + ny * setback
        current = clip_halfplane(current, ox, oy, nx, ny)
    return current


def derive_axis(poly):
    n = len(poly)
    best_i, best_score = 0, float("inf")
    for i in range(n):
        others = [poly[j] for j in range(n) if j != i]
        d = [math.hypot(poly[i][0] - o[0], poly[i][1] - o[1]) for o in others]
        score = (abs(d[0] - d[1]) if len(d) == 2 else min(d)) - 0.001 * sum(d)
        if score < best_score:
            best_score, best_i = score, i
    apex = poly[best_i]
    far_pts = [poly[j] for j in range(n) if j != best_i]
    far_mid = (sum(p[0] for p in far_pts) / len(far_pts), sum(p[1] for p in far_pts) / len(far_pts))
    dx, dy = far_mid[0] - apex[0], far_mid[1] - apex[1]
    length = math.hypot(dx, dy)
    return apex, (dx / length, dy / length)


def extrude_polygon_brep(poly_xy, z0, z1):
    pts = [rg.Point3d(x, y, z0) for x, y in poly_xy]
    pts.append(pts[0])
    base_curve = rg.PolylineCurve(pts)
    base_plane = rg.Plane(rg.Point3d(0, 0, z0), rg.Vector3d.ZAxis)
    base_brep = rg.Brep.CreatePlanarBreps(base_curve, 0.001)
    if not base_brep:
        return None
    extrusion = rg.Extrusion.Create(base_curve, z1 - z0, True)
    return extrusion.ToBrep() if extrusion else None


def run(corridor_poly, site_poly, setback, base_elev, slope, floor_height, max_floors):
    corridor_xy = [(p.X, p.Y) for p in corridor_poly]
    site_xy = [(p.X, p.Y) for p in site_poly]

    apex, axis = derive_axis(corridor_xy)
    zoning_footprint = offset_polygon_inward(site_xy, setback)

    floor_breps = []
    for i in range(max_floors):
        z0 = base_elev + i * floor_height
        z1 = base_elev + (i + 1) * floor_height
        min_dist = (z1 - base_elev) / slope
        ox, oy = apex[0] + axis[0] * min_dist, apex[1] + axis[1] * min_dist
        clipped = clip_halfplane(zoning_footprint, ox, oy, axis[0], axis[1])
        if len(clipped) < 3:
            break
        brep = extrude_polygon_brep(clipped, z0, z1)
        if brep:
            floor_breps.append(brep)

    apex_pt = rg.Point3d(apex[0], apex[1], base_elev)
    return floor_breps, len(floor_breps), apex_pt


# Grasshopper wiring: uncomment when pasted into an actual GhPython
# component, with input parameters matching the names in the docstring.
#
# floor_breps, floor_count, apex_pt = run(
#     corridor_poly, site_poly, setback, base_elev, slope, floor_height, max_floors
# )
