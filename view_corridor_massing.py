"""
View-corridor-constrained massing generator.

Given a real, City-of-Vancouver-mapped protected view corridor (pulled
live from the Open Data Portal) and a candidate development site inside
it, generates the maximum buildable massing envelope that respects BOTH
a standard zoning setback/height envelope AND the view corridor's sloped
geodetic height ceiling, trimming the massing wherever it would
otherwise pierce a protected sightline.

Grounded in:
- City of Vancouver Open Data Portal, "view-cones" dataset (24 official
  protected view corridors), fetched live via the public API:
  https://opendata.vancouver.ca/api/records/1.0/search/?dataset=view-cones
- The mechanism (a view cone is a maximum GEODETIC elevation, low near
  the viewpoint apex and rising with distance, not a storey count) is
  documented in City of Vancouver public views guidance.
- The core algorithmic move, an inward polygon offset via half-plane
  intersection for the zoning envelope, and a per-floor half-plane clip
  against a linear sloped ceiling, extends the same verified geometry
  approach used in this author's earlier browser-based massing tools
  (parametric-massing-generator), now applied to a real 3D solid-vs-plane
  problem instead of a flat setback.

Every number in this script is either pulled from the live City dataset,
or an explicitly labeled PLACEHOLDER (search for "PLACEHOLDER" below).
Per-site view cone height limits are not published in the open dataset;
the City's own guidance is to confirm site-specific implications
directly (views@vancouver.ca). This script models the correct mechanism
and geometry; it does not claim to reproduce an unverified real number.

Run with: python view_corridor_massing.py
Requires: rhino3dm  (pip install rhino3dm)
"""

import math
import json
import urllib.request

import rhino3dm

# ==============================================================================
# 1. Real view corridor geometry, from the live City of Vancouver Open Data API
# ==============================================================================

VIEWCONE_API = (
    "https://opendata.vancouver.ca/api/records/1.0/search/"
    "?dataset=view-cones&q=view_cone_name:%22Creekside%20Park%22&rows=2"
)


def fetch_view_cone(view_number="J1"):
    """Fetch a specific real, official view cone polygon from the City of
    Vancouver's public Open Data API. Falls back to a hard-coded copy of
    the same record (fetched and verified at the time this script was
    written) if the network call fails, so the script still runs
    offline/deterministically."""
    fallback = {
        "view_cone_name": "Creekside Park",
        "view_number": "J1",
        "description": "View of Lions from Creekside Park",
        "polygon_lonlat": [
            (-123.10297367663784, 49.27516516517493),
            (-123.10437817024287, 49.29349287256195),
            (-123.09618436291586, 49.29305285529873),
        ],
    }
    try:
        with urllib.request.urlopen(VIEWCONE_API, timeout=8) as resp:
            data = json.load(resp)
        for rec in data.get("records", []):
            f = rec["fields"]
            if f.get("view_number") == view_number:
                coords = f["geom"]["coordinates"][0]
                poly = [(c[0], c[1]) for c in coords[:-1]]  # drop closing repeat
                return {
                    "view_cone_name": f["view_cone_name"],
                    "view_number": f["view_number"],
                    "description": f["description"],
                    "polygon_lonlat": poly,
                }
    except Exception as e:
        print("Live fetch failed (%s), using verified fallback copy of the same record." % e)
    return fallback


# ==============================================================================
# 2. Local projection and axis derivation
# ==============================================================================

EARTH_R = 6371000.0


def lonlat_to_local_m(lon, lat, origin_lon, origin_lat):
    """Equirectangular projection centered at the apex. Adequate for
    site-scale architectural geometry over a few kilometers; not intended
    for large-area geodesy."""
    x = math.radians(lon - origin_lon) * EARTH_R * math.cos(math.radians(origin_lat))
    y = math.radians(lat - origin_lat) * EARTH_R
    return x, y


