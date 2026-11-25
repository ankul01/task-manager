package com.taskmanager.controller;

import com.taskmanager.dto.VersionResponse;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api")
public class VersionController {

  private static final String SERVICE = "task-manager";
  private static final String VERSION = "0.1.0";

  @GetMapping("/version")
  public VersionResponse version() {
    return new VersionResponse(
        SERVICE, VERSION, System.getProperty("java.version"), "up");
  }
}