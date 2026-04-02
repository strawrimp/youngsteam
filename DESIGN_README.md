# Design System - Quick Start

The design system is now complete and ready for implementation. Here's what exists and how to use it.

## Files Created

### Documentation

- **DESIGN.md** — Complete design system specification
  - Color palette (agent colors, neutral colors, semantic colors)
  - Typography system (Geist font, type scale)
  - Spacing & layout grid (8px base grid, responsive breakpoints)
  - Component design patterns (buttons, inputs, cards, messages, etc.)
  - Accessibility standards (WCAG AA, focus rings, keyboard navigation)
  - Implementation guidelines

- **DESIGN_SETUP.md** — Step-by-step implementation guide
  - How to install Tailwind CSS and dependencies
  - How to configure Vite and PostCSS
  - How to update existing components to use Tailwind
  - How to integrate shadcn/ui (Phase 3)
  - Troubleshooting and verification checklist

### Configuration Files

- **tailwind.config.ts** — Design tokens in Tailwind format
  - Agent colors (manager, developer, designer, researcher)
  - Neutral colors (surfaces, borders, text)
  - Semantic colors (success, warning, error, info)
  - Typography scale (Geist font with 8 size variants)
  - Spacing scale (8px-based grid: xs to 4xl)
  - Box shadows, animations, and transitions

- **postcss.config.cjs** — PostCSS configuration
  - Enables Tailwind CSS and Autoprefixer in the build pipeline

- **frontend/src/styles/globals.css** — Global styles & components
  - Tailwind directives (@tailwind base, components, utilities)
  - Base HTML element styling
  - Component classes (.btn, .input, .badge, .card, .message-*, etc.)
  - Accessibility utilities (sr-only, focus-visible-ring)
  - Responsive utilities
  - Dark mode and high contrast support (future-ready)
  - Reduced motion support

## Design Palette (Approved)

### Agent Colors

| Role | Color | Hex | Usage |
|------|-------|-----|-------|
| Manager (Leadership) | Blue | `#4E7EBE` | Headers, decisions, hierarchy |
| Developer (Technical) | Green | `#4A9B6F` | Code, technical indicators |
| Designer (Creative) | Purple | `#7C6BA8` | Design assets, visuals |
| Researcher (Analytical) | Amber | `#D4A055` | Data, insights, research |

### Typography

- **Font:** Geist (with system fallbacks)
- **Sizes:** 32px (H1) → 11px (caption)
- **Base:** 16px (body), line-height 1.5
- **Weights:** 400 (regular), 500 (medium), 600 (bold)

### Spacing

- **Base grid:** 8px
- **Scale:** 4px, 8px, 12px, 16px, 24px, 32px, 48px, 64px
- **Padding:** 8px (component internal), 16px (between components)
- **Margins:** 16px (sections), 24px (major dividers)

## Implementation Phases

### Phase 1: Install & Configure ✓
- [x] Design system documentation complete
- [x] Tailwind CSS config created
- [ ] Dependencies installed (`npm install -D tailwindcss`)
- [ ] Styles entry point added to main.tsx
- [ ] Geist font imported in index.html

→ **See:** DESIGN_SETUP.md "Phase 1: Install Dependencies"

### Phase 2: Migrate Components (Next)
- [ ] Update ChatWindow.tsx to use Tailwind
- [ ] Update AgentPanel.tsx with agent colors
- [ ] Update VotingPanel.tsx for voting UI
- [ ] Remove old CSS module files
- [ ] Test responsive layout at different breakpoints
- [ ] Verify accessibility (keyboard focus, contrast, touch targets)

→ **See:** DESIGN_SETUP.md "Phase 2: Refactor Existing Components"

### Phase 3: shadcn/ui Integration
- [ ] Install shadcn/ui components
- [ ] Replace Tailwind-only buttons with shadcn buttons
- [ ] Add form components for input fields
- [ ] Add card and dialog components
- [ ] Create component library documentation

→ **See:** DESIGN_SETUP.md "Phase 4: Install shadcn/ui"

