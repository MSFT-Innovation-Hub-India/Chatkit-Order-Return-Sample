# ChatKit Industry Use Cases

This document outlines compelling industry scenarios where ChatKit's hybrid approach (natural language + contextual widgets) provides significant value.

---

## Table of Contents

1. [Manufacturing: Quality Inspection & Defect Logging](#1-manufacturing-quality-inspection--defect-logging)
2. [Retail: Customer Service Order Management](#2-retail-customer-service-order-management)
3. [HR: Employee Self-Service Portal](#3-hr-employee-self-service-portal)
4. [Field Service: Technician Work Order Management](#4-field-service-technician-work-order-management)
5. [Finance: Expense Approval Workflow](#5-finance-expense-approval-workflow)
6. [Comparison Matrix](#comparison-matrix)

---

## 1. Manufacturing: Quality Inspection & Defect Logging

### The Problem
Quality inspectors on the floor need to log defects quickly. Traditional apps require navigating menus. Voice/chat alone lacks structured data.

### ChatKit Solution

```
Inspector: "Found a scratch defect on production line 3, batch 2847"

AI: "I'll log that defect. Please confirm the details:"

┌─────────────────────────────────────────────────────────┐
│ 🔍 Defect Report                          [Draft]       │
├─────────────────────────────────────────────────────────┤
│ Line: [Line 3 ▼]     Batch: [2847     ]                │
│ Defect Type: [Scratch ▼]  Severity: [● Minor ○ Major]  │
│ Photo: [📷 Capture]                                     │
│ Root Cause: [_______________]                           │
│                                                         │
│ [Submit Report]  [Add Another]  [Escalate to Supervisor]│
└─────────────────────────────────────────────────────────┘

Inspector: "Actually severity is major, and it's affecting every 5th unit"

AI: *Updates widget* "Updated to Major. I'll also flag this as a 
    recurring issue and notify the line supervisor."
```

### Why It's Compelling
- NL captures initial context fast (hands might be dirty/gloved)
- Widget ensures all required fields are captured
- Can mix: speak the observation, tap to select from dropdowns
- Integrates with MES/ERP systems

### Key Features
- [ ] Defect type dropdown (pre-populated from quality standards)
- [ ] Photo capture integration
- [ ] Severity classification
- [ ] Automatic supervisor escalation
- [ ] Recurring issue detection

---

## 2. Retail: Customer Service Order Management

### The Problem
CS agents juggle multiple systems. Looking up orders, processing returns, applying discounts all require different screens.

### ChatKit Solution

```
Agent: "Customer Jane calling about order from last week"

AI: "I found 2 recent orders for Jane Smith:"

┌─────────────────────────────────────────────────────────┐
│ 📦 Order #ORD-78234              Delivered Dec 15      │
├─────────────────────────────────────────────────────────┤
│ • Blue Widget (x2)              $49.99                 │
│ • Premium Case                  $19.99                 │
│ Subtotal: $69.98  |  Status: ✅ Delivered              │
│                                                         │
│ [Start Return] [Track Package] [Apply Discount] [Notes]│
└─────────────────────────────────────────────────────────┘

Agent: "She wants to return the case, it was damaged"

AI: *Shows return widget*
┌─────────────────────────────────────────────────────────┐
│ ↩️ Return Request                                       │
├─────────────────────────────────────────────────────────┤
│ Item: Premium Case ($19.99)                            │
│ Reason: [Damaged/Defective ▼]                          │
│ Resolution: ● Refund  ○ Exchange  ○ Store Credit       │
│ Shipping: ● Prepaid Label  ○ Customer Drop-off         │
│                                                         │
│ [Process Return $19.99]  [Offer 20% Keep Discount]     │
└─────────────────────────────────────────────────────────┘
```

### Why It's Compelling
- Agent can describe situation naturally, AI finds the right data
- Widget actions are one-click (no navigating to return portal)
- AI can suggest actions ("Offer discount to keep item")
- Reduces average handle time significantly

### Key Features
- [ ] Order lookup by customer name, email, or order number
- [ ] Order history display with status
- [ ] One-click return initiation
- [ ] Discount application with approval workflow
- [ ] Customer communication templates

---

## 3. HR: Employee Self-Service Portal

### The Problem
Employees have questions but hate navigating HR portals. HR teams are overwhelmed with routine requests.

### ChatKit Solution

```
Employee: "I need to take Friday off for a doctor's appointment"

AI: "I'll submit a PTO request for you. You have 12 days remaining."

┌─────────────────────────────────────────────────────────┐
│ 🏖️ Time Off Request                                    │
├─────────────────────────────────────────────────────────┤
│ Type: [PTO ▼]      Date: [Jan 24, 2026]                │
│ Duration: ● Full Day  ○ Half Day (AM)  ○ Half Day (PM)│
│ Reason: Medical appointment (optional)                 │
│                                                         │
│ Manager: Sarah Johnson                                  │
│ Coverage: [Select backup ▼] or "AI will suggest"       │
│                                                         │
│ [Submit Request]  [Check Team Calendar First]          │
└─────────────────────────────────────────────────────────┘

Employee: "Actually make it half day afternoon"

AI: *Updates widget* "Updated to half day PM. Your calendar 
    shows a 2pm meeting - should I reschedule it?"
```

### Why It's Compelling
- Natural conversation for the request
- Widget ensures policy compliance (date format, approval flow)
- AI proactively identifies conflicts
- Works for: PTO, expense reports, benefits questions, onboarding tasks

### Key Features
- [ ] PTO balance display
- [ ] Team calendar conflict detection
- [ ] Manager approval workflow
- [ ] Meeting rescheduling integration
- [ ] Policy Q&A capability

---

## 4. Field Service: Technician Work Order Management

### The Problem
Technicians in the field need quick access to job details, parts ordering, and status updates while on-site.

### ChatKit Solution

#### Step 1: Arrival & Work Order Display

```
Tech: "Starting the HVAC repair at Contoso building B"

AI: "Found your 10 AM appointment. Here's the work order:"

┌─────────────────────────────────────────────────────────┐
│ 🔧 Work Order #WO-4521                    [In Progress]│
├─────────────────────────────────────────────────────────┤
│ Site: Contoso Corp - Building B, Floor 3               │
│ Issue: AC unit not cooling, reported 2 days ago        │
│ Equipment: Carrier 50XC (S/N: AC-8847)                 │
│ History: Last service 6 months ago (filter replaced)   │
│                                                         │
│ Checklist:                                              │
│ ☑ Check refrigerant levels                             │
│ ☐ Inspect compressor                                   │
│ ☐ Test thermostat                                      │
│ ☐ Clean coils                                          │
│                                                         │
│ [Order Parts] [Add Notes] [Request Backup] [Complete]  │
└─────────────────────────────────────────────────────────┘
```

#### Step 2: Part Ordering with Smart Options

```
Tech: "Compressor is shot, I need a replacement CR-440"

AI: "I'll check availability and schedule options:"

┌─────────────────────────────────────────────────────────────────────────────┐
│ 📦 Part Needed: CR-440 Compressor                                          │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│ AVAILABILITY CHECK:                                                        │
│ ┌─────────────────────────────────────────────────────────────────────────┐│
│ │ ❌ Your truck inventory      — Not in stock                            ││
│ │ ⚠️  Branch (12 miles away)   — 1 available, pickup by 4 PM today       ││
│ │ ✅ Warehouse                 — 3 in stock, deliver tomorrow 10 AM      ││
│ │ 🚐 Mike's truck (8 mi away)  — Has 1, he can meet you in 45 min        ││
│ └─────────────────────────────────────────────────────────────────────────┘│
│                                                                             │
│ SELECT OPTION:                                                             │
│ ○ Pick up from branch today (complete repair today)                       │
│ ● Ship to customer site tomorrow + schedule return visit                  │
│ ○ Coordinate with Mike (he's on another job, may delay him)               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Step 3: Return Visit Scheduling

```
Tech: "Ship it here, I'll come back tomorrow"

AI: "Got it. Let me check the customer's availability:"

┌─────────────────────────────────────────────────────────────────────────────┐
│ 📅 Schedule Return Visit                                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ Part ETA: Tomorrow (Jan 19) by 10:00 AM                                    │
│ Customer: Contoso Corp - Building B                                        │
│                                                                             │
│ Available slots (after part arrives):                                      │
│ ┌───────────────────────────────────────────────────────────────────────┐  │
│ │ ○ Tomorrow 10:30 AM - 12:00 PM  (first available)                    │  │
│ │ ● Tomorrow  1:00 PM -  2:30 PM  (customer preferred)                 │  │
│ │ ○ Tomorrow  3:00 PM -  4:30 PM                                       │  │
│ └───────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│ Notify customer: ● Email  ☑ SMS  ○ Call                                    │
│                                                                             │
│ [Confirm Order + Schedule]  [Call Customer First]                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### Step 4: Confirmation Summary

```
Tech: "1 PM works, confirm it"

AI: ✅ "Done! Here's the summary:"

┌─────────────────────────────────────────────────────────────────────────────┐
│ ✅ Work Order Updated                                                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ TODAY'S VISIT: Marked as "Diagnosis Complete - Parts Ordered"              │
│                                                                             │
│ PART ORDER:                                                                │
│ • CR-440 Compressor → Contoso Building B                                   │
│ • ETA: Tomorrow 10:00 AM                                                   │
│ • Tracking: Will notify you when shipped                                   │
│                                                                             │
│ RETURN VISIT SCHEDULED:                                                    │
│ • Tomorrow 1:00 PM - 2:30 PM                                               │
│ • Customer notified via Email + SMS                                        │
│ • Added to your calendar                                                   │
│                                                                             │
│ [Add Notes for Next Visit]  [View Updated Schedule]  [Next Job]            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Urgent Same-Day Scenario

For critical situations (e.g., hospital HVAC):

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ⚡ URGENT: Same-Day Options                                                │
├─────────────────────────────────────────────────────────────────────────────┤
│ Customer SLA: Critical (4-hour response)                                   │
│                                                                             │
│ ✅ FASTEST: Branch pickup (12 mi)                                          │
│    Leave now → Back by 3:45 PM → Complete by 5:30 PM                       │
│    [Get Directions] [Reserve Part]                                         │
│                                                                             │
│ ⚡ ALTERNATIVE: Mike can bring part                                        │
│    His current job ends ~4 PM → Here by 4:45 PM                            │
│    [Request Handoff] (Mike gets notified)                                  │
│                                                                             │
│ ⏱️ Express delivery: Part by 6 PM today (+$75 fee, customer approval req'd)│
│    [Request Customer Approval]                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Why It's Compelling

| Traditional Process | With ChatKit |
|---------------------|--------------|
| Call dispatcher | Chat: "Need CR-440" |
| Dispatcher checks inventory | AI shows all options instantly |
| Back-and-forth on scheduling | See customer availability in-widget |
| Manual calendar updates | Auto-syncs to tech's calendar |
| Customer gets a phone call | Auto SMS/email notification |
| Paperwork to update work order | Work order updated automatically |
| **~15-20 min process** | **~2 min process** |

### Key Features
- [ ] Work order display with equipment history
- [ ] Diagnostic checklist with progress tracking
- [ ] Multi-source inventory lookup (truck, branch, warehouse, other techs)
- [ ] Smart scheduling based on part ETA + customer availability
- [ ] Customer notification automation
- [ ] Work order state management (diagnosis → parts ordered → scheduled → complete)

---

## 5. Finance: Expense Approval Workflow

### The Problem
Managers receive expense reports via email, must log into expense system, review details, check policies, and approve/reject. Time-consuming and easy to miss.

### ChatKit Solution

```
Manager: "Show me pending expense reports"

AI: "You have 3 pending approvals ($2,847 total):"

┌─────────────────────────────────────────────────────────┐
│ 💰 Expense Approval Queue                               │
├─────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────┐│
│ │ Sarah Chen - Client Dinner        $487    [!Policy] ││
│ │ Dec 15 • NYC • 4 attendees                          ││
│ │ [View Receipt] [✓ Approve] [✗ Reject] [? Ask]       ││
│ └─────────────────────────────────────────────────────┘│
│ ┌─────────────────────────────────────────────────────┐│
│ │ Mike Ross - Travel to Seattle     $1,245            ││
│ │ Dec 18-20 • Flight + Hotel + Meals                  ││
│ │ [View Details] [✓ Approve] [✗ Reject] [? Ask]       ││
│ └─────────────────────────────────────────────────────┘│
│ ┌─────────────────────────────────────────────────────┐│
│ │ Lisa Park - Software License      $1,115  [!Budget] ││
│ │ Annual renewal • Figma Team                         ││
│ │ [View Details] [✓ Approve] [✗ Reject] [? Ask]       ││
│ └─────────────────────────────────────────────────────┘│
│                                                         │
│ [Approve All Standard] [Bulk Reject] [Export Report]   │
└─────────────────────────────────────────────────────────┘

Manager: "What's the policy flag on Sarah's dinner?"

AI: "The per-person limit is $100 for client dinners. 
    Sarah's comes to $121.75/person. However, the 
    client was Contoso (Tier 1 account) and she noted 
    it was a contract signing celebration."

Manager: "That's fine, approve it"

AI: *Updates widget, shows ✓ Approved on Sarah's expense*
    "Approved! Sarah will be notified. 2 remaining."
```

### Why This Is an Excellent Demo

1. **Everyone understands it** - managers, finance, employees
2. **Clear NL + Widget value** - ask questions naturally, act with one click
3. **Shows AI intelligence** - flags policy issues, provides context
4. **Obvious time savings** - no logging into Concur/SAP
5. **Easy to extend** - add receipt OCR, budget tracking, analytics

### Key Features
- [ ] Expense queue with policy violation flags
- [ ] Receipt image viewing
- [ ] Policy explanation on demand
- [ ] One-click approve/reject
- [ ] Bulk actions for standard expenses
- [ ] Submitter notification

---

## Comparison Matrix

| Use Case | NL Value | Widget Value | Implementation Effort | Demo Impact |
|----------|----------|--------------|----------------------|-------------|
| **Expense Approval** | Query policies, ask about flags | Approve/reject in one click | Medium | ⭐⭐⭐⭐⭐ |
| **Quality Defect Logging** | Describe defect naturally | Structured form with dropdowns | Medium | ⭐⭐⭐⭐ |
| **Customer Service** | Find orders, understand issue | Process returns, apply discounts | Higher | ⭐⭐⭐⭐ |
| **HR Self-Service** | Ask policy questions | Submit requests with validation | Medium | ⭐⭐⭐⭐ |
| **Field Service** | Check-in, describe issues | Checklists, parts ordering, scheduling | Higher | ⭐⭐⭐⭐⭐ |

---

## Implementation Notes

### Common Patterns Across Use Cases

1. **Query → Display → Action** flow
   - User asks a question (NL)
   - AI shows relevant widget with data
   - User takes action via widget button

2. **Progressive Disclosure**
   - Start with summary view
   - Drill down on demand ("What's the policy flag?")
   - Show detailed widget when needed

3. **AI-Assisted Context**
   - AI explains flags, warnings, exceptions
   - AI suggests actions based on context
   - AI proactively identifies conflicts/issues

4. **State Management**
   - Widget updates reflect actions immediately
   - Backend persists state changes
   - Notifications triggered automatically

### Technical Considerations

- **Data Integration**: Each use case needs API connections to backend systems (ERP, HRIS, CRM, etc.)
- **Authentication**: User context determines what data they can see/modify
- **Audit Trail**: All actions should be logged for compliance
- **Offline Support**: Field service may need offline capability

---

## Next Steps

1. Choose a use case to implement
2. Define the data model and mock data
3. Create widget builders in `use_cases/{use_case}/widgets.py`
4. Define agent tools in `use_cases/{use_case}/agent.py`
5. Implement action handlers in `use_cases/{use_case}/actions.py`
6. Test the full flow

---

*Document created: January 18, 2026*
