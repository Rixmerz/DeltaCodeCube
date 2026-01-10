import { McpError, ErrorCode } from '@modelcontextprotocol/sdk/types.js';
import { ZodError } from 'zod';
import { Logger } from './logger.js';

export class ErrorHandler {
  constructor(private logger: Logger) {}

  handleToolError(error: unknown, toolName: string): never {
    if (error instanceof McpError) {
      this.logger.error(`Tool error in ${toolName}`, {
        code: error.code,
        message: error.message
      });
      throw error;
    }

    if (error instanceof ZodError) {
      const message = error.errors
        .map(e => `${e.path.join('.')}: ${e.message}`)
        .join(', ');
      this.logger.error(`Validation error in ${toolName}`, { errors: error.errors });
      throw new McpError(ErrorCode.InvalidParams, `Invalid parameters: ${message}`);
    }

    if (error instanceof Error) {
      this.logger.error(`Unexpected error in ${toolName}`, {
        name: error.name,
        message: error.message,
        stack: error.stack
      });
      throw new McpError(ErrorCode.InternalError, `Internal error: ${error.message}`);
    }

    this.logger.error(`Unknown error in ${toolName}`, { error });
    throw new McpError(ErrorCode.InternalError, 'An unknown error occurred');
  }

  createInvalidParamsError(message: string): McpError {
    return new McpError(ErrorCode.InvalidParams, message);
  }

  createNotFoundError(resource: string, id: string | number): McpError {
    return new McpError(ErrorCode.InvalidParams, `${resource} not found: ${id}`);
  }

  createInternalError(message: string): McpError {
    return new McpError(ErrorCode.InternalError, message);
  }
}
