# AI Virtual Company - Design System

**Version:** 1.0
**Last Updated:** 2026-04-02
**Status:** Active

This document defines the visual language, component patterns, and implementation guidelines for the AI Virtual Company multi-agent collaboration system. All design work follows WCAG AA accessibility standards and a data-driven, professional aesthetic.

---

## Color System

The color palette is built around four agent roles, each with a distinct but cohesive personality. Colors are toned down for reduced cognitive load while maintaining clear visual distinction.

### Primary Agent Colors

| Role | Name | Hex | RGB | Usage | Accessibility |
|------|------|-----|-----|-------|----------------|
| Manager | Leadership Blue | `#4E7EBE` | rgb(78, 126, 190) | Agent card headers, decision badges, hierarchy indicators | WCAG AA on white |
| Developer | Technical Green | `#4A9B6F` | rgb(74, 155, 111) | Code blocks, technical indicators, development status | WCAG AA on white |
| Designer | Creative Purple | `#7C6BA8` | rgb(124, 107, 168) | Design assets, visual elements, creative work indicators | WCAG AA on white |
| Researcher | Analytical Amber | `#D4A055` | rgb(212, 160, 85) | Data visualizations, research badges, analytical insights | WCAG AA on white (7:1 ratio) |

### Neutral Colors

| Usage | Hex | RGB | Notes |
|-------|-----|-----|-------|
| Backgrounds | `#FFFFFF` | rgb(255, 255, 255) | Primary background |
| Surface | `#F7F9FC` | rgb(247, 249, 252) | Secondary backgrounds, panels |
| Borders | `#E1E7F0` | rgb(225, 231, 240) | Subtle dividers, input borders |
| Text Primary | `#1A202C` | rgb(26, 32, 44) | Body text, headings |
| Text Secondary | `#718096` | rgb(113, 128, 150) | Secondary text, captions, disabled states |
| Text Tertiary | `#A0AEC0` | rgb(160, 174, 192) | Placeholder text, hints |
| Hover | `#EDF2F7` | rgb(237, 242, 247) | Interactive element backgrounds |
| Active | `#E2E8F0` | rgb(226, 232, 240) | Active/pressed state backgrounds |

### Semantic Colors

| Purpose | Hex | RGB | Use Case |
|---------|-----|-----|----------|
| Success | `#2F855A` | rgb(47, 133, 90) | Voting results, successful actions, confirmations |
| Warning | `#C05621` | rgb(192, 86, 33) | Network warnings, incomplete states, cautions |
| Error | `#C53030` | rgb(197, 48, 48) | Error messages, failed operations, vote rejections |
| Info | `#2D3748` | rgb(45, 55, 72) | Information badges, neutral notifications |

---

## Typography

### Typeface

**Primary Font:** Geist (system fallback: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica Neue, sans-serif)

The Geist family provides a clean, modern aesthetic that works well at both small and large sizes. It's data-centric while remaining friendly, fitting the multi-agent communication context.

### Type Scale

| Role | Size | Weight | Line Height | Letter Spacing | Usage |
|------|------|--------|-------------|-----------------|-------|
| **H1 Headline** | 32px | 600 Bold | 1.4 (44px) | -0.01em | Main page titles, conversation topics |
| **H2 Section** | 24px | 600 Bold | 1.3 (31px) | -0.005em | Panel headers, agent names |
| **H3 Subsection** | 20px | 600 Bold | 1.3 (26px) | 0em | Card titles, voting topics |
| **Body Large** | 18px | 400 Regular | 1.5 (27px) | 0em | Important body text, agent responses |
| **Body** | 16px | 400 Regular | 1.5 (24px) | 0em | Default body text, chat messages |
| **Body Small** | 14px | 400 Regular | 1.5 (21px) | 0.01em | Secondary text, captions |
| **Label** | 12px | 500 Medium | 1.4 (17px) | 0.02em | Button labels, tags, chips |
| **Caption** | 11px | 400 Regular | 1.4 (15px) | 0.01em | Timestamps, metadata, hints |

