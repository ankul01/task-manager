---
plan_id: 20261126-144511-containerize-task-manager
status: draft
created_at: 2026-11-26T14:45:51Z
revised_at: "2026-11-26T15:17:21Z"
model: gemini-4-hydrogen
route_name: gemini-hydrogen
workflow_run_url: https://github.com/ankul01/task-manager/actions/runs/45842132935
requirement: "Containerize task-manager for Lane A Render Free staging using the backend-java skill contract: add a root linux/amd64 multi-stage Java 21 Dockerfile tuned for 512 MB RAM binding ${PORT:-8080} and a root render.yaml Blueprint (runtime: image, plan: free, pointing to ghcr.io/ankul01/task-manager:latest). Ensure the health endpoint configured in deploy.yml returns fast HTTP 200 without DB dependencies."
---

# Draft Plan: 20261126-144511-containerize-task-manager

> **Human Review Required:** Merging this Pull Request to the default branch marks this exact file and commit SHA as approved for implementation.

### 1. Confirmed Decisions, Open Checks, and Assumptions

**Confirmed Decisions (from User Feedback & `skills/backend-java.md`)**
* **Build Tool & Packaging**: Maven (`pom.xml` at repository root) without relying on `./mvnw`. The builder stage uses `maven:3.9-eclipse-temurin-21-alpine` with `mvn -B dependency:go-offline` and `mvn -B package -DskipTests`, copying the Spring Boot repackaged fat JAR (`target/*.jar`, excluding `*.jar.original`) to `/app/app.jar`.
* **Runtime & `backend-java` Contract**:
  * Builder stage: `FROM --platform=linux/amd64 maven:3.9-eclipse-temurin-21-alpine AS builder`
  * Runtime stage: `FROM --platform=linux/amd64 eclipse-temurin:21-jre-alpine`
  * Non-root Alpine user/group `app` (`addgroup -S app && adduser -S app -G app`, `chown app:app /app/app.jar`, `USER app`; no specific numeric UID required).
  * Standardized JVM options: `ENV JAVA_TOOL_OPTIONS="-XX:MaxRAMPercentage=65.0 -XX:+UseSerialGC -Xss256k -Djava.security.egd=file:/dev/./urandom"`
  * Port & entrypoint: `EXPOSE 8080` and `ENTRYPOINT ["sh", "-c", "exec java -Dserver.port=${PORT:-8080} -jar /app/app.jar"]`.
* **GHCR Image Visibility & `render.yaml`**: `ghcr.io/ankul01/task-manager:latest` will be publicly pullable; no GHCR registry credentials are to be added to `render.yaml`.
* **Database Strategy (Lane A)**: Target DB-less / in-memory (H2) startup with no external database environment variables required (Neon Postgres wiring is deferred to Lane C).
* **Health Check Latency & Timeouts**: Target `< 50ms` response time with zero DB calls. Render's HTTP probe expects `2xx`/`3xx` within 5 seconds, and `reusable-deploy-render.yml` waits 20s after triggering the deploy hook before polling every 10s up to 120s (`smoke_timeout_sec: 120`).

**Remaining Implementation-Time Checks**
* Confirm the exact `health_path` value configured in `.github/workflows/deploy.yml` (referred to as `<CONFIRM_HEALTH_PATH>`) and verify whether that endpoint (e.g., `GET /api/ping`) already exists or must be added.
* Inspect `pom.xml` and `src/main/resources/application.*` during implementation to verify whether external DataSource, JPA, or Flyway/migration settings currently block startup when no external DB is configured.

**Assumptions**
* `.github/workflows/deploy.yml` and `reusable-deploy-render.yml` already handle building/pushing `ghcr.io/ankul01/task-manager:latest` and executing the Render deploy hook and smoke poll.
* Render Free tier provides 512 MB RAM and shared fractional CPU, making the standardized `backend-java` JVM flags (`MaxRAMPercentage=65.0`, `UseSerialGC`, `-Xss256k`) sufficient to keep total RSS within limits while allowing cold start within the 120s smoke window.

---

### 2. Scope and Non-Goals

