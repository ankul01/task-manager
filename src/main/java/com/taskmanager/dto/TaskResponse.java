package com.taskmanager.dto;

import com.taskmanager.domain.Task;
import com.taskmanager.domain.TaskPriority;
import com.taskmanager.domain.TaskStatus;
import io.swagger.v3.oas.annotations.media.Schema;
import java.time.Instant;

@Schema(description = "Task representation returned by the API")
public record TaskResponse(
    @Schema(description = "Unique task id", example = "42") Long id,
    @Schema(description = "Task title", example = "Review pull request") String title,
    @Schema(description = "Task description", example = "Verify OpenAPI schema examples") String description,
    @Schema(description = "Current status", example = "TODO") TaskStatus status,
    @Schema(description = "Priority", example = "MEDIUM") TaskPriority priority,
    @Schema(description = "Creation timestamp (UTC)", example = "2026-11-28T08:00:00Z") Instant createdAt) {

  public static TaskResponse from(Task task) {
    return new TaskResponse(
        task.getId(),
        task.getTitle(),
        task.getDescription(),
        task.getStatus(),
        task.getPriority(),
        task.getCreatedAt());
  }
}