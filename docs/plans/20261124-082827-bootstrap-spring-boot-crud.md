---
plan_id: 20261124-082827-bootstrap-spring-boot-crud
status: draft
created_at: 2026-11-24T08:28:41Z
revised_at: "2026-11-24T11:19:47Z"
model: gemini-4-hydrogen
workflow_run_url: https://github.com/ankul01/task-manager/actions/runs/45356402226
requirement: "Initialize a Java Spring Boot task-manager REST API with a Task entity (id, title, description, status, priority, createdAt) and basic CRUD endpoints (POST, GET list, GET by id, PUT, DELETE) using an in-memory H2 database and unit/MockMvc tests."
---

# Draft Plan: 20261124-082827-bootstrap-spring-boot-crud

> **Human Review Required:** Merging this Pull Request to the default branch marks this exact file and commit SHA as approved for implementation.

### 1. Clarifying Questions and Assumptions

**Clarifying Questions**
1. What are the allowed values for `status` (e.g., `TODO`, `IN_PROGRESS`, `DONE`) and `priority` (e.g., `LOW`, `MEDIUM`, `HIGH`), and what defaults apply when omitted on creation?
2. Should `PUT` replace all mutable fields (full update) or preserve omitted fields, and should `createdAt` and `id` be immutable?
3. Should the base resource path remain `/api/tasks` or be `/tasks`, and what default/maximum `size` and response structure (e.g., Spring `Page` vs. a custom `PagedResponse` wrapper) are preferred for the paginated `GET` list endpoint?
4. Should validation errors and missing resources return a standardized JSON error structure (e.g., RFC 7807 Problem Details)?

**Assumptions**
- Target stack is **Java 21**, **Maven**, and the **latest compatible Spring Boot 3.x release** with Spring Web, Spring Data JPA, Bean Validation, and H2.
- Authentication and authorization are explicitly out of scope for v1.
- `Task` uses a generated Long or UUID primary key (`id`), required `title`, optional `description`, enum-based `status` (default `TODO`) and `priority` (default `MEDIUM`), and server-generated `createdAt` timestamp.
- Base resource path is `/api/tasks` (pending confirmation if `/tasks` without the `/api` prefix is preferred).
- `GET /api/tasks` supports pagination via `page` (0-indexed, default `0`) and `size` (default `20`, capped at a reasonable maximum such as `100`) query parameters.
- `PUT /api/tasks/{id}` performs a full update of mutable fields (`title`, `description`, `status`, `priority`) while preserving `id` and `createdAt`.
- No persistent database is required at this stage.

---

### 2. Scope and Non-Goals

**In Scope**
- Initializing a clean Spring Boot Maven project targeting Java 21 with the latest compatible Spring Boot version and H2 in-memory persistence.
- Defining the `Task` JPA entity, enums (`TaskStatus`, `TaskPriority`), DTOs, and repository interface.
- Implementing a service layer, REST controller (`/api/tasks`), input validation, and global exception handling (400, 404).
- Supporting `page` and `size` pagination query parameters on the `GET` list endpoint.
- Writing unit tests (service layer) and `MockMvc` integration/slice tests (controller endpoints, pagination, and validation).

**Non-Goals**
- User authentication/authorization (Spring Security, JWT, OAuth2) for v1.
- External/persistent databases (PostgreSQL, MySQL) or schema migration tools (Flyway/Liquibase).
- Frontend UI, API gateway, caching, async processing, or audit history beyond `createdAt`.
- Complex search/filtering, custom sorting parameters, or `PATCH` endpoints (unless requested later).

---

### 3. Testable Acceptance Criteria

1. **Application Boot & Persistence**: The Spring Boot application builds with Maven on Java 21, starts cleanly with an in-memory H2 database, and auto-creates the `tasks` table.
2. **Create Task (`POST /api/tasks`)**: Valid payload returns `201 Created` with generated `id`, populated `createdAt`, default `status`/`priority` if omitted, and `Location` header; invalid payload (e.g., blank `title`) returns `400 Bad Request`.
3. **List Tasks with Pagination (`GET /api/tasks?page=&size=`)**: Accepts optional `page` and `size` query parameters (defaulting to `page=0` and `size=20`), returns `200 OK` with the requested slice of persisted tasks and pagination metadata (or an empty content list when none exist); invalid parameters (e.g., `page < 0` or `size < 1`) return `400 Bad Request`.
4. **Get Task by ID (`GET /api/tasks/{id}`)**: Returns `200 OK` with the matching task; returns `404 Not Found` for a non-existent `id`.
5. **Update Task (`PUT /api/tasks/{id}`)**: Valid payload updates mutable fields and returns `200 OK` while keeping `id` and `createdAt` unchanged; invalid payload returns `400 Bad Request`; missing `id` returns `404 Not Found`.
6. **Delete Task (`DELETE /api/tasks/{id}`)**: Removes an existing task and returns `204 No Content`; returns `404 Not Found` if `id` does not exist.
7. **Automated Test Suite**: All unit and `MockMvc` tests pass in a clean Maven build (`mvn test`).

