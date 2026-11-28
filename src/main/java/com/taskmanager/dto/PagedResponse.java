package com.taskmanager.dto;

import io.swagger.v3.oas.annotations.media.Schema;
import java.util.List;

@Schema(description = "Page of items with pagination metadata")
public record PagedResponse<T>(
    @Schema(description = "Items in this page") List<T> content,
    @Schema(description = "Zero-based page index", example = "0") int page,
    @Schema(description = "Requested page size", example = "10") int size,
    @Schema(description = "Total items across all pages", example = "25") long totalElements,
    @Schema(description = "Total number of pages", example = "3") int totalPages,
    @Schema(description = "Whether this is the first page") boolean first,
    @Schema(description = "Whether this is the last page") boolean last) {}