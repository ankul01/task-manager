---
plan_id: 20261125-171459-api-ping-endpoint
status: draft
created_at: 2026-11-25T17:15:59Z
model: nvidia/nemotron-3-ultra-550b-a55b
route_name: nvidia-nemotron
workflow_run_url: https://github.com/ankul01/task-manager/actions/runs/45662678290
requirement: "Add a lightweight GET /api/ping REST endpoint to task-manager for pipeline smoke testing.\n\nRequirements:\n1. Expose GET /api/ping returning HTTP 200 OK with Content-Type application/json and exact JSON body:\n   {\"status\":\"pong\",\"service\":\"task-manager\"}\n2. Keep it completely stateless inside a small controller class (e.g., PingController). Do NOT modify any database schema, entities, repositories, or existing endpoints, and do NOT add new Maven dependencies.\n3. If Spring Security is configured in the project, permit unauthenticated GET access to /api/ping; otherwise keep standard controller behavior.\n4. Add one focused controller test class (PingControllerTest) using @WebMvcTest and MockMvc verifying HTTP 200 and both JSON fields (\"status\" = \"pong\", \"service\" = \"task-manager\").\n5. Verify mvn test passes cleanly."
---

# Draft Plan: 20261125-171459-api-ping-endpoint

> **Human Review Required:** Merging this Pull Request to the default branch marks this exact file and commit SHA as approved for implementation.

## 1. Clarifying Questions & Assumptions
| # | Question / Assumption | Resolution |
|---|-----------------------|------------|
| 1 | **Spring Boot version & packaging** – assumes a standard Spring Boot 2.x/3.x web MVC project (spring-boot-starter-web) with Maven. | Proceed with standard annotations (`@RestController`, `@GetMapping`). |
| 2 | **Spring Security presence** – the codebase may or may not have `spring-boot-starter-security`. | If Security is on classpath, add a minimal permit rule; otherwise no config change. |
| 3 | **Base package for component scan** – controller will be placed under the existing base package (e.g., `com.example.taskmanager`). | Use existing package structure; no new package needed. |
| 4 | **Existing test suite** – assumes JUnit 5 + Spring Test + MockMvc are already on test classpath (typical for Spring Boot). | No new test dependencies. |
| 5 | **Build tool** – Maven (`mvn test`). | Verify with `mvn clean test` after changes. |
| 6 | **Port/context-path** – endpoint path is absolute `/api/ping` (no extra context-path prefix). | Map exactly `@GetMapping("/api/ping")`. |

## 2. Scope & Non-Goals
| Scope (In) | Non-Goals (Out) |
|------------|-----------------|
| New `PingController` class with single `GET /api/ping` | Any database schema, entity, repository, or service changes |
| Optional one-line Security permit rule (if Security exists) | New Maven/Gradle dependencies |
| `PingControllerTest` (`@WebMvcTest` + MockMvc) | Integration tests, contract tests, or end-to-end tests |
| `mvn test` clean pass verification | Performance/load testing, CI pipeline changes |

## 3. Testable Acceptance Criteria
| ID | Criterion | Verification |
|----|-----------|--------------|
| AC-1 | `GET /api/ping` returns **HTTP 200** | MockMvc `status().isOk()` |
| AC-2 | Response **Content-Type** = `application/json` | `content().contentType(MediaType.APPLICATION_JSON)` |
| AC-3 | JSON body **exactly** `{"status":"pong","service":"task-manager"}` | `jsonPath("$.status").value("pong")` & `jsonPath("$.service").value("task-manager")` |
| AC-4 | Endpoint accessible **without authentication** when Spring Security is present | Security config permits `/api/ping`; test runs without `@WithMockUser` |
| AC-5 | `mvn test` executes **zero failures** | CI/local build passes |

## 4. Proposed Implementation Steps
| Step | Action | Details |
|------|--------|---------|
| 1 | **Create `PingController`** | `src/main/java/.../controller/PingController.java`<br>`@RestController`<br>`@GetMapping("/api/ping")`<br>`public Map<String,String> ping() { return Map.of("status","pong","service","task-manager"); }` |
| 2 | **Conditional Security permit** (only if `spring-boot-starter-security` detected) | Locate `SecurityFilterChain` / `WebSecurityConfigurerAdapter` bean; add `.requestMatchers("/api/ping").permitAll()` |
| 3 | **Create `PingControllerTest`** | `src/test/java/.../controller/PingControllerTest.java`<br>`@WebMvcTest(PingController.class)`<br>`@Autowired MockMvc mockMvc;`<br>Single test method asserting AC-1…AC-3. |
| 4 | **Run full test suite** | `mvn clean test` – confirm zero regressions. |
| 5 | **Optional smoke test** | `curl -i http://localhost:8080/api/ping` after `mvn spring-boot:run`. |

## 5. Test Cases, Risks & Rollback
### Test Cases (automated in `PingControllerTest`)
| TC | Description | Expected |
|----|-------------|----------|
| TC-1 | Happy path GET `/api/ping` | 200, correct JSON |
| TC-2 | Wrong HTTP method (POST) | 405 Method Not Allowed (default Spring MVC) |
| TC-3 | Security disabled – unauthenticated access | 200 |
| TC-4 | Security enabled – unauthenticated access | 200 (permitAll) |

### Risks & Mitigations
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Spring Security not on classpath but permit rule added | Low | Compile error | Guard config with `@ConditionalOnClass(SecurityFilterChain.class)` or check classpath before editing. |
| Existing global `@RestControllerAdvice` alters response wrapper | Medium | JSON mismatch | Controller returns `Map`; ensure no advice wraps it. If it does, add `@ResponseBody` + `produces = APPLICATION_JSON_VALUE`. |
| Port/context-path mismatch in deployment | Low | 404 in smoke test | Document exact path `/api/ping`; no context-path prefix. |

### Rollback Approach
1. **Revert controller file** – delete `PingController.java`.
2. **Revert security config** – remove the single `.requestMatchers("/api/ping").permitAll()` line.
3. **Delete test class** – remove `PingControllerTest.java`.
4. Run `mvn clean test` to confirm baseline passes.
