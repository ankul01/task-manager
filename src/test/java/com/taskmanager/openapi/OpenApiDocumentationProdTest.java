package com.taskmanager.openapi;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.test.context.ActiveProfiles;
import org.springframework.test.web.servlet.MockMvc;

@SpringBootTest
@AutoConfigureMockMvc
@ActiveProfiles("prod")
class OpenApiDocumentationProdTest {

  @Autowired private MockMvc mockMvc;

  @Test
  void documentationEndpointsAreDisabledInProd() throws Exception {
    mockMvc.perform(get("/openapi.json")).andExpect(status().isNotFound());
    mockMvc.perform(get("/docs")).andExpect(status().isNotFound());
    mockMvc.perform(get("/swagger-ui/index.html")).andExpect(status().isNotFound());
    mockMvc.perform(get("/v3/api-docs")).andExpect(status().isNotFound());
  }

  @Test
  void pingStillWorksWhenDocsDisabled() throws Exception {
    mockMvc.perform(get("/api/ping")).andExpect(status().isOk());
  }
}