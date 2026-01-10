#!/usr/bin/env node

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { Logger } from './utils/logger.js';
import { ErrorHandler } from './utils/errors.js';
import { config } from './config.js';
import { initDatabase, closeDatabase } from './db/database.js';
import { registerTools } from './tools/index.js';
import Database from 'better-sqlite3';

class BigContextMCPServer {
  private server: Server;
  private logger: Logger;
  private errorHandler: ErrorHandler;
  private db: Database.Database | null = null;

  constructor() {
    this.logger = new Logger(config.logging.level);
    this.errorHandler = new ErrorHandler(this.logger);

    this.server = new Server(
      {
        name: config.server.name,
        version: config.server.version,
      },
      {
        capabilities: {
          tools: {},
        },
      }
    );

    this.setupErrorHandlers();
  }

  private setupErrorHandlers(): void {
    this.server.onerror = (error) => {
      this.logger.error('Server error', { error: String(error) });
    };

    process.on('uncaughtException', (error) => {
      this.logger.error('Uncaught exception', { error: error.message, stack: error.stack });
      process.exit(1);
    });

    process.on('unhandledRejection', (reason) => {
      this.logger.error('Unhandled rejection', { reason: String(reason) });
      process.exit(1);
    });

    process.on('SIGINT', async () => {
      this.logger.info('Received SIGINT, shutting down gracefully');
      await this.shutdown();
    });

    process.on('SIGTERM', async () => {
      this.logger.info('Received SIGTERM, shutting down gracefully');
      await this.shutdown();
    });
  }

  async initialize(): Promise<void> {
    this.logger.info('Initializing BigContext MCP Server');

    // Initialize database
    this.db = initDatabase(config.db.path);
    this.logger.info('Database initialized', { path: config.db.path });

    // Register tools
    await registerTools(this.server, {
      db: this.db,
      errorHandler: this.errorHandler,
      logger: this.logger,
    });

    this.logger.info('Tools registered successfully');
  }

  async start(): Promise<void> {
    const transport = new StdioServerTransport();
    await this.server.connect(transport);

    this.logger.info('BigContext MCP Server started successfully');
  }

  async shutdown(): Promise<void> {
    this.logger.info('Shutting down server');
    closeDatabase();
    await this.server.close();
    process.exit(0);
  }
}

// Start server
const server = new BigContextMCPServer();
await server.initialize();
await server.start();
