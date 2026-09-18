"""
Standalone correctness check for the view-corridor massing algorithm,
before it goes into any deliverable script. Run with: python geom_verify.py
"""
import math

# ---- Real Creekside Park view cone (view number J1/J2), City of Vancouver
# Open Data Portal, dataset "view-cones", fetched live via the public API:
# https://opendata.vancouver.ca/api/records/1.0/search/?dataset=view-cones
# Polygon (lon, lat): apex is the vertex with the distinctly different
# latitude (south, near the viewpoint); the far edge is the two vertices
# sharing the northern latitude (toward the mountains).
CONE_POLY_LONLAT = [
    (-123.10297367663784, 49.27516516517493),  # apex (viewpoint side)
    (-123.10437817024287, 49.29349287256195),  # far edge, west
    (-123.09618436291586, 49.29305285529873),  # far edge, east
]

def lonlat_to_local_m(lon, lat, origin_lon, origin_lat):
    """Equirectangular projection centered at origin, adequate at this
    scale (a few km) for site-scale architectural geometry, not for
    large-area geodesy."""
    R = 6371000.0
    x = math.radians(lon - origin_lon) * R * math.cos(math.radians(origin_lat))
    y = math.radians(lat - origin_lat) * R
    return x, y

apex_lon, apex_lat = CONE_POLY_LONLAT[0]
cone_local = [lonlat_to_local_m(lon, lat, apex_lon, apex_lat) for lon, lat in CONE_POLY_LONLAT]
apex = cone_local[0]
far_mid = ((cone_local[1][0] + cone_local[2][0]) / 2, (cone_local[1][1] + cone_local[2][1]) / 2)

print("Apex (local m):", apex)
print("Far edge midpoint (local m):", far_mid)
dist_apex_to_far = math.hypot(far_mid[0] - apex[0], far_mid[1] - apex[1])
print("Distance apex -> far edge midpoint: %.1f m" % dist_apex_to_far)

# Axis direction (unit vector) from apex toward the far edge
axis_dx = far_mid[0] - apex[0]
axis_dy = far_mid[1] - apex[1]
axis_len = math.hypot(axis_dx, axis_dy)
axis = (axis_dx / axis_len, axis_dy / axis_len)

def distance_along_axis(p):
    return (p[0] - apex[0]) * axis[0] + (p[1] - apex[1]) * axis[1]

print("\ndistance_along_axis(apex) should be 0:", round(distance_along_axis(apex), 6))
print("distance_along_axis(far_mid) should be ~%.1f:" % dist_apex_to_far, round(distance_along_axis(far_mid), 1))

# ---- Sloped ceiling: PLACEHOLDER example rate, clearly not an official
# figure (the City's own guidance is that site-specific view cone height
# implications must be confirmed directly with views@vancouver.ca; the
# open dataset gives geometry, not per-site elevation limits). Using a
# representative rate for testing the geometry only.
BASE_ELEV_M = 40.0     # example geodetic elevation at the apex
SLOPE = 0.06            # example: +1m of allowed height per ~16.7m of distance

def height_limit(p):
    d = max(0.0, distance_along_axis(p))
    return BASE_ELEV_M + SLOPE * d

print("\nheight_limit(apex) = %.1f m (should equal BASE_ELEV_M)" % height_limit(apex))
print("height_limit(far_mid) = %.1f m (should be higher)" % height_limit(far_mid))
assert abs(height_limit(apex) - BASE_ELEV_M) < 1e-6
assert height_limit(far_mid) > height_limit(apex)
print("Sloped ceiling sanity check: PASS")

# ---- Half-plane clipping (Sutherland-Hodgman), re-verified fresh in
# Python rather than assumed to carry over correctly from the earlier
# JavaScript version.
def clip_halfplane(poly, ox, oy, nx, ny):
    if not poly:
        return []
    out = []
    n = len(poly)
    for i in range(n):
        curr = poly[i]
        prev = poly[i - 1]
        curr_in = (curr[0] - ox) * nx + (curr[1] - oy) * ny >= -1e-9
        prev_in = (prev[0] - ox) * nx + (prev[1] - oy) * ny >= -1e-9
        if curr_in:
            if not prev_in:
                out.append(intersect(prev, curr, ox, oy, nx, ny))
            out.append(curr)
        elif prev_in:
            out.append(intersect(prev, curr, ox, oy, nx, ny))
    return out

