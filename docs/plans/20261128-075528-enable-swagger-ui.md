---
plan_id: 20261128-075528-enable-swagger-ui
status: draft
created_at: 2026-11-28T07:55:28Z
model: gemini-4-hydrogen
route_name: gemini-hydrogen
workflow_run_url: https://github.com/ankul01/task-manager/actions/runs/46123395335
requirement: "I want to implement interactive API documentation for my application using Swagger UI (OpenAPI specification).\n\nObjective:\n\nExpose all available REST API endpoints through a single, interactive Swagger UI page.\n\nExpected functionality:\n\nAutomatically discover and document all available API endpoints.\n\nDisplay endpoints grouped by API tags or functional modules.\n\nShow HTTP methods (GET, POST, PUT, PATCH, DELETE).\n\nDisplay request parameters, headers, path variables, and query parameters.\n\nAutomatically generate request and response schemas with appropriate data types.\n\nProvide sample JSON request payloads with meaningful example values.\n\nAllow users to modify sample payloads and execute APIs directly using the \"Try it out\" functionality.\n\nDisplay actual API responses, HTTP status codes, response headers, and error messages.\n\nSupport API authentication, including Bearer Token/JWT authentication where applicable.\n\nProvide clear descriptions for each endpoint, request field, and response structure.\n\nImplementation requirements:\n\nFirst, identify the framework and existing application architecture.\n\nPrefer the framework's native OpenAPI and Swagger UI integration rather than building a custom documentation interface.\n\nAvoid duplicating API definitions or maintaining documentation manually.\n\nEnsure the documentation stays synchronized with the actual API implementation.\n\nKeep the Swagger UI accessible through a dedicated endpoint, such as /docs.\n\nProvide an OpenAPI JSON specification endpoint, such as /openapi.json.\n\nInclude instructions for enabling or disabling Swagger documentation across development, staging, and production environments.\n\nExpected outcome:\n\nA fully functional, interactive API documentation portal where developers and testers can discover, understand, authenticate against, and test all available APIs from one page without requiring an external API testing tool."
---

# Draft Plan: 20261128-075528-enable-swagger-ui

> **Human Review Required:** Merging this Pull Request to the default branch marks this exact file and commit SHA as approved for implementation.

### 1. Clarifying Questions & Assumptions

**Clarifying Questions**
1. **Spring Boot Stack:** Is the application built on Spring Boot 3.x with Spring Web MVC (blocking) or Spring WebFlux (reactive)?
2. **Security Framework:** Is Spring Security enabled, and does the service validate JWTs/Bearer tokens directly or behind an API gateway?
3. **Environment Policy:** Should Swagger UI and `/openapi.json` be enabled by default in `dev` and `staging` and disabled in `prod`, or accessible in `prod` behind authentication?
4. **Reverse Proxy / Base Path:** Is the service deployed behind a path-prefix proxy (e.g., `/api` or custom context path) that affects Swagger UI's "Try it out" server URL?
5. **Sensitive / Internal Endpoints:** Are there internal or operational endpoints (e.g., `/actuator/**`, `/api/ping`) that should be excluded from the public OpenAPI spec?

**Assumptions**
- The service is a **Java 21 + Spring Boot 3.x (Spring Web MVC)** application deployed in a memory-constrained container (512 MB RAM on Render Free).
- **`springdoc-openapi-starter-webmvc-ui`** is the standard native OpenAPI 3 / Swagger UI integration for Spring Boot 3 (zero manual spec duplication, runtime reflection over controllers and DTOs).
- Spring Security (if present) uses a filter chain where public documentation paths (`/docs`, `/swagger-ui/**`, `/openapi.json`) must be explicitly permitted when enabled.
- Existing health check endpoints (e.g., `GET /api/ping` or `/actuator/health`) must remain fast and unauthenticated.

---

### 2. Scope & Non-Goals

