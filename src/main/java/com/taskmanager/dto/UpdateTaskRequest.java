package com.taskmanager.dto;

import com.taskmanager.domain.TaskPriority;
import com.taskmanager.domain.TaskStatus;
import jakarta.validation.constraints.NotBlank;

public record UpdateTaskRequest(
    @NotBlank String title,
    String description,
    TaskStatus status,
    TaskPriority priority) {}