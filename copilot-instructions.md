<!-- GSD:project-start source:PROJECT.md -->

## Project

**FiftyOne Datumaro Pose Importer**

A local utility project to load an image folder and a Datumaro JSON export (from CVAT frame export) into FiftyOne. It creates a dataset that correctly renders pose/keypoint skeletons with proper keypoint visibility handling. It is designed for single-user, config-driven usage in a local workflow.

**Core Value:** Given only config paths, the project reliably imports and visualizes CVAT/Datumaro pose annotations in FiftyOne with correct skeleton visibility behavior.

### Constraints

- **Runtime**: Must work in local environment — single-user development flow
- **Data Input**: Must support Datumaro JSON from CVAT exports — this is the required source format
- **Usability**: Config-first setup — no hardcoded paths in import logic
- **Visualization Correctness**: Skeleton visibility semantics must be preserved — incorrect visibility undermines dataset trust

<!-- GSD:project-end -->

<!-- GSD:stack-start source:research/STACK.md -->

## Technology Stack

## Recommended stack

| Layer | Choice | Why |
|---|---|---|
| Runtime | Python 3.11 | Best compatibility for FiftyOne/Datumaro ecosystem |
| Dataset + Visualization | `fiftyone` | Native keypoint and skeleton rendering in app |
| Annotation parsing | `datumaro` | Reliable handling of CVAT-exported Datumaro schema |
| Config validation | `pydantic` + `pyyaml` | Typed config for image/datumaro paths and import options |
| CLI | `typer` | Simple command entrypoint for local workflows |
| Tests | `pytest` | Regression coverage for mapping/visibility semantics |

## Critical mapping contract

## Avoid

- Ad-hoc JSON-only parsing without Datumaro model checks.
- Treating hidden and absent as identical states.
- Dropping missing joints instead of preserving index alignment.

<!-- GSD:stack-end -->

<!-- GSD:conventions-start source:CONVENTIONS.md -->

## Conventions

Conventions not yet established. Will populate as patterns emerge during development.
<!-- GSD:conventions-end -->

<!-- GSD:architecture-start source:ARCHITECTURE.md -->

## Architecture

Architecture not yet mapped. Follow existing patterns found in the codebase.
<!-- GSD:architecture-end -->

<!-- GSD:skills-start source:skills/ -->

## Project Skills

No project skills found. Add skills to any of: `.github/skills/`, `.agents/skills/`, `.cursor/skills/`, `.github/skills/`, or `.codex/skills/` with a `SKILL.md` index file.
<!-- GSD:skills-end -->

<!-- GSD:workflow-start source:GSD defaults -->

## GSD Workflow Enforcement

Before using Edit, Write, or other file-changing tools, start work through a GSD command so planning artifacts and execution context stay in sync.

Use these entry points:

- `/gsd-quick` for small fixes, doc updates, and ad-hoc tasks
- `/gsd-debug` for investigation and bug fixing
- `/gsd-execute-phase` for planned phase work

Do not make direct repo edits outside a GSD workflow unless the user explicitly asks to bypass it.
<!-- GSD:workflow-end -->

<!-- GSD:profile-start -->

## Developer Profile

> Profile not yet configured. Run `/gsd-profile-user` to generate your developer profile.
> This section is managed by `generate-claude-profile` -- do not edit manually.
<!-- GSD:profile-end -->
