# 22 Deployment Pipeline & Environments

## Objective
Create CI/CD pipelines for dev, staging, and production with versioned migrations.

## Prerequisites
- Codebase matured

## Deliverables
- GitHub Actions workflow
- Environment configs (.env.staging, .env.prod templates)
- Automated migrations step
- Canary deployment script (optional)

## Suggested Steps
1. Define build + test job.
2. Add staging deploy job triggered on main merges.
3. Integrate migration execution pre-app start.
4. Draft rollback procedure documentation.

## Prompts You Can Use
- "Create GitHub Actions workflow for build, test, deploy to staging." 
- "Add migration execution step to CI pipeline." 
- "Document rollback process for failed production deploy." 

## Acceptance Criteria
- Pipeline runs automatically on push/merge.
- Deployments reproducible with versioned artifacts.

## Next Task
Proceed to 23 Future Enhancements & Roadmap.