# Low-Level Design (LLD) Diagrams Directory

This folder contains the complete Low-Level Design (LLD) diagram portfolio for the **Campus Delivery Management System (CDMS)** final Capstone Project evaluation.

All diagrams are provided in two formats:
1. **Vector SVG (`.svg`)**: Crisp, standalone, scalable graphics ready to be embedded into presentation slides, project reports, or viewed directly in any browser.
2. **Mermaid Source (`.mmd`)**: Standard Mermaid syntax files that can be edited in Mermaid Live Editor, rendered in GitHub, or embedded in Markdown.
3. **Interactive Viewer (`index.html`)**: A standalone web application allowing the student and faculty to navigate, inspect, zoom, and present all diagrams during the viva defense.

---

## Diagram Index & Syllabus Mapping

| # | Diagram Name | Formats | Evaluation Criteria Mapped | Description |
|---|---|---|---|---|
| **01** | `01_use_case_diagram` | [.svg](01_use_case_diagram.svg) / [.mmd](01_use_case_diagram.mmd) | **Point 1 & 6:** Requirement Analysis & Use Cases | System boundary, 3 actors (Learner, Security Staff, Operations Admin), background timer, 25 use cases with `<<include>>` and `<<extend>>`. |
| **02** | `02_class_diagram_domain_entities` | [.svg](02_class_diagram_domain_entities.svg) / [.mmd](02_class_diagram_domain_entities.mmd) | **Point 2 & 3:** Class Diagram & OOP Principles | Complete domain entity and document models (`Document` base, `User`, `Package`, `StorageLocation`, `PickupToken`, `PickupRecord`), attributes, types, methods, and exact multiplicities. |
| **03** | `03_class_diagram_services_and_architecture` | [.svg](03_class_diagram_services_and_architecture.svg) / [.mmd](03_class_diagram_services_and_architecture.mmd) | **Point 2, 4, 7:** Class Diagram, SOLID & API Design | Layered architecture class model: Routers, Use Case Services, Protocols/Interfaces, Unit of Work, and Composition Root. |
| **04** | `04_sequence_package_intake` | [.svg](04_sequence_package_intake.svg) / [.mmd](04_sequence_package_intake.mmd) | **Point 6 & 9:** Sequence Diagrams & Edge Cases | Gate No. 2 package arrival, input validation, duplicate tracking ID check, triage (VERIFIED / UNIDENTIFIED / DAMAGED), and atomic commit. |
| **05** | `05_sequence_storage_allocation` | [.svg](05_sequence_storage_allocation.svg) / [.mmd](05_sequence_storage_allocation.mmd) | **Point 5 & 6:** Design Patterns & Sequence Flow | Strategy Pattern ranking (`SuitableSizeStrategy` / `FirstAvailableStrategy`) and atomic single-document conditional reservation (`occupied_count < capacity`). |
| **06** | `06_sequence_pickup_request_and_token` | [.svg](06_sequence_pickup_request_and_token.svg) / [.mmd](06_sequence_pickup_request_and_token.mmd) | **Point 6 & 9:** Sequence Flow & Security | Learner requests pickup: cryptographic HMAC-SHA256 generation, 6-digit one-time code (shown once), salt, 30-min window, and previous token revocation. |
| **07** | `07_sequence_pickup_handover_concurrency` | [.svg](07_sequence_pickup_handover_concurrency.svg) / [.mmd](07_sequence_pickup_handover_concurrency.mmd) | **Point 6, 9, 10:** Concurrency Barrier & Double Pickup | 4-layer defense against double handover: Idempotency-Key check, constant-time HMAC comparison, atomic token consumption (`used_at IS NULL`), status CAS, and UK constraint. |
| **08** | `08_activity_package_lifecycle` | [.svg](08_activity_package_lifecycle.svg) / [.mmd](08_activity_package_lifecycle.mmd) | **Point 6:** Activity Diagrams | Complete end-to-end parcel lifecycle swimlane: Arrival -> Triage Hold -> Shelf Storage -> Pickup Request -> Verification -> Handover or Return/Lost Terminus. |
| **09** | `09_activity_concurrency_storage_handover` | [.svg](09_activity_concurrency_storage_handover.svg) / [.mmd](09_activity_concurrency_storage_handover.mmd) | **Point 6 & 9:** Concurrency & Race Resolution | Detailed step-by-step race resolution for concurrent shelf allocations and simultaneous pickup handovers. |
| **10** | `10_state_machine_diagram` | [.svg](10_state_machine_diagram.svg) / [.mmd](10_state_machine_diagram.mmd) | **Point 5 & 6:** State Pattern & Lifecycle | 12-state package lifecycle state diagram with all transitions, precondition guards, role permissions, and terminal state invariants (`COLLECTED`, `RETURNED`, `LOST`). |
| **11** | `11_component_architecture_diagram` | [.svg](11_component_architecture_diagram.svg) / [.mmd](11_component_architecture_diagram.mmd) | **Point 7 & 10:** Layered Monolith Architecture | Architectural component diagram: Client Tier (React SPA), API & Middleware (FastAPI), Service Layer, Pure Domain, Repositories, and MongoDB 6+. |
| **12** | `12_database_er_schema_diagram` | [.svg](12_database_er_schema_diagram.svg) / [.mmd](12_database_er_schema_diagram.mmd) | **Point 8:** Database Schema & Indexing | 10 MongoDB collections, sequence IDs, foreign key references, unique constraints, and compound indexes mapped from domain classes. |
| **13** | `13_design_patterns_diagram` | [.svg](13_design_patterns_diagram.svg) / [.mmd](13_design_patterns_diagram.mmd) | **Point 5:** Design Patterns Architecture | Comprehensive design pattern map covering Strategy, Observer, State, Factory, Repository/Unit of Work, Singleton, and Decorator with code justifications. |

---

## How to View and Present During Evaluation

### 1. Interactive Web Presentation
Open [`index.html`](index.html) in any modern web browser:
```bash
# macOS
open diagrams/index.html

# Linux
xdg-open diagrams/index.html
```
The viewer provides tabbed navigation across all 13 diagrams, toggleable vector SVG rendering, inspectable Mermaid source code, and LLD evaluation criteria notes.

### 2. Standalone SVG Viewing
Each `.svg` file can be opened individually in Chrome, Safari, Edge, or Firefox, or imported directly into PowerPoint/Keynote slides and LaTeX/Word capstone reports without any pixelation.

### 3. Modifying Diagrams
To modify any diagram, edit the corresponding `.mmd` file in VS Code (with the Mermaid Preview extension) or copy the code directly into [Mermaid Live Editor](https://mermaid.live).
