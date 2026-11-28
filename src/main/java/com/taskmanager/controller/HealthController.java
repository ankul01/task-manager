package com.taskmanager.controller;

import com.taskmanager.dto.HealthResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import java.sql.Connection;
import java.time.Instant;
import javax.sql.DataSource;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@Tag(name = "Health", description = "Application health checks")
@RestController
public class HealthController {

  private final DataSource dataSource;

  public HealthController(DataSource dataSource) {
    this.dataSource = dataSource;
  }

  @Operation(
      summary = "Check application health",
      description = "Verifies database connectivity and returns UP or DOWN.")
  @ApiResponse(
      responseCode = "200",
      description = "Health status",
      content = @Content(schema = @Schema(implementation = HealthResponse.class)))
  @GetMapping({"/api/health", "/health"})
  public ResponseEntity<HealthResponse> checkHealth() {
    try (Connection connection = dataSource.getConnection()) {
      if (connection.isValid(2)) {
        return ResponseEntity.ok(new HealthResponse("UP", Instant.now()));
      }
      return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
          .body(new HealthResponse("DOWN", Instant.now()));
    } catch (Exception e) {
      return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
          .body(new HealthResponse("DOWN", Instant.now()));
    }
  }
}