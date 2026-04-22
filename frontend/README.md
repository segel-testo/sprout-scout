# Sprout Scout — Frontend

Angular 21 UI for [Sprout Scout](../README.md). Lets users search by Austrian zip code and see vegan dishes extracted from local restaurant menus.

## What's in here

- `src/app/components/search/` — Zip input, mode toggle (on-demand vs auto-scan), and the live scan counter. Subscribes to the backend SSE stream in auto-scan mode.
- `src/app/components/restaurant-card/` — Renders three states per restaurant: dishes with confidence scores, a "View menu on foodora →" button when the menu lives on a delivery platform, or a fallback-links block (website / Google Maps / OSM) when no menu is online. Surfaces the OSM `diet:vegan` hint when present.
- `src/app/services/restaurant.ts` — REST client for `/api/restaurants` and `/api/restaurants/{id}/vegan`, plus an Observable-wrapped `EventSource` for the SSE `/api/restaurants/scan` endpoint.

The user-facing toggle is persisted to `localStorage` under `sprout-scout-mode`; default is **on-demand**.

The backend must be running at `http://localhost:8000` (see the [main README](../README.md) for setup).

---

This project was generated using [Angular CLI](https://github.com/angular/angular-cli) version 21.2.2.

## Development server

To start a local development server, run:

```bash
ng serve
```

Once the server is running, open your browser and navigate to `http://localhost:4200/`. The application will automatically reload whenever you modify any of the source files.

## Code scaffolding

Angular CLI includes powerful code scaffolding tools. To generate a new component, run:

```bash
ng generate component component-name
```

For a complete list of available schematics (such as `components`, `directives`, or `pipes`), run:

```bash
ng generate --help
```

## Building

To build the project run:

```bash
ng build
```

This will compile your project and store the build artifacts in the `dist/` directory. By default, the production build optimizes your application for performance and speed.

## Running unit tests

To execute unit tests with the [Vitest](https://vitest.dev/) test runner, use the following command:

```bash
ng test
```

## Running end-to-end tests

For end-to-end (e2e) testing, run:

```bash
ng e2e
```

Angular CLI does not come with an end-to-end testing framework by default. You can choose one that suits your needs.

## Additional Resources

For more information on using the Angular CLI, including detailed command references, visit the [Angular CLI Overview and Command Reference](https://angular.dev/tools/cli) page.
