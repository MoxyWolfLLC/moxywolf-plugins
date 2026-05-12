# UX Specification Template

Use this template to document the purpose, user motivations, interaction behaviors, and state conditions for each screen or component BEFORE generating code. A completed UX spec feeds directly into the `/design` command's generation process.

## How This Template Maps to Frontend-Design Patterns

| Template Section | Informs | Plugin Pattern |
|---|---|---|
| 2.X.1 Purpose | Page type selection | Page Type Blueprints (dashboard, marketing, settings, etc.) |
| 2.X.2 User Motivations | Design direction | Density, mood, primary action decisions |
| 2.X.3 Key Components | Component selection | shadcn/ui Component Selection table |
| 2.X.4 Action Consequences | Feedback patterns | Dialog (destructive), Sonner/toast (success/error), inline confirmation |
| 2.X.5 State Conditions | Required states | Loading (Skeleton), Empty (icon + CTA), Error (message + retry) |
| 3.1 User Flow Narrative | Navigation design | Sidebar nav, tab structure, breadcrumbs |
| 7 Responsive | Breakpoint strategy | Mobile-first breakpoint table (default → sm → md → lg → xl) |
| 7 Accessibility | a11y requirements | WCAG AA checklist, semantic HTML, keyboard nav |

---

## Template

# UX Documentation for [Screen/Component Name]

* **Document Version:**
* **Date Created:**
* **Last Updated:**
* **Author(s):**

## 1. Title Page

1.1 **Document Title**
*Example: "<ProductName> Visual Specification"*

1.2 **Purpose Statement**
*Brief paragraph describing the goal of the document (e.g., to support design, development, and compliance review).*

## 2. Screen Overview Sections

*For each major UI screen or component, repeat the following structure:*

### 2.X [Screen Name]

(e.g., Dashboard, Project View, Analysis View, Rule Detail)

2.X.1 **Purpose**
*What is this screen for? What decisions or tasks does it support?*

→ **Design gate**: This answer determines the page type blueprint (SaaS dashboard, marketing landing, settings/admin, onboarding, or data table).

2.X.2 **User Motivations**

* Why do users come to this screen?
* What actions are they trying to complete?

→ **Design gate**: The primary action listed here becomes the single primary CTA for code generation. Secondary actions inform `Button variant="outline"` or `variant="ghost"` placement.

2.X.3 **Key Components**
*A numbered or bulleted breakdown of UI elements, annotated if necessary.*

→ **Design gate**: Map each element to a shadcn/ui component using the Component Selection table in the frontend-design skill.

2.X.4 **Action Consequences**

| **Action** | **Outcome** | **Can It Fail?** | **Confirmation / Undo** |
| ---------- | ----------- | ---------------- | ----------------------- |
| Click XYZ  | Description | Yes/No           | Tooltip/Modal/None      |

→ **Design gate**: This table determines which feedback patterns to implement:
- Destructive actions → `AlertDialog` with explicit confirmation
- Success feedback → `Sonner` toast (auto-dismiss)
- Failure feedback → `Sonner` toast with retry action or inline `FormMessage`
- Undo-capable → toast with "Undo" action button

2.X.5 **State Conditions**

| **Condition**           | **UI Behavior**                                |
| ----------------------- | ---------------------------------------------- |
| Empty / Loading / Error | What the user sees or can do in that state     |
| Conflict / Partial Data | UI indicators, error banners, disabled actions |

→ **Design gate**: Every condition listed here MUST have a corresponding implementation using the Three Required States pattern (Skeleton for loading, icon + CTA for empty, message + retry for error). Additional conditions (conflict, partial data) map to `Badge` status indicators or inline `Alert` components.

## 3. Cross-Screen Interactions

### 3.1 User Flow Narrative
*A paragraph-style walk-through from entry point (e.g., dashboard) through key screens, aligned to the user journey.*

→ **Design gate**: This narrative determines navigation structure (sidebar items, tab groupings, breadcrumb hierarchy) and informs which screens share layout shells.

### 3.2 Flow Diagram
*Optional: Include a rendered user flow (PlantUML, Mermaid, or image).*

## 4. Component-Level Detail (if needed)

*For technical audiences or XAI-driven systems.*

### 4.1 Detailed Component (e.g., Rule Evaluation)

* Expanded explanations, labels, data formats
* Embedded JSON output or data artifacts

## 5. Additional System States

*Reusable conditions or failure scenarios across screens.*

| **Scenario**                   | **UI Behavior**                                       |
| ------------------------------ | ----------------------------------------------------- |
| Network Failure / Timeout      | Banner: "Check network" / Retry option                |
| Conflicting Rules              | Alert: "Conflicting results – strictest rule applied" |
| Backend Error / Export Failure | Toast: "Export failed. Try again later."              |

→ **Design gate**: Each scenario maps to a reusable error component. Network failures → full-width `Alert` banner with `AlertDescription` and retry `Button`. Conflicts → inline `Alert` variant="destructive". Transient failures → `Sonner` toast with action.

## 6. Icon & Tag Legend

| **Symbol** | **Meaning**                      |
| ---------- | -------------------------------- |
| ✅          | Rule passed                      |
| ❌          | Rule failed                      |
| ⚪          | Rule not found / not applicable  |
| ❓          | Uncertain / manual review needed |

→ **Design gate**: Map each symbol to a `Badge` variant with semantic color (green-600, red-600, gray-400, yellow-600) and ensure accessible labels via `aria-label`.

## 7. Responsive Design Considerations

### Desktop (1200px+)

* Specifications

### Tablet (768px - 1199px)

* Specifications

### Mobile (< 768px)

* Specifications

→ **Design gate**: These specs override or extend the default mobile-first breakpoint strategy. Desktop maps to `lg:` and `xl:`, tablet to `md:`, mobile to default and `sm:`.

### Accessibility Requirements

* Specifications

→ **Design gate**: These requirements supplement the standard WCAG AA checklist. Any screen-specific a11y needs (e.g., ARIA live regions for real-time data, focus trapping in multi-step flows) are captured here and enforced in the output checklist.
