---
plan_id: 20261124-082827-bootstrap-spring-boot-crud
status: draft
created_at: 2026-11-24T08:28:41Z
model: gemini-4-hydrogen
workflow_run_url: https://github.com/ankul01/task-manager/actions/runs/45356402226
requirement: "Initialize a Java Spring Boot task-manager REST API with a Task entity (id, title, description, status, priority, createdAt) and basic CRUD endpoints (POST, GET list, GET by id, PUT, DELETE) using an in-memory H2 database and unit/MockMvc tests."
---

# Draft Plan: 20261124-082827-bootstrap-spring-boot-crud

> **Human Review Required:** Merging this Pull Request to the default branch marks this exact file and commit SHA as approved for implementation.

### 1. Clarifying Questions and Assumptions

**Clarifying Questions**
1. Which Java version (e.g., 17 or 21) and Spring Boot version (e.g., 3.x) should be targeted, and is Maven or Gradle preferred?
2. What are the allowed values for `status` (e.g., `TODO`, `IN_PROGRESS`, `DONE`) and `priority` (e.g., `LOW`, `MEDIUM`, `HIGH`), and what defaults apply when omitted on creation?
3. Should `PUT` replace all mutable fields (full update) or preserve omitted fields, and should `createdAt` and `id` be immutable?
4. Is pagination/sorting or filtering (e.g., by `status` or `priority`) needed for the `GET` list endpoint?
5. Should validation errors and missing resources return a standardized JSON error structure (e.g., RFC 7807 Problem Details)?

**Assumptions**
- Target stack is Java 17+, Spring Boot 3.x, Maven, Spring Web, Spring Data JPA, Bean Validation, and H2.
- `Task` uses a generated Long or UUID primary key (`id`), required `title`, optional `description`, enum-based `status` (default `TODO`) and `priority` (default `MEDIUM`), and server-generated `createdAt` timestamp.
- Base resource path is `/api/tasks`.
- `PUT /api/tasks/{id}` performs a full update of mutable fields (`title`, `description`, `status`, `priority`) while preserving `id` and `createdAt`.
- No authentication or persistent database is required at this stage.

---

### 2. Scope and Non-Goals

**In Scope**
- Initializing a clean Spring Boot project structure with Maven/Gradle configuration and H2 in-memory persistence.
- Defining the `Task
` JPA entity, enums (`TaskStatus`, `TaskPriority`), DTOs, and repository interface.
- Implementing a service layer, REST controller (`/api/tasks`), input validation, and global exception handling (400, 404).
- Writing unit tests (service layer) and `MockMvc` integration/slice tests (controller endpoints and validation).

**Non-Goals**
- User authentication/authorization (Spring Security, JWT, OAuth2).
- External/persistent databases (PostgreSQL, MySQL) or schema migration tools (Flyway/Liquibase).
- Frontend UI, API gateway, caching, async processing, or audit history beyond `createdAt`.
- Pagination, complex search, or `PATCH` endpoints (unless requested later).

---

### 3. Testable Acceptance Criteria

1. **Application Boot & Persistence**: The Spring Boot application starts cleanly with an in-memory H2 database and auto-creates the `tasks` table.
2. **Create Task (`POST /api/tasks`)**: Valid payload returns `201 Created` with generated `id`, populated `createdAt`, default `status`/`priority` if omitted, and `Location` header; invalid payload (e.g., blank `title`) returns `400 Bad Request`.
3. **List Tasks (`GET /api/tasks`)**: Returns `200 OK` with a JSON array of all persisted tasks (or an empty array `[]` when none exist).
4. **Get Task by ID (`GET /api/tasks/{id}`)**: Returns `200 OK` with the matching task; returns `404 Not Found` for a non-existent `id`.
5. **Update Task (`PUT /api/tasks/{id}`)**: Valid payload updates mutable fields and returns `200 OK` while keeping `id` and `createdAt` unchanged; invalid payload returns `400 Bad Request`; missing `id` returns `404 Not Found`.
6. **Delete Task (`DELETE /api/tasks/{id}`)**: Removes an existing task and returns `204 No Content`; returns `404 Not Found` if `id` does not exist.
7. **Automated Test Suite**: All unit and `MockMvc` tests pass in a clean build (`mvn test` / `gradle test`).

---

### 4. Proposed Implementation Steps

1. **Project Initialization & Configuration**
   - Bootstrap project metadata and dependencies (`spring-boot-starter-web`, `spring-boot-starter-data-jpa`, `spring-boot-starter-validation`, `h2`, `spring-boot-starter-test`).
   - Configure `application.properties`/`application.yml` for in-memory H2, JPA DDL auto-generation, and optional H2 console (dev profile only).
2. **Domain Model & Persistence**
   - Define `TaskStatus` and `TaskPriority` enums.
   - Create `Task` JPA entity with validation constraints, `@PrePersist` (or JPA auditing) for `createdAt`, and defaults.
   - Create `TaskRepository` extending `JpaRepository`.
3. **DTOs, Service Layer, & Exception Handling**
   - Define request/response DTOs to decouple API contracts from the JPA entity and protect `id`/`createdAt`.
   - Implement `TaskService` for CRUD operations and entity-to-DTO mapping.
   - Add a custom `TaskNotFoundException` and a `@RestControllerAdvice` handler mapping validation errors (`400`), malformed enum/JSON payloads (`400`), and missing tasks (`404`) consistently.
4. **REST Controller**
   - Implement `TaskController` exposing `POST`, `GET` (list and by `id`), `PUT`, and `DELETE` under `/api/tasks` with `@Valid` request bodies and proper HTTP status codes.
5. **Testing & Verification**
   - Implement unit tests for `TaskService` using mocked `TaskRepository`.
   - Implement `MockMvc` tests covering all CRUD endpoints, edge cases, and error responses.
   - Run the full test suite and verify application startup.

---

### 5. Test Cases, Risks, and Rollback Approach

**Key Test Cases**
- **Service Unit Tests**:
  - Create task assigns defaults and delegates save.
  - Get/Update/Delete throw `TaskNotFoundException` when repository returns empty/non-existent.
  - Update modifies only mutable fields and preserves `createdAt`.
- **Controller `MockMvc` Tests**:
  - `POST /api/tasks`: valid request -> `201`; blank/missing `title` or invalid enum -> `400`.
  - `GET /api/tasks`: empty list -> `200 []`; populated list -> `200` with items.
  - `GET /api/tasks/{id}`: existing -> `200`; unknown ID -> `404`; invalid ID type -> `400`.
  - `PUT /api/tasks/{id}`: valid update -> `200`; invalid payload -> `400`; unknown ID -> `404`.
  - `DELETE /api/tasks/{id}`: existing -> `204`; unknown ID -> `404`.

**Risks & Mitigations**
- *Exposing JPA entities directly* -> Mitigated by using dedicated request/response DTOs.
- *Unfriendly 500 errors on invalid enum strings or malformed JSON* -> Mitigated by handling `HttpMessageNotReadableException` in `@RestControllerAdvice` to return `400`.
- *Accidental H2 console exposure in non-local environments* -> Keep H2 console disabled by default or scoped to a local/dev profile.
- *Data loss on restart* -> Expected for H2 in-memory; clearly document as a non-goal for this phase.

**Rollback Approach**
- Because this initializes a new service/module with no external database migrations or downstream dependencies, rollback consists of reverting the initialization commit(s) or removing the feature branch/artifact before deployment. No data migration rollback is required since H2 is ephemeral.