### Phase 4: Polish & Dark Mode
- [ ] Add dark mode CSS variables
- [ ] Test dark mode in browser
- [ ] Create Storybook documentation
- [ ] Performance optimization
- [ ] Mobile responsive refinements

### Phase 5: Live Deployment
- [ ] Build and test production bundle
- [ ] Performance audit (Lighthouse)
- [ ] Accessibility audit (WAVE, axe)
- [ ] Cross-browser testing
- [ ] Deploy to production

## Quick Commands

```bash
# Install Tailwind dependencies (Phase 1)
cd frontend
npm install -D tailwindcss postcss autoprefixer @tailwindcss/forms

# Start dev server (works after Phase 1)
bun run dev

# Test at different viewport sizes
# Chrome DevTools → F12 → Toggle device toolbar (Ctrl+Shift+M)
```

## Component Examples

Once Tailwind is installed, components will look like:

```typescript
// Agent Card using Tailwind
<div className="rounded-md p-md text-white shadow-sm"
     style={{ backgroundColor: '#4E7EBE' }}>
  <h3 className="text-lg font-semibold mb-xs">Agent Name</h3>
  <span className="inline-block text-xs opacity-80">role</span>
</div>

// Message using Tailwind
<div className="message-user rounded-[12px] rounded-br-sm text-white px-lg py-md">
  Hello, how can I help?
</div>

// Button using Tailwind
<button className="btn bg-agent-manager text-white px-lg py-md rounded-sm">
  Cast Vote
</button>
```

## Verification Checklist

Before moving to Phase 2:
- [ ] Read DESIGN.md completely
- [ ] Run `npm install -D tailwindcss` successfully
- [ ] Update `main.tsx` to import `globals.css`
- [ ] Update `index.html` with Geist font link
- [ ] Restart dev server: `bun run dev`
- [ ] No console errors or warnings

Before Phase 3:
- [ ] All components using Tailwind classes (no CSS modules)
- [ ] Responsive layout tested at 320px, 768px, 1440px
- [ ] Keyboard navigation works (Tab through all elements)
- [ ] Focus rings visible on all interactive elements
- [ ] Touch targets are 44px minimum
- [ ] Color contrast tested (WebAIM Contrast Checker)

## FAQ

**Q: Why Tailwind instead of CSS Modules?**
A: Tailwind provides a consistent design system out of the box. It's faster to build, easier to maintain consistency, and pairs well with shadcn/ui components.

**Q: Do I need to use shadcn/ui?**
A: No, shadcn/ui is optional. Tailwind alone is sufficient. shadcn/ui is helpful for complex components like dialogs, dropdowns, and forms.

**Q: Can I use this with other CSS-in-JS libraries?**
A: Yes, Tailwind works alongside styled-components, Emotion, etc. But it's not recommended — stick with Tailwind classes for simplicity.

**Q: How do I customize colors for specific agents?**
A: Use the AGENT_COLORS constant and apply dynamically:

```typescript
import { AGENT_COLORS } from '../constants/colors'

<div style={{ backgroundColor: AGENT_COLORS[agentRole] }} />
```

**Q: Will dark mode break existing styles?**
A: No, dark mode CSS is contained in a media query. Light mode remains default until dark mode is explicitly enabled.

## Support & Resources

- **Tailwind Documentation:** https://tailwindcss.com/docs
- **shadcn/ui Components:** https://ui.shadcn.com
- **Color Contrast Checker:** https://webaim.org/resources/contrastchecker/
- **WCAG Guidelines:** https://www.w3.org/WAI/WCAG21/quickref/
- **Design File:** See DESIGN.md for complete specifications

## Next Steps

1. **Review DESIGN.md** to understand the complete design system
2. **Follow DESIGN_SETUP.md** to install Tailwind CSS
3. **Update components** to use Tailwind classes
4. **Test responsiveness** at different viewport sizes
5. **Verify accessibility** using browser tools and keyboard navigation

---

**Status:** Ready for Phase 1 installation
**Last Updated:** 2026-04-02
**Design System Version:** 1.0
