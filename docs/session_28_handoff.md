# Dexter AI Operating System — Session 28 Handoff Summary

This document captures the latest product direction and UI priorities from the Session 28 handoff.

## Product objective
Dexter is being built as a **local AI Operating System** for Ubuntu that combines:
- AI assistant interaction
- agent orchestration
- automation control
- system monitoring
- human approval workflows

## Current focus
The immediate development focus is the **Dexter Dashboard Interface** as the central command console.

Primary screens:
1. Main Dashboard
2. All Agents Monitor
3. Dexter Live Monitor
4. Settings / Control Panel

## Main dashboard priorities
Required widgets:
- User Speech
- Dexter Response
- Sticky Notes
- Central AI Orb

Optional widgets:
- Live Operations
- Agent Quick Status
- Pending Approvals
- Current Goal
- Recent Logs
- Quick Actions

## AI Orb direction
The orb is treated as Dexter’s visual core and should communicate runtime state.

Requested visual improvements:
- plasma-like surface
- deeper glow
- particle effects
- breathing animation
- reactor-style powered base (rings, mist, layered platform)

## Live monitor goals
The Live Monitor should provide clear real-time visibility into:
- activity timeline
- browser/terminal/file actions
- tool usage states
- active agents and health

This is intended to be the primary trust-and-oversight view for day-to-day operation.

## Settings and customization
Dashboard customization should include:
- add/remove/move/resize widgets
- rename widgets and agents
- enable/disable agents
- save/reset layouts
- orb visual customization (size, colors, intensity, speed)

A dual mode UX is expected:
- **View Mode** for normal operation
- **Edit Mode** for layout/design customization

## Startup behavior target
On laptop boot:
1. Ubuntu starts
2. Dexter server auto-starts
3. Dashboard opens automatically

The dashboard should behave like an app window while remaining minimizable and movable.

## Next implementation phase
After UI generation is finalized, engineering priorities are:
- real-time event streaming
- agent telemetry integration
- live browser monitoring
- terminal monitoring
- music player integration
- persistent custom layout saving

## Long-term vision
Dexter evolves into a complete AI OS control center with:
- voice-first interaction
- orchestrated multi-agent execution
- local automation workflows
- transparent monitoring and human-in-the-loop control