### Text Colors by Context

- **Primary text on white:** `#1A202C` (Text Primary)
- **Secondary text on white:** `#718096` (Text Secondary)
- **Disabled text:** `#A0AEC0` (Text Tertiary)
- **Text on agent color backgrounds:** `#FFFFFF` (white) with 0.9 opacity for subtlety
- **Links:** Use agent color (e.g., Manager Blue for navigation, role-appropriate for agent-specific links)

---

## Spacing & Layout Grid

The system uses an 8px base grid for consistent spacing across all components.

### Spacing Scale

| Tokens | Value | Use Case |
|--------|-------|----------|
| xs | 4px | Micro spacing (icon spacing, internal button padding adjustments) |
| sm | 8px | Component internal padding, tight spacing |
| md | 12px | Default spacing between elements within components |
| lg | 16px | Spacing between components, input fields, card padding |
| xl | 24px | Section spacing, major layout dividers |
| 2xl | 32px | Container padding, page margins |
| 3xl | 48px | Large section separators |
| 4xl | 64px | Top-level layout spacing |

### Layout Grid (Main Dashboard)

The dashboard uses a responsive 3-column grid:

**Desktop (1440px+):**
```
┌─────────────┬──────────────────┬─────────────┐
│  Agent      │    Chat Window   │  Voting /   │
│  Panel      │   (Core)         │  Memory     │
│  (280px)    │  (1fr, flexible) │  (300px)    │
│             │                  │             │
└─────────────┴──────────────────┴─────────────┘
```
- Left sidebar (AgentPanel): 280px fixed
- Center (ChatWindow): flexible (1fr)
- Right sidebar (VotingPanel/MemoryPanel): 300px fixed
- Gutters: 16px between columns
- Page margins: 16px all sides

**Tablet (768px - 1440px):**
```
┌──────────────────────────────┐
│   Agent Panel (Top Tab)      │
├──────────────────────────────┤
│      Chat Window (Main)      │
├──────────────────────────────┤
│  Voting Panel (Modal/Bottom) │
└──────────────────────────────┘
```
- Single column, full width
- Agent panel switches to tab navigation
- Voting panel becomes modal or collapsible panel
- Page margins: 12px all sides

**Mobile (< 768px):**
```
┌──────────────┐
│  Agent Tabs  │
├──────────────┤
│ Chat (main)  │
├──────────────┤
│ Actions Bar  │
└──────────────┘
```
- Single column, full width
- Bottom navigation tabs for switching between panels
- Page margins: 8px all sides
- Touch targets: minimum 44px height

---

## Component Design Patterns

### Agent Card (Primary Component)

**Container:**
- Background: Agent color (from Primary Agent Colors)
- Border radius: 8px
- Padding: 12px
- Border: 1px solid (10% darker than background)
- Box shadow: 0 2px 8px rgba(0, 0, 0, 0.04)

**Content:**
- Agent name: H3, white text, 600 weight
- Role badge: 12px, white background at 20% opacity, rounded 4px
- Status indicator: 8px dot, positioned top-right
  - Active: `#2F855A` (Success green)
  - Thinking: `#4E7EBE` (Manager blue, animated pulse)
  - Idle: `#A0AEC0` (Tertiary gray)
  - Error: `#C53030` (Error red)

**Interactive States:**
- Hover: Opacity -0.05 (slightly darker)
- Active: Border changes to 2px, padding adjusted to 11px
- Focus: 2px focus ring at 2px offset

### Message Container (Chat)

**User Message:**
- Background: Agent color (matched to sender role, if agent-sent)
- Alignment: Right-aligned
- Padding: 12px 16px
- Border radius: 12px (rounded except bottom-right corner: 4px)
- Text color: White
- Max width: 75% of chat width

