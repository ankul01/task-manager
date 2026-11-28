package com.taskmanager.openapi;

import static org.hamcrest.Matchers.containsString;
import static org.hamcrest.Matchers.not;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import org.springframework.test.web.servlet.request.RequestPostProcessor;

@SpringBootTest
@AutoConfigureMockMvc
class OpenApiDocumentationTest {

  @Autowired private MockMvc mockMvc;

  @Test
  void openApiJsonIsAvailableWithExpectedMetadata() throws Exception {
    mockMvc
        .perform(get("/openapi.json"))
        .andExpect(status().isOk())
        .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_JSON))
        .andExpect(jsonPath("$.openapi").value(containsString("3.")))
        .andExpect(jsonPath("$.info.title").value("Task Manager API"))
        .andExpect(jsonPath("$.components.securitySchemes.bearerAuth.type").value("http"))
        .andExpect(jsonPath("$.components.securitySchemes.bearerAuth.scheme").value("bearer"))
        .andExpect(jsonPath("$.paths['/api/tasks']").exists())
        .andExpect(jsonPath("$.paths['/api/version']").exists())
        .andExpect(jsonPath("$.tags[?(@.name=='Tasks')]").exists())
        .andExpect(jsonPath("$.tags[?(@.name=='Metadata')]").exists());
  }

  @Test
  void openApiJsonExcludesPingAndActuator() throws Exception {
    MvcResult result = mockMvc.perform(get("/openapi.json")).andExpect(status().isOk()).andReturn();
    String body = result.getResponse().getContentAsString();
    org.hamcrest.MatcherAssert.assertThat(body, not(containsString("\"/api/ping\"")));
    org.hamcrest.MatcherAssert.assertThat(body, not(containsString("\"/actuator/")));
  }

  @Test
  void swaggerUiDocsEndpointIsReachable() throws Exception {
    mockMvc
        .perform(get("/docs"))
        .andExpect(status().is3xxRedirection());
    mockMvc
        .perform(get("/swagger-ui/index.html"))
        .andExpect(status().isOk())
        .andExpect(content().contentTypeCompatibleWith(MediaType.TEXT_HTML));
  }

  @Test
  void forwardedHeadersProduceHttpsServerUrl() throws Exception {
    mockMvc
        .perform(
            get("/openapi.json")
                .with(forwardedHeaders("https", "example.onrender.com")))
        .andExpect(status().isOk())
        .andExpect(jsonPath("$.servers[0].url").value(containsString("https://example.onrender.com")));
  }

  private static RequestPostProcessor forwardedHeaders(String proto, String host) {
    return request -> {
      request.addHeader("X-Forwarded-Proto", proto);
      request.addHeader("X-Forwarded-Host", host);
      return request;
    };
  }
}