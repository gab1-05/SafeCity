# SDG Alignment — SafeCity

## Selected SDG: 11 — Sustainable Cities and Communities

**Target 11.3:** By 2030, enhance inclusive and sustainable urbanization and capacity for participatory, integrated and sustainable human settlement planning and management in all countries.

SafeCity directly advances Target 11.3 by giving citizens a participatory channel to report civic incidents, track their resolution, and hold authorities accountable — making urban governance inclusive, transparent, and data-driven.

---

## Feature-to-Target Mapping

| # | SafeCity feature | SDG 11.3 indicator addressed | How it contributes |
|---|-----------------|------------------------------|--------------------|
| 1 | Citizen incident reporting (7-step wizard with anonymity option) | Participatory urban governance | Enables any citizen to report potholes, sanitation, safety issues without needing to visit an office or know the right department. |
| 2 | Role-based access (citizen, department staff, responder, admin) | Inclusive institutional participation | Different stakeholder groups have appropriate visibility and action rights, ensuring inclusive decision-making. |
| 3 | SLA tracking with escalation rules | Sustainable urban management | Departments are accountable for resolution timelines; breached SLAs auto-escalate so issues don't stagnate. |
| 4 | Public incident map | Transparency in urban services | Citizens can see reported incidents and their status in their neighbourhood, building trust and participation. |
| 5 | Anonymous reporting | Inclusive participation for vulnerable groups | Victims of unsafe conditions can report without fear of retaliation, lowering barriers to participation. |
| 6 | Authority dashboard & workflow panel | Integrated human settlement planning | Authorities see a consolidated view of incidents across departments, enabling data-driven resource allocation. |
| 7 | Role requests & permission guards | Participatory governance guardrails | Citizens can request elevated roles; admins review and approve, ensuring transparent access control. |
| 8 | Audit log of all state changes | Accountability in public service | Every incident transition is immutably recorded with actor, timestamp, and changes — enabling oversight. |
| 9 | Media attachments (photos of incidents) | Evidence-based urban management | Visual evidence supports faster, better-targeted municipal responses. |
| 10 | Departmental workload analytics | Sustainable resource allocation | Analytics surface which departments/wards have the most open or overdue incidents, guiding budget and staffing. |
| 11 | Password policy, lockout, 2FA | Trust in digital public services | Security controls protect citizen data, encouraging adoption of the digital participation channel. |
| 12 | API-first design with OpenAPI spec | Interoperable urban data | The API can be integrated with other municipal systems, supporting integrated settlement planning. |

---

## Stakeholder Validation — The Bombay Salesian Society

**Role:** Client institution and evaluation partner for the SafeCity SDP.

**Validation evidence:**
- The Bombay Salesian Society is identified as the client institution in `docs/README.md` and `docs/ARCHITECTURE.md`.
- They are listed as evaluators who "assess architecture, process, and delivery quality" in `docs/OVERVIEW.md`.
- The project addresses their stated need: fragmented civic complaint channels (phone, WhatsApp, walk-ins, departmental inboxes) with no visibility into what is outstanding or who is working on it.
- The seed data includes civic departments (Health Services, Sanitation, etc.) relevant to a municipal/society context.

**Stakeholder needs addressed:**
| Stakeholder need | SafeCity response |
|------------------|-------------------|
| Citizens need a single channel to report issues | 7-step reporting wizard with web + anonymous options |
| Authorities need to see what's outstanding | Authority dashboard with incident queue and workflow |
| Departments need SLA accountability | SLA tracking with auto-escalation on breach |
| Everyone needs transparency | Public incident map with real-time status |

---

## Measurable Outcome Indicators

| Indicator | Baseline | Target | Measurement method |
|-----------|----------|--------|-------------------|
| Incidents reported per month | 0 (no system) | 50+ | Count of Incident records created |
| Average resolution time | Not tracked | < 7 days for low/medium, < 24h for emergency | `sla_deadline` vs `resolved_at` in Incident model |
| SLA compliance rate | 0% | ≥ 80% resolved within SLA | `sla_breached` flag analytics |
| Citizen reports with anonymity | 0% | ≥ 10% of reports | `is_anonymous` field on Incident |
| Departments using the dashboard | 0 | All active departments | Active users in `UserRole.DEPARTMENT_STAFF` |
| Repeat citizen usage | Not measured | ≥ 30% of citizens submit > 1 report | Reporter field grouping on Incident |

---

## Transparency Deviations

- The public map shows incident locations but anonymizes reporter identity for anonymous reports.
- SLA deadlines are configured per severity (low: 120h, medium: 72h, high: 24h, critical: 6h) in `seed_demo_data.py`; actual municipal SLAs may differ and should be configured by the deploying authority.
- Google OAuth is not available on tunnel/demo URLs (Google requires pre-registered redirect URIs); username/password login is the demo path.
