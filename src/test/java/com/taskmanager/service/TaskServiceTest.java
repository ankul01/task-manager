package com.taskmanager.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.taskmanager.domain.Task;
import com.taskmanager.domain.TaskPriority;
import com.taskmanager.domain.TaskStatus;
import com.taskmanager.dto.CreateTaskRequest;
import com.taskmanager.dto.UpdateTaskRequest;
import com.taskmanager.exception.TaskNotFoundException;
import com.taskmanager.repository.TaskRepository;
import java.time.Instant;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.test.util.ReflectionTestUtils;

@ExtendWith(MockitoExtension.class)
class TaskServiceTest {

  @Mock private TaskRepository taskRepository;

  private TaskService taskService;

  @BeforeEach
  void setUp() {
    taskService = new TaskService(taskRepository);
  }

  @Test
  void createAppliesDefaults() {
    when(taskRepository.save(any(Task.class)))
        .thenAnswer(
            inv -> {
              Task saved = inv.getArgument(0);
              ReflectionTestUtils.setField(saved, "id", 1L);
              if (saved.getCreatedAt() == null) {
                ReflectionTestUtils.setField(saved, "createdAt", Instant.parse("2026-01-01T00:00:00Z"));
              }
              return saved;
            });

    var response =
        taskService.create(new CreateTaskRequest("Title", "Desc", null, null));

    assertThat(response.title()).isEqualTo("Title");
    assertThat(response.status()).isEqualTo(TaskStatus.TODO);
    assertThat(response.priority()).isEqualTo(TaskPriority.MEDIUM);
  }

  @Test
  void updatePreservesIdAndCreatedAt() {
    Task existing = sampleTask(5L);
    Instant created = existing.getCreatedAt();
    when(taskRepository.findById(5L)).thenReturn(Optional.of(existing));
    when(taskRepository.save(any(Task.class))).thenAnswer(inv -> inv.getArgument(0));

    var response =
        taskService.update(
            5L,
            new UpdateTaskRequest(
                "New title", "New desc", TaskStatus.DONE, TaskPriority.HIGH));

    assertThat(response.id()).isEqualTo(5L);
    assertThat(response.createdAt()).isEqualTo(created);
    assertThat(response.title()).isEqualTo("New title");
  }

  @Test
  void getByIdThrowsWhenMissing() {
    when(taskRepository.findById(99L)).thenReturn(Optional.empty());
    assertThatThrownBy(() -> taskService.getById(99L))
        .isInstanceOf(TaskNotFoundException.class);
  }

  @Test
  void listUsesPageRequest() {
    when(taskRepository.findAll(any(Pageable.class)))
        .thenReturn(new PageImpl<>(java.util.List.of(sampleTask(1L))));
    taskService.list(1, 5);
    ArgumentCaptor<Pageable> captor = ArgumentCaptor.forClass(Pageable.class);
    verify(taskRepository).findAll(captor.capture());
    assertThat(captor.getValue()).isEqualTo(PageRequest.of(1, 5));
  }

  private static Task sampleTask(Long id) {
    Task task = new Task();
    task.setTitle("Sample");
    task.setDescription("D");
    task.setStatus(TaskStatus.TODO);
    task.setPriority(TaskPriority.MEDIUM);
    ReflectionTestUtils.setField(task, "id", id);
    ReflectionTestUtils.setField(task, "createdAt", Instant.parse("2020-01-01T00:00:00Z"));
    return task;
  }
}