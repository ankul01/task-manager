package com.taskmanager.dto;

import com.taskmanager.domain.TaskPriority;
import com.taskmanager.domain.TaskStatus;
import jakarta.validation.constraints.NotBlank;

public record CreateTaskRequest(
    @NotBlank String title,
    String description,
    TaskStatus status,
    TaskPriority priority) {}