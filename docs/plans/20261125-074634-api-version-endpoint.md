---
plan_id: 20261125-074634-api-version-endpoint
status: draft
created_at: 2026-11-25T07:47:32Z
model: nvidia/nemotron-3-ultra-550b-a55b
route_name: nvidia-nemotron
workflow_run_url: https://github.com/ankul01/task-manager/actions/runs/45570758801
requirement: "Add a single read-only GET /api/version endpoint that returns HTTP 200 with JSON {\"service\": \"task-manager\", \"version\": \"0.1.0\", \"javaVersion\": \"<current JVM version>\"}, plus one @WebMvcTest MockMvc test verifying HTTP 200 and all three JSON fields. Keep the plan brief with zero open questions and do not modify existing entities, repositories, or database configuration."
revised_at: "2026-11-25T07:49:53Z"
---

# Draft Plan: 20261125-074634-api-version-endpoint

> **Human Review Required:** Merging this Pull Request to the default branch marks this exact file and commit SHA as approved for implementation.

**Plan: Add GET /api/version Endpoint**

---

### 1. Clarifying Questions & Assumptions
- **Assumption**: Spring Boot 3.x, Java 21, Spring Web MVC stack.
- **Assumption**: Version string "0.1.0" is static (from `build.properties` or hard-coded constant).
- **Assumption**: `javaVersion` sourced at runtime via `System.getProperty("java.version")`.
- **Assumption**: No authentication/authorization required for this endpoint.
- **Assumption**: Existing `@SpringBootApplication` component scan will pick up new controller.

---

### 2. Scope & Non-Goals
| In Scope | Out of Scope |
|----------|--------------|
| New `VersionController` with `GET /api/version` | Database changes, entities, repositories |
| `@WebMvcTest` for `VersionController` | Integration tests, actuator endpoints |
| JSON response with 4 fields (service, version, javaVersion, status) | Version auto-increment, Git metadata |
| HTTP 200 only | Error handling (no failure paths) |

---

### 3. Testable Acceptance Criteria
1. `GET /api/version` returns **200 OK**.
2. Response `Content-Type: application/json`.
3. Body matches exactly:
   ```json
   {
     "service": "task-manager",
     "version": "0.1.0",
     "javaVersion": "<runtime JVM version>",
     "status": "up"
   }
   ```
4. `@WebMvcTest` passes asserting status, content-type, and all four fields.

---

### 4. Implementation Steps
1. **Create DTO/Record** `VersionResponse(service: String, version: String, javaVersion: String, status: String)`.
2. **Create `VersionController`**:
   - `@RestController @RequestMapping("/api")`
   - `GET /version` → returns `VersionResponse("task-manager", "0.1.0", System.getProperty("java.version"), "up")`.
3. **Add `@WebMvcTest(VersionController.class)`** test:
   - `mockMvc.perform(get("/api/version"))`
   - `.andExpect(status().isOk())`
   - `.andExpect(content().contentType(MediaType.APPLICATION_JSON))`
   - `.andExpect(jsonPath("$.service").value("task-manager"))`
   - `.andExpect(jsonPath("$.version").value("0.1.0"))`
   - `.andExpect(jsonPath("$.javaVersion").exists())`
   - `.andExpect(jsonPath("$.status").value("up"))`
4. **Verify** `mvn test` passes.

---

### 5. Test Cases, Risks, Rollback
| Test Case | Expected |
|-----------|----------|
| Happy path GET /api/version | 200 + correct JSON |
| Invalid method (POST) | 405 (Spring default) |
| Invalid path | 404 |

**Risks**
- Low: trivial endpoint, no external deps.
- `javaVersion` format varies by JVM vendor (acceptable).

**Rollback**
- Revert the two new files (`VersionController.java`, `VersionControllerTest.java`).
- No DB migrations, config changes, or dependent code to unwind.
