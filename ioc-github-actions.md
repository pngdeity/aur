# DevOps Handoff Document: CI/CD Inversion of Control Pipeline

## 1. Project Overview
**Goal:** To redesign and future-proof the CI/CD pipeline for a personal website encompassing parallel Hugo and .NET (Blazor) builds, targeting a GitHub Pages deployment.
**Objective:** Migrate from a tightly coupled, vendor-specific (GitHub Actions) YAML configuration to a vendor-agnostic, Inversion of Control (IoC) architecture. 
**Scope:** The pipeline has been refactored to treat the CI/CD platform purely as a "dumb" orchestrator. All domain logic, dependency management, and compilation instructions have been extracted into standard shell scripts housed within the repository.

## 2. Key Stakeholders & Contacts
* **Primary Engineer / Project Owner:** [Your Name/Email] - *Responsible for architectural decisions, application code (Hugo/Blazor), and final approvals.*
* **Incoming DevOps Engineer:** [Incoming Engineer Name/Email] - *Responsible for pipeline maintenance, future Docker containerization, and monitoring deployment health.*

## 3. Current Status & Recent Activity
* **Refactoring Complete:** The monolithic `build-deploy.yaml` file has been stripped of inline bash commands (`curl`, `tar`, `sed`) and specific environment setup actions (`actions/setup-node`, `actions/setup-dotnet`).
* **IoC Implementation:** A "Bootstrapper" script pattern is currently deployed. The GitHub Actions runner blindly executes `./ci/build.sh` and uploads the resulting artifacts from a standardized `./ci/out/` directory.
* **Local Parity:** Because the execution logic now resides entirely in standard shell scripts, the entire pipeline can be run, tested, and debugged natively on a local Linux machine prior to pushing to the CI runner.

## 4. Key Deliverables
The following files have been drafted and establish the new architectural contract:
* `.github/workflows/build-deploy.yaml`: The simplified orchestrator file defining triggers and artifact routing.
* `ci/build.sh`: The main entrypoint script for the CI framework.
* `ci/setup-env.sh`: Bootstraps the runner environment (downloads Dart Sass and Hugo Extended into a local `./ci/bin` directory).
* `ci/execute-build.sh`: Handles `npm ci`, `hugo` compilation, `dotnet publish` for Blazor, HTML `sed` replacements, and standardizes the output payload into `./ci/out/`.

## 5. Critical Next Steps
1.  **Permission Verification:** Ensure all shell scripts have execution permissions applied (`chmod +x ci/*.sh`) before committing them to version control.
2.  **Local Pipeline Validation:** Execute `./ci/build.sh` natively from the project root to verify that the `ci/out/blog/` and `ci/out/app/` directories populate correctly with the expected static assets.
3.  **Deploy and Monitor:** Push the refactored workflow to the `main` branch and monitor the GitHub Actions console to ensure the Pages deployment succeeds without missing dependencies.

## 6. Pending Items & Risks
* **Future Docker Migration (Pending):** The current architecture utilizes a Bootstrapper script to natively install tools on the Ubuntu runner. This was chosen for simplicity regarding the current GitHub Pages target. As complexity scales, the `setup-env.sh` logic should be ported into a `Dockerfile.build` container to achieve absolute environmental isolation. The IoC contract guarantees this will require zero changes to the GitHub Actions YAML file.
* **Risk - Toolchain Drifts:** The Bootstrapper script currently assumes `nodejs` and `dotnet` are pre-installed globally (which is true for GitHub `ubuntu-latest` runners). If migrating to a bare-metal runner or a different vendor before the Docker migration, standard `apt-get` installation commands for Node and .NET must be added to `ci/setup-env.sh`.

## 7. Resources
* **Application Repository:** [Insert Link to GitHub Repository]
* **Production Environment:** GitHub Pages ([Insert live website URL])
* **Hugo Documentation:** [Hugo CLI Reference](https://gohugo.io/commands/hugo/)
* **Blazor Documentation:** [Host and Deploy ASP.NET Core Blazor WebAssembly](https://learn.microsoft.com/en-us/aspnet/core/blazor/host-and-deploy/webassembly)
