package com.taskmanager.dto;

import com.taskmanager.domain.TaskPriority;
import com.taskmanager.domain.TaskStatus;
import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.NotBlank;

@Schema(description = "Payload to create a new task")
public record CreateTaskRequest(
    @Schema(description = "Short task title", example = "Review pull request", requiredMode = Schema.RequiredMode.REQUIRED)
        @NotBlank
        String title,
    @Schema(description = "Optional longer description", example = "Check OpenAPI annotations and tests")
        String description,
    @Schema(description = "Initial workflow status", example = "TODO") TaskStatus status,
    @Schema(description = "Priority level", example = "MEDIUM") TaskPriority priority) {}