# CONTEXT.md

## What this folder is

Working area for `qbrain`: a Quake-focused LLM knowledge system backed by SQLite/FTS5 (with optional vectors), plus a Python CLI.

## Why it exists

- Prototype a durable "LLM wiki" style brain for Quake/idTech research and synthesis.
- Keep database-backed knowledge workflows ergonomic via a Python + uv + Typer tool.
- Explore and adapt ideas from Karpathy/Garry approaches for Jack's use case.

## Created

- Date: 2026-04-05
- Created by: Nano 🛸

## Scope notes

- `superpowers/` is a reference implementation to study/adapt.
- Keep secrets out of committed files; prefer env-based local configuration.
