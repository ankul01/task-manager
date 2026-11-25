package com.taskmanager.controller;

import com.taskmanager.dto.PingResponse;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class PingController {

  private final String serviceName;

  public PingController(@Value("${spring.application.name}") String serviceName) {
    this.serviceName = serviceName;
  }

  @GetMapping("/api/ping")
  public ResponseEntity<PingResponse> ping() {
    return ResponseEntity.ok(new PingResponse("ok", serviceName));
  }
}