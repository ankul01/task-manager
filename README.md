# task-manager

Spring Boot REST API for managing tasks (in-memory H2).

## Requirements

- Java 21
- Maven 3.8+ or `./mvnw`

## Commands

```bash
./mvnw test
./mvnw spring-boot:run
```

API base path: `http://localhost:8080/api/tasks`

## API documentation (Swagger UI)

Interactive OpenAPI documentation is provided by [springdoc-openapi](https://springdoc.org/).

| Resource | Path |
|----------|------|
| Swagger UI | `http://localhost:8080/docs` |
| OpenAPI 3 JSON | `http://localhost:8080/openapi.json` |

Endpoints under `/actuator/**` and `GET /api/ping` are excluded from the published spec.

### Environments

| Profile | Default docs |
|---------|----------------|
| local (default `application.yml`) | enabled |
| `dev` | enabled |
| `staging` | enabled |
| `prod` | disabled |

Activate a profile when running:

```bash
./mvnw spring-boot:run -Dspring-boot.run.profiles=prod
```

Override without changing files:

```bash
export SPRINGDOC_API_DOCS_ENABLED=false
export SPRINGDOC_SWAGGER_UI_ENABLED=false
```

When documentation is disabled, `/docs`, `/openapi.json`, `/swagger-ui/**`, and `/v3/api-docs/**` return HTTP 404.

Behind a TLS-terminating reverse proxy (e.g. Render), the app uses `server.forward-headers-strategy=framework` so Swagger UI "Try it out" uses `https://` when `X-Forwarded-Proto` is set.

Use the **Authorize** button in Swagger UI to supply a Bearer JWT for endpoints that require authentication when security is enabled.