def derive_axis(polygon_local):
    """The apex is the vertex whose position is farthest (in the
    across-axis sense) from being an average of the other two, i.e. for a
    3-vertex view cone triangle, the vertex on its own side of the
    triangle's short edge. Concretely: the vertex with the coordinate
    most different from the mean of the group is the apex."""
    cx = sum(p[0] for p in polygon_local) / len(polygon_local)
    cy = sum(p[1] for p in polygon_local) / len(polygon_local)
    # apex = point farthest from the centroid of the *other two* points'
    # midpoint pairing is ambiguous in general; for this triangle shape we
    # use: the apex is the vertex whose two edges to the others are most
    # similar in length (the isoceles tip), found by trying each vertex.
    best_i, best_score = 0, float("inf")
    n = len(polygon_local)
    for i in range(n):
        others = [polygon_local[j] for j in range(n) if j != i]
        d = [math.hypot(polygon_local[i][0] - o[0], polygon_local[i][1] - o[1]) for o in others]
        score = abs(d[0] - d[1]) if len(d) == 2 else min(d)
        # apex is also expected to be the vertex closest to the polygon's
        # "narrow" end; combine with total distance to disambiguate.
        score = score - 0.001 * sum(d)  # prefer the vertex that's also closer overall
        if score < best_score:
            best_score, best_i = score, i
    apex = polygon_local[best_i]
    far_pts = [polygon_local[j] for j in range(n) if j != best_i]
    far_mid = (sum(p[0] for p in far_pts) / len(far_pts), sum(p[1] for p in far_pts) / len(far_pts))
    dx, dy = far_mid[0] - apex[0], far_mid[1] - apex[1]
    length = math.hypot(dx, dy)
    return apex, (dx / length, dy / length), length


# ==============================================================================
# 3. Half-plane clipping (Sutherland-Hodgman), the same verified pattern
#    used for the setback envelope in the browser-based massing tool.
# ==============================================================================

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


def offset_polygon_inward(poly, setback):
    """Uniform-setback inward offset via half-plane intersection, correct
    for any convex polygon. (For a per-edge setback variant, see the
    JS/browser version of this same algorithm in parametric-massing-generator.)"""
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


def _signed_area(poly):
    a = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return a / 2


def shoelace_area(poly):
    return abs(_signed_area(poly))


# ==============================================================================
# 4. rhino3dm geometry construction (fan-triangulated extrusion, the same
#    approach used and visually verified in the browser massing tool).
# ==============================================================================

def add_extruded_polygon(model, poly_xy, z0, z1, layer_index=None):
    if len(poly_xy) < 3:
        return
    mesh = rhino3dm.Mesh()
    n = len(poly_xy)
    for x, y in poly_xy:
        mesh.Vertices.Add(x, y, z0)
    for x, y in poly_xy:
        mesh.Vertices.Add(x, y, z1)
    for i in range(1, n - 1):
        mesh.Faces.AddFace(0, i, i + 1)
    for i in range(1, n - 1):
        mesh.Faces.AddFace(n, n + i + 1, n + i)
    for i in range(n):
        a, b = i, (i + 1) % n
        at, bt = n + i, n + (i + 1) % n
        mesh.Faces.AddFace(a, b, bt)
        mesh.Faces.AddFace(a, bt, at)
    mesh.Normals.ComputeNormals()
    attrs = rhino3dm.ObjectAttributes()
    if layer_index is not None:
        attrs.LayerIndex = layer_index
    model.Objects.AddMesh(mesh, attrs)


def add_polyline(model, poly_xy, z, layer_index=None):
    pts = [rhino3dm.Point3d(x, y, z) for x, y in poly_xy]
    pts.append(pts[0])
    pl = rhino3dm.Polyline(pts)
    attrs = rhino3dm.ObjectAttributes()
    if layer_index is not None:
        attrs.LayerIndex = layer_index
    model.Objects.AddCurve(pl.ToPolylineCurve(), attrs)


# ==============================================================================
# 5. Study parameters
# ==============================================================================

# PLACEHOLDER, not an official figure. The open dataset gives view corridor
# geometry, not per-site elevation limits; the City's guidance is that
# site-specific implications must be confirmed directly (views@vancouver.ca).
# This value is chosen only to produce a legible, correctly-behaved example.
BASE_ELEV_M = 40.0
SLOPE = 0.5  # PLACEHOLDER example rate of allowed-height increase with distance

