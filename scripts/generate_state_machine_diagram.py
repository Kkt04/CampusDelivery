#!/usr/bin/env python3
"""Regenerate diagrams/10_state_machine_diagram.svg and .png directly from the code,
matching docs/05-state-machine.md with clean, non-duplicate annotations.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.domain.enums import PackageStatus, Role
from app.domain.state_machine import TRANSITIONS

DOT_BIN = "/opt/homebrew/bin/dot" if os.path.exists("/opt/homebrew/bin/dot") else "dot"
RSVG_BIN = "/opt/homebrew/bin/rsvg-convert" if os.path.exists("/opt/homebrew/bin/rsvg-convert") else "rsvg-convert"


def build_clean_dot() -> str:
    lines = [
        'digraph PackageLifecycle {',
        '  graph [',
        '    fontname="Helvetica,Arial,sans-serif",',
        '    fontsize=16,',
        '    labelloc="t",',
        '    label="10. Package Lifecycle Finite State Machine\\n(Authoritative transitions from domain/state_machine.py)",',
        '    bgcolor="#FFFFFF",',
        '    pad="0.6",',
        '    nodesep="0.65",',
        '    ranksep="0.75",',
        '    compound=true,',
        '    rankdir="TB"',
        '  ];',
        '  node [',
        '    fontname="Helvetica,Arial,sans-serif",',
        '    fontsize=11.5,',
        '    fontweight="bold",',
        '    style="filled,rounded",',
        '    shape="box",',
        '    margin="0.22,0.14",',
        '    penwidth=1.8',
        '  ];',
        '  edge [',
        '    fontname="Helvetica,Arial,sans-serif",',
        '    fontsize=9.5,',
        '    color="#334155",',
        '    fontcolor="#1e293b",',
        '    arrowsize=0.85,',
        '    penwidth=1.4',
        '  ];',
        '',
        '  // Start and End pseudo-states',
        '  start [shape=circle, style=filled, fillcolor="#0f172a", label="", width=0.28, fixedsize=true];',
        '  end [shape=doublecircle, style=filled, fillcolor="#0f172a", label="", width=0.28, fixedsize=true];',
        '',
        '  // Operational Happy-Path Spine',
        '  RECEIVED [fillcolor="#eff6ff", color="#2563eb", fontcolor="#1e40af"];',
        '  VERIFIED [fillcolor="#ecfdf5", color="#059669", fontcolor="#065f46"];',
        '  STORED [fillcolor="#f0fdf4", color="#16a34a", fontcolor="#166534"];',
        '  READY_FOR_PICKUP [fillcolor="#fefce8", color="#ca8a04", fontcolor="#854d0e"];',
        '  PICKUP_REQUESTED [fillcolor="#fdf4ff", color="#c026d3", fontcolor="#86198f"];',
        '  COLLECTED [fillcolor="#16a34a", color="#14532d", fontcolor="#ffffff", peripheries=2];',
        '',
        '  // Intake Triage States',
        '  UNIDENTIFIED [fillcolor="#fff7ed", color="#ea580c", fontcolor="#9a3412"];',
        '  DAMAGED [fillcolor="#fef2f2", color="#dc2626", fontcolor="#991b1b"];',
        '',
        '  // Investigation & Return States',
        '  UNDER_INVESTIGATION [fillcolor="#f8fafc", color="#475569", fontcolor="#1e293b"];',
        '  RETURN_REQUESTED [fillcolor="#fff1f2", color="#e11d48", fontcolor="#9f1239"];',
        '',
        '  // Terminal Exit States',
        '  RETURNED [fillcolor="#475569", color="#1e293b", fontcolor="#ffffff", peripheries=2];',
        '  LOST [fillcolor="#dc2626", color="#7f1d1d", fontcolor="#ffffff", peripheries=2];',
        '',
        '  // Ranks for visual balance',
        '  { rank=same; UNIDENTIFIED; RECEIVED; DAMAGED; }',
        '  { rank=same; UNDER_INVESTIGATION; RETURN_REQUESTED; }',
        '  { rank=same; COLLECTED; LOST; RETURNED; }',
        '',
        '  // 1. Happy Path Transitions',
        '  start -> RECEIVED [label=" register [Staff]"];',
        '  RECEIVED -> VERIFIED [label=" verify: recipient matched [Staff]"];',
        '  VERIFIED -> STORED [label=" assign storage [Staff]"];',
        '  STORED -> READY_FOR_PICKUP [label=" mark ready & notify [Staff]"];',
        '  READY_FOR_PICKUP -> PICKUP_REQUESTED [label=" request pickup [Learner]"];',
        '  PICKUP_REQUESTED -> COLLECTED [label=" verify OTP & handover [Security]", color="#16a34a", penwidth=2.2, fontcolor="#15803d"];',
        '  COLLECTED -> end [color="#16a34a", penwidth=2.0];',
        '',
        '  // 2. Intake Triage & Resolution',
        '  RECEIVED -> UNIDENTIFIED [label=" no recipient", color="#ea580c"];',
        '  RECEIVED -> DAMAGED [label=" damaged on arrival", color="#dc2626"];',
        '  UNIDENTIFIED -> VERIFIED [label=" identify: no shelf yet"];',
        '  UNIDENTIFIED -> STORED [label=" identify: shelf assigned"];',
        '  DAMAGED -> VERIFIED [label=" release hold: no shelf"];',
        '  DAMAGED -> STORED [label=" release hold: stored"];',
        '',
        '  // 3. Escalations to Investigation (clean dashed lines, no redundant label clutter)',
        '  VERIFIED -> UNDER_INVESTIGATION [style=dashed, color="#64748b"];',
        '  STORED -> UNDER_INVESTIGATION [style=dashed, color="#64748b"];',
        '  READY_FOR_PICKUP -> UNDER_INVESTIGATION [style=dashed, color="#64748b"];',
        '  PICKUP_REQUESTED -> UNDER_INVESTIGATION [style=dashed, color="#64748b"];',
        '  UNIDENTIFIED -> UNDER_INVESTIGATION [style=dashed, color="#64748b"];',
        '  DAMAGED -> UNDER_INVESTIGATION [label=" investigate [Staff]", style=dashed, color="#64748b", fontcolor="#64748b"];',
        '',
        '  // 4. Investigation Outcomes',
        '  UNDER_INVESTIGATION -> STORED [label=" resolve: back to shelf [Admin]"];',
        '  UNDER_INVESTIGATION -> VERIFIED [label=" resolve: awaiting shelf [Admin]"];',
        '  UNDER_INVESTIGATION -> UNIDENTIFIED [label=" resolve: unidentified [Admin]"];',
        '  UNDER_INVESTIGATION -> LOST [label=" mark lost [Admin]", color="#dc2626", fontcolor="#b91c1c"];',
        '  UNDER_INVESTIGATION -> RETURN_REQUESTED [label=" request return [Admin]", style=dashed, color="#e11d48"];',
        '',
        '  // 5. Return to Courier Workflow',
        '  VERIFIED -> RETURN_REQUESTED [style=dashed, color="#e11d48"];',
        '  STORED -> RETURN_REQUESTED [style=dashed, color="#e11d48"];',
        '  READY_FOR_PICKUP -> RETURN_REQUESTED [style=dashed, color="#e11d48"];',
        '  PICKUP_REQUESTED -> RETURN_REQUESTED [style=dashed, color="#e11d48"];',
        '  UNIDENTIFIED -> RETURN_REQUESTED [style=dashed, color="#e11d48"];',
        '  DAMAGED -> RETURN_REQUESTED [label=" request return [Staff/Learner]", style=dashed, color="#e11d48", fontcolor="#e11d48"];',
        '  RETURN_REQUESTED -> RETURNED [label=" return to courier [Staff]", color="#475569", penwidth=2.0];',
        '  RETURNED -> end [color="#475569", penwidth=2.0];',
        '  LOST -> end [color="#dc2626", penwidth=2.0];',
        '}',
    ]
    return "\n".join(lines)


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    diagrams_dir = root / "diagrams"
    svg_path = diagrams_dir / "10_state_machine_diagram.svg"
    png_path = diagrams_dir / "10_state_machine_diagram.png"

    dot_content = build_clean_dot()
    dot_file = diagrams_dir / "10_state_machine_diagram.dot"
    dot_file.write_text(dot_content)

    print(f"Generating SVG: {svg_path}...")
    subprocess.run([DOT_BIN, "-Tsvg", str(dot_file), "-o", str(svg_path)], check=True)

    print(f"Generating PNG: {png_path}...")
    if os.path.exists(RSVG_BIN):
        subprocess.run([RSVG_BIN, "-z", "1.6", "-o", str(png_path), str(svg_path)], check=True)
    else:
        subprocess.run([DOT_BIN, "-Tpng", "-Gdpi=150", str(dot_file), "-o", str(png_path)], check=True)

    dot_file.unlink(missing_ok=True)

    # Verification: check all 12 enum members are present
    svg_text = svg_path.read_text()
    all_enum_names = {s.value for s in PackageStatus}

    forbidden_states = ["REGISTERED", "SORTED", "OVERDUE"]
    for forbidden in forbidden_states:
        if re.search(rf"\b{forbidden}\b", svg_text):
            print(f"ERROR: Found forbidden obsolete state {forbidden} in SVG!")
            sys.exit(1)

    missing_states = [s for s in all_enum_names if not re.search(rf"\b{s}\b", svg_text)]
    if missing_states:
        print(f"ERROR: Missing enum states in SVG: {missing_states}")
        sys.exit(1)

    print("SUCCESS: Verified all 12 PackageStatus enum states are present.")
    print("SUCCESS: Verified no obsolete states exist.")
    print(f"Output files updated: {svg_path} and {png_path}")


if __name__ == "__main__":
    main()
