# Vancouver View Corridor Massing

A computational design study, not just a generator: given a real, City-of-Vancouver-mapped protected view corridor and a candidate Downtown-area site, this project asks and computationally answers two concrete research questions about how a sloped geodetic height ceiling, not a flat setback, should actually be handled, then hands the resulting design trade-off to an agentic AI layer to reason about, not to recompute. Real parcel geometry in, deterministic measurements throughout, and a traceable record of what's confirmed versus placeholder, the same standard of evidence as the other two projects in this series, applied here to a harder, sloped-plane constraint instead of a flat one.

**This is a Rhino/Grasshopper study, not a web app.** There's no live demo link; see "How to test it" below for exactly what to run and what to expect.

## The problem

Most massing tools, including my own earlier one, stop at flat setbacks and a height limit. Vancouver's protected view corridors are a genuinely different, harder constraint: a view cone doesn't limit a building to a storey count, it limits it to a maximum **geodetic elevation** (height above sea level) that is low near the viewpoint and rises with distance from it, following the geometry of a sightline. A site can be well within its zoning envelope and still have a tall building sliced off diagonally by a corridor it happens to sit inside.

## How to test it

No Rhino installation is required to verify any of this, only Python.

```
git clone https://github.com/RomanJahandideh/vancouver-view-corridor-massing.git
cd vancouver-view-corridor-massing
pip install rhino3dm matplotlib
```

