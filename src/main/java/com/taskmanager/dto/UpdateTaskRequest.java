package com.taskmanager.dto;

import com.taskmanager.domain.TaskPriority;
import com.taskmanager.domain.TaskStatus;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

@Schema(description = "Payload to update an existing task")
public record UpdateTaskRequest(
    @Schema(description = "Updated task title", example = "Ship Swagger UI", requiredMode = Schema.RequiredMode.REQUIRED)
        @NotBlank
        String title,
    @Schema(description = "Updated description", example = "Enable /docs and /openapi.json")
        String description,
    @Schema(description = "Workflow status", example = "IN_PROGRESS") TaskStatus status,
    @Schema(description = "Priority level", example = "HIGH") TaskPriority priority) {}