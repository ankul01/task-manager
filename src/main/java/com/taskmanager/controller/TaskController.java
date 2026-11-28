package com.taskmanager.controller;

import com.taskmanager.dto.CreateTaskRequest;
import com.taskmanager.dto.PagedResponse;
import com.taskmanager.dto.TaskResponse;
import com.taskmanager.dto.UpdateTaskRequest;
import com.taskmanager.service.TaskService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.responses.ApiResponses;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import jakarta.validation.constraints.Max;
import jakarta.validation.constraints.Min;
import java.net.URI;
import org.springframework.http.MediaType;
import org.springframework.http.ProblemDetail;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.servlet.support.ServletUriComponentsBuilder;

@Tag(name = "Tasks", description = "Create, list, update, and delete tasks")
@RestController
@RequestMapping("/api/tasks")
@Validated
public class TaskController {

  private final TaskService taskService;

  public TaskController(TaskService taskService) {
    this.taskService = taskService;
  }

  @Operation(summary = "Create a task", description = "Creates a new task and returns its representation.")
  @ApiResponses({
    @ApiResponse(
        responseCode = "201",
        description = "Task created",
        content = @Content(schema = @Schema(implementation = TaskResponse.class))),
    @ApiResponse(
        responseCode = "400",
        description = "Validation error",
        content = @Content(schema = @Schema(implementation = ProblemDetail.class))),
    @ApiResponse(
        responseCode = "500",
        description = "Unexpected error",
        content = @Content(schema = @Schema(implementation = ProblemDetail.class)))
  })
  @PostMapping
  public ResponseEntity<TaskResponse> create(@Valid @RequestBody CreateTaskRequest request) {
    TaskResponse created = taskService.create(request);
    URI location =
        ServletUriComponentsBuilder.fromCurrentRequest()
            .path("/{id}")
            .buildAndExpand(created.id())
            .toUri();
    return ResponseEntity.created(location).body(created);
  }

  @Operation(summary = "List tasks", description = "Returns a page of tasks.")
  @ApiResponses({
    @ApiResponse(
        responseCode = "200",
        description = "Paged task list",
        content =
            @Content(
                mediaType = MediaType.APPLICATION_JSON_VALUE,
                schema = @Schema(implementation = PagedResponse.class))),
    @ApiResponse(
        responseCode = "400",
        description = "Invalid pagination parameters",
        content = @Content(schema = @Schema(implementation = ProblemDetail.class)))
  })
  @GetMapping
  public PagedResponse<TaskResponse> list(
      @Parameter(description = "Zero-based page index", example = "0")
          @RequestParam(defaultValue = "0")
          @Min(0)
          int page,
      @Parameter(description = "Page size (1–100)", example = "10")
          @RequestParam(defaultValue = "10")
          @Min(1)
          @Max(100)
          int size) {
    return taskService.list(page, size);
  }

  @Operation(summary = "Get task by id")
  @ApiResponses({
    @ApiResponse(
        responseCode = "200",
        description = "Task found",
        content = @Content(schema = @Schema(implementation = TaskResponse.class))),
    @ApiResponse(
        responseCode = "404",
        description = "Task not found",
        content = @Content(schema = @Schema(implementation = ProblemDetail.class)))
  })
  @GetMapping("/{id}")
  public TaskResponse getById(
      @Parameter(description = "Task identifier", example = "1") @PathVariable Long id) {
    return taskService.getById(id);
  }

  @Operation(summary = "Update a task")
  @ApiResponses({
    @ApiResponse(
        responseCode = "200",
        description = "Task updated",
        content = @Content(schema = @Schema(implementation = TaskResponse.class))),
    @ApiResponse(
        responseCode = "400",
        description = "Validation error",
        content = @Content(schema = @Schema(implementation = ProblemDetail.class))),
    @ApiResponse(
        responseCode = "404",
        description = "Task not found",
        content = @Content(schema = @Schema(implementation = ProblemDetail.class)))
  })
  @PutMapping("/{id}")
  public TaskResponse update(
      @Parameter(description = "Task identifier", example = "1") @PathVariable Long id,
      @Valid @RequestBody UpdateTaskRequest request) {
    return taskService.update(id, request);
  }

  @Operation(summary = "Delete a task")
  @ApiResponses({
    @ApiResponse(responseCode = "204", description = "Task deleted"),
    @ApiResponse(
        responseCode = "404",
        description = "Task not found",
        content = @Content(schema = @Schema(implementation = ProblemDetail.class)))
  })
  @DeleteMapping("/{id}")
  public ResponseEntity<Void> delete(
      @Parameter(description = "Task identifier", example = "1") @PathVariable Long id) {
    taskService.delete(id);
    return ResponseEntity.noContent().build();
  }
}