**Scope**
* Add a root `Dockerfile` conforming to `skills/backend-java.md` (`linux/amd64` multi-stage build with `maven:3.9-eclipse-temurin-21-alpine` and `eclipse-temurin
:21-jre-alpine`, non-root `app` user, standardized `JAVA_TOOL_OPTIONS`, and `-Dserver.port=${PORT:-8080}`).
* Add a root `render.yaml` Blueprint (`type: web`, `name: task-manager`, `runtime: image`, `plan: free`, `image.url: ghcr.io/ankul01/task-manager:latest`, `healthCheckPath` matching `.github/workflows/deploy.yml`, with no GHCR credentials).
* Ensure the application boots cleanly in Lane A without external DB environment variables (using DB-less / in-memory H2 defaults if needed) and that `<CONFIRM_HEALTH_PATH>` (adding a zero-DB `GET /api/ping` if `/api/ping` is configured and missing) returns HTTP `200` in `< 50ms`.

**Non-Goals**
* Provisioning, wiring, or migrating Neon Postgres or any external managed database (deferred to Lane C).
* Adding GHCR pull credentials to `render.yaml` or modifying CI/CD workflows (`.github/workflows/deploy.yml` / `reusable-deploy-render.yml`).
* Publishing `linux/arm64` multi-arch images or configuring paid Render tiers, autoscaling, or custom domains.

---

### 3. Testable Acceptance Criteria