def intersect(p1, p2, ox, oy, nx, ny):
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    denom = dx * nx + dy * ny
    t = ((ox - p1[0]) * nx + (oy - p1[1]) * ny) / denom if denom != 0 else 0
    t = max(0.0, min(1.0, t))
    return (p1[0] + dx * t, p1[1] + dy * t)

def shoelace_area(poly):
    a = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2

# Test: a 40m x 40m square, clip to keep only points with x >= 10
# (i.e. inward normal = (1,0), origin at x=10). Expect a 30x40 rectangle.
square = [(0, 0), (40, 0), (40, 40), (0, 40)]
clipped = clip_halfplane(square, 10, 0, 1, 0)
area = shoelace_area(clipped)
print("\nHalf-plane clip test: 40x40 square, x>=10 -> area (expect 1200):", area)
assert abs(area - 1200) < 1e-6, "Half-plane clip FAILED"
print("Half-plane clip test: PASS")

# ---- Floor-by-floor trimming against the sloped ceiling: for a candidate
# footprint fully inside the cone polygon, at floor elevation Z, keep only
# the region where height_limit(p) >= Z, i.e. distance_along_axis(p) >=
# (Z - BASE_ELEV_M) / SLOPE. This is a single half-plane clip per floor,
# valid because height_limit is linear in distance-along-axis.
def clip_floor_to_ceiling(poly_local, floor_z):
    min_dist = (floor_z - BASE_ELEV_M) / SLOPE
    # half-plane: keep points with distance_along_axis(p) >= min_dist
    # i.e. (p - apex).axis >= min_dist  =>  origin = apex + axis*min_dist, normal = axis
    ox = apex[0] + axis[0] * min_dist
    oy = apex[1] + axis[1] * min_dist
    return clip_halfplane(poly_local, ox, oy, axis[0], axis[1])

# A test footprint placed well inside the cone, spanning a range of
# distances from the apex so some floors get trimmed and some don't.
# Roughly centered along the axis at ~120m from the apex.
test_center = (apex[0] + axis[0] * 120, apex[1] + axis[1] * 120)
perp = (-axis[1], axis[0])  # perpendicular to axis
half_w, half_d = 15, 20
footprint = [
    (test_center[0] - axis[0]*half_d - perp[0]*half_w, test_center[1] - axis[1]*half_d - perp[1]*half_w),
    (test_center[0] + axis[0]*half_d - perp[0]*half_w, test_center[1] + axis[1]*half_d - perp[1]*half_w),
    (test_center[0] + axis[0]*half_d + perp[0]*half_w, test_center[1] + axis[1]*half_d + perp[1]*half_w),
    (test_center[0] - axis[0]*half_d + perp[0]*half_w, test_center[1] - axis[1]*half_d + perp[1]*half_w),
]
print("\nTest footprint distance-along-axis range:",
      round(min(distance_along_axis(p) for p in footprint), 1), "to",
      round(max(distance_along_axis(p) for p in footprint), 1))

floor_h = 3.5
n_candidate_floors = 20
print("\nfloor | z(m) | ceiling min-dist(m) | footprint area (m2)")
prev_area = None
areas = []
for i in range(n_candidate_floors):
    z = BASE_ELEV_M + (i + 1) * floor_h  # geodetic elevation of this floor's top
    clipped = clip_floor_to_ceiling(footprint, z)
    area = shoelace_area(clipped) if len(clipped) >= 3 else 0.0
    areas.append(area)
    min_dist = (z - BASE_ELEV_M) / SLOPE
    print(f"{i+1:5d} | {z:5.1f} | {min_dist:8.1f} | {area:8.1f}")

print("\nSanity checks:")
print("- Full footprint area (m2):", round(shoelace_area(footprint), 1))
print("- Lowest floor area should equal full footprint area (nothing trimmed yet near the base):",
      "PASS" if abs(areas[0] - shoelace_area(footprint)) < 1.0 else "FAIL")
print("- Areas should be non-increasing as floors get higher (monotonic trimming):",
      "PASS" if all(areas[i] >= areas[i+1] - 1e-6 for i in range(len(areas)-1)) else "FAIL")
print("- Top floor should be smaller than the bottom floor (some trimming occurred):",
      "PASS" if areas[-1] < areas[0] else "FAIL (increase n_candidate_floors or check geometry)")
