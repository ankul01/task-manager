package com.taskmanager.controller;

import com.taskmanager.dto.HealthResponse;
import java.sql.Connection;
import java.time.Instant;
import javax.sql.DataSource;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class HealthController {

  private final DataSource dataSource;

  public HealthController(DataSource dataSource) {
    this.dataSource = dataSource;
  }

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
