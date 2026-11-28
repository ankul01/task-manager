package com.taskmanager.dto;

import io.swagger.v3.oas.annotations.media.Schema;

@Schema(description = "Service version and runtime metadata")
public record VersionResponse(
    @Schema(description = "Service name", example = "task-manager") String service,
    @Schema(description = "Semantic API version", example = "0.1.0") String version,
    @Schema(description = "JVM version string", example = "21.0.2") String javaVersion,
    @Schema(description = "Operational status", example = "up") String status) {}