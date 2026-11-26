package com.taskmanager.controller;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

@WebMvcTest(VersionController.class)
class VersionControllerTest {

  @Autowired private MockMvc mockMvc;

  @Test
  void apiVersionReturnsOkWithExpectedJsonFields() throws Exception {
    mockMvc
        .perform(get("/api/version"))
        .andExpect(status().isOk())
        .andExpect(content().contentType(MediaType.APPLICATION_JSON))
        .andExpect(jsonPath("$.service").value("task-manager"))
        .andExpect(jsonPath("$.version").value("0.1.0"))
        .andExpect(jsonPath("$.javaVersion").exists())
        .andExpect(jsonPath("$.status").value("up"));
  }
}