**Agent Response:**
- Background: `#F7F9FC` (Surface)
- Alignment: Left-aligned
- Padding: 12px 16px
- Border radius: 12px (rounded except bottom-left corner: 4px)
- Border left: 4px solid agent color
- Text color: `#1A202C` (Text Primary)
- Agent name above message: H4, agent color, 14px weight 600

**System Message (Decision/Voting Result):**
- Background: `#EDF2F7` (Hover)
- Border left: 4px solid `#2D3748` (Info)
- Padding: 12px 16px
- Border radius: 8px
- Icon: Left-aligned, 20px size, `#2D3748`
- Typography: Body small, `#718096` (Secondary text)

### Button

**Base Button (Primary):**
- Background: Agent color (context-dependent)
- Padding: 10px 16px (36px height total)
- Border radius: 6px
- Text: Label, white, 500 weight
- Border: None
- Cursor: pointer
- Transition: all 200ms ease

**States:**
- Default: Base styling
- Hover: Brightness +10%, shadow 0 4px 12px rgba(agent-color, 0.15)
- Active/Pressed: Brightness -10%, shadow inset 0 2px 4px rgba(0, 0, 0, 0.1)
- Disabled: Opacity 0.5, cursor not-allowed, no shadow
- Focus: 2px outline ring at 2px offset, outline color = agent color

**Secondary Button:**
- Background: Transparent
- Border: 1px solid agent color
- Text: Agent color
- Hover: Background = agent color at 5% opacity
- Active: Background = agent color at 10% opacity

**Ghost Button (Icon-only or minimal):**
- Background: Transparent
- Padding: 8px (36px height for square, 8px padding all sides)
- Border: None
- Icon size: 20px
- Hover: Background `#EDF2F7`
- Active: Background `#E2E8F0`

### Input Field

**Base Input:**
- Background: White (`#FFFFFF`)
- Border: 1px solid `#E1E7F0`
- Border radius: 6px
- Padding: 10px 12px
- Height: 36px (including padding)
- Font: Body, 16px
- Placeholder color: `#A0AEC0` (Text Tertiary)

**States:**
- Default: Base styling
- Hover: Border color → `#718096`
- Focus: Border color → agent color, outline none, box-shadow: 0 0 0 3px agent-color at 10% opacity
- Disabled: Background `#F7F9FC`, text `#A0AEC0`, border `#E1E7F0`
- Error: Border color `#C53030`, bottom border 2px instead of 1px
- Success: Border color `#2F855A`

**Text Area:**
- Same as input but min-height 80px
- Resize: vertical only
- Line height: 1.5

### Badge/Chip

**Style:**
- Background: Agent color at 15% opacity (light version)
- Text: Agent color
- Padding: 4px 8px
- Border radius: 4px
- Font: Label, 12px, 500 weight
- Border: None

**Variants:**
- Outlined: Border 1px agent color, transparent background, agent color text
- Solid: Agent color background, white text
- Muted: `#A0AEC0` text/border, `#EDF2F7` background

---

## Interactive States & Feedback

### Loading States

**Spinner (Indeterminate):**
- Size: 24px (16px in compact contexts)
- Color: Agent color (or primary blue for generic)
- Animation: Smooth rotation, 1s loop
- SVG: Circular arc, 4px stroke width

**Skeleton (Content Placeholder):**
- Background: `#E1E7F0`
- Animation: Subtle pulse from 100% to 95% opacity, 1.5s loop
- Used for: Agent cards, message previews, voting results

**Progress Bar (Linear):**
- Height: 4px
- Background: `#E1E7F0`
- Foreground: Agent color (or voted-for agent color)
- Border radius: 2px
- Animation: Smooth width transition, 300ms ease

### Hover & Focus States

**General:**
- Hover: Subtle background change, cursor pointer, shadow increase
- Focus: 2px ring outline, offset 2px, outline-color = agent color
- Active: Pressed effect (slight inset shadow), no hover shadow

