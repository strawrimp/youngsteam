
## Skill routing

When the user's request matches an available skill, ALWAYS invoke it using the Skill
tool as your FIRST action. Do NOT answer directly, do NOT use other tools first.
The skill has specialized workflows that produce better results than ad-hoc answers.

Key routing rules:
- Product ideas, "is this worth building", brainstorming → invoke office-hours
- Bugs, errors, "why is this broken", 500 errors → invoke investigate
- Ship, deploy, push, create PR → invoke ship
- QA, test the site, find bugs → invoke qa
- Code review, check my diff → invoke review
- Update docs after shipping → invoke document-release
- Weekly retro → invoke retro
- Design system, brand → invoke design-consultation
- Visual audit, design polish → invoke design-review
- Architecture review → invoke plan-eng-review
- Save progress, checkpoint, resume → invoke checkpoint
- Code quality, health check → invoke health

## Design System Reference

The design system for AI Virtual Company is fully documented and ready for implementation:

- **DESIGN.md** — Complete design specification (colors, typography, spacing, components, accessibility)
- **DESIGN_README.md** — Quick start guide and overview
- **DESIGN_SETUP.md** — Step-by-step implementation instructions
- **tailwind.config.ts** — Design tokens in Tailwind format
- **postcss.config.cjs** — PostCSS configuration
- **frontend/src/styles/globals.css** — Global styles and component classes

When working on UI improvements, frontend code, or component development:
1. Reference DESIGN.md for specifications
2. Use colors from AGENT_COLORS constant (manager, developer, designer, researcher)
3. Use Tailwind classes with the design tokens from tailwind.config.ts
4. Ensure WCAG AA accessibility compliance (focus rings, 44px touch targets, color contrast)
5. Test responsive layout at 320px, 768px, and 1440px breakpoints

Current color palette (toned-down, professional):
- Manager: #4E7EBE (leadership blue)
- Developer: #4A9B6F (technical green)
- Designer: #7C6BA8 (creative purple)
- Researcher: #D4A055 (analytical amber)