---

### 4. Proposed Implementation Steps

1. **Project Initialization & Configuration**
   - Bootstrap a Maven `pom.xml` configured for Java 21 and the latest compatible Spring Boot 3.x parent/BOM with dependencies (`spring-boot-starter-web`, `spring-boot-starter-data-jpa`, `spring-boot-starter-validation`, `h2`, `spring-boot-starter-test`).
   - Configure `application.properties`/`application.yml` for in-memory H2, JPA DDL auto-generation, and optional H2 console (dev profile only).
2. **Domain Model & Persistence**
   - Define `TaskStatus` and `TaskPriority` enums.
   - Create `Task` JPA entity with validation constraints, `@PrePersist` (or JPA auditing) for `createdAt`, and defaults.
   - Create `TaskRepository` extending `JpaRepository` (which provides `findAll(Pageable)` out of the box).
3. **DTOs, Service Layer, & Exception Handling**
   - Define request/response DTOs (including a paginated response DTO if avoiding direct serialization of Spring's `PageImpl`) to decouple API contracts from the JPA entity and protect `id`/`createdAt`.
   - Implement `TaskService` for CRUD operations, paginated retrieval using `PageRequest.of(page, size)`, and entity-to-DTO mapping.
   - Add a custom `TaskNotFoundException` and a `@RestControllerAdvice` handler mapping validation/constraint errors (`400`), malformed enum/JSON/query parameter types (`400`), and missing tasks (`404`) consistently.
4. **REST Controller**
   - Implement `TaskController` exposing `POST`, `GET` (paginated list accepting `page` and `size` query params, and `GET` by `id`), `PUT`, and `DELETE` under `/api/tasks` with `@Valid`/`@Validated` validation and proper HTTP status codes.
5. **Testing & Verification**
   - Implement unit tests for `TaskService` using mocked `TaskRepository`, including pagination delegation.
   - Implement `MockMvc` tests covering all CRUD endpoints, `page`/`size` query parameter behavior, edge cases, and error responses.
   - Run `mvn test` and verify application startup.

---

### 5. Test Cases, Risks, and Rollback Approach

**Key Test Cases**
- **Service Unit Tests**:
  - Create task assigns defaults and delegates save.
  - List tasks builds the expected `PageRequest(page, size)` and maps `Page<Task>` results accurately.
  - Get/Update/Delete throw `TaskNotFoundException` when repository returns empty/non-existent.
  - Update modifies only mutable fields and preserves `createdAt`.
- **Controller `MockMvc` Tests**:
  - `POST /api/tasks`: valid request -> `201`; blank/missing `title` or invalid enum -> `400`.
  - `GET /api/tasks`: empty database -> `200` with empty content; default `page`/`size` returns first page; explicit `?page=1&size=2` returns expected slice and metadata; invalid `page`/`size` (negative, zero size, non-numeric) -> `400`.
  - `GET /api/tasks/{id}`: existing -> `200`; unknown ID -> `404`; invalid ID type -> `400`.
  - `PUT /api/tasks/{id}`: valid update -> `200`; invalid payload -> `400`; unknown ID -> `404`.
  - `DELETE /api/tasks/{id}`: existing -> `204`; unknown ID -> `404`.

**Risks & Mitigations**
- *Exposing JPA entities or unstable `PageImpl` JSON structure directly* -> Mitigated by using dedicated request/response and page wrapper DTOs.
- *Excessively large `size` parameter causing memory or response bloat* -> Mitigated by enforcing `@Min`/`@Max` bounds on `page` and `size` query parameters.
- *Unfriendly 500 errors on invalid enum strings, malformed JSON, or invalid query parameter types* -> Mitigated by handling `HttpMessageNotReadableException`, `ConstraintViolationException`, and `MethodArgumentTypeMismatchException` in `@RestControllerAdvice` to return `400`.
- *Accidental H2 console exposure in non-local environments* -> Keep H2 console disabled by default or scoped to a local/dev profile.
- *Data loss on restart* -> Expected for H2 in-memory; clearly document as a non-goal for this phase.

**Rollback Approach**
- Because this initializes a new service/module with no external database migrations or downstream dependencies, rollback consists of reverting the initialization commit(s) or removing the feature branch/artifact before deployment. No data migration rollback is required since H2 is ephemeral.
