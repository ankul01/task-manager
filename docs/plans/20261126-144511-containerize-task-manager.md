---
plan_id: 20261126-144511-containerize-task-manager
status: draft
created_at: 2026-11-26T14:45:51Z
model: gemini-4-hydrogen
route_name: gemini-hydrogen
workflow_run_url: https://github.com/ankul01/task-manager/actions/runs/45842132935
requirement: "Containerize task-manager for Lane A Render Free staging using the backend-java skill contract: add a root linux/amd64 multi-stage Java 21 Dockerfile tuned for 512 MB RAM binding ${PORT:-8080} and a root render.yaml Blueprint (runtime: image, plan: free, pointing to ghcr.io/ankul01/task-manager:latest). Ensure the health endpoint configured in deploy.yml returns fast HTTP 200 without DB dependencies."
---

# Draft Plan: 20261126-144511-containerize-task-manager

> **Human Review Required:** Merging this Pull Request to the default branch marks this exact file and commit SHA as approved for implementation.

### 1. Clarifying Questions and Assumptions

**Clarifying Questions**
* Which build tool and wrapper are used at the repository root (Maven `mvnw` or Gradle `gradlew`), and what is the expected built JAR artifact path?
* What exact health check path and timeout expectations are configured in `deploy.yml`?
* Is `ghcr.io/ankul01/task-manager:latest` publicly pullable, or does Render require GHCR registry credentials?
* Does the application currently require a database connection at startup (e.g., JPA schema validation, Flyway/Liquibase, or DataSource auto-configuration), or is a DB-less/H2/disabled-DB staging profile already available?
* Are there specific constraints in the `backend-java` skill contract (e.g., exact base image family, non-root UID, or standardized JVM flags) beyond Java 21 and 512 MB tuning?

**Assumptions**
* The service is a Java 21 web application (likely Spring Boot) configured to read the listening port from `PORT` (or `SERVER_PORT`) with a default of `8080`.
* `deploy.yml` already exists and handles building/pushing the `linux/amd64` image to `ghcr.io/ankul01/task-manager:latest` and polling a defined health endpoint.
* Render Free tier provides 512 MB RAM and shared fractional CPU, requiring conservative JVM heap/metaspace bounds and a lightweight GC (such as SerialGC) to prevent OOMKills and slow cold starts.
* Staging health checks should confirm process liveness without querying an external database.

---

### 2. Scope and Non-Goals

**Scope**
* Add a root `Dockerfile` targeting `linux/amd64` using a multi-stage Java 21 build/runtime setup, tuned for 512 MB RAM and binding to `${PORT:-8080}`.
* Add a root `render.yaml` Blueprint configured with `runtime: image`, `plan: free`, and image `ghcr.io/ankul01/task-manager:latest`, aligned with the `deploy.yml` health check path.
* Verify and adjust application/health-check configuration so the endpoint referenced in `deploy.yml` starts cleanly and returns HTTP `200` quickly without database dependencies.

**Non-Goals**
* Provisioning or migrating a managed PostgreSQL/MySQL database on Render.
* Modifying application domain logic, API contracts, or CI/CD pipeline workflows in `deploy.yml` (unless a misaligned health path requires sync).
* Publishing multi-architecture (`linux/arm64`) images or configuring paid Render tiers, autoscaling, or custom domains.

---

### 3. Testable Acceptance Criteria

1. **Container Build (`linux/amd64`)**: Building from the root `Dockerfile` for `linux/amd64` completes without errors using multi-stage layering, runs as a non-root user, and does not embed build tools or source files in the final runtime stage.
2. **512 MB Memory & Port Binding**: Running the container locally with a hard 512 MB memory limit and no swap succeeds without OOMKill; the server binds to `8080` when `PORT` is unset and binds to a custom port (e.g., `9090`) when `PORT` is supplied.
3. **DB-Independent Fast Health Check**: With no database running or DB environment variables provided, the container starts within Render's startup window and `GET` requests to the health endpoint specified in `deploy.yml` return HTTP `200` in under 1 second.
4. **Render Blueprint Validity**: `render.yaml` passes Render Blueprint validation with `runtime: image`, `plan: free`, image URL `ghcr.io/ankul01/task-manager:latest`, and a matching `healthCheckPath`.

