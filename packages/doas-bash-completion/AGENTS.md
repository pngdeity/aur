# Specialized Mandates: doas-bash-completion

## 1. Standards
- **Namespace**: All functions and variables MUST use the `_comp_` namespace (e.g., `_comp_cmd_doas`) as per bash-completion 2.16+ standards.
- **Dynamic Help**: Use `_comp_compgen_help` to parse options at runtime.
