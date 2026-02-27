import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    globals: true,
    environment: "node",
    coverage: {
      provider: "v8",
      reporter: ["text", "html"],
      include: ["src/**/*.ts"],
    },
    // Run unit → integration → e2e in order
    sequence: {
      setupFiles: "list",
    },
  },
  resolve: {
    alias: {
      "@": "/src",
    },
  },
});
