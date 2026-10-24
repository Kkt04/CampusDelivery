# Low-Level Design (LLD) Diagrams Directory
## Campus Delivery Management System (CDMS)

This directory contains the complete, streamlined Low-Level Design (LLD) diagram portfolio for the Capstone Project evaluation.

All diagrams are provided in three synchronized formats:
1. **High-Resolution PNG (`.png`)**: Crisp, publication-grade bitmap photos on a pure white (`#FFFFFF`) background. Ideal for inserting into project reports, PowerPoint/Keynote slides, or instant viewing.
2. **Vector SVG (`.svg`)**: Clean, scalable vector graphics with dark high-contrast lines and clear arrowheads.
3. **Mermaid Source (`.mmd`)**: Standard, human-readable Mermaid syntax files ready for version control or [Mermaid Live Editor](https://mermaid.live).
4. **Interactive Viewer (`index.html`)**: A clean web viewer to navigate, inspect, and present diagrams during the defense.

---

## Diagram Index & Syllabus Mapping

| # | Diagram Name | Photo / Vector / Source | Evaluation Criteria Mapped | Description |
|---|---|---|---|---|
| **01** | `01_use_case_diagram` | [.png](01_use_case_diagram.png) / [.svg](01_use_case_diagram.svg) / [.mmd](01_use_case_diagram.mmd) | **Point 1:** Requirement Analysis & Use Cases | System boundary, 3 actors (Learner, Security Staff, Ops Admin), core use cases with `<<include>>` relationships. |
| **02** | `02_class_diagram_domain_entities` | [.png](02_class_diagram_domain_entities.png) / [.svg](02_class_diagram_domain_entities.svg) / [.mmd](02_class_diagram_domain_entities.mmd) | **Point 2 & 3:** Class Diagram & OOP Principles | Domain entity and document models (`BaseDocument`, `User`, `Package`, `StorageLocation`, `PickupToken`, `PickupRecord`), attributes, types, methods, and exact multiplicities. |
| **03** | `03_class_diagram_services_and_architecture` | [.png](03_class_diagram_services_and_architecture.png) / [.svg](03_class_diagram_services_and_architecture.svg) / [.mmd](03_class_diagram_services_and_architecture.mmd) | **Point 2, 4, 7:** Class Diagram, SOLID & API Design | Layered architecture class model: Presentation Routers, Application Services, Domain Protocols (DIP), and MongoUnitOfWork. |
| **04** | `04_sequence_package_intake` | [.png](04_sequence_package_intake.png) / [.svg](04_sequence_package_intake.svg) / [.mmd](04_sequence_package_intake.mmd) | **Point 6 & 9:** Sequence Diagrams & Edge Cases | Gate No. 2 package arrival, input validation, duplicate tracking ID check, student triage, and event publishing. |
| **05** | `05_sequence_storage_allocation` | [.png](05_sequence_storage_allocation.png) / [.svg](05_sequence_storage_allocation.svg) / [.mmd](05_sequence_storage_allocation.mmd) | **Point 5 & 6:** Design Patterns & Sequence Flow | Strategy Pattern ranking (`SuitableSizeStrategy`) and atomic single-document conditional reservation (`occupied_count < capacity`). |
| **06** | `06_sequence_pickup_request_and_token` | [.png](06_sequence_pickup_request_and_token.png) / [.svg](06_sequence_pickup_request_and_token.svg) / [.mmd](06_sequence_pickup_request_and_token.mmd) | **Point 6 & 9:** Sequence Flow & Security | Learner requests pickup: cryptographic HMAC-SHA256 generation, 6-digit one-time code (shown once), salt, 30-min window, and previous token revocation. |
| **07** | `07_sequence_pickup_handover_concurrency` | [.png](07_sequence_pickup_handover_concurrency.png) / [.svg](07_sequence_pickup_handover_concurrency.svg) / [.mmd](07_sequence_pickup_handover_concurrency.mmd) | **Point 6, 9, 10:** Concurrency Barrier & Double Pickup | 4-layer defense against double handover: token bucket rate limit, atomic token consumption (`used_at IS NULL`), status CAS, and UK constraint. |
| **08** | `08_activity_package_lifecycle` | [.png](08_activity_package_lifecycle.png) / [.svg](08_activity_package_lifecycle.svg) / [.mmd](08_activity_package_lifecycle.mmd) | **Point 6:** Activity Diagrams | Complete end-to-end parcel lifecycle: Arrival -> Triage Hold -> Shelf Storage -> Pickup Request -> Verification -> Handover or Return. |
| **09** | `09_activity_concurrency_storage_handover` | [.png](09_activity_concurrency_storage_handover.png) / [.svg](09_activity_concurrency_storage_handover.svg) / [.mmd](09_activity_concurrency_storage_handover.mmd) | **Point 6 & 9:** Concurrency & Race Resolution | Detailed step-by-step race resolution for concurrent shelf allocations and simultaneous pickup handovers. |
| **10** | `10_state_machine_diagram` | [.png](10_state_machine_diagram.png) / [.svg](10_state_machine_diagram.svg) / [.mmd](10_state_machine_diagram.mmd) | **Point 5 & 6:** State Pattern & Lifecycle | Package lifecycle state diagram with all transitions, precondition guards, role permissions, and terminal state invariants (`COLLECTED`, `RETURNED`). |
| **11** | `11_component_architecture_diagram` | [.png](11_component_architecture_diagram.png) / [.svg](11_component_architecture_diagram.svg) / [.mmd](11_component_architecture_diagram.mmd) | **Point 7 & 10:** Layered Monolith Architecture | Architectural component diagram: Client Tier (React SPA), API Gateway (FastAPI), Service Layer, Pure Domain, and MongoDB 6+. |
| **12** | `12_database_er_schema_diagram` | [.png](12_database_er_schema_diagram.png) / [.svg](12_database_er_schema_diagram.svg) / [.mmd](12_database_er_schema_diagram.mmd) | **Point 8:** Database Schema & Indexing | MongoDB collections, sequence IDs, foreign key references, unique constraints, and compound indexes mapped from domain classes. |
| **13** | `13_design_patterns_diagram` | [.png](13_design_patterns_diagram.png) / [.svg](13_design_patterns_diagram.svg) / [.mmd](13_design_patterns_diagram.mmd) | **Point 4 & 5:** Design Patterns Architecture | Comprehensive design pattern map covering Strategy, Observer, State, Factory, Repository/Unit of Work, Singleton, and Decorator with code justifications. |

---

## How to View and Present During Evaluation

### 1. Interactive Web Presentation
Open [`index.html`](index.html) in your browser:
```bash
open diagrams/index.html
```
The viewer provides tabs for **PNG Photo**, **Vector SVG**, and **Mermaid Source**, with 1-click fullscreen opening.

### 2. Direct PNG Inspection
Open any `.png` file directly on your desktop or embed into your presentation slides without any rendering dependencies.
