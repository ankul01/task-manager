---
plan_id: 20261124-082827-bootstrap-spring-boot-crud
status: draft
created_at: 2026-11-24T08:28:41Z
revised_at: "2026-11-24T11:41:58Z"
model: gemini-4-hydrogen
workflow_run_url: https://github.com/ankul01/task-manager/actions/runs/45356402226
requirement: "Initialize a Java Spring Boot task-manager REST API with a Task entity (id, title, description, status, priority, createdAt) and basic CRUD endpoints (POST, GET list, GET by id, PUT, DELETE) using an in-memory H2 database and unit/MockMvc tests."
---

# Draft Plan: 20261124-082827-bootstrap-spring-boot-crud

> **Human Review Required:** Merging this Pull Request to the default branch marks this exact file and commit SHA as approved for implementation.

### 1. Clarifying Questions and Assumptions

**Resolved Decisions (from Review Feedback)**
1. **Allowed `status` and `priority` values**: Confirmed as enums `TaskStatus` (`TODO`, `IN_PROGRESS`, `DONE`; default `TODO`) and `TaskPriority` (`LOW`, `MEDIUM`, `HIGH`; default `MEDIUM`).
2. **Immutability and `PUT` semantics**: Confirmed that `id` and `createdAt` are strictly immutable. `PUT /api/tasks/{id}` performs a full update of mutable fields (`title`, `description`, `status`, `priority`) while preserving `id` and `createdAt`.
3. **Resource path and pagination defaults**: Confirmed base resource path is `/api/tasks`. `GET /api/tasks` supports pagination with `page` (0-indexed, default `0`) and `size` (default `10`, capped at a reasonable maximum such as `100`), returning a custom `PagedResponse` wrapper DTO for a stable JSON contract.
4. **Standardized error responses**: Confirmed that validation failures and error conditions (e.g., `400`, `404`) must return a standardized JSON error structure (using RFC 7807 `ProblemDetail` via Spring Boot 3's built-in support, enriched with consistent `timestamp` and field-level `errors` details).

**Remaining Clarifying Questions**
- None blocking implementation; minor details such as the maximum `size` cap (`100`) and whether `CODING_GUIDELINES.md` should live at the repository root or under `docs/CODING_GUIDELINES.md` can follow standard repository convention (defaulting to `CODING_GUIDELINES.md` at the root).

**Assumptions**
- Target stack is **Java 21**, **Maven**, and the **latest compatible Spring Boot 3.x release** with Spring Web, Spring Data JPA, Bean Validation, and H2.
- **Extensibility for Authentication & Authorization**: While active authentication/authorization (Spring Security, JWT, OAuth2) is deferred from v1, the application architecture must be cleanly extensible to support AuthN/AuthZ in subsequent iterations:
  - Keep endpoints stateless and RESTful under `/api/tasks` so a `SecurityFilterChain` can protect `/api/**` without route restructuring.
  - Separate API DTOs from JPA entities and isolate business logic in the service layer so user/tenant context (e.g., `@AuthenticationPrincipal`, ownership checks, or role-based `@PreAuthorize` rules) can be introduced with minimal refactoring.
  - Design the standardized JSON error handler to cleanly accommodate `401 Unauthorized` and `403 Forbidden` responses in the future.
- `Task` uses a server-generated `Long` or `UUID` primary key (`id`), required non-blank `title`, optional `description`, enum-based `status` and `priority`, and server-generated immutable `createdAt` timestamp (`Instant` / UTC).
- Implementation follows modern Java 21 and Spring Boot industry coding standards (e.g., Java `record` types for immutable DTOs, constructor-based dependency injection, `final` fields, clear package boundaries, and consistent formatting/naming), documented in a dedicated `CODING_GUIDELINES.md` file.
- No persistent external database is required at this stage.

---

### 2. Scope and Non-Goals

**In Scope**
- Initializing a clean Spring Boot Maven project targeting Java 21 with the latest compatible Spring Boot 3.x version and H2 in-memory persistence.
- Creating a separate `CODING_GUIDELINES.md` file documenting the Java 21 & Spring Boot industry coding standards applied across the project.
- Defining the `Task` JPA entity, enums (`TaskStatus`, `TaskPriority`), immutable request/response DTOs (Java `record`s), `PagedResponse` wrapper, and `TaskRepository`.
- Implementing a service layer, REST controller (`/api/tasks`), input validation, and global `@RestControllerAdvice` exception handling returning a standardized JSON error format (RFC 7807 `ProblemDetail` with field error details).
- Supporting `page` (default `0`) and `size` (default `10`) pagination query parameters on the `GET /api/tasks` endpoint.
- Structuring packages, service boundaries, and error handling so Authentication and Authorization can be added cleanly in future phases.
- Writing unit tests (service layer) and `MockMvc` integration/slice tests (controller endpoints, pagination with default size `10`, immutability of `id`/`createdAt`, and standardized JSON error responses).

**Non-Goals**
- Implementing active user authentication/authorization (Spring Security, JWT, OAuth2, login/user entities) in v1—only architectural readiness/extensibility is in scope.
- External/persistent databases (PostgreSQL, MySQL) or schema migration tools (Flyway/Liquibase).
- Frontend UI, API gateway, caching, async processing, or audit history beyond `createdAt`.
- Complex search/filtering, custom sorting parameters, or `PATCH` endpoints (unless requested later).

---

### 3. Testable Acceptance Criteria

1. **Application Boot & Persistence**: The Spring Boot application builds with Maven on Java 21, starts cleanly with an in-memory H2 database, and auto-creates the `tasks` table.
2. **Coding Guidelines Documentation**: A dedicated `CODING_GUIDELINES.md` file exists in the project documenting Java 21 and Spring Boot industry standards (immutability, Java `record` DTOs, constructor injection, exception handling, testing conventions, and layering), and the codebase adheres to it.
3. **Create Task (`POST /api/tasks`)**: Valid payload returns `201 Created` with generated `id`, populated `createdAt`, default `status` (`TODO`) and `priority` (`MEDIUM`) if omitted, and `Location` header; invalid payload (e.g., blank `title`, invalid enum) returns `400 Bad Request` with the standardized JSON error structure.
4. **List Tasks with Pagination (`GET /api/tasks?page=&size=`)**: Accepts optional `page` and `size` query parameters (defaulting to `page=0` and `size=10`), returns `200 OK` with the requested slice of persisted tasks and pagination metadata (`content`, `page`, `size`, `totalElements`, `totalPages`, `first`, `last`); invalid parameters (e.g., `page < 0`, `size < 1`, or `size > 100`) return `400 Bad Request` with the standardized JSON error structure.
5. **Get Task by ID (`GET /api/tasks/{id}`)**: Returns `200 OK` with the matching task; returns `404 Not Found` with the standardized JSON error structure for a non-existent `id`.
6. **Update Task (`PUT /api/tasks/{id}`)**: Valid payload updates mutable fields (`title`, `description`, `status`, `priority`) and returns `200 OK` while guaranteeing `id` and `createdAt` remain immutable even if supplied in the request; invalid payload returns `400 Bad Request` and missing `id` returns `404 Not Found` using the standardized JSON error structure.
7. **Delete Task (`DELETE /api/tasks/{id}`)**: Removes an existing task and returns `204 No Content`; returns `404 Not Found` with the standardized JSON error structure if `id` does not exist.
8. **AuthN/AuthZ Extensibility**: Package structure, DTO boundaries, stateless REST design, and centralized exception handling allow adding Spring Security and user/ownership scoping without breaking `/api/tasks` API contracts or coupling domain logic to transport details.
9. **Automated Test Suite**: All unit and `MockMvc` tests pass in a clean Maven build (`mvn test`).

---

### 4. Proposed Implementation Steps

1. **Coding Guidelines & Project Initialization**
   - Author `CODING_GUIDELINES.md` establishing industry-standard Java 21 and Spring Boot conventions:
     - Clean layered/package structure (`controller`, `service`, `repository`, `domain`/`model`, `dto`, `exception`, `config`).
     - Constructor injection only (no field `@Autowired`), `final` dependencies, Java `record`s for immutable DTOs, `Instant` (UTC) for timestamps, explicit `Optional` handling, and clear Javadoc on public APIs/contracts.
     - Standardized REST conventions, validation placement, and testing standards (AAA pattern, AssertJ, Mockito, `@WebMvcTest`/full `MockMvc`).
   - Bootstrap a Maven `pom.xml` configured for Java 21 and the latest compatible Spring Boot 3.x parent/BOM with dependencies (`spring-boot-starter-web`, `spring-boot-starter-data-jpa`, `spring-boot-starter-validation`, `h2`, `spring-boot-starter-test`).
   - Configure `application.yml` (or `application.properties`) for in-memory H2, JPA DDL auto-generation, `spring.mvc.problemdetails.enabled=true`, and optional H2 console (dev profile only).
2. **Domain Model & Persistence**
   - Define `TaskStatus` (`TODO`, `IN_PROGRESS`, `DONE`) and `TaskPriority` (`LOW`, `MEDIUM`, `HIGH`) enums.
   - Create the `Task` JPA entity with Bean Validation constraints, `@Column(updatable = false, nullable = false)` on `id` and `createdAt`, `@PrePersist` for server-generated `createdAt` and default `status`/`priority` assignment, and controlled mutation methods to enforce `id`/`createdAt` immutability.
   - Create `TaskRepository` extending `JpaRepository` (providing `findAll(Pageable)`).
3. **Immutable DTOs, Service Layer, & Standardized Error Handling**
   - Define Java `record` DTOs:
     - `CreateTaskRequest` and `UpdateTaskRequest` (excluding `id` and `createdAt` from accepted mutable fields, with Bean Validation annotations).
     - `TaskResponse` and generic `PagedResponse<T>` DTOs to decouple API contracts from the JPA entity and Spring's `PageImpl` serialization.
   - Implement `TaskService` (interface + implementation, or clean service class with constructor injection) for CRUD operations, paginated retrieval using `PageRequest.of(page, size)`, and entity-to-DTO mapping—structured cleanly so user/principal context parameters or authorization checks can be added easily later.
   - Add `TaskNotFoundException` and a `@RestControllerAdvice` global exception handler producing a standardized JSON error structure (RFC 7807 `ProblemDetail` with consistent `type`, `title`, `status`, `detail`, `instance`, `timestamp`, and structured `errors` map/list for validation failures), handling:
     - `MethodArgumentNotValidException` (`400`)
     - `ConstraintViolationException` (`400`)
     - `HttpMessageNotReadableException` / invalid enum values (`400`)
     - `MethodArgumentTypeMismatchException` (`400`)
     - `TaskNotFoundException` (`404`)
4. **REST Controller**
   - Implement `TaskController` exposing `POST`, `GET` (paginated list with `@RequestParam(defaultValue = "0") @Min(0) int page` and `@RequestParam(defaultValue = "10") @Min(1) @Max(100) int size`, plus `GET` by `id`), `PUT`, and `DELETE` under `/api/tasks` with `@Valid`, `@Validated`, and proper HTTP status codes (`201`, `200`, `204`).
5. **Testing & Verification**
   - Implement unit tests for `TaskService` using mocked `TaskRepository`, verifying defaults, pagination delegation, `TaskNotFoundException`, and `id`/`createdAt` immutability during updates.
   - Implement `MockMvc` tests covering all `/api/tasks` CRUD endpoints, default pagination (`page=0`, `size=10`), explicit `page`/`size` query parameters, immutability checks on `PUT`, and standardized JSON error payload assertions for `400` and `404` responses.
   - Run `mvn test` and verify clean application startup.

---

### 5. Test Cases, Risks, and Rollback Approach

**Key Test Cases**
- **Service Unit Tests**:
  - Create task assigns default `status=TODO`, `priority=MEDIUM`, generates `createdAt`, and delegates save.
  - List tasks builds `PageRequest.of(page, size)` (defaulting to `0, 10` at controller boundary) and maps `Page<Task>` to `PagedResponse<TaskResponse>` accurately.
  - Get/Update/Delete throw `TaskNotFoundException` when repository returns empty/non-existent.
  - Update modifies only `title`, `description`, `status`, and `priority`, leaving `id` and `createdAt` unchanged.
- **Controller `MockMvc` Tests**:
  - `POST /api/tasks`: valid request -> `201` with `Location` header and populated `id`/`createdAt`; blank/missing `title` or invalid enum -> `400` with standardized JSON error body including field details.
  - `GET /api/tasks`: empty database -> `200` with empty `content` and `size=10`; >10 tasks with no query params -> returns 10 items (`page=0`, `size=10`); explicit `?page=1&size=5` returns expected slice and metadata; invalid `page`/`size` (`page=-1`, `size=0`, `size=101`, non-numeric) -> `400` with standardized JSON error body.
  - `GET /api/tasks/{id}`: existing -> `200`; unknown ID -> `404` with standardized JSON error body; invalid ID type -> `400` with standardized JSON error body.
  - `PUT /api/tasks/{id}`: valid update -> `200` and verifies `id` and `createdAt` remain unchanged (even if sent in JSON body); invalid payload -> `400` with standardized JSON error body; unknown ID -> `404` with standardized JSON error body.
  - `DELETE /api/tasks/{id}`: existing -> `204`; unknown ID -> `404` with standardized JSON error body.

**Risks & Mitigations**
- *Exposing JPA entities or unstable `PageImpl` JSON structure directly* -> Mitigated by using immutable Java `record` DTOs and a `PagedResponse<T>` wrapper.
- *Accidental mutation of `id` or `createdAt` during `PUT`* -> Mitigated by excluding them from `UpdateTaskRequest`, marking JPA columns `updatable = false`, and asserting immutability in unit and `MockMvc` tests.
- *Excessively large `size` parameter causing memory or response bloat* -> Mitigated by enforcing `@Min`/`@Max` bounds on `page` and `size` query parameters (`defaultValue = "10"`, max `100`).
- *Inconsistent or opaque error responses on invalid input* -> Mitigated by centralizing all exception mapping in `@RestControllerAdvice` using a standardized RFC 7807 JSON structure.
- *Future AuthN/AuthZ integration causing breaking changes* -> Mitigated by keeping `/api/tasks` stateless, avoiding entity exposure, isolating business logic in `TaskService`, and structuring exception handling to easily add `401`/`403` handlers later.
- *Accidental H2 console exposure in non-local environments* -> Keep H2 console disabled by default or scoped to a local/dev profile.
- *Data loss on restart* -> Expected for H2 in-memory; documented as a non-goal for this phase.

**Rollback Approach**
- Because this initializes a new service/module with no external database migrations or downstream dependencies, rollback consists of reverting the initialization commit(s) (including `CODING_GUIDELINES.md`) or removing the feature branch/artifact before deployment. No data migration rollback is required since H2 is ephemeral.
