import { z } from 'zod';

export const IngestDocumentSchema = z.object({
  path: z.string().min(1, 'Path is required'),
  title: z.string().optional(),
  force: z.boolean().optional().default(false),
  chunkSize: z.number().positive().optional().default(2000),
  overlap: z.number().nonnegative().optional().default(100),
});

export const SearchSegmentSchema = z.object({
  query: z.string().min(1, 'Query is required'),
  documentId: z.number().positive().optional(),
  segmentId: z.number().positive().optional(),
  limit: z.number().positive().optional().default(5),
  includeContext: z.boolean().optional().default(true),
  contextWords: z.number().positive().optional().default(50),
});

export const GetMetadataSchema = z.object({
  documentId: z.number().positive().optional(),
  segmentId: z.number().positive().optional(),
  includeWordFrequencies: z.boolean().optional().default(false),
  topTerms: z.number().positive().optional().default(10),
  includeStructure: z.boolean().optional().default(true),
});

export const CompareSegmentsSchema = z.object({
  segmentIdA: z.number().positive(),
  segmentIdB: z.number().positive(),
  findBridges: z.boolean().optional().default(true),
  maxBridges: z.number().positive().optional().default(3),
});

export const ListDocumentsSchema = z.object({
  limit: z.number().positive().optional().default(20),
  offset: z.number().nonnegative().optional().default(0),
});

export const DeleteDocumentSchema = z.object({
  documentId: z.number().positive(),
});

export type IngestDocumentInput = z.infer<typeof IngestDocumentSchema>;
export type SearchSegmentInput = z.infer<typeof SearchSegmentSchema>;
export type GetMetadataInput = z.infer<typeof GetMetadataSchema>;
export type CompareSegmentsInput = z.infer<typeof CompareSegmentsSchema>;
export type ListDocumentsInput = z.infer<typeof ListDocumentsSchema>;
export type DeleteDocumentInput = z.infer<typeof DeleteDocumentSchema>;