**Keyboard Focus Visible:**
- All interactive elements must show focus ring on keyboard navigation
- Focus ring color: Agent color or primary blue
- Focus ring width: 2px
- Focus ring offset: 2px
- High contrast: 3:1 minimum contrast ratio

### Animations

**Micro-interactions:**
- Message appear: Fade in + slide up (200ms, ease-out)
- Button press: Scale 0.95 (100ms, ease-in-out)
- Hover transition: 150ms ease-out for color/shadow changes
- Loading spinner: Rotate 360deg (1s, linear, infinite)
- Voting result reveal: Stagger each agent result by 100ms

**System-wide motion:**
- Avoid flashing or strobing (≥3Hz)
- Respect `prefers-reduced-motion` media query
- Animations should aid understanding, not distract

---

## Voting Panel

**Container:**
- Background: Surface (`#F7F9FC`)
- Border: 1px solid Borders (`#E1E7F0`)
- Border radius: 8px
- Padding: 16px

**Structure:**
- Title: H3, "투표 진행 중" or "투표 결과"
- Topic: Body small, Text secondary, 12px
- Candidate cards: 4 per row (desktop), 2 per row (tablet), 1 per row (mobile)

**Candidate Card (Voting):**
- Background: White, border 1px `#E1E7F0`
- Padding: 12px
- Border radius: 6px
- Agent avatar: 32px circle, agent color
- Agent name: H4, Text primary
- Vote button: 36px, secondary style (border, no background)
- Hover: Background `#F7F9FC`, border brightens

**Candidate Card (After Vote):**
- Background: Agent color at 10% opacity
- Border: 2px solid agent color
- Vote checkbox: Visible, checked, agent color
- Percentage: Display vote count and percentage
- Bar: Linear progress below, agent color

**Results Display:**
- Winner badge: "✓ 선택됨" (green checkmark)
- Tally: "4/4 투표"
- Consensus type: "만장일치" or "3/4 합의" etc.

---

## Memory Panel

**Container:**
- Background: White
- Border left: 4px solid `#E1E7F0`
- Padding: 16px

**Tab Navigation:**
- Tabs: "전략", "목표", "프로젝트", "결정사항"
- Inactive tab: Text secondary, underline none
- Active tab: Text primary, underline 2px agent color
- Tab spacing: 16px between tabs

**Memory Item:**
- Background: Surface (`#F7F9FC`)
- Padding: 12px
- Border radius: 6px
- Margin bottom: 12px
- Category badge: Top-left, agent color
- Timestamp: Caption, Text tertiary, bottom-right
- Content: Body small, Text primary

**Search Input:**
- Full width of panel
- Margin bottom: 16px
- Placeholder: "메모리 검색..."

---

## Accessibility Standards

### WCAG AA Compliance

- **Color Contrast:** All text on colored backgrounds must meet 4.5:1 for body text, 3:1 for large text
- **Focus Indicators:** All interactive elements must have visible focus rings (minimum 2px outline)
- **Keyboard Navigation:**
  - Tab order follows visual flow
  - Tab targets include all buttons, inputs, links
  - Tab wrap-around at start and end
  - Escape key closes modals and dropdowns
- **Touch Targets:** Minimum 44px × 44px for all interactive elements
- **Motion:** Respect `prefers-reduced-motion: reduce` media query
- **Alt Text:** All images must have descriptive alt text
- **Semantic HTML:** Use `<button>`, `<input>`, `<nav>`, `<main>`, `<aside>` appropriately
- **Screen Reader:**
  - Use `aria-label` for icon-only buttons
  - Use `aria-live="polite"` for voting updates
  - Use `aria-current="page"` for active navigation
  - Use `role="status"` for status messages

### Dark Mode Support

Dark mode is **not required for Phase 1** but is designed for future implementation:

