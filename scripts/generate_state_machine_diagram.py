#!/usr/bin/env python3
"""Regenerate diagrams/10_state_machine_diagram.svg and .png directly from the code."""
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


def role_label(roles: frozenset[Role]) -> str:
    if roles == frozenset({Role.SECURITY, Role.ADMIN}):
        return "Staff"
    if roles == frozenset({Role.ADMIN}):
        return "Admin"
    if roles == frozenset({Role.SECURITY}):
        return "Security"
    if roles == frozenset({Role.LEARNER}):
        return "Learner"
    if roles == frozenset({Role.ADMIN, Role.LEARNER}):
        return "Admin/Learner"
    return "/".join(sorted(r.value.capitalize() for r in roles))


def build_dot() -> str:
    lines = [
        'digraph PackageLifecycle {',
        '  graph [',
        '    fontname="Helvetica,Arial,sans-serif",',
        '    fontsize=14,',
        '    labelloc="t",',
        '    label="10. Package Lifecycle Finite State Machine\\n(Authoritative transitions from domain/state_machine.py)",',
        '    bgcolor="#FFFFFF",',
        '    pad="0.5",',
        '    nodesep="0.6",',
        '    ranksep="0.7",',
        '    compound=true,',
        '    rankdir="TB"',
        '  ];',
        '  node [',
        '    fontname="Helvetica,Arial,sans-serif",',
        '    fontsize=11,',
        '    fontweight="bold",',
        '    style="filled,rounded",',
        '    shape="box",',
        '    margin="0.2,0.12",',
        '    penwidth=1.5',
        '  ];',
        '  edge [',
        '    fontname="Helvetica,Arial,sans-serif",',
        '    fontsize=9.5,',
        '    color="#334155",',
        '    fontcolor="#1e293b",',
        '    arrowsize=0.8,',
        '    penwidth=1.3',
        '  ];',
        '',
        '  // Start pseudo-state',
        '  start [shape=circle, style=filled, fillcolor="#0f172a", label="", width=0.28, fixedsize=true];',
        '',
        '  // Happy-path / Main Operational States',
        '  RECEIVED [fillcolor="#eff6ff", color="#2563eb", fontcolor="#1e40af"];',
        '  VERIFIED [fillcolor="#ecfdf5", color="#059669", fontcolor="#065f46"];',
        '  STORED [fillcolor="#f0fdf4", color="#16a34a", fontcolor="#166534"];',
        '  READY_FOR_PICKUP [fillcolor="#fefce8", color="#ca8a04", fontcolor="#854d0e"];',
        '  PICKUP_REQUESTED [fillcolor="#fdf4ff", color="#c026d3", fontcolor="#86198f"];',
        '',
        '  // Terminal Success State',
        '  COLLECTED [fillcolor="#16a34a", color="#14532d", fontcolor="#ffffff", peripheries=2];',
        '',
        '  // Exception / Intake Triage States',
        '  UNIDENTIFIED [fillcolor="#fff7ed", color="#ea580c", fontcolor="#9a3412"];',
        '  DAMAGED [fillcolor="#fef2f2", color="#dc2626", fontcolor="#991b1b"];',
        '',
        '  // Investigation & Return States',
        '  UNDER_INVESTIGATION [fillcolor="#f1f5f9", color="#475569", fontcolor="#1e293b"];',
        '  RETURN_REQUESTED [fillcolor="#fff1f2", color="#e11d48", fontcolor="#9f1239"];',
        '',
        '  // Terminal Failure/Exit States',
        '  RETURNED [fillcolor="#475569", color="#1e293b", fontcolor="#ffffff", peripheries=2];',
        '  LOST [fillcolor="#dc2626", color="#7f1d1d", fontcolor="#ffffff", peripheries=2];',
        '',
        '  // Initial edge',
        '  start -> RECEIVED [label=" register\\n[Staff]"];',
        '',
    ]

    for t in TRANSITIONS:
        roles_str = role_label(t.roles)
        label = f' {t.action}\\n[{roles_str}]'
        # Add special color styling for terminal or critical edges
        edge_style = ''
        if t.target == PackageStatus.COLLECTED:
            edge_style = ' [color="#16a34a", penwidth=2.0, fontcolor="#15803d"]'
        elif t.target == PackageStatus.LOST:
            edge_style = ' [color="#dc2626", penwidth=1.8, fontcolor="#b91c1c"]'
        elif t.target == PackageStatus.RETURNED:
            edge_style = ' [color="#475569", penwidth=1.8, fontcolor="#334155"]'

        lines.append(f'  {t.source.value} -> {t.target.value} [label="{label}"]{edge_style};')

    lines.append('}')
    return "\n".join(lines)


def main() -> None:
    root = Path(__file__).resolve().parent.parent
    diagrams_dir = root / "diagrams"
    svg_path = diagrams_dir / "10_state_machine_diagram.svg"
    png_path = diagrams_dir / "10_state_machine_diagram.png"

    dot_content = build_dot()
    dot_file = diagrams_dir / "10_state_machine_diagram.dot"
    dot_file.write_text(dot_content)

    print(f"Generating SVG: {svg_path}...")
    subprocess.run([DOT_BIN, "-Tsvg", str(dot_file), "-o", str(svg_path)], check=True)

    print(f"Generating PNG: {png_path}...")
    # Prefer rsvg-convert for high-DPI rasterization, fallback to dot -Tpng
    if os.path.exists(RSVG_BIN):
        subprocess.run([RSVG_BIN, "-z", "1.5", "-o", str(png_path), str(svg_path)], check=True)
    else:
        subprocess.run([DOT_BIN, "-Tpng", "-Gdpi=150", str(dot_file), "-o", str(png_path)], check=True)

    # Clean up intermediate dot file
    dot_file.unlink(missing_ok=True)

    # Verification: Extract all states and diff against PackageStatus
    svg_text = svg_path.read_text()
    all_enum_names = {s.value for s in PackageStatus}

    # Verify no nonexistent states exist in SVG
    forbidden_states = ["REGISTERED", "SORTED", "OVERDUE"]
    for forbidden in forbidden_states:
        if re.search(rf"\b{forbidden}\b", svg_text):
            print(f"ERROR: Found forbidden obsolete state {forbidden} in SVG!")
            sys.exit(1)

    # Verify all 12 enum states exist in SVG
    missing_states = []
    for state in all_enum_names:
        if not re.search(rf"\b{state}\b", svg_text):
            missing_states.append(state)

    if missing_states:
        print(f"ERROR: Missing enum states in SVG: {missing_states}")
        sys.exit(1)

    print("SUCCESS: Verified all 12 PackageStatus enum states are present.")
    print("SUCCESS: Verified no obsolete states (REGISTERED, SORTED, OVERDUE) exist.")
    print(f"Output files updated: {svg_path} and {png_path}")


if __name__ == "__main__":
    main()
