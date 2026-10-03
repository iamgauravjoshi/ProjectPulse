import { z } from "zod";

export const projectSchema = z.object({
  id: z.uuid(),
  name: z.string().min(1),
  description: z.string(),
});

export const projectListSchema = z.array(projectSchema);
export type ProjectSummary = z.infer<typeof projectSchema>;

const canonicalSchema = z.object({
  id: z.uuid(),
  projectId: z.uuid(),
  title: z.string(),
  description: z.string(),
  sourceKind: z.enum(["MANUAL", "SEED"]),
  sourceLabel: z.string(),
  version: z.number().int().positive(),
  updatedAt: z.iso.datetime({ offset: true }),
});
const nullableId = z.uuid().nullable();
export const workspaceSchema = z
  .object({
    project: projectSchema,
    members: z.array(
      z.object({ id: z.uuid(), name: z.string(), role: z.string() }),
    ),
    requirements: z.array(
      canonicalSchema.extend({
        status: z.enum(["DRAFT", "ACTIVE", "COMPLETED", "ARCHIVED"]),
        phase: z.number().int().positive(),
      }),
    ),
    decisions: z.array(
      canonicalSchema.extend({
        decisionStatus: z.enum([
          "DISCUSSION",
          "PROPOSAL",
          "PROVISIONAL",
          "REVIEW_REQUIRED",
          "CONFIRMED",
          "SUPERSEDED",
          "REJECTED",
        ]),
        impactArea: z.string(),
        madeBy: nullableId,
        confirmedAt: z.iso.datetime({ offset: true }).nullable(),
      }),
    ),
    commitments: z.array(
      canonicalSchema.extend({
        status: z.enum(["OPEN", "IN_PROGRESS", "DONE", "CANCELLED"]),
        ownerId: nullableId,
        saidBy: nullableId,
        dueDate: z.iso.date().nullable(),
        dependencyId: nullableId,
      }),
    ),
    risks: z.array(
      canonicalSchema.extend({
        status: z.enum(["OPEN", "MITIGATED", "CLOSED"]),
        severity: z.enum(["LOW", "MEDIUM", "HIGH", "CRITICAL"]),
      }),
    ),
    milestones: z.array(
      canonicalSchema.extend({
        status: z.enum(["PLANNED", "AT_RISK", "COMPLETED", "CANCELLED"]),
        date: z.iso.date(),
      }),
    ),
    dependencies: z.array(
      canonicalSchema.extend({
        status: z.enum(["PENDING", "READY", "BLOCKED"]),
        ownerId: nullableId,
        blockedMilestoneId: nullableId,
      }),
    ),
    questions: z.array(
      canonicalSchema.extend({
        status: z.enum(["OPEN", "RESOLVED", "CLOSED"]),
        ownerId: nullableId,
      }),
    ),
    activity: z.array(
      z.object({
        id: z.uuid(),
        action: z.string(),
        entityType: z.string(),
        createdAt: z.iso.datetime({ offset: true }),
      }),
    ),
    generatedAt: z.iso.datetime({ offset: true }),
  })
  .superRefine((data, context) => {
    const groups = [
      data.requirements,
      data.decisions,
      data.commitments,
      data.risks,
      data.milestones,
      data.dependencies,
      data.questions,
    ];
    if (
      groups.some((group) =>
        group.some((record) => record.projectId !== data.project.id),
      )
    ) {
      context.addIssue({
        code: "custom",
        message: "Workspace contains records from another project.",
      });
    }
  });

export type Workspace = z.infer<typeof workspaceSchema>;
