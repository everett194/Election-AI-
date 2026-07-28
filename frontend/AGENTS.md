# VoteLocal frontend

React + Vite + Tailwind CSS frontend for VoteLocal. Originally exported from
Figma Make as a static design demo (fictional placeholder data throughout);
now wired to the real backend in `../` (see `../election_lookup.py`,
`../questionnaire_scoring.py`, and `../backend/app.py`).

## Development Server

Not auto-started. Run `npm install` once, then `npm run dev` from this
directory. Defaults to port 5173 (override with `PORT=xxxx npm run dev`).
The backend API must be running separately (see `../README.md`); its base
URL is read from `VITE_API_BASE_URL` (see `src/api.ts`), defaulting to
`http://localhost:8000`.

## Project Structure

- `src/main.tsx` - React entrypoint; imports `src/index.css` and mounts `src/App.tsx` into the `#root` element
- `src/App.tsx` - Top-level component: page routing (via `src/context/nav.tsx`) and app-wide data state
- `src/api.ts` - Fetch client for the backend API. The only place that talks to the network.
- `src/index.css` - Global CSS entrypoint and Tailwind CSS v4 import
- `index.html` - Vite HTML shell containing the `#root` element and loading `src/main.tsx`
- `vite.config.ts` - Vite configuration: React, Tailwind CSS v4, and the `@` alias for `src`
- `src/pages/` - One component per screen (Home, ElectionResults, Race, CandidateProfile, Comparison, Questionnaire, ResultsDashboard)
- `src/components/` - Shared presentational components (Cards, Badges, Nav, Footer, generic `ui.tsx` primitives)

## Styling

Tailwind CSS v4 through the `@tailwindcss/vite` plugin configured in `vite.config.ts`. `src/index.css` imports Tailwind with `@import 'tailwindcss';` and defines the design tokens (`@theme` block: colors, fonts, radii). Use Tailwind utility classes directly in JSX.

## Data

There is no local/fake data module anymore -- `src/data/placeholder.ts` was deleted. Every page fetches through `src/api.ts`. When the backend has nothing for a field (biography, campaign finance, endorsements, public statements, voting record), the UI renders an explicit "not available" state instead of inventing content -- do not reintroduce placeholder values.