**Dark Mode Color Mapping:**
- Backgrounds: `#0F1419` (instead of white)
- Surfaces: `#1A202C` (instead of `#F7F9FC`)
- Borders: `#2D3748` (instead of `#E1E7F0`)
- Text primary: `#E2E8F0` (instead of `#1A202C`)
- Text secondary: `#A0AEC0` (instead of `#718096`)
- Agent colors: Increase brightness by 15% for text visibility

**Implementation:** CSS variables with `@media (prefers-color-scheme: dark)` media query.

---

## Implementation Guidelines

### CSS Architecture

**Approach:** CSS Modules + CSS Variables (Phase 2) → Tailwind CSS (Phase 3)

**Phase 1 (Current):**
- Component-scoped CSS Modules
- Color values as exported constants (colors.ts)
- No global styles except typography

**Phase 2:**
- Introduce CSS variables for theming
- Create utility classes for common patterns
- Maintain CSS Modules for components

**Phase 3:**
- Migrate to Tailwind CSS for utility-first styling
- Use tailwind.config.js for design tokens
- Replace CSS Modules with Tailwind classes

### Component File Structure

Each component should follow this pattern:

```
Component.tsx          // React component
Component.module.css   // Scoped styles
Component.types.ts     // TypeScript interfaces (if needed)
```

### Color Usage in Code

Use semantic token names, not raw hex:

```typescript
// ✓ Good
const managerColor = AGENT_COLORS.manager;
const buttonBg = semanticColors.success;

// ✗ Avoid
const color = '#4E7EBE';
const bgColor = '#2F855A';
```

### Font Implementation

Geist font can be loaded via:
- System fonts (current fallback stack)
- Google Fonts CDN (Phase 2)
- Local WOFF2 files (if performance-critical)

Current `index.html` should include:
```html
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@400;500;600&display=swap" rel="stylesheet">
```

### Breakpoints

Define breakpoints in `styles/breakpoints.ts`:

```typescript
export const breakpoints = {
  mobile: 320,
  tablet: 768,
  desktop: 1440,
} as const;

export const mediaQueries = {
  mobile: `@media (max-width: ${breakpoints.tablet - 1}px)`,
  tablet: `@media (min-width: ${breakpoints.tablet}px) and (max-width: ${breakpoints.desktop - 1}px)`,
  desktop: `@media (min-width: ${breakpoints.desktop}px)`,
} as const;
```

### Testing & Validation

- **Color Contrast:** Use WebAIM Contrast Checker or Chrome DevTools audit
- **Responsive:** Test at 320px, 768px, 1440px viewports
- **Focus States:** Keyboard-only navigation on all pages
- **Motion:** Test with `prefers-reduced-motion: reduce` enabled

---

## Future Considerations

### Phase 2 Enhancements
- Dark mode implementation
- Animation library (Framer Motion or Spring)
- Advanced typography (variable fonts)
- Micro-interaction refinements

### Phase 3 Integration
- Tailwind CSS migration
- Component library (Storybook)
- Design tokens auto-generation
- CSS-in-JS alternative evaluation

### Beyond
- Internationalization (i18n) – Korean + English typography
- RTL support (if needed)
- High contrast mode support
- Custom theming system per organization

---

## Design Token Export

All design tokens should be exportable for:
- Frontend CSS/Tailwind configuration
- Backend error message styling (if applicable)
- Documentation generation
- Design tool integration (Figma)

---

## References

- **Accessibility:** [WCAG 2.1 AA](https://www.w3.org/WAI/WCAG21/quickref/)
- **Typography:** [Geist Font](https://vercel.com/font)
- **Color Science:** [Accessible Colors](https://accessible-colors.com/)
- **Responsive Design:** [Mobile First Approach](https://responsivedesign.is/)

---

**Last Review:** 2026-04-02
**Next Review:** 2026-05-02 (after Phase 2 implementation)
**Ownership:** Frontend Team (Design System)