1. **Container Build (`linux/amd64` & `backend-java` Contract)**: Building from the root `Dockerfile` for `linux/amd64` runs Maven (`mvn -B dependency:go-offline` and `mvn -B package -DskipTests`) in `maven:3.9-eclipse-temurin-21-alpine`, packages only the Spring Boot repackaged fat JAR (excluding `*.jar.original`) into `/app/app.jar` on `eclipse-temurin:21-jre-alpine`, runs as non-root user `app`, and contains no Maven/build artifacts in the final stage.
2. **512 MB Memory & Port Binding**: Running the container locally under a strict 512 MB memory limit with no swap succeeds using `JAVA_TOOL_OPTIONS="-XX:MaxRAMPercentage=65.0 -XX:+UseSerialGC -Xss256k -Djava.security.egd=file:/dev/./urandom"` without OOMKill; Spring Boot binds to `8080` when `PORT` is unset and binds to a custom port (e.g., `10000`) when `PORT` is provided.
3. **DB-Independent Fast Health Check**: With no external database running or DB environment variables provided, the container starts cleanly (within the 20s initial wait + 120s polling window of `reusable-deploy-render.yml`) and `GET` requests to `<CONFIRM_HEALTH_PATH>` from `.github/workflows/deploy.yml` return HTTP `200` in `< 50ms` (well under Render's 5s probe timeout) with zero DB calls.
4. **Render Blueprint Validity**: Root `render.yaml` defines `type: web`, `name: task-manager`, `runtime: image`, `plan: free`, `image.url: ghcr.io/ankul01/task-manager:latest`, `healthCheckPath: <CONFIRM_HEALTH_PATH>`, and omits registry credentials, passing Render Blueprint validation.

---

### 4. Proposed Implementation Steps

1. **Inspect Workflow, Skill Contract, and App Startup Configuration**
   * Read `skills/backend-java.md` to confirm exact compliance with all image, user, JVM, and Blueprint rules.
   * Read `.github/workflows/deploy.yml` to capture the exact `health_path` (`<CONFIRM_HEALTH_PATH>`).
   * Inspect `pom.xml` and `src/main/resources/application.*` to verify Spring Boot repackaging behavior, H2/in-memory DB support, and whether any external DataSource, JPA schema validation, or Flyway/Liquibase configuration blocks DB-less startup.
2. **Ensure DB-Less / H2 Startup and Zero-DB Health Endpoint**
   * If `application.*` or `pom.xml` currently requires an external database at startup, configure a default DB-less / in-memory H2 setup for Lane A so the service boots without external DB environment variables.
   * Verify `<CONFIRM_HEALTH_PATH>` exists and performs no database queries; if `.github/workflows/deploy.yml` uses `/api/ping` and the route is missing (or touches the DB), add/update a lightweight zero-DB `GET /api/ping` endpoint returning HTTP `200` in `< 50ms`.
3. **Create Root `Dockerfile`**
   * Implement the two-stage `linux/amd64` `Dockerfile` per `skills/backend-java.md`:
     * Stage 1 (`builder`): `FROM --platform=linux/amd64 maven:3.9-eclipse-temurin-21-alpine AS builder`, copy `pom.xml`, run `mvn -B dependency:go-offline`, copy `src`, run `mvn -B package -DskipTests`, and isolate the Spring Boot fat JAR (excluding `*.jar.original`).
     * Stage 2 (runtime): `FROM --platform=linux/amd64 eclipse-temurin:21-jre-alpine`, create system group/user `app` (`addgroup -S app && adduser -S app -G app`), copy the fat JAR to `/app/app.jar` with `chown app:app /app/app.jar`, switch to `USER app`, set `ENV JAVA_TOOL_OPTIONS="-XX:MaxRAMPercentage=65.0 -XX:+UseSerialGC -Xss256k -Djava.security.egd=file:/dev/./urandom"`, `EXPOSE 8080`, and set `ENTRYPOINT ["sh", "-c", "exec java -Dserver.port=${PORT:-8080} -jar /app/app.jar"]`.
4. **Create Root `render.yaml` Blueprint**
   * Add `render.yaml` at the repository root with:
     * `services` entry `type: web`, `name: task-manager`, `runtime: image`, `plan: free`, `image.url: ghcr.io/ankul01/task-manager:latest`, and `healthCheckPath` set to the exact `health_path` from `.github/workflows/deploy.yml` (no GHCR credentials).
5. **Local Verification & Blueprint Validation**
   * Build the `linux/amd64` image locally, verify `USER app` and `/app/app.jar` contents, run under `--memory=512m --memory-swap=512m` with no external DB env vars, test `PORT` default (`8080`) and override (e.g., `PORT=10000`), measure `<CONFIRM_HEALTH_PATH>` latency (`< 50ms`, HTTP `200`), and validate `render.yaml`.

---

### 5. Test Cases, Risks, and Rollback Approach

**Test Cases**
* **Maven Multi-Stage Build & Image Hygiene**: `linux/amd64` Docker build succeeds using `mvn -B dependency:go-offline` and `mvn -B package -DskipTests` without `./mvnw`; final image runs as non-root `app`, excludes `*.jar.original`, and contains only JRE + `/app/app.jar`.
* **Default & Custom Port Binding**: Container listens on `8080` when `PORT` is unset, and listens on `10000` when `PORT=10000` is passed.
* **512 MB Memory Constraint Smoke Test**: Container runs under `--memory=512m --memory-swap=512m` with the standardized `JAVA_TOOL_OPTIONS` while handling repeated health-check probes without OOMKill.
* **DB-Absent Fast Health Check**: With zero DB env vars and no external DB running, container finishes booting well within the 20s wait + 120s smoke window (`smoke_timeout_sec: 120`) and `GET <CONFIRM_HEALTH_PATH>` returns HTTP `200` in `< 50ms`.
* **Staging Blueprint Deploy**: Render Blueprint sync pulls public `ghcr.io/ankul01/task-manager:latest` without registry credentials, passes Render's 5s HTTP probe on `healthCheckPath`, and passes `reusable-deploy-render.yml` smoke polling.

**Risks**
* **512 MB OOMKill**: Native memory (metaspace, code cache, direct buffers, thread stacks) plus 65% heap could approach 512 MB under load. *Mitigation*: Use the standardized `backend-java` flags (`-XX:MaxRAMPercentage=65.0 -XX:+UseSerialGC -Xss256k`) and verify RSS under `--memory=512m --memory-swap=512m` locally.
* **Slow Cold Start Exceeding 120s Smoke Window**: Shared fractional CPU on Render Free can slow Spring Boot startup. *Mitigation*: Keep `JAVA_TOOL_OPTIONS` lightweight (`UseSerialGC`, `-Djava.security.egd=file:/dev/./urandom`) and avoid external DB connection retries at boot.
* **Health Path Mismatch or DB-Coupled Health Route**: If `render.yaml` `healthCheckPath` diverges from `health_path` in `.github/workflows/deploy.yml`, or if the endpoint triggers a DB query/indicator, probes will fail or exceed 50ms/5s. *Mitigation*: Sync `healthCheckPath` directly with `.github/workflows/deploy.yml` and ensure the route (such as `GET /api/ping`) has zero DB dependencies.
* **Accidental Copying of `*.jar.original`**: Maven Spring Boot builds produce both the executable fat JAR and `*.jar.original`, which would break `target/*.jar` copy/execution if both are matched. *Mitigation*: Explicitly exclude `*.jar.original` when copying the built artifact to `/app/app.jar`.

**Rollback Approach**
* Revert the commit(s) introducing `Dockerfile`, `render.yaml`, and any Lane A DB-less/health-endpoint changes via `git revert`.
* Delete or suspend the Render Blueprint service in the Render dashboard if a broken staging deployment is active.
