---
name: frontend
description: >-
  Use for UI tasks: implementing components, pages, routing, styling,
  responsive design, accessibility, and client-side logic with any framework
  (React, Vue, Svelte, Solid, vanilla JS, etc.).
---

# Frontend Development

## When to use
- Building UI components, pages, or screens
- Implementing responsive/layout CSS
- Adding client-side logic (fetch, state, validation)
- Configuring a frontend build tool (Vite, Webpack, etc.)
- Setting up routing, navigation, or page transitions
- Accessibility improvements or testing
- When the task involves HTML, CSS, JS/TS in the browser

## Fundamentals (language-agnostic)

### Core web platform
- Semantic HTML: `<header>`, `<main>`, `<nav>`, `<section>`, `<article>`, `<form>`, `<button>` over `<div>`
- CSS: box model, flexbox, grid, cascade, specificity
- JS/TS: DOM API, events, async, fetch, module system

### Responsive design
- Mobile-first: start from smallest screen, add `min-width` breakpoints
- Fluid: `clamp()`, `vw/vh`, `%` over fixed px
- Touch targets: minimum 44×44px
- Test at 320px, 768px, 1024px, 1440px

### Accessibility (WCAG)
- All images need `alt` text
- All form inputs need `<label>`
- Color contrast: 4.5:1 for normal text, 3:1 for large (WCAG AA)
- Keyboard: Tab through all interactive elements, visible focus ring
- ARIA: `aria-label`, `aria-expanded`, `aria-controls` when semantic HTML is not enough

## Framework-specific patterns

### State management progression
1. **Component state** (useState, ref) — for isolated UI state (open/close, input value)
2. **Server state** (TanStack Query, SWR, RTK Query, Apollo) — for API data, caching, refetching
3. **URL state** (React Router, vue-router, Next.js) — for shareable views

### Components
- One file per component: `Button.tsx`, `UserProfile.tsx`
- Props interface exported and explicit
- Default export only for pages; named exports for everything else

### Styling
| Approach | When |
|----------|------|
| Utility-first (Tailwind) | New projects, rapid prototyping, design system |
| CSS Modules | Existing project, scoped styles |
| CSS-in-JS | When dynamic styles at runtime are needed |
| BEM | Custom CSS in legacy projects |

## Common recipes

### Debounced input
```typescript
// Generic debounce utility
function debounce<T extends (...args: unknown[]) => unknown>(
  fn: T,
  ms: number
): (...args: Parameters<T>) => void {
  let timer: ReturnType<typeof setTimeout>;
  return (...args) => {
    clearTimeout(timer);
    timer = setTimeout(() => fn(...args), ms);
  };
}
```

### Fetch wrapper
```typescript
// Language-agnostic pattern
async function api<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json', ...init?.headers },
    ...init,
  });
  if (!res.ok) throw new ApiError(res.status, await res.text());
  return res.json() as Promise<T>;
}
```
(Port to your framework's fetch library or equivalent)

## Resources
- [web.dev](https://web.dev/) — performance and a11y guides
- [WCAG Quick Reference](https://www.w3.org/WAI/WCAG22/quickref/)
- [Can I Use](https://caniuse.com/) — browser support tables
