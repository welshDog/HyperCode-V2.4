import { Controller, Get } from "@nestjs/common";

@Controller()
export class AppController {
  @Get("health")
  health() {
    return { status: "ok", agent: "architect", port: process.env.PORT ?? 8080 };
  }

  @Get("info")
  info() {
    return {
      name: "architect-agent",
      version: "0.0.1",
      role: "Planning and goal decomposition agent",
    };
  }
}