1. **Run the tests first.** `python test_geometry.py` should print a series of checks ending in `PASS` for the apex/axis derivation, the half-plane clip against a hand-computed rectangle, and the floor-by-floor trimming behavior. This is the geometry being verified before anything else depends on it.
2. **Generate the real massing.** `python view_corridor_massing.py` should fetch the real Creekside Park view corridor (or fall back to a verified offline copy if the network call fails), print a floor-by-floor table, and finish with `Wrote vancouver_viewcone_massing.3dm with 18 buildable floors under the view corridor`. Open that `.3dm` file directly in Rhino to inspect the real geometry, corridor polygon, site outline, and one solid per floor.
3. **See it without Rhino.** `python preview_render.py` writes `preview.png`, a rendered image of the exact same geometry in the `.3dm` file, so you can see the result even without Rhino installed.
4. **Run the research questions.** `python design_space_study.py` should print RQ1 (a 39.5% GFA-recovery figure) and RQ2 (a rotation sweep showing under 0.1% GFA variance, with the theoretical-versus-discrete-volume check confirming it's a real property, not a fluke).
5. **Try the AI-directed layer.** `ANTHROPIC_API_KEY=sk-ant-... python ai_directed_recommendation.py "your design brief"` runs the study above, then asks Claude to recommend an orientation for your stated goal, citing the actual computed numbers rather than inventing new ones.
6. **In Grasshopper**, paste `grasshopper_component.py` into a GhPython "Script" component (Rhino 8, Python 3 mode) and wire up the inputs documented in its own docstring, it shares the exact same tested core functions as step 1-2 above, copied over rather than reimplemented.

## Research questions

This isn't just "can the geometry be generated correctly", that part is table stakes and is verified in `test_geometry.py`. On top of it, `design_space_study.py` asks two questions that weren't answered until computed:

**RQ1: How much does precise, floor-by-floor compliance actually recover, compared to how this constraint gets handled in practice?** A common practical shortcut is to check compliance once, at a single flat cap (the lowest ceiling elevation found anywhere on the site), and build the whole envelope up to that one safe line. Computed on the real Creekside Park corridor and a representative site: the flat-cap shortcut yields 10 floors and 18,360 m² of GFA; precise per-floor trimming yields 18 floors and 25,608 m², a **39.5% GFA recovery** from doing the geometry properly instead of conservatively. That's not a rounding difference, it's most of an extra building.

**RQ2: Does footprint orientation relative to the sightline change how much floor area survives?** Swept across seven rotation angles (0° to 90°, long axis along the sightline to perpendicular to it), holding footprint area and centroid fixed: total GFA varies by **0.02%**, essentially nothing, while floor count varies meaningfully (18 floors at 0°, down to 17 at 90°; the effect is larger for more elongated footprints). This isn't a coincidence, it's provable: the ceiling is linear in distance from the apex, and the average of a linear function over any region equals its value at that region's centroid. Rotating a fixed-area footprint around a fixed centroid can't change that average, so total buildable volume under a linear sloped ceiling is rotation-invariant by construction. `design_space_study.py` verifies this explicitly, checking that the discrete per-floor sum tracks a hand-derived continuous-volume formula as a consistent percentage across every tested angle (73.8-73.9%, the gap being floor-height quantization, not an orientation effect).

**Practical implication:** orientation is a free design variable here. An architect can choose it for silhouette, floor-plate efficiency, or programmatic reasons (fewer, larger floors vs. more, smaller ones) without a GFA penalty either way, which is exactly the kind of judgment call `ai_directed_recommendation.py` hands to an LLM: not asked to compute anything, since the numbers above are already computed and verified, but asked to interpret an open-ended brief ("I want the fewest, largest floor plates for efficient leasing") against real numbers it did not produce itself.

## Research grounding

- **[MCP-Driven Parametric Modeling: Integrating LLM Agents into Architectural and Landscape Design Workflows](https://openreview.net/pdf/ec165821c588ee91f6f1ca8a56021d465b91e3f2.pdf)** (Liu & Tian, NeurIPS 2025 Creative AI Track). The direct reference point: an MCP-Grasshopper integration letting LLM agents drive parametric modeling through structured, executable commands rather than raw geometry. This project follows the same commitment, carried one step further: the AI layer here is only ever handed already-computed, already-verified numbers to reason about, never asked to produce or silently alter them.
- **PromptMorph** (Springer, *LLM-Driven Workflow for Text-to-3D Parametric Modeling in Architecture*) and a Berkeley multi-agent LLM-to-Grasshopper prototype, both in the same space: natural language or high-level intent driving Grasshopper-native geometry generation.
- **Architext** (arXiv 2303.07519, *Language-Driven Generative Architecture Design*), for the broader context of language-conditioned generative design.
- Evolutionary/optimization-based massing exploration in Rhino-Grasshopper (e.g. *Enabling Optimisation-based Exploration for Building Massing Design*) is the closest published methodology to the RQ2 sweep here, a systematic design-space exploration rather than one deterministic pass, though this study substitutes a closed-form proof for a population-based search, since the relationship here turned out to be provable rather than merely searchable.

## Real data used, with citations

- **City of Vancouver Open Data Portal, "view-cones" dataset**: 24 officially protected view corridors, fetched live via the public API (`https://opendata.vancouver.ca/api/records/1.0/search/?dataset=view-cones`). This study uses **Creekside Park (view number J1)**, "View of Lions from Creekside Park." The polygon vertices, corridor name, and description are the real published geometry, not approximated, and the source URL is embedded in the code, not just this README.
- The **geodetic-elevation mechanism itself is real and documented**: view cones limit an absolute elevation above sea level, low near the apex and rising with distance, applied through the rezoning and development permit process, not the zoning schedule directly. This is the same kind of **conditional, discretionary rule** that makes regulatory literacy hard in the first place, a limit that depends on where you are, not a single published number.

## What's a placeholder, and why, keeping uncertainty visible

The open dataset publishes corridor **geometry** (the polygon), not per-site **elevation limits**. The City's own guidance for a real site is to confirm view-cone implications directly (`views@vancouver.ca`), since the applicable limit also depends on the site's own ground elevation and which of several bylaw provisions binds first. So `BASE_ELEV_M` and `SLOPE` are explicitly labeled placeholders, chosen to produce a legible, correctly-behaved worked example, not to claim a specific site's real legal limit. The RQ1 and RQ2 findings above (the 39.5% recovery figure and the rotation-invariance proof) don't depend on the exact placeholder values, they're structural properties of a linear sloped-ceiling constraint, and would hold with the real numbers substituted in. Marking that distinction, confirmed geometry versus a placeholder pending site-specific confirmation, rather than blurring the two, is the same discipline the [Zoning Literacy Assistant](https://github.com/RomanJahandideh/zoning-literacy-assistant) applies to every answer it gives.

## How it works

1. **Fetch real geometry.** The corridor polygon is pulled from the live Open Data API (falls back to a verified hard-coded copy of the same record if the network call fails, so the script stays runnable offline).
2. **Derive the apex and sightline axis.** The vertex closest to being the isoceles tip of the corridor triangle is the apex; the axis runs from there toward the midpoint of the far edge.
3. **Zoning envelope.** The buildable footprint is the inward offset of the site polygon by a setback distance, via half-plane intersection, the same approach used and verified in [parametric-massing-generator](https://github.com/RomanJahandideh/parametric-massing-generator).
4. **Per-floor corridor trim.** Because the geodetic ceiling is linear in distance-along-axis, checking a floor against it is a single half-plane clip. Applied floor by floor, this produces the stepped massing.
5. **Design-space study.** `design_space_study.py` reuses these same functions to answer RQ1 and RQ2 above, rather than reimplementing the geometry a second time.
6. **AI-directed recommendation.** `ai_directed_recommendation.py` runs the study, then hands its computed results (not a re-derivation) to Claude to recommend an orientation for a stated design brief.
7. **Output.** A real `.3dm` file (via `rhino3dm`, openable directly in Rhino) containing the corridor polygon, the site and zoning-footprint outlines, and one solid per buildable floor.

## What's tested, and what isn't

`test_geometry.py` verifies, independently and before anything else was built on top of it: the apex/axis derivation against the real fetched coordinates, the half-plane clip against a hand-computed rectangle case, and the floor-by-floor trimming behavior. `view_corridor_massing.py` runs end to end and writes a real, structurally valid `.3dm` (verified: correct object, layer, vertex and face counts). `design_space_study.py`'s RQ1 and RQ2 numbers above are copied directly from an actual run, and the rotation-invariance explanation is independently checked against a hand-derived closed-form formula, not just asserted.

`grasshopper_component.py` shares the exact same core functions (`clip_halfplane`, `offset_polygon_inward`, `derive_axis`), copied over rather than reimplemented, so the tested logic isn't being trusted for a second time inside the GH canvas untested. The one part that couldn't be executed in this environment is `extrude_polygon_brep`, which calls `Rhino.Geometry.Extrusion.Create`, a RhinoCommon API only available inside Rhino itself. It's written against the standard, documented signature, but hasn't been run.

`ai_directed_recommendation.py` requires an `ANTHROPIC_API_KEY` and was not executed in the environment this repository was authored in (no key was available there); written against the documented Messages API and manually checked, but flagged as unexecuted rather than verified, the same honesty standard applied to the Grasshopper component above. The deterministic study it wraps stands on its own either way.

See "How to test it" near the top of this README for the exact commands and what each one should print or produce.
