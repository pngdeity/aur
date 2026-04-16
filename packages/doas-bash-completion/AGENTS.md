# Specialized Mandates: doas-bash-completion

## 1. Research & Documentation
- **Upstream Source**: When retrieving information about this package's build system, testing, or any topic relevant to the ABS files here, you MUST reference the official source repository: https://github.com/aarchetype/bash-completion

## 2. Standards
- **Namespace**: All functions and variables MUST use the `_comp_` namespace (e.g., `_comp_cmd_doas`) as per bash-completion 2.16+ standards.
- **Dynamic Help**: Use `_comp_compgen_help` to parse options at runtime.
- **Automation**: The `update.sh` script is an idempotent hook called by the master sync script; do not move metadata logic here.
