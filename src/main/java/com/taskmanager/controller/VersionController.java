package com.taskmanager.controller;

import com.taskmanager.dto.VersionResponse;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@Tag(name = "Metadata", description = "Service version and runtime information")
@RestController
@RequestMapping("/api")
public class VersionController {

  private static final String SERVICE = "task-manager";
  private static final String VERSION = "0.1.0";

  @Operation(summary = "Get API version", description = "Returns service name, version, and JVM details.")
  @ApiResponse(
      responseCode = "200",
      description = "Version payload",
      content = @Content(schema = @Schema(implementation = VersionResponse.class)))
  @GetMapping("/version")
  public VersionResponse version() {
    return new VersionResponse(
        SERVICE, VERSION, System.getProperty("java.version"), "up");
  }
}