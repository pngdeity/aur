# Specialized Mandates: gemini-bash-completion

## 1. Research & Documentation
- **Upstream Source**: When retrieving information about this package's build system, testing, or any topic relevant to the ABS files here, you MUST reference the official source repository: https://github.com/google-gemini/gemini-cli

## 2. Standards
- **Namespace**: All functions and variables MUST use the `_comp_` namespace (e.g., `_comp_cmd_gemini`) as per bash-completion 2.16+ standards.
- **Dynamic Help**: Use `_comp_compgen_help` for global options.
- **Automation**: The `update.sh` script uses `npx` to dynamically extract subcommands from the latest binary; ensure this logic remains isolated from generic metadata tasks.
