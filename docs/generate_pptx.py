#!/usr/bin/env python3
"""Generates the official Capstone Evaluation PPTX deck for Campus Delivery.

To run:
    pip install python-pptx
    python docs/generate_pptx.py
"""
import sys
import os

try:
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.enum.text import PP_ALIGN
    from pptx.dml.color import RGBColor
except ImportError:
    print("=" * 60)
    print("Notice: 'python-pptx' is not installed in the current environment.")
    print("To generate the PowerPoint (.pptx) file, please run:")
    print("    pip install python-pptx")
    print("    python docs/generate_pptx.py")
    print("=" * 60)
    sys.exit(0)

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)

# Color palette
DARK_BG = RGBColor(15, 23, 42)      # #0f172a
CARD_BG = RGBColor(30, 41, 59)      # #1e293b
ACCENT = RGBColor(59, 130, 246)     # #3b82f6
CYAN = RGBColor(56, 189, 248)       # #38bdf8
WHITE = RGBColor(248, 250, 252)     # #f8fafc
MUTED = RGBColor(148, 163, 184)     # #94a3b8

SLIDES_DATA = [
    {
        "title": "Campus Delivery Management System (CDMS)",
        "subtitle": "Gate No. 2 High-Concurrency Parcel Custody & Verification Architecture",
        "bullets": [
            "Final Year Capstone Project Evaluation: System Design & System Development (LLD)",
            "Evaluation Period: First Week of November 2026",
            "Zero-Loss Custody Chain: 4-layer defence-in-depth against double-handover fraud",
            "Atomic CAS Concurrency: Race-free shelf reservation & single-use pickup tokens",
            "81 Automated Tests: Unit, integration & race conditions with 100% pass rate",
            "Full Bilingual Localization: English and Hindi support across 3 actor dashboards"
        ],
        "image": "diagrams/11_component_architecture_diagram.png",
        "notes": "Good morning respected evaluators. Today we present CDMS for Gate No. 2 parcel management. We will demonstrate how our system strictly satisfies all 10 Low-Level Design evaluation criteria."
    },
    {
        "title": "Problem Statement: Gate No. 2 Operational Chaos",
        "subtitle": "The Operational Bottleneck at University Campus Entrance",
        "bullets": [
            "400+ Daily Shipments: Influx from Amazon, Flipkart, BlueDart, DTDC, India Post",
            "Manual Paper Registers: Illegible records, manual phone searching, zero instant audit",
            "Identity Impersonation: Students claiming others' parcels without cryptographic proof",
            "Shelf Overfill & Damage: Lack of capacity-aware storage leads to misplaced/broken goods",
            "Overdue Dormancy: Parcels languish for weeks with no automated student reminders",
            "Solution: 100% digital custody, salted HMAC-SHA256 tokens, automated 3-day overdue alerts"
        ],
        "image": "diagrams/01_use_case_diagram.png",
        "notes": "Gate No. 2 suffers from long student queues, lost parcels, and zero proof of delivery. CDMS solves this by digitizing the entire lifecycle with atomic CAS operations and cryptographic verification."
    },
    {
        "title": "End-to-End System Architecture (Layered Monolith)",
        "subtitle": "Clean / Onion Architecture with Zero-Dependency Domain Core",
        "bullets": [
            "Presentation Layer: React 18, TypeScript, Tailwind CSS, Lucide, Bilingual i18n",
            "API Layer: FastAPI REST routes, OAuth2 JWT bearer auth, Pydantic v2 DTOs, Role-Aware Presenters",
            "Application Services: PackageIntakeService, StorageAllocationService, PickupService",
            "Pure Domain Core: Finite State Machine table & guards, Strategy algorithms, EventBus",
            "Persistence: Unit of Work & PyMongo Repositories with atomic CAS queries",
            "Architectural Decision: Layered Monolith chosen over microservices to eliminate distributed 2PC latency"
        ],
        "image": "diagrams/11_component_architecture_diagram.png",
        "notes": "We chose a Layered Modular Monolith over microservices. A campus gate needs sub-15ms latency and atomic consistency without the complexity of distributed two-phase commits."
    },
    {
        "title": "Criterion 1: Requirement Analysis (FRs, NFRs & Actors)",
        "subtitle": "Role-Based Access Control and System Boundaries",
        "bullets": [
            "Three Strict Human Actors: Security Staff, Learners, and Operations Admins",
            "FR-1 to FR-3: Rapid intake barcode scanning, size-aware bin allocation, multi-channel alerts",
            "FR-4 to FR-6: Cryptographic one-time pickup tokens, atomic handover, dispute management",
            "NFR-1 (Atomicity): Zero double-delivery, zero shelf overfills under concurrency",
            "NFR-2 (Security): Student data isolation; salted HMAC tokens never stored in plaintext",
            "NFR-3 (Idempotency): Safe mutation retries via client-supplied Idempotency-Key headers"
        ],
        "image": "diagrams/01_use_case_diagram.png",
        "notes": "We rigorously enforce boundaries across 3 actors. Our NFRs guarantee that even under heavy concurrent staff interactions, no parcel can ever be double-collected."
    },
    {
        "title": "Criterion 2: Class Diagram & Domain Entities",
        "subtitle": "Document Entity Hierarchy & Structural Multiplicities",
        "bullets": [
            "Document Base Model: Common identity (id: int), timestamps, serialization (to_doc, from_doc)",
            "10 Derived Entities: User, Package, StorageLocation, PickupToken, PickupRecord, Incident, etc.",
            "Multiplicity: User (1) -- (0..*) Package (Student owns zero or many packages)",
            "Multiplicity: Package (0..1) -- (0..1) StorageLocation (occupied_count <= capacity)",
            "Multiplicity: Package (1) -- (0..*) PickupToken (At most one active token)",
            "Multiplicity: Package (1) -- (0..1) PickupRecord (Handover proof; UNIQUE(package_id))"
        ],
        "image": "diagrams/02_class_diagram_domain_entities.png",
        "notes": "In backend/app/infrastructure/models.py, ten core entities inherit from Document. The 1 to 0..1 relationship between Package and PickupRecord is locked by a unique database index."
    },
    {
        "title": "Criterion 3: Object-Oriented Design (4 Pillars)",
        "subtitle": "Abstraction, Encapsulation, Inheritance, and Polymorphism in Action",
        "bullets": [
            "Abstraction: StorageAllocationStrategy and NotificationChannel defined via typing.Protocol",
            "Encapsulation: StorageCandidate.accepts(size) encapsulates dimension & free slot validation",
            "Encapsulation: PackageTransitioner.apply() encapsulates status change, audit, and events",
            "Inheritance: Document base model inherited by 10 entities; custom AppException hierarchy",
            "Polymorphism: SuitableSizeStrategy & FirstAvailableStrategy satisfy rank() polymorphically"
        ],
        "image": "diagrams/03_class_diagram_services_and_architecture.png",
        "notes": "We use typing.Protocol for structural subtyping. Services depend purely on abstractions, and business constraints are tightly encapsulated within domain value objects."
    },
    {
        "title": "Criterion 4: SOLID Principles Mapped to Code",
        "subtitle": "Direct Code Evidence for S, O, L, I, and D Principles",
        "bullets": [
            "S (Single Responsibility): Dedicated services (PackageIntakeService, StorageAllocationService, PickupService)",
            "O (Open/Closed): Strategies and notification channels registered in container.py without editing services",
            "L (Liskov Substitution): Strategies and channels honor identical contracts without side effects",
            "I (Interface Segregation): Micro-protocols with single methods (rank(), send())",
            "D (Dependency Inversion): Services receive abstract protocols; wired in Composition Root (container.py)"
        ],
        "image": "diagrams/13_design_patterns_diagram.png",
        "notes": "Each service has one reason to change. If a new SMS channel or storage strategy is introduced, we simply add a class and register it in container.py without modifying existing workflows."
    },
    {
        "title": "Criterion 5: Design Patterns & Architectural Justifications",
        "subtitle": "State, Strategy, Observer, Repository, Unit of Work, and Factory",
        "bullets": [
            "State Pattern (Table FSM): 12 statuses, 19 valid edges with guards in domain/state_machine.py",
            "Strategy Pattern: SuitableSizeStrategy vs. FirstAvailableStrategy in domain/allocation.py",
            "Observer Pattern: In-process EventBus publishes PackageStatusChanged to NotificationDispatcher",
            "Repository & Unit of Work: Decouples PyMongo queries and coordinates atomic transactions",
            "Factory Pattern: NotificationChannelFactory builds configured notification channels"
        ],
        "image": "diagrams/10_state_machine_diagram.png",
        "notes": "Our table-driven State machine eliminates spaghetti if/elif statements while avoiding 12 bloated GoF classes. Observer pattern decouples notification delivery from database commits."
    },
    {
        "title": "Criterion 6: Sequence & Activity Diagrams",
        "subtitle": "Intake, Cryptographic Token Issuance, and Handover Concurrency",
        "bullets": [
            "Intake Flow: Courier scan -> Student match -> Strategy rank -> Atomic shelf reserve -> Stored",
            "Token Issuance: Ownership check -> Revoke active -> HMAC-SHA256 salted hash -> 30-min timer",
            "Handover Sequence: Lock package -> Validate recipient & token -> Atomic mark_used() CAS",
            "Handover Completion: Update COLLECTED -> Release shelf -> Write immutable PickupRecord",
            "Alternate Flows: Expired token (400), 3 wrong attempts (Locked), Damaged package diversion"
        ],
        "image": "diagrams/07_sequence_pickup_handover_concurrency.png",
        "notes": "This sequence diagram details our concurrent handover verification. The atomic CAS operation mark_used() guarantees that exactly one guard can collect a package."
    },
    {
        "title": "Criterion 7: API & Interface Design (RESTful Clean Architecture)",
        "subtitle": "Pydantic v2 DTOs, Role-Aware Presenters, and Idempotency",
        "bullets": [
            "Resource Hierarchy: /api/v1/packages, /api/v1/pickups, /api/v1/storage, /api/v1/incidents",
            "Pydantic Validation: Institutional ID regex, phone regex, courier tracking normalizers",
            "Role-Aware Presenters: presenters.py masks internal security notes when viewed by students",
            "RFC 7807 Error Responses: Standardized JSON payloads (code, message, detail)",
            "Network Idempotency: Mutation endpoints support Idempotency-Key with SHA-256 fingerprinting"
        ],
        "image": "diagrams/06_sequence_pickup_request_and_token.png",
        "notes": "Our REST API enforces strict validation and privacy masking. Role-aware presenters ensure students never see staff notes or internal guard IDs."
    },
    {
        "title": "Criterion 8: Database Schema, Indexing & Concurrency Control",
        "subtitle": "10 Collections, Compound Indexes, and Atomic CAS Queries",
        "bullets": [
            "Unique Indexes: users.institutional_id, packages.tracking_id, pickup_records.package_id",
            "Compound Indexes: packages(status, arrived_at), notifications(user_id, created_at)",
            "Atomic CAS Shelf Reservation: find_one_and_update with $expr: {$lt: ['$occupied_count', '$capacity']}",
            "Atomic CAS Token Redemption: find_one_and_update with used_at: None, revoked_at: None",
            "Double Handover Defense: pickup_records.package_id unique index rejects secondary insertions"
        ],
        "image": "diagrams/12_database_er_schema_diagram.png",
        "notes": "We achieve race-free execution in MongoDB using atomic Compare-And-Swap operations. Two concurrent requests for the final shelf slot cannot both win."
    },
    {
        "title": "Criterion 9: Error Handling, Validation & 20 Edge Cases",
        "subtitle": "Defensive Architecture, Brute-Force Lockout & Overdue Automation",
        "bullets": [
            "Comprehensive Domain Exceptions: AppException -> ConflictError, NotFoundError, etc.",
            "Double Handover Race: Prevented by atomic token CAS & unique pickup_records index",
            "Brute Force Lockout: 3 failed attempts lock token; IP sliding window rate limit",
            "Zero-Knowledge Token Storage: Salted HMAC-SHA256 hash stored; plaintext never in database",
            "Damaged on Intake: Diverts to DAMAGED state and opens incident investigation ticket",
            "Automated 3-Day Overdue: Daily notifications sent; awaiting_storage counter incremented"
        ],
        "image": "diagrams/09_activity_concurrency_storage_handover.png",
        "notes": "We designed defensive programming guards for over 20 real-world edge cases, from brute-force token lockouts to automated 3-day overdue tracking."
    },
    {
        "title": "Criterion 10: Working Implementation & Testing Rigor",
        "subtitle": "81 Automated Pytest Suites & Bilingual React Application",
        "bullets": [
            "Backend: Python 3.12, FastAPI, PyMongo, Pydantic v2, Pytest (81 tests passing)",
            "Frontend: React 18, TypeScript, Vite, Tailwind CSS, Lucide Icons, Context state",
            "Accessibility: 100% Hindi/English Bilingual Localization toggle across all pages",
            "Test Coverage: test_allocation, test_rules, test_state_machine, test_auth, test_pickup",
            "Concurrency Test: test_concurrent_handover_results_in_exactly_one_collection passes"
        ],
        "image": "diagrams/08_activity_package_lifecycle.png",
        "notes": "Our entire system is backed by 81 automated tests that verify state transitions, role security, and concurrent handovers with a 100% pass rate."
    },
    {
        "title": "5-Minute Live System Evaluation Demonstration",
        "subtitle": "Dual-Browser Live Walkthrough Across Guard and Student Roles",
        "bullets": [
            "Step 1: Guard intakes Amazon shipment AMZ-998811; matches student Ananya Iyer",
            "Step 2: SuitableSizeStrategy auto-allocates optimal shelf slot G2-A1",
            "Step 3: Student receives real-time notification; clicks [Get Pickup Code]",
            "Step 4: System generates 6-digit code with live 30-minute countdown timer",
            "Step 5: Guard enters ID & code -> Atomic verification & handover completion",
            "Step 6: Guard re-submits identical code -> System returns 409 Conflict rejection"
        ],
        "image": "diagrams/07_sequence_pickup_handover_concurrency.png",
        "notes": "Now we present our live demonstration. In side-by-side browser windows, we show intake, auto-allocation, token generation, handover, and our instant 409 conflict rejection on duplicate pickup."
    },
    {
        "title": "Limitations, Scalability & Production Roadmap",
        "subtitle": "Acknowledging Design Trade-offs & Future Multi-Campus Growth",
        "bullets": [
            "Current Boundaries (M1): Single-node MongoDB, in-process EventBus, console mock SMS",
            "Multi-Gate Sharding (M2): Shard MongoDB collections by campus_id and gate_id",
            "Transactional Outbox: Apache Kafka / RabbitMQ broker for guaranteed event streaming",
            "AI Barcode OCR Camera: Hardware camera integration at Gate No. 2 for 2-second touchless intake",
            "Disaster Recovery: Point-in-time oplog backups with 99.99% availability SLA"
        ],
        "image": "diagrams/11_component_architecture_diagram.png",
        "notes": "For Milestone 1, our architecture handles 5,000 students effortlessly. For Milestone 2, our roadmap introduces database sharding and the Transactional Outbox pattern."
    },
    {
        "title": "Conclusion & Master Viva Defense Matrix",
        "subtitle": "10/10 Evaluation Criteria Satisfied with Verifiable Code Rigor",
        "bullets": [
            "State Machine Table: backend/app/domain/state_machine.py:63",
            "Strategy Pattern: backend/app/domain/allocation.py:31",
            "Atomic Storage CAS: backend/app/repositories/mongo_repos.py:338",
            "Atomic Token CAS: backend/app/repositories/mongo_repos.py:384",
            "Anti-Double Handover: backend/app/services/pickup.py:81",
            "Composition Root (DIP): backend/app/container.py:30",
            "Thank you! We welcome the evaluation committee's questions and code review."
        ],
        "image": "diagrams/13_design_patterns_diagram.png",
        "notes": "In conclusion, CDMS fulfills every LLD requirement. We have our codebase and tests open for your inspection. Thank you!"
    }
]

