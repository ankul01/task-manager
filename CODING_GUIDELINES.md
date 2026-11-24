# Coding guidelines

## Stack

- Java 21
- Spring Boot 3.x, Maven
- Constructor-based dependency injection only; depend on `final` fields

## Layering

Packages under `com.taskmanager`:

- `controller` — HTTP adapters, validation entry points
- `service` — business logic and DTO mapping
- `repository` — Spring Data interfaces
- `domain` — JPA entities and enums
- `dto` — immutable Java `record` types for API contracts
- `exception` — domain errors and `@RestControllerAdvice` handlers

## API and domain

- Expose DTOs only; never serialize JPA entities directly
- Use `Instant` (UTC) for timestamps
- Use enums for `status` and `priority`
- Centralize error responses as RFC 7807 `ProblemDetail` with `timestamp` and field `errors` where applicable

## Testing

- Service layer: JUnit 5 + Mockito, AssertJ assertions, AAA structure
- HTTP layer: `@WebMvcTest` + MockMvc
- Prefer behavior-focused tests aligned with acceptance criteria in `docs/plans/`