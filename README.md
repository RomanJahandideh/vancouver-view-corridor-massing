# Vancouver View Corridor Massing

A Rhino/Grasshopper study: generates the maximum buildable massing on a real Downtown-area Vancouver site, trimmed against one of the City's actual protected view corridors, a sloped geodetic height ceiling, not a flat setback, using a real polygon pulled live from the City's Open Data Portal.

**This is a Rhino/Grasshopper study, not a web app.** There's no live demo link; see "Run it" below for how to open the outputs.

## The problem

Most massing tools, including my own earlier ones, stop at flat setbacks and a height limit. Vancouver's protected view corridors are a genuinely different, harder constraint: a view cone doesn't limit a building to a storey count, it limits it to a maximum **geodetic elevation** (height above sea level) that is low near the viewpoint and rises with distance from it, following the natural geometry of a sightline. A site can be well within its zoning envelope and still have a large part of a tall building sliced off diagonally by a corridor it happens to sit inside.

This project builds that: given a real view corridor polygon and a candidate site, it computes, floor by floor, whether the standard zoning envelope is still fully buildable, partially trimmed, or fully excluded by the corridor's sloped ceiling, and generates the resulting stepped massing solid.

## Research grounding

- **[MCP-Driven Parametric Modeling: Integrating LLM Agents into Architectural and Landscape Design Workflows](https://openreview.net/pdf/ec165821c588ee91f6f1ca8a56021d465b91e3f2.pdf)** (Liu & Tian, NeurIPS 2025 Creative AI Track). The direct reference point for this project: an MCP-Grasshopper integration letting LLM agents drive parametric modeling through structured, executable commands rather than raw geometry. This project doesn't wire up MCP itself, but follows the same underlying commitment: the geometric logic is explicit, testable code, not an opaque generative output.
- **PromptMorph** (Springer, *LLM-Driven Workflow for Text-to-3D Parametric Modeling in Architecture*) and the Berkeley multi-agent LLM-to-Grasshopper prototype, both explored in the same space: natural language or high-level intent driving Grasshopper-native geometry generation.
- **Architext** (arXiv 2303.07519, *Language-Driven Generative Architecture Design*), for the broader context of language-conditioned generative design.

## Real data used

- **City of Vancouver Open Data Portal, "view-cones" dataset**: 24 officially protected view corridors, fetched live via the public API (`https://opendata.vancouver.ca/api/records/1.0/search/?dataset=view-cones`). This study uses **Creekside Park (view number J1)**, "View of Lions from Creekside Park." The polygon vertices, corridor name, and description are the real published geometry, not approximated.
- The **geodetic-elevation mechanism itself is real and documented**: view cones limit an absolute elevation above sea level, low near the apex and rising with distance, applied through the rezoning and development permit process, not the zoning schedule directly.

## What's a placeholder, and why

The open dataset publishes corridor **geometry** (the polygon), not per-site **elevation limits**. The City's own guidance for a real site is to confirm view-cone implications directly (`views@vancouver.ca`), since the applicable limit also depends on the site's own ground elevation and which of several bylaw provisions binds first. So `BASE_ELEV_M` and `SLOPE` in `view_corridor_massing.py` are explicitly labeled placeholders, chosen only to produce a legible, correctly-behaved worked example, not to claim a specific site's real legal limit. This mirrors the same honesty pattern as the [Zoning Literacy Assistant](https://github.com/RomanJahandideh/zoning-literacy-assistant): say plainly what's confirmed and what needs to be checked, rather than presenting a placeholder as fact.

## How it works

1. **Fetch real geometry.** The corridor polygon is pulled from the live Open Data API (falls back to a verified hard-coded copy of the same record if the network call fails, so the script stays runnable offline).
2. **Derive the apex and sightline axis.** The vertex closest to being the isoceles tip of the corridor triangle is the apex (viewpoint side); the axis runs from there toward the midpoint of the far edge (toward the protected view target).
3. **Zoning envelope.** The site's buildable footprint is the inward offset of the site polygon by a setback distance, via half-plane intersection (Sutherland-Hodgman clipping against each inward-shifted edge), the same approach used and verified in [parametric-massing-generator](https://github.com/RomanJahandideh/parametric-massing-generator).
4. **Per-floor corridor trim.** Because the geodetic ceiling is linear in distance-along-axis, checking a floor against it is a single half-plane clip: keep only the part of the footprint far enough from the apex that the ceiling has already risen above that floor's elevation. Applied floor by floor, this produces the stepped massing.
5. **Output.** A real `.3dm` file (via `rhino3dm`, openable directly in Rhino) containing the corridor polygon, the site and zoning-footprint outlines, and one solid per buildable floor.

## What's tested, and what isn't

`test_geometry.py` verifies, independently and before anything else was built on top of it: the apex/axis derivation against the real fetched coordinates, the half-plane clip against a hand-computed rectangle case, and the floor-by-floor trimming behavior (monotonically non-increasing footprint area with height, full at the base, excluded once the ceiling has dropped below the floor). `view_corridor_massing.py` runs end to end and writes a real, structurally valid `.3dm` (verified: correct object, layer, vertex and face counts).

`grasshopper_component.py` shares the exact same core functions (`clip_halfplane`, `offset_polygon_inward`, `derive_axis`), copied over rather than reimplemented, so the tested logic isn't being trusted for a second time inside the GH canvas untested. The one part that couldn't be executed in this environment is `extrude_polygon_brep`, which calls `Rhino.Geometry.Extrusion.Create`, a RhinoCommon API only available inside Rhino itself. It's written against the standard, documented signature, but hasn't been run. Worth knowing before treating it as verified.

## Run it

**Standalone (no Rhino needed), writes a real .3dm and a preview image:**
```
pip install rhino3dm matplotlib
python test_geometry.py          # verification, run first
python view_corridor_massing.py  # writes vancouver_viewcone_massing.3dm
python preview_render.py         # writes preview.png
```
Open `vancouver_viewcone_massing.3dm` directly in Rhino to inspect the real geometry.

**In Grasshopper:** paste `grasshopper_component.py` into a GhPython "Script" component (Rhino 8, Python 3 mode), wire up the inputs described in its docstring (`corridor_poly`, `site_poly`, `setback`, `base_elev`, `slope`, `floor_height`, `max_floors`), matching the same parameters used in the standalone script.
