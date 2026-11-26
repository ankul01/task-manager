package com.taskmanager.dto;

public record VersionResponse(
    String service, String version, String javaVersion, String status) {}