blank_slide_layout = prs.slide_layouts[6]  # blank layout

for idx, data in enumerate(SLIDES_DATA):
    slide = prs.slides.add_slide(blank_slide_layout)
    
    # Background shape
    bg = slide.shapes.add_shape(1, 0, 0, prs.slide_width, prs.slide_height)  # MSO_SHAPE.RECTANGLE
    bg.fill.solid()
    bg.fill.fore_color.rgb = DARK_BG
    bg.line.fill.background()

    # Header Box
    header_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.5), Inches(11.7), Inches(1.3))
    tf = header_box.text_frame
    tf.word_wrap = True
    
    p = tf.paragraphs[0]
    p.text = data["title"]
    p.font.size = Pt(26)
    p.font.bold = True
    p.font.color.rgb = WHITE

    p2 = tf.add_paragraph()
    p2.text = data["subtitle"]
    p2.font.size = Pt(14)
    p2.font.color.rgb = CYAN
    p2.space_before = Pt(4)

    # Left content box (Bullets)
    content_box = slide.shapes.add_textbox(Inches(0.8), Inches(2.0), Inches(6.8), Inches(4.8))
    ctf = content_box.text_frame
    ctf.word_wrap = True
    
    for i, bullet in enumerate(data["bullets"]):
        p = ctf.add_paragraph() if i > 0 else ctf.paragraphs[0]
        p.text = f"•  {bullet}"
        p.font.size = Pt(14)
        p.font.color.rgb = WHITE
        p.space_after = Pt(10)

    # Right side: Diagram Image if exists
    img_path = data.get("image")
    if img_path and os.path.exists(img_path):
        slide.shapes.add_picture(img_path, Inches(7.8), Inches(2.0), width=Inches(4.8))

    # Speaker notes
    if "notes" in data and hasattr(slide, "notes_slide"):
        slide.notes_slide.notes_text_frame.text = data["notes"]

output_path = "docs/CampusDelivery_Capstone_Presentation.pptx"
prs.save(output_path)
print(f"Successfully generated PowerPoint presentation at: {output_path}")
