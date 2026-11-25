package com.taskmanager.controller;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.test.context.TestPropertySource;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest(PingController.class)
@TestPropertySource(properties = "spring.application.name=task-manager")
class PingControllerTest {

  @Autowired private MockMvc mockMvc;

  @Test
  void apiPingReturnsOkWithServiceNameFromConfiguration() throws Exception {
    mockMvc
        .perform(get("/api/ping"))
        .andExpect(status().isOk())
        .andExpect(content().contentType("application/json"))
        .andExpect(jsonPath("$.status").value("ok"))
        .andExpect(jsonPath("$.service").value("task-manager"));
  }
}