# Client Instance Agent Protocol

## Purpose

The Synnergyze agent creates a client-specific scaffold, extracts the required modules, and pushes the result to the client's GitHub repository with explicit permission.

The agent is not a random code generator. It is a controlled builder.

## Client instance flow

1. Client gives business narration.
2. Synnergyze creates a workspace map.
3. Agent extracts the required template modules.
4. Agent creates database schema and API routes.
5. Client approves the build summary.
6. Client connects GitHub.
7. Client connects OpenAI backend key.
8. Agent commits scaffold into client's GitHub.
9. Deployment runs on client's VM or approved cloud.
10. RiverOS logs the build event.

## Required client assets

- Client name
- Workspace type
- Business type, if any
- GST profile, if any
- GitHub repository access
- OpenAI project/service account key
- Deployment target
- Domain, if any

## Key rule

The client's keys must stay under the client's control.

Synnergyze can orchestrate. It should not permanently own the client's secrets.

## Recommended GitHub access

Use one of these:

1. GitHub App installation scoped to selected repositories.
2. Fine-grained personal access token scoped to one repository.
3. SSH deploy key scoped to one repository.
4. GitHub Actions secret created by the repository owner.

Avoid broad personal tokens.

## Recommended OpenAI access

Use a project-specific or service-account key for each client instance.

Do not use one master key for all clients.

## RiverOS evidence events

Every agent action should produce an evidence event:

- CLIENT_INSTANCE_CREATED
- TEMPLATE_SELECTED
- REPOSITORY_CONNECTED
- SECRET_REGISTERED
- SCAFFOLD_GENERATED
- BUILD_SUMMARY_APPROVED
- GITHUB_PUSH_REQUESTED
- GITHUB_PUSH_COMPLETED
- DEPLOYMENT_STARTED
- DEPLOYMENT_COMPLETED
- HANDOVER_PACK_GENERATED
