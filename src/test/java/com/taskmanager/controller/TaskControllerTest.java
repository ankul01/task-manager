package com.taskmanager.controller;

import static org.hamcrest.Matchers.hasSize;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.delete;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.put;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.taskmanager.domain.TaskPriority;
import com.taskmanager.domain.TaskStatus;
import com.taskmanager.dto.PagedResponse;
import com.taskmanager.dto.TaskResponse;
import com.taskmanager.exception.TaskNotFoundException;
import com.taskmanager.service.TaskService;
import java.time.Instant;
import java.util.List;
import org.junit.jupiter.api.Test;
import com.taskmanager.exception.GlobalExceptionHandler;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest(TaskController.class)
@Import(GlobalExceptionHandler.class)
class TaskControllerTest {

  @Autowired private MockMvc mockMvc;

  @MockBean private TaskService taskService;

  @Test
  void createReturns201() throws Exception {
    Instant now = Instant.parse("2026-01-01T12:00:00Z");
    when(taskService.create(any()))
        .thenReturn(
            new TaskResponse(1L, "T", "D", TaskStatus.TODO, TaskPriority.MEDIUM, now));

    mockMvc
        .perform(
            post("/api/tasks")
                .contentType(MediaType.APPLICATION_JSON)
                .content("{\"title\":\"T\",\"description\":\"D\"}"))
        .andExpect(status().isCreated())
        .andExpect(header().exists("Location"))
        .andExpect(jsonPath("$.id").value(1));
  }

  @Test
  void createBlankTitleReturns400() throws Exception {
    mockMvc
        .perform(
            post("/api/tasks").contentType(MediaType.APPLICATION_JSON).content("{\"title\":\"\"}"))
        .andExpect(status().isBadRequest())
        .andExpect(jsonPath("$.errors.title").exists());
  }

  @Test
  void listDefaultsToPage0Size10() throws Exception {
    when(taskService.list(0, 10))
        .thenReturn(new PagedResponse<>(List.of(), 0, 10, 0, 0, true, true));

    mockMvc
        .perform(get("/api/tasks"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.size").value(10))
        .andExpect(jsonPath("$.page").value(0));
    verify(taskService).list(0, 10);
  }

  @Test
  void listInvalidSizeReturns400() throws Exception {
    mockMvc.perform(get("/api/tasks?size=101")).andExpect(status().isBadRequest());
  }

  @Test
  void getByIdNotFound() throws Exception {
    when(taskService.getById(9L)).thenThrow(new TaskNotFoundException(9L));
    mockMvc.perform(get("/api/tasks/9")).andExpect(status().isNotFound());
  }

  @Test
  void deleteReturns204() throws Exception {
    mockMvc.perform(delete("/api/tasks/1")).andExpect(status().isNoContent());
    verify(taskService).delete(1L);
  }

  @Test
  void deleteNotFound() throws Exception {
    doThrow(new TaskNotFoundException(2L)).when(taskService).delete(2L);
    mockMvc.perform(delete("/api/tasks/2")).andExpect(status().isNotFound());
  }

  @Test
  void putUpdatesTask() throws Exception {
    Instant now = Instant.parse("2026-01-01T12:00:00Z");
    when(taskService.update(eq(3L), any()))
        .thenReturn(
            new TaskResponse(
                3L, "Updated", "D", TaskStatus.IN_PROGRESS, TaskPriority.HIGH, now));

    mockMvc
        .perform(
            put("/api/tasks/3")
                .contentType(MediaType.APPLICATION_JSON)
                .content(
                    "{\"title\":\"Updated\",\"description\":\"D\","
                        + "\"status\":\"IN_PROGRESS\",\"priority\":\"HIGH\"}"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.title").value("Updated"));
  }
}