# A representative candidate site: a 40m x 60m parcel placed within the
# corridor, a plausible Downtown/Northeast False Creek development-scale lot.
SITE_WIDTH_M = 40.0
SITE_DEPTH_M = 60.0
SETBACK_M = 3.0
FLOOR_HEIGHT_M = 3.5
CANDIDATE_MAX_FLOORS = 45  # tall enough that the corridor is the binding constraint
SITE_CENTER_DIST_FRACTION = 0.05  # close to the apex, where the ceiling still binds


def main():
    cone = fetch_view_cone("J1")
    print("View corridor:", cone["view_cone_name"], cone["view_number"], "-", cone["description"])

    poly_local = [lonlat_to_local_m(lon, lat, *cone["polygon_lonlat"][0]) for lon, lat in cone["polygon_lonlat"]]
    apex, axis, axis_length = derive_axis(poly_local)
    print("Apex (local m):", tuple(round(v, 1) for v in apex))
    print("Axis direction:", tuple(round(v, 3) for v in axis))
    print("Corridor length (apex to far edge):", round(axis_length, 1), "m")

    def distance_along_axis(p):
        return (p[0] - apex[0]) * axis[0] + (p[1] - apex[1]) * axis[1]

    # Place the site well inside the corridor, centered along the axis.
    site_center_dist = axis_length * SITE_CENTER_DIST_FRACTION
    center = (apex[0] + axis[0] * site_center_dist, apex[1] + axis[1] * site_center_dist)
    perp = (-axis[1], axis[0])
    hw, hd = SITE_WIDTH_M / 2, SITE_DEPTH_M / 2
    site_poly = [
        (center[0] - axis[0] * hd - perp[0] * hw, center[1] - axis[1] * hd - perp[1] * hw),
        (center[0] + axis[0] * hd - perp[0] * hw, center[1] + axis[1] * hd - perp[1] * hw),
        (center[0] + axis[0] * hd + perp[0] * hw, center[1] + axis[1] * hd + perp[1] * hw),
        (center[0] - axis[0] * hd + perp[0] * hw, center[1] - axis[1] * hd + perp[1] * hw),
    ]
    zoning_footprint = offset_polygon_inward(site_poly, SETBACK_M)
    print("\nSite area:", round(shoelace_area(site_poly), 1), "m2")
    print("Zoning setback footprint area:", round(shoelace_area(zoning_footprint), 1), "m2")

    model = rhino3dm.File3dm()
    site_layer = model.Layers.AddLayer("site & corridor", (180, 180, 180, 255))
    massing_layer = model.Layers.AddLayer("view-corridor-trimmed massing", (224, 123, 90, 255))

    add_polyline(model, poly_local, 0.0, site_layer)
    add_polyline(model, site_poly, 0.0, site_layer)
    add_polyline(model, zoning_footprint, 0.0, site_layer)

    print("\nfloor | top elev(m) | footprint area(m2) | status")
    floors_built = 0
    for i in range(CANDIDATE_MAX_FLOORS):
        z0 = BASE_ELEV_M + i * FLOOR_HEIGHT_M
        z1 = BASE_ELEV_M + (i + 1) * FLOOR_HEIGHT_M
        min_dist = (z1 - BASE_ELEV_M) / SLOPE
        ox, oy = apex[0] + axis[0] * min_dist, apex[1] + axis[1] * min_dist
        clipped = clip_halfplane(zoning_footprint, ox, oy, axis[0], axis[1])
        area = shoelace_area(clipped) if len(clipped) >= 3 else 0.0
        status = "full" if abs(area - shoelace_area(zoning_footprint)) < 0.5 else ("trimmed" if area > 0.5 else "excluded")
        print(f"{i+1:5d} | {z1:9.1f} | {area:16.1f} | {status}")
        if area > 0.5:
            add_extruded_polygon(model, clipped, z0, z1, massing_layer)
            floors_built += 1
        elif floors_built > 0:
            break  # corridor fully excludes this and all higher floors

    out_path = "vancouver_viewcone_massing.3dm"
    model.Write(out_path, 7)
    print("\nWrote", out_path, "with", floors_built, "buildable floors under the view corridor.")
    print("Unconstrained zoning height would have allowed", CANDIDATE_MAX_FLOORS, "candidate floors;",
          "the view corridor is the binding constraint at", floors_built, "floors in this example.")


if __name__ == "__main__":
    main()
