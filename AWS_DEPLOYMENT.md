# AWS staging deployment

This is a staging deployment runbook, not production approval. The Qdrant
service uses ECS-managed EBS storage that is deleted when its service task
terminates. Treat indexed data as disposable and keep a re-ingestion source.

## What is already in the repository

- The GitHub Actions workflow runs tests on `main`, `ci-setup`, and version tags.
- Application images are deployed to ECS only on pushes to `main` or version
  tags. `ci-setup` runs CI but does not deploy.
- A version tag targets the protected `production` environment and is blocked
  unless its `PRODUCTION_READY` variable is explicitly set to `true`.
- The ECS API/UI deployment assumes both services already exist and preserves
  their current task-definition configuration.

## Staging prerequisites

Before provisioning anything, verify the AWS CLI credentials and target account.
The deployment scripts create or update AWS resources and can incur charges.

The staging account must already have:

- The ECS cluster and API/UI services used by the project.
- A Service Connect namespace configured as the cluster default.
- The subnet, security groups, IAM execution/EBS roles, and Secrets Manager
  secrets expected by `Deploy-StudyPilot-Qdrant.ps1`.
- ECS execution-role permission to read the Qdrant API key secret.
- GitHub Actions environment variables and an OIDC role configured for the CI
  workflow if automated image deployment is wanted.

The Qdrant deployment script contains staging-specific resource names and a
subnet. Review those values against the verified target account before running
it; do not use it as a production provisioning script.

## Staging sequence

1. Review the current AWS identity and confirm the intended region, cluster,
   subnet, IAM roles, and secret names.
2. Provision Qdrant from the repository root:

   ```powershell
   .\Deploy-StudyPilot-Qdrant.ps1
   ```

   This creates an ECS service and registers a task definition. The root script
   forwards to the implementation under `.github\workflows`.
3. Wait until the Qdrant ECS service is healthy, then configure API/UI
   Service Connect and the API's Qdrant settings:

   ```powershell
   .\Connect-StudyPilot-Services.ps1 `
     -Region eu-west-2 `
     -Cluster 'your-cluster-name' `
     -ApiService studypilot-api-staging `
     -UiService studypilot-ui-staging `
     -Namespace 'your-service-connect-namespace' `
     -WhatIf
   ```

   Inspect the preview. If it is correct, repeat the command without `-WhatIf`.
   The helper validates Qdrant health and namespace membership, then configures
   the API to use `http://studypilot-qdrant:6333`, collection
   `ai_study_notes`, and the Qdrant key from Secrets Manager.
4. Ingest the approved notes/PDFs into the staging Qdrant collection from a
   controlled task that can reach Qdrant inside the VPC. Provisioning Qdrant
   does not populate the collection.
5. Push the approved application revision to `main` to run the CI deployment,
   or follow the project's controlled release process. The workflow waits for
   API and UI services to stabilize, but a successful rollout is not a
   functional or production sign-off.
6. Smoke-test `/health` and an authenticated `/chat` request, inspect ECS task
   events and CloudWatch logs, and verify retrieval citations against indexed
   staging data.

Do not expose Qdrant or the demo API key publicly. The app still uses demo
single-key authentication and local SQLite-backed memory; this setup is not
suitable for a multi-user production service. Replace those components and
provide durable Qdrant storage/backups before production use.
