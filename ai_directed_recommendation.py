"""
AI-directed design recommendation, layered on top of the deterministic
design-space study, not replacing it.

design_space_study.py establishes, by computation and a mathematical
argument, that total buildable volume under this view corridor is
invariant to footprint rotation, but floor count is not. That leaves a
real decision for a designer: given a specific programmatic goal
(fewer, larger floors vs. more, smaller ones, say), which orientation
should they actually use? That's exactly the kind of judgment call
this project's other two tools also hand to an LLM: not asked to
compute anything, since the geometry is already computed and verified,
but asked to interpret an open-ended design brief against numbers it
did not produce itself and could not silently get wrong.

Requires an ANTHROPIC_API_KEY environment variable. Not executed in
the environment this repository was authored in (no key was available
there); written against the documented Messages API and manually
checked for correctness, but flagged here as unexecuted rather than
verified, the same honesty standard used elsewhere in this repo for
the Grasshopper component.

Run with: ANTHROPIC_API_KEY=sk-ant-... python ai_directed_recommendation.py "your brief"
"""

import os
import sys
import json
import urllib.request

from design_space_study import run as run_design_space_study

SYSTEM_PROMPT = (
    "You are advising an architect on massing orientation under a real view-corridor "
    "constraint. You will be given a design brief and the results of a deterministic "
    "computational study: total buildable GFA at each footprint rotation angle, and the "
    "floor count at each angle. The study already establishes, by computation, that total "
    "GFA is essentially invariant to rotation here, while floor count varies. Do not "
    "recompute, second-guess, or restate any number as if you derived it; treat the given "
    "numbers as ground truth. Your job is only to recommend ONE rotation angle from the "
    "given options that best serves the stated brief, and explain why in plain language, "
    "citing the actual numbers you were given. Respond with a single JSON object only, no "
    "prose: {\"recommended_angle\": number, \"reasoning\": string}."
)


def call_claude(system_prompt, user_content):
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        raise RuntimeError("Set ANTHROPIC_API_KEY to run this script.")
    body = json.dumps({
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 300,
        "system": system_prompt,
        "messages": [
            {"role": "user", "content": user_content},
            {"role": "assistant", "content": "{"},  # prefill forces a bare JSON object back
        ],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "Content-Type": "application/json",
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.load(resp)
    content = data["content"][0]["text"]
    return json.loads("{" + content)


def main():
    brief = sys.argv[1] if len(sys.argv) > 1 else (
        "I want the fewest, largest floor plates possible, for efficient generic office "
        "leasing, without giving up any total floor area."
    )
    print("Design brief:", brief)
    print("\nRunning the deterministic design-space study first (the numbers below are computed, not AI-generated)...\n")
    study = run_design_space_study()

    rotation_summary = [
        {"angle_deg": angle, "floors": floors, "gfa_m2": round(gfa, 1)}
        for angle, floors, gfa in study["rotation_results"]
    ]
    user_content = (
        "DESIGN BRIEF:\n" + brief + "\n\n"
        "COMPUTED RESULTS (per rotation angle, 0deg = long axis along the sightline):\n"
        + json.dumps(rotation_summary, indent=2)
    )

    try:
        result = call_claude(SYSTEM_PROMPT, user_content)
        print("\nRecommended orientation:", result["recommended_angle"], "degrees")
        print("Reasoning:", result["reasoning"])
    except Exception as e:
        print("\nCouldn't get an AI recommendation:", e)
        print("(The deterministic study above still stands on its own.)")


if __name__ == "__main__":
    main()
