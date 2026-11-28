package com.taskmanager.config;

import io.swagger.v3.oas.models.Components;
import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import io.swagger.v3.oas.models.security.SecurityScheme;
import org.springdoc.core.customizers.ServerBaseUrlCustomizer;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpRequest;

@Configuration
public class OpenApiConfig {

  @Bean
  public OpenAPI taskManagerOpenApi() {
    return new OpenAPI()
        .info(
            new Info()
                .title("Task Manager API")
                .version("0.1.0")
                .description(
                    "Interactive REST API for managing tasks. Authenticate via Bearer JWT in"
                        + " Swagger UI when authorization is required."))
        .components(
            new Components()
                .addSecuritySchemes(
                    "bearerAuth",
                    new SecurityScheme()
                        .type(SecurityScheme.Type.HTTP)
                        .scheme("bearer")
                        .bearerFormat("JWT")
                        .description("HTTP Bearer JWT token")));
  }

  @Bean
  ServerBaseUrlCustomizer forwardedServerBaseUrlCustomizer() {
    return (serverBaseUrl, request) -> {
      String proto = header(request, "X-Forwarded-Proto");
      String host = header(request, "X-Forwarded-Host");
      if (proto == null || host == null) {
        return serverBaseUrl;
      }
      String hostName = host.split(",")[0].trim();
      String baseUrl = proto + "://" + hostName;
      return baseUrl.endsWith("/") ? baseUrl : baseUrl + "/";
    };
  }

  private static String header(HttpRequest request, String name) {
    if (request == null) {
      return null;
    }
    String value = request.getHeaders().getFirst(name);
    if (value == null || value.isBlank()) {
      return null;
    }
    return value.trim();
  }
}