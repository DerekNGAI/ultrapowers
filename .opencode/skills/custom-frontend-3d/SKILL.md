---
name: custom-frontend-3d
description: You MUST invoke whenever working with frontend UI, design systems, responsive layouts, animations, accessibility, Three.js, React Three Fiber, Babylon.js, PlayCanvas, shaders, WebGL scenes, 3D product viewers, or any DOM UI layered over 3D.
---

# Frontend UI + 3D + Playwright

Build, debug, refine, and verify frontend experiences with live browser evidence at every step.
This skill is especially for UI-heavy work, Three.js, and hybrid DOM + canvas experiences.

## Mandatory rule

Playwright MCP is required from the beginning to the end of every task.
Do not investigate, plan, implement, debug, optimize, or verify purely by reading code.
Never claim a fix works unless Playwright MCP has just verified it in the browser.
If Playwright MCP is unavailable, stop and say the task cannot be completed safely under this skill.

## When to invoke

Invoke this skill whenever the task involves any of the following:
- Frontend UI implementation, bug fixing, refactoring, polish, responsiveness, accessibility, visual QA, animation, or performance tuning
- Three.js, React Three Fiber, Babylon.js, PlayCanvas, GLSL shaders, post-processing, raycasting, camera controls, scene architecture, asset loading, texture issues, or render-loop problems
- DOM overlays on top of canvas or WebGL scenes
- Design-system work for web interfaces
- Layout, spacing, overflow, focus, motion, interaction, or theme issues
- Product viewers, immersive hero sections, interactive 3D explainers, configurators, or scene-based storytelling

## Core operating principles

- Browser truth beats code assumptions.
- Small verified increments beat large speculative rewrites.
- UI quality includes accessibility, responsiveness, motion, performance, and state coverage.
- 3D should support spatial understanding, immersion, or product presentation — not replace clear UI unnecessarily.
- Prefer maintainable systems over one-off visual hacks.
- Treat console warnings, resize issues, focus loss, and asset failures as real bugs.

## Required workflow

### 1. Investigate with Playwright MCP first

Always begin with Playwright MCP before touching code.

Required actions:
- Open the running page, app, component preview, or repro route
- Inspect the current behavior in a live browser
- Capture baseline screenshots at desktop and mobile
- Check console errors and warnings
- Check failed network requests and broken assets
- Exercise the exact user flow that is broken or being built
- Inspect hover, click, keyboard, touch, scroll, resize, and focus behavior
- For 3D tasks, inspect canvas sizing, device-pixel-ratio behavior, controls, animation loops, overlays, loading states, and visual stability

Do not proceed to implementation until the live browser evidence is clear.

### 2. Plan only what can be verified

Turn the findings into small implementation steps.

For each step define:
- the exact files to change
- the exact behavior expected after the change
- the exact Playwright MCP checks that will prove success
- what adjacent areas need a quick regression pass

Never batch many risky UI or 3D changes together unless the task explicitly requires it.

### 3. Implement in small increments

After every meaningful code change:
- rerun Playwright MCP
- reload the affected view
- repeat the relevant user interactions
- compare the live result with the expected result
- check console again
- check layout again
- check for regression in nearby UI or scene behavior

Implementation is not complete until the browser confirms it.

### 4. Verify from beginning to end with Playwright MCP

Final verification must include:
- desktop breakpoint
- mobile breakpoint
- any critical intermediate breakpoint when layout complexity demands it
- light and dark theme, if present
- empty, loading, error, and success states
- keyboard navigation and visible focus
- reduced-motion behavior when animations exist
- for 3D: camera behavior, resize behavior, overlay alignment, asset loading, and scene interaction stability

No final answer without final live verification.

## Frontend UI standards

Use these standards unless the project already has a stronger established system:

### Typography
- Keep body text clearly readable
- Never let UI text drop into illegibility
- Use clear hierarchy for labels, body, headings, and display text
- Avoid oversized display typography in dense product UI
- Prefer stable numeric alignment for counters, stats, timers, and prices

### Spacing and layout
- Use a consistent spacing system rather than arbitrary values
- Keep rhythm clean and intentional
- Prefer left alignment for dense informational UI
- Use centered layouts only when the content genuinely benefits
- Avoid “AI template” repetition such as identical three-card rows everywhere
- Vary layout rhythm while preserving alignment discipline

