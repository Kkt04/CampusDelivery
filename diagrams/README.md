# Low-Level Design (LLD) Diagrams Directory
## Campus Delivery Management System (CDMS)

This directory contains the Low-Level Design (LLD) diagram portfolio for the Capstone Project evaluation.

All diagrams are provided in **2 essential visual formats** on a pure white (`#FFFFFF`) background:
1. **High-Resolution PNG (`.png`)**: Standalone, publication-grade image photos with bold, clear lines. Ready to drag and drop into PowerPoint slides, Word reports, or view natively on any device.
2. **Vector SVG (`.svg`)**: Scalable vector graphics for browser inspection and infinite-resolution printing.
3. **Interactive Viewer (`index.html`)**: A clean web viewer to inspect and present both PNG photos and SVGs during the defense.

---

## Diagram Index & Syllabus Mapping

| # | Diagram Name | Photo (PNG) & Vector (SVG) | Evaluation Criteria Mapped | Description |
|---|---|---|---|---|
| **01** | `01_use_case_diagram` | [.png](01_use_case_diagram.png) / [.svg](01_use_case_diagram.svg) | **Point 1:** Requirement Analysis & Use Cases | System boundary, 3 actors (Learner, Security Staff, Ops Admin), core use cases with `<<include>>` relationships. |
| **02** | `02_class_diagram_domain_entities` | [.png](02_class_diagram_domain_entities.png) / [.svg](02_class_diagram_domain_entities.svg) | **Point 2 & 3:** Class Diagram & OOP Principles | Domain entity and document models (`BaseDocument`, `User`, `Package`, `StorageLocation`, `PickupToken`, `PickupRecord`), attributes, types, methods, and exact multiplicities. |
| **03** | `03_class_diagram_services_and_architecture` | [.png](03_class_diagram_services_and_architecture.png) / [.svg](03_class_diagram_services_and_architecture.svg) | **Point 2, 4, 7:** Class Diagram, SOLID & API Design | Layered architecture class model: Presentation Routers, Application Services, Domain Protocols (DIP), and MongoUnitOfWork. |
| **04** | `04_sequence_package_intake` | [.png](04_sequence_package_intake.png) / [.svg](04_sequence_package_intake.svg) | **Point 6 & 9:** Sequence Diagrams & Edge Cases | Gate No. 2 package arrival, input validation, duplicate tracking ID check, learner identification, manual rack entry, and event publishing. |
| **05** | `05_sequence_storage_allocation` | [.png](05_sequence_storage_allocation.png) / [.svg](05_sequence_storage_allocation.svg) | **Point 5 & 6:** Design Patterns & Sequence Flow | Direct manual rack assignment or Strategy Pattern ranking (`SuitableSizeStrategy`) and atomic single-document conditional reservation (`occupied_count < capacity`). |
| **06** | `06_sequence_pickup_request_and_token` | [.png](06_sequence_pickup_request_and_token.png) / [.svg](06_sequence_pickup_request_and_token.svg) | **Point 6 & 9:** Sequence Flow & Security | Learner requests pickup: cryptographic HMAC-SHA256 generation, 6-digit one-time code (shown once), salt, 30-min window, and previous token revocation. |
| **07** | `07_sequence_pickup_handover_concurrency` | [.png](07_sequence_pickup_handover_concurrency.png) / [.svg](07_sequence_pickup_handover_concurrency.svg) | **Point 6, 9, 10:** Concurrency Barrier & Double Pickup | 4-layer defense against double handover: token bucket rate limit, atomic token consumption (`used_at IS NULL`), status CAS, and UK constraint. |
| **08** | `08_activity_package_lifecycle` | [.png](08_activity_package_lifecycle.png) / [.svg](08_activity_package_lifecycle.svg) | **Point 6:** Activity Diagrams | Complete end-to-end parcel lifecycle: Arrival -> Manual Rack Intake -> Ready for Pickup -> OTP Handover or Learner/Security Return. |
| **09** | `09_activity_concurrency_storage_handover` | [.png](09_activity_concurrency_storage_handover.png) / [.svg](09_activity_concurrency_storage_handover.svg) | **Point 6 & 9:** Concurrency & Race Resolution | Detailed step-by-step race resolution for concurrent shelf allocations and simultaneous pickup handovers. |
| **10** | `10_state_machine_diagram` | [.png](10_state_machine_diagram.png) / [.svg](10_state_machine_diagram.svg) | **Point 5 & 6:** State Pattern & Lifecycle | Package lifecycle state diagram with all transitions, precondition guards, role permissions, and terminal state invariants (`COLLECTED`, `RETURNED`). |
| **11** | `11_component_architecture_diagram` | [.png](11_component_architecture_diagram.png) / [.svg](11_component_architecture_diagram.svg) | **Point 7 & 10:** Layered Monolith Architecture | Architectural component diagram: Client Tier (React SPA), API Gateway (FastAPI), Service Layer, Pure Domain, and MongoDB 6+. |
| **12** | `12_database_er_schema_diagram` | [.png](12_database_er_schema_diagram.png) / [.svg](12_database_er_schema_diagram.svg) | **Point 8:** Database Schema & Indexing | MongoDB collections, sequence IDs, foreign key references, unique constraints, and compound indexes mapped from domain classes. |
| **13** | `13_design_patterns_diagram` | [.png](13_design_patterns_diagram.png) / [.svg](13_design_patterns_diagram.svg) | **Point 4 & 5:** Design Patterns Architecture | Comprehensive design pattern map covering Strategy, Observer, State, Factory, Repository/Unit of Work, Singleton, and Decorator with code justifications. |

---

## How to View and Present During Evaluation

### 1. Interactive Web Presentation
Open [`index.html`](index.html) in your browser:
```bash
open diagrams/index.html
```
The viewer provides tabs for **PNG Photo** and **Vector SVG**, with 1-click fullscreen opening.

### 2. Direct PNG Inspection
Open any `.png` file directly on your desktop or embed it into your PowerPoint slides without any rendering dependencies.
