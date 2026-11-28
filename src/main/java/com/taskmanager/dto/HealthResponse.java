package com.taskmanager.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.time.Instant;

@Schema(description = "Health check result")
public record HealthResponse(
    @Schema(description = "Aggregate health", example = "UP") String status,
    @Schema(description = "Time of the check (UTC)", example = "2026-11-28T08:00:00Z") Instant timestamp) {}