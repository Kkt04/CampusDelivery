# 11. M1 presentation outline (about 12 minutes + demo + questions)

| # | Slide | Content | Time |
|---|---|---|---|
| 1 | Title | Campus Delivery Management System, your name, guide, date | 0:20 |
| 2 | Problem | Gate No. 2 today: paper registers, manual coordination, no proof of handover, no visibility of overdue or unidentified parcels | 1:00 |
| 3 | Objectives and scope | Seven objectives (01-requirements §1.2); what is in and out of M1 | 0:45 |
| 4 | Users and use cases | Three roles; use-case diagram | 0:45 |
| 5 | Architecture | Component diagram; layered modular monolith; why not microservices (one sentence each: scale, transactions, team) | 1:15 |
| 6 | Package lifecycle | State diagram; condition vs status vs overdue | 1:15 |
| 7 | Database | ER diagram; three key constraints: `UNIQUE(tracking_id)`, `UNIQUE(pickup_records.package_id)`, `CHECK occupied ≤ capacity` | 1:00 |
| 8 | OOP and SOLID | One concrete example per principle (07-solid-and-patterns) | 1:15 |
| 9 | Design patterns | State, Strategy, Repository + UoW, Observer, Factory; one trade-off each | 1:00 |
| 10 | Reliability | Double-pickup defence in four layers; atomic capacity; idempotency keys; notification failure isolation | 1:30 |
| 11 | Security | bcrypt, JWT, RBAC on server, hashed single-use codes, rate limit, audit log | 0:45 |
| 12 | Testing | 74 tests: categories and the concurrency test; ran on PostgreSQL and SQLite | 0:45 |
| 13 | Live demo | Follow the 5-minute demo script in README §6 | 5:00 |
| 14 | Limitations and next steps | From 10-limitations | 0:30 |
| 15 | Thank you / questions | | – |

**Demo tips.** Use two browser windows (normal + private) so the learner and the guard are signed in at
the same time. Before the demo, run `docker compose down -v && docker compose up --build`, or recreate the
database and reseed, so the data matches the script. Keep Swagger (`/docs`) open in a tab to show the
409 response from a second handover if faculty ask.