**Scope**
- Integrate native `springdoc-openapi` to automatically discover all REST `@RestController` endpoints, HTTP methods, path/query/header parameters, and request/response DTO schemas.
- Configure Swagger UI at `/docs` and OpenAPI 3 JSON specification at `/openapi.json`.
- Configure global OpenAPI metadata (title, version, description, server URLs) and a global **Bearer JWT (`HTTP Bearer`)** security scheme for "Try it out" authorization.
- Group endpoints by functional modules using `@Tag` annotations and enrich DTOs/controllers with `@Operation`, `@ApiResponse`, and `@Schema` (descriptions, types, and meaningful `example` values).
- Provide Spring profile / property-based toggles to enable or disable Swagger UI and OpenAPI endpoints across `dev`, `staging`, and `prod`.
- Update security and CORS configuration (if applicable) so Swagger UI assets and "Try it out" calls function properly.

**Non-Goals**
- Building a custom documentation frontend or manually authoring static `openapi.yaml` / `openapi.json` files.
- Writing custom API gateway routing, rate limiting, or OAuth2 authorization server flows.
- Refactoring existing business logic or changing REST API contracts solely for documentation.

---

### 3. Testable Acceptance Criteria

1. **Swagger UI & Spec Paths:** When documentation is enabled, `GET /docs` redirects to/renders the interactive Swagger UI (`HTTP 200`), and `GET /openapi.json` returns a valid OpenAPI 3.x JSON document (`HTTP 200`, `application/json`).
2. **Automatic Endpoint Discovery:** All active application REST endpoints appear in `/openapi.json` with accurate HTTP methods (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`), path variables, query parameters, headers, and grouped `@Tag` sections.
3. **Schemas & Sample Payloads:** Request and response models display accurate JSON data types, field descriptions, required markers, and meaningful example values; Swagger UI pre-populates sample JSON payloads.
4. **Interactive Execution ("Try it out"):** Executing an endpoint from `/docs` sends the live HTTP request and displays the actual status code, response headers, and response/error body.
5. **Bearer / JWT Auth Support:** Swagger UI displays an **Authorize** button accepting a Bearer JWT token and injects `Authorization: Bearer <token>` into protected endpoint requests.
6. **Environment Toggle:** Setting the disable flags (e.g., in `application-prod.yml` or via env vars) causes `/docs`, `/swagger-ui/**`, and `/openapi.json` to return `HTTP 404` without affecting application startup or the health check endpoint (`< 50ms`).
7. **Resource Footprint:** Enabling `springdoc-openapi` keeps container startup and runtime memory within the 512 MB Render Free ceiling without OOM errors.

---

### 4. Proposed Implementation Steps

1. **Architecture & Dependency Audit**
   - Confirm Spring Boot version (`3.x`), web stack (Web MVC vs. WebFlux), security setup, and existing DTO validation annotations (`jakarta.validation.constraints.*`, which `springdoc` automatically reads for required fields, min/max, and patterns).
2. **Add `springdoc-openapi` Dependency**
   - Add `org.springdoc:springdoc-openapi-starter-webmvc-ui` (compatible with the project's Spring Boot 3.x version) in `pom.xml`.
3. **Configure Paths & Environment Toggles**
   - In `application.yml` (base defaults):
     - Set `springdoc.api-docs.path=/openapi.json`
     - Set `springdoc.swagger-ui.path=/docs`
     - Enable `tryItOutEnabled`, sorting by method/tags, and disable `/actuator/**` exposure if not desired (`springdoc.paths-to-exclude` or `springdoc.show-actuator=false`).
   - Add environment-specific configuration (`application-dev.yml`, `application-staging.yml`, `application-prod.yml`, plus environment variable overrides `SPRINGDOC_API_DOCS_ENABLED` / `SPRINGDOC_SWAGGER_UI_ENABLED`) so docs are enabled in `dev`/`staging` and disabled by default in `prod`.
   - Document the exact environment variables and profile flags in `README.md`.
4. **OpenAPI Global Configuration & JWT Security Scheme**
   - Create an `@Configuration` class exposing an `OpenAPI` bean with API metadata (`Info`, `Server` with dynamic base URL support for local vs. Render HTTPS) and a `Components` `SecurityScheme` (`type=HTTP`, `scheme=bearer`, `bearerFormat=JWT`).
   - Apply `@SecurityRequirement` globally or per secured controller/endpoint so public endpoints (e.g., login, health ping) do not falsely require auth in the UI.
5. **Annotate Controllers & DTOs Incrementally**
   - Add `@Tag` to each `@RestController` to group endpoints by functional module.
   - Add `@Operation` and `@ApiResponses` (including standard `400`, `401`, `403`, `404`, `500` error schemas) on controller methods.
   - Add `@Schema(description = "...", example = "...")` to request/response DTO fields so Swagger UI generates meaningful sample JSON payloads.
6. **Spring Security Integration**
   - If Spring Security is present, permit `/docs`, `/swagger-ui/**`, `/swagger-ui.html`, and `/openapi.json` **only when** Swagger is enabled (e.g., via conditional property or profile) so disabled environments return `404` cleanly rather than `401`/`403` redirects.
   - Ensure `X-Forwarded-*` headers (`server.forward-headers-strategy=framework`) are respected if deployed behind Render's TLS-terminating proxy so "Try it out" uses `https://` rather than `http://`.

---

### 5. Test Cases, Risks, & Rollback Approach

**Test Cases**
1. **Integration — Docs Enabled (`dev`/`staging`):** `MockMvc` / `TestRestTemplate` verifies `GET /openapi.json` returns `200` with expected tags, paths, schemas, and `bearerAuth` security scheme; `GET /docs` returns `200` (or redirect to `/swagger-ui/index.html` returning `200`).
2. **Integration — Docs Disabled (`prod`):** With `springdoc.api-docs.enabled=false` and `springdoc.swagger-ui.enabled=false`, verify `GET /openapi.json` and `GET /docs` return `404`, while the health check endpoint still returns `200` in `< 50ms`.
3. **End-to-End Auth & Try-It-Out:** In Swagger UI, authenticate via **Authorize** with a valid JWT, execute a protected `POST` endpoint with the pre-filled sample payload, and verify a `200`/`201` response; execute without a token and verify `401` is rendered properly.
4. **Contract Drift Check:** Add or modify a controller field/parameter in a test or PR check and confirm `/openapi.json` reflects the change automatically without manual edits.
5. **Container Memory Smoke Test:** Build the `linux/amd64` Docker image and verify startup time and heap usage stay safely below Render's 512 MB RAM ceiling.

**Risks & Mitigations**
- **Risk: Sensitive endpoints or internal DTOs exposed in prod.**
  - *Mitigation:* Disable `springdoc` by default in `application-prod.yml`, exclude actuator/internal paths, and add an automated test asserting `404` under the `prod` profile.
- **Risk: Mixed-content / wrong scheme ("Try it out" sends `http://` on HTTPS Render deployment).**
  - *Mitigation:* Configure `server.forward-headers-strategy=framework` and relative server URL (`/`) in the `OpenAPI` bean.
- **Risk: Memory overhead on Render Free (512 MB RAM).**
  - *Mitigation:* `springdoc-openapi` caches the generated spec after first request; validate RAM usage under `JAVA_TOOL_OPTIONS` (`MaxRAMPercentage=65.0`) and avoid scanning unnecessary packages via `springdoc.packages-to-scan`.
- **Risk: Spring Boot / `springdoc-openapi` version mismatch causing runtime `NoSuchMethodError` or `ControllerAdviceBean` errors.**
  - *Mitigation:* Pin the exact `springdoc-openapi-starter-webmvc-ui` version matching the project's Spring Boot 3.x minor release and verify via Spring Boot integration tests.

**Rollback Approach**
1. **Immediate Runtime Rollback (Zero Redeploy):** Set environment variables `SPRINGDOC_API_DOCS_ENABLED=false` and `SPRINGDOC_SWAGGER_UI_ENABLED=false` in the hosting environment (e.g., Render) and restart the service.
2. **Code Rollback:** Revert the commit/PR removing the `springdoc-openapi` dependency, configuration classes/properties, annotations, and security path matchers, then redeploy the prior GHCR image tag.