### Accessibility
- Use semantic HTML whenever possible
- Maintain correct heading order
- Preserve visible focus states
- Ensure keyboard navigation works
- Respect reduced motion
- Ensure touch targets are comfortably tappable
- Provide labels and accessible names for controls
- Design empty, loading, and error states as first-class states

### Responsiveness
- Think mobile-first
- Check for overflow, clipped text, broken wrapping, and unreachable controls
- Ensure overlays, drawers, modals, and sticky elements do not block core content
- Re-test interaction patterns on smaller screens instead of assuming desktop behavior scales down

### Visual taste
- Avoid generic gradient-heavy “AI” aesthetics unless explicitly requested
- Use color with restraint
- Prefer intentional hierarchy, contrast, and whitespace over decorative clutter
- Keep interfaces clean, specific, and product-appropriate

## 3D standards

Use these standards whenever working with Three.js or related 3D libraries:

### Scene role
- Use 3D where spatial understanding or immersive presentation adds value
- Keep text-heavy, form-heavy, and accessibility-critical UI in the DOM when possible
- Do not use 3D as a substitute for simple readable UI

### Rendering and performance
- Cap renderer pixel ratio to a sane maximum
- Be conservative with post-processing
- Minimize unnecessary draw calls
- Reuse materials where possible
- Use instancing for repeated geometry
- Lazy-load heavy scenes when they are not immediately visible
- Keep animation loops disciplined and intentional

### Assets and textures
- Verify all models, textures, and environment assets actually load in the browser
- Watch for CORS and cross-origin texture problems
- For externally sourced textures, set cross-origin correctly before assigning the source
- Prefer asset pipelines that are realistic for the environment the app runs in

### Interaction
- Verify camera framing on load and on resize
- Ensure controls feel stable and bounded
- Prevent DOM overlays from accidentally stealing or blocking intended scene interaction
- Confirm raycasting and pointer behavior after layout changes
- Test hover and selection states in the real browser, not just in theory

### Lifecycle hygiene
- Clean up geometries, materials, textures, render targets, event listeners, animation frames, and observers
- Avoid leaks on route changes, modal open/close cycles, or scene remounts
- Re-verify after repeated entry/exit flows

## DOM + canvas integration rules

When the page mixes HTML UI and 3D:
- Define which layer owns pointer input at each moment
- Avoid invisible overlays blocking the canvas
- Keep tooltips, menus, dialogs, and HUD panels legible over bright and dark scenes
- Ensure critical actions still have accessible DOM fallbacks where practical
- Re-test alignment between scene hotspots and UI overlays after every layout or camera change

## Performance verification rules

Never describe performance as “good” without checking it live.

Always inspect for:
- jank during interaction
- dropped frames during camera movement or animation
- layout thrash from UI updates
- oversized textures
- excessive post-processing cost
- unnecessary rerenders in React / R3F
- memory growth after repeating the same flow

## Definition of done

A task is done only when Playwright MCP has verified that:
- the requested behavior works
- the UI looks correct at required breakpoints
- there are no relevant console errors
- accessibility basics still hold
- the touched flow has no obvious regression
- the 3D scene remains stable, correctly framed, and performant enough for the task context

## Agent behavior

The agent should be:
- visually opinionated, but system-aware
- skeptical of unverified assumptions
- precise about CSS, layout, motion, and rendering details
- proactive about accessibility and responsiveness
- relentless about checking the live browser after every meaningful change

## Default checklist before every response

Before coding:
- What does the browser do right now?
- What exactly is broken, missing, or weak?
- What is the smallest verifiable next step?

After coding:
- Did Playwright MCP confirm the exact intended behavior?
- Did nearby UI or scene behavior regress?
- Did responsiveness, focus, console health, and visual stability remain intact?

## Special environment rules

When working in sandboxed iframe-style environments:
- do not assume storage APIs are available
- do not assume local binary fetch behavior will work for models, textures, audio, or WASM
- verify actual asset loading behavior in the live browser
- be extra careful with cross-origin image and texture handling