package com.taskmanager.controller;

import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import java.sql.Connection;
import java.sql.SQLException;
import javax.sql.DataSource;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.boot.test.mock.mockito.MockBean;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest(HealthController.class)
class HealthControllerTest {

  @Autowired private MockMvc mockMvc;

  @MockBean private DataSource dataSource;

  @Test
  void apiHealthEndpointReturnsUpWhenDatabaseIsHealthy() throws Exception {
    Connection connection = mock(Connection.class);
    when(connection.isValid(anyInt())).thenReturn(true);
    when(dataSource.getConnection()).thenReturn(connection);

    mockMvc
        .perform(get("/api/health"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.status").value("UP"))
        .andExpect(jsonPath("$.timestamp").exists());
  }

  @Test
  void healthEndpointAliasReturnsUpWhenDatabaseIsHealthy() throws Exception {
    Connection connection = mock(Connection.class);
    when(connection.isValid(anyInt())).thenReturn(true);
    when(dataSource.getConnection()).thenReturn(connection);

    mockMvc
        .perform(get("/health"))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.status").value("UP"))
        .andExpect(jsonPath("$.timestamp").exists());
  }

  @Test
  void healthReturnsServiceUnavailableWhenDatabaseConnectionFails() throws Exception {
    when(dataSource.getConnection()).thenThrow(new SQLException("DB connection failure"));

    mockMvc
        .perform(get("/api/health"))
        .andExpect(status().isServiceUnavailable())
        .andExpect(jsonPath("$.status").value("DOWN"))
        .andExpect(jsonPath("$.timestamp").exists());
  }

  @Test
  void healthReturnsServiceUnavailableWhenConnectionIsNotValid() throws Exception {
    Connection connection = mock(Connection.class);
    when(connection.isValid(anyInt())).thenReturn(false);
    when(dataSource.getConnection()).thenReturn(connection);

    mockMvc
        .perform(get("/api/health"))
        .andExpect(status().isServiceUnavailable())
        .andExpect(jsonPath("$.status").value("DOWN"))
        .andExpect(jsonPath("$.timestamp").exists());
  }
}
