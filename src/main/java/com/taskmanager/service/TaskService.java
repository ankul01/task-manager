package com.taskmanager.service;

import com.taskmanager.domain.Task;
import com.taskmanager.domain.TaskPriority;
import com.taskmanager.domain.TaskStatus;
import com.taskmanager.dto.CreateTaskRequest;
import com.taskmanager.dto.PagedResponse;
import com.taskmanager.dto.TaskResponse;
import com.taskmanager.dto.UpdateTaskRequest;
import com.taskmanager.exception.TaskNotFoundException;
import com.taskmanager.repository.TaskRepository;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class TaskService {

  private final TaskRepository taskRepository;

  public TaskService(TaskRepository taskRepository) {
    this.taskRepository = taskRepository;
  }

  @Transactional
  public TaskResponse create(CreateTaskRequest request) {
    Task task = new Task();
    task.setTitle(request.title());
    task.setDescription(request.description());
    task.setStatus(request.status() != null ? request.status() : TaskStatus.TODO);
    task.setPriority(request.priority() != null ? request.priority() : TaskPriority.MEDIUM);
    return TaskResponse.from(taskRepository.save(task));
  }

  @Transactional(readOnly = true)
  public PagedResponse<TaskResponse> list(int page, int size) {
    Page<Task> result = taskRepository.findAll(PageRequest.of(page, size));
    return new PagedResponse<>(
        result.getContent().stream().map(TaskResponse::from).toList(),
        result.getNumber(),
        result.getSize(),
        result.getTotalElements(),
        result.getTotalPages(),
        result.isFirst(),
        result.isLast());
  }

  @Transactional(readOnly = true)
  public TaskResponse getById(Long id) {
    return TaskResponse.from(
        taskRepository.findById(id).orElseThrow(() -> new TaskNotFoundException(id)));
  }

  @Transactional
  public TaskResponse update(Long id, UpdateTaskRequest request) {
    Task task =
        taskRepository.findById(id).orElseThrow(() -> new TaskNotFoundException(id));
    TaskStatus status = request.status() != null ? request.status() : task.getStatus();
    TaskPriority priority = request.priority() != null ? request.priority() : task.getPriority();
    task.applyMutableFields(request.title(), request.description(), status, priority);
    return TaskResponse.from(taskRepository.save(task));
  }

  @Transactional
  public void delete(Long id) {
    if (!taskRepository.existsById(id)) {
      throw new TaskNotFoundException(id);
    }
    taskRepository.deleteById(id);
  }
}