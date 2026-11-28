---
plan_id: 20261128-075528-enable-swagger-ui
status: draft
created_at: 2026-11-28T07:55:28Z
revised_at: 2026-11-28T08:02:16Z
model: gemini-4-hydrogen
route_name: gemini-hydrogen
workflow_run_url: https://github.com/ankul01/task-manager/actions/runs/46123395335
requirement: "I want to implement interactive API documentation for my application using Swagger UI (OpenAPI specification).\n\nObjective:\n\nExpose all available REST API endpoints through a single, interactive Swagger UI page.\n\nExpected functionality:\n\nAutomatically discover and document all available API endpoints.\n\nDisplay endpoints grouped by API tags or functional modules.\n\nShow HTTP methods (GET, POST, PUT, PATCH, DELETE).\n\nDisplay request parameters, headers, path variables, and query parameters.\n\nAutomatically generate request and response schemas with appropriate data types.\n\nProvide sample JSON request payloads with meaningful example values.\n\nAllow users to modify sample payloads and execute APIs directly using the \"Try it out\" functionality.\n\nDisplay actual API responses, HTTP status codes, response headers, and error messages.\n\nSupport API authentication, including Bearer Token/JWT authentication where applicable.\n\nProvide clear descriptions for each endpoint, request field, and response structure.\n\nImplementation requirements:\n\nFirst, identify the framework and existing application architecture.\n\nPrefer the framework's native OpenAPI and Swagger UI integration rather than building a custom documentation interface.\n\nAvoid duplicating API definitions or maintaining documentation manually.\n\nEnsure the documentation stays synchronized with the actual API implementation.\n\nKeep the Swagger UI accessible through a dedicated endpoint, such as /docs.\n\nProvide an OpenAPI JSON specification endpoint, such as /openapi.json.\n\nInclude instructions for enabling or disabling Swagger documentation across development, staging, and production environments.\n\nExpected outcome:\n\nA fully functional, interactive API documentation portal where developers and testers can discover, understand, authenticate against, and test all available APIs from one page without requiring an external API testing tool."
---

# Draft Plan: 20261128-075528-enable-swagger-ui

> **Human Review Required:** Merging this Pull Request to the default branch marks this exact file and commit SHA as approved for implementation.

### 1. Confirmed Architecture Decisions & Assumptions

All clarifying questions have been resolved:

- **Spring Boot Stack:** Java 21 with **Spring Boot 3.x + Spring Web MVC (blocking)**. Use `org.springdoc:springdoc-openapi-starter-webmvc-ui` for native OpenAPI 3 and Swagger UI integration.
- **Security Framework:** No API gateway is present. **Do not introduce Spring Security** if it is not already configured in the repository. If Spring Security is already present, permit `/docs`, `/openapi.json`, `/openapi.json/**`, `/swagger-ui/**`, `/swagger-ui.html`, and `/v3/api-docs/**` **only when** Swagger documentation is enabled.
- **Environment Policy:** Enabled by default in `local`, `dev`, and `staging` (`springdoc.api-docs.enabled=true`, `springdoc.swagger-ui.enabled=true`), and disabled by default in `prod` (`application-prod.yml` with environment variable override support).
- **Reverse Proxy & Base Path:** The service is deployed at root `/` (no path-prefix proxy) behind a TLS-terminating reverse proxy (Render). `server.forward-headers-strategy=framework` will be configured so Swagger UI "Try it out" requests use the `https://` scheme properly.
- **Excluded Internal Endpoints:** `/actuator/**` and `/api/ping` will be excluded from the generated OpenAPI specification via `springdoc.paths-to-exclude`.

**Remaining Assumptions**
- The application is deployed in a memory-constrained container (512 MB RAM ceiling on Render Free), so `springdoc-openapi` package scanning and startup overhead must fit comfortably within `JAVA_TOOL_OPTIONS` (`MaxRAMPercentage=65.0`).
- Existing health check endpoints (e.g., `GET /api/ping` or `/actuator/health`) remain fast (`< 50ms`), zero-DB, and unauthenticated.
- Existing DTOs use `jakarta.validation.constraints.*` (if present), which `springdoc-openapi` inspects automatically for required fields and constraints.

---

### 2. Scope & Non-Goals

**Scope**
- Integrate `springdoc-openapi-starter-webmvc-ui` to automatically discover all active `@RestController` endpoints, HTTP methods (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`), path/query/header parameters, and request/response DTO schemas.
- Expose Swagger UI at `/docs` and the OpenAPI 3 JSON specification at `/openapi.json`.
- Exclude operational/internal paths (`/actuator/**` and `/api/ping`) from the OpenAPI spec via `springdoc.paths-to-exclude`.
- Configure `server.forward-headers-strategy=framework` and root `/` server resolution so "Try it out" executes against `https://` behind Render's TLS-terminating proxy.
- Configure global OpenAPI metadata (title, version, description) and a **Bearer JWT (`HTTP Bearer`)** `SecurityScheme` for "Try it out" authorization where applicable.
- Group endpoints by functional modules using `@Tag` annotations and enrich controllers and DTOs with `@Operation`, `@ApiResponses`, and `@Schema` (descriptions, data types, and meaningful `example` values).
- Provide profile-based and environment-variable toggles across local, `dev`, `staging`, and `prod`, along with documentation in `README.md`.
- Update existing Spring Security configuration (if and only if Spring Security is already in the project) to conditionally permit Swagger UI and OpenAPI endpoints when enabled.

**Non-Goals**
- Introducing Spring Security (or any new authentication middleware) if it does not already exist in the repository.
- Building a custom documentation UI or manually authoring static `openapi.yaml` / `openapi.json` files.
- Implementing API gateway routing, rate limiting, or OAuth2 authorization server flows.
- Refactoring existing business logic or altering REST API contracts solely for documentation.

---

### 3. Testable Acceptance Criteria

1. **Swagger UI & Spec Paths:** When enabled, `GET /docs` renders/redirects to the interactive Swagger UI (`HTTP 200`), and `GET /openapi.json` returns a valid OpenAPI 3.x JSON document (`HTTP 200`, `application/json`).
2. **Automatic Endpoint Discovery & Exclusions:** All active application REST endpoints appear in `/openapi.json` with accurate HTTP methods, path variables, query parameters, headers, and `@Tag` groupings, while `/actuator/**` and `/api/ping` are excluded.
3. **Schemas & Sample Payloads:** Request and response models display accurate JSON data types, field descriptions, required markers, and meaningful example values; Swagger UI pre-populates sample JSON payloads.
4. **Interactive Execution & TLS Scheme:** Executing an endpoint via "Try it out" from `/docs` sends the live HTTP request (honoring `X-Forwarded-Proto: https` via `server.forward-headers-strategy=framework`) and displays the actual status code, response headers, and response/error body.
5. **Bearer / JWT Auth Support:** Swagger UI displays an **Authorize** button accepting a Bearer JWT token and injects `Authorization: Bearer <token>` into protected endpoint requests.
6. **Environment Toggle:** Under the `prod` profile (`application-prod.yml`) or with `SPRINGDOC_API_DOCS_ENABLED=false` and `SPRINGDOC_SWAGGER_UI_ENABLED=false`, `/docs`, `/swagger-ui/**`, `/openapi.json`, and `/v3/api-docs/**` return `HTTP 404` without affecting application startup or `GET /api/ping` (`< 50ms`).
7. **Security Non-Intrusion:** If Spring Security is absent from the repository, no Spring Security dependency or filter chain is added; if present, documentation paths are permitted only when Swagger is enabled.
8. **Resource Footprint:** Enabling `springdoc-openapi` keeps container startup and runtime memory within the 512 MB Render Free ceiling without OOM errors.

---

### 4. Proposed Implementation Steps

1. **Architecture & Dependency Audit**
   - Inspect `pom.xml` and application configuration to confirm the exact Spring Boot 3.x version, existing `@RestController` packages, DTO validation annotations, and whether Spring Security is already configured.
2. **Add `springdoc-openapi-starter-webmvc-ui` Dependency**
   - Add `org.springdoc:springdoc-openapi-starter-webmvc-ui` (version compatible with the project's Spring Boot 3.x minor version) to `pom.xml`.
3. **Configure Paths, Exclusions, Forwarded Headers, & Environment Toggles**
   - In `application.yml` (base defaults, enabled for local/dev/staging):
     - `springdoc.api-docs.enabled: true`
     - `springdoc.api-docs.path: /openapi.json`
     - `springdoc.swagger-ui.enabled: true`
     - `springdoc.swagger-ui.path: /docs`
     - `springdoc.paths-to-exclude: /actuator/**,/api/ping`
     - `springdoc.show-actuator: false`
     - `springdoc.swagger-ui.try-it-out-enabled: true`
     - `springdoc.swagger-ui.operations-sorter: method`
     - `springdoc.swagger-ui.tags-sorter: alpha`
     - `server.forward-headers-strategy: framework`
   - Add environment-specific configuration:
     - `application-dev.yml` and `application-staging.yml` (explicitly keeping docs enabled or inheriting base defaults).
     - `application-prod.yml` setting `springdoc.api-docs.enabled: false` and `springdoc.swagger-ui.enabled: false`.
     - Support standard Spring Boot environment variable overrides (`SPRINGDOC_API_DOCS_ENABLED`, `SPRINGDOC_SWAGGER_UI_ENABLED`).
   - Document local, `dev`, `staging`, and `prod` toggle instructions and env vars in `README.md`.
4. **OpenAPI Global Configuration & Bearer JWT Security Scheme**
   - Create an `@Configuration` class exposing an `OpenAPI` bean with:
     - `Info` metadata (API title, version, description).
     - Relative root server (`new Server().url("/")`) combined with `server.forward-headers-strategy=framework` so Render's TLS-terminating proxy preserves `https://`.
     - `Components` defining an HTTP Bearer JWT `SecurityScheme` (`type=HTTP`, `scheme=bearer`, `bearerFormat=JWT`).
   - Apply `@SecurityRequirement` at the controller or operation level (or globally with overrides on public endpoints) so Bearer auth is surfaced cleanly where applicable.
5. **Annotate Controllers & DTOs Incrementally**
   - Add `@Tag` to each `@RestController` to group endpoints by functional module.
   - Add `@Operation` and `@ApiResponses` (covering success responses plus standard `400`, `401`, `403`, `404`, `500` error structures) on controller endpoints.
   - Add `@Schema(description = "...", example = "...")` to request/response DTO fields so Swagger UI displays accurate descriptions and realistic sample JSON payloads.
6. **Conditional Spring Security Permit Rules (Only If Already Present)**
   - **If and only if** Spring Security is already configured in the repository, update the security filter chain to permit `/docs`, `/openapi.json`, `/openapi.json/**`, `/swagger-ui/**`, `/swagger-ui.html`, and `/v3/api-docs/**` **only when** `springdoc.swagger-ui.enabled` / `springdoc.api-docs.enabled` are `true` (so disabled `prod` environments return `404` cleanly rather than exposing docs or altering auth behavior).
   - Do not add `spring-boot-starter-security` if it is not already in `pom.xml`.

---

### 5. Test Cases, Risks, & Rollback Approach

**Test Cases**
1. **Integration — Docs Enabled (`local`/`dev`/`staging`):** `MockMvc` / `TestRestTemplate` verifies:
   - `GET /openapi.json` returns `200` (`application/json`) containing expected `@Tag` groups, REST paths, schemas, and the Bearer JWT `securitySchemes` entry.
   - `GET /openapi.json` does **not** contain `/api/ping` or `/actuator/**` paths.
   - `GET /docs` returns `200` (or redirects to `/swagger-ui/index.html` returning `200`).
2. **Integration — Docs Disabled (`prod`):** With `--spring.profiles.active=prod` (or `springdoc.api-docs.enabled=false` and `springdoc.swagger-ui.enabled=false`), verify `GET /openapi.json`, `GET /docs`, `GET /swagger-ui/index.html`, and `GET /v3/api-docs` return `404`, while `GET /api/ping` still returns `200` in `< 50ms`.
3. **Forwarded Headers / HTTPS Scheme Verification:** Send `GET /openapi.json` with `X-Forwarded-Proto: https` and `X-Forwarded-Host: example.onrender.com` and verify the resolved server URL uses `https://` rather than `http://`.
4. **End-to-End Auth & Try-It-Out:** In Swagger UI at `/docs`, authenticate via **Authorize** with a Bearer JWT (where applicable), execute an endpoint using the pre-filled sample payload, and verify the actual status code, response headers, and response/error payload render correctly.
5. **Contract Synchronization Check:** Verify in tests that controller method/DTO changes appear automatically in `/openapi.json` with zero manual spec updates.
6. **Container Memory Smoke Test:** Build the `linux/amd64` Docker image and verify startup time and runtime RSS stay safely within Render Free's 512 MB RAM ceiling.

**Risks & Mitigations**
- **Risk: Sensitive or internal endpoints exposed in `prod` or in OpenAPI spec.**
  - *Mitigation:* Exclude `/actuator/**` and `/api/ping` via `springdoc.paths-to-exclude`, disable `springdoc` in `application-prod.yml`, and assert `404` under the `prod` profile in automated tests.
- **Risk: Mixed-content errors ("Try it out" defaults to `http://` behind Render TLS termination).**
  - *Mitigation:* Set `server.forward-headers-strategy=framework` and root `/` server URL, verified with `X-Forwarded-Proto: https` tests.
- **Risk: Accidentally altering authentication behavior by adding Spring Security.**
  - *Mitigation:* Explicitly forbid adding Spring Security dependencies; only update permit matchers conditionally if Spring Security already exists.
- **Risk: Memory overhead on Render Free (512 MB RAM).**
  - *Mitigation:* Scope scanning via `springdoc.packages-to-scan` if needed and verify heap/RSS under `JAVA_TOOL_OPTIONS="-XX:MaxRAMPercentage=65.0 -XX:+UseSerialGC -Xss256k"`.
- **Risk: Spring Boot 3.x / `springdoc-openapi` version mismatch.**
  - *Mitigation:* Pin the `springdoc-openapi-starter-webmvc-ui` version matching the project's Spring Boot 3.x release and validate with Spring Boot integration tests.

**Rollback Approach**
1. **Immediate Runtime Rollback (Zero Redeploy):** Set environment variables `SPRINGDOC_API_DOCS_ENABLED=false` and `SPRINGDOC_SWAGGER_UI_ENABLED=false` in Render and restart the service.
2. **Code Rollback:** Revert the commit/PR removing the `springdoc-openapi-starter-webmvc-ui` dependency, `OpenAPI` configuration, properties/profiles, controller/DTO annotations, and any conditional security path matchers, then redeploy the previous GHCR image tag.