---

### 4. Proposed Implementation Steps

1. **Inspect Existing Contracts & Configuration**
   * Read the `backend-java` skill contract to lock down required base images, user permissions, and JVM tuning rules.
   * Check `deploy.yml` for the configured health check path, build context, and any expected environment variables.
   * Check the build descriptor and application configuration to identify the Java build tool, startup dependencies (e.g., DataSource/migrations), and health endpoint implementation.
2. **Decouple Startup & Health Check from Database**
   * Ensure the health endpoint configured in `deploy.yml` does not fail or block when no database is attached (e.g., disabling DB health indicators for the liveness/health route or gating DB auto-configuration behind an optional staging profile).
3. **Create Root `Dockerfile`**
   * Implement a multi-stage `linux/amd64` build: stage 1 compiles and packages the JAR using Java 21; stage 2 copies only the runnable artifact onto a minimal Java 21 JRE image under a non-root user.
   * Configure entrypoint/JVM options tailored for 512 MB total container RAM (capping heap and metaspace/native overhead so total RSS stays safely below 512 MB) and wiring the server port to `${PORT:-8080}`.
4. **Create Root `render.yaml` Blueprint**
   * Define a web service Blueprint using `runtime: image`, `plan: free`, `image.url: ghcr.io/ankul01/task-manager:latest`, `healthCheckPath` matching `deploy.yml`, and any non-secret staging environment variables needed for DB-less startup.
5. **Local Verification & Blueprint Validation**
   * Build the `linux/amd64` image locally, run it under a strict 512 MB memory cap without DB backing, test default and custom `PORT` bindings, and validate `render.yaml`.

---

### 5. Test Cases, Risks, and Rollback Approach

**Test Cases**
* **Build & Image Hygiene**: `linux/amd64` multi-stage build succeeds; runtime image executes as non-root and contains only JRE + application artifact.
* **Default & Custom Port Binding**: Container listens on `8080` when `PORT` is omitted, and on `10000` (Render's typical dynamic port) when `PORT=10000` is set.
* **Memory Constraint Smoke Test**: Container runs under `--memory=512m --memory-swap=512m` while receiving repeated health-check requests without crashing or excessive GC pauses.
* **DB-Absent Health Check**: Health endpoint configured in `deploy.yml` returns HTTP `200` within `<1s` when no database URL/service is present.
* **Staging Blueprint Deploy**: Render Blueprint sync pulls `ghcr.io/ankul01/task-manager:latest`, passes the health check, and marks the service live.

**Risks**
* **512 MB OOMKill**: JVM heap plus metaspace, thread stacks, and direct/code-cache memory can exceed 512 MB if only heap percentage is tuned. *Mitigation*: Explicitly cap heap, metaspace, and thread stack sizes, and use SerialGC to minimize native memory overhead.
* **Startup Timeout on Render Free Tier**: Shared fractional CPU can slow Java cold starts and trigger Render health-check timeouts. *Mitigation*: Minimize classpath/auto-configuration scanning and keep the health route lightweight.
* **Private GHCR Image Pull Failure**: Render Free staging will fail to pull if `ghcr.io/ankul01/task-manager:latest` is private without configured credentials. *Mitigation*: Verify package visibility or document registry credential setup in Render.
* **Hidden DB Startup Dependencies**: Frameworks/migration tools may fail boot before the HTTP server starts if a DataSource is missing. *Mitigation*: Verify DB-less startup locally prior to pushing.

**Rollback Approach**
* Revert the commit(s) introducing `Dockerfile`, `render.yaml`, and any staging health/profile configuration changes via `git revert`.
* Delete or suspend the Render Blueprint service in the Render dashboard if a broken staging deployment is active.
