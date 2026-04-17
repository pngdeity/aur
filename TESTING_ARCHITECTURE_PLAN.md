# Architecture & Testing Strategy for Automation Scripts

**Status:** Proposed  
**Scope:** `@scripts/**` automation refactoring and test architecture  
**Author:** Gemini AI (Autonomous Engineering)

## 1. Executive Summary

The current state of the repository’s automation layer (`scripts/*.sh`) relies heavily on Bash. While Bash is performant and universally available on Arch Linux, it lacks robust constructs for Dependency Injection (DI), explicit interface contracts, and unit testing—making the system fragile as complexity scales.

This document proposes an "Enterprise-Grade" re-architecture of the package management automation. The goal is to transition the core logic from procedural Bash scripts into a Domain-Driven Design (DDD) model characterized by **Inversion of Control (IoC)**, **Dependency Injection (DI)**, and strict **Design-by-Contract (DbC)** principles, heavily inspired by modern .NET architectures.

---

## 2. Language Evaluation: Python vs. Nim

To achieve strict contracts and testability, we must replace complex Bash logic with a more structured language. **Python 3** and **Nim** were evaluated with equal rigor based on their ability to fulfill these architectural requirements.

### 2.1 Nim Evaluation
Nim is a statically typed, compiled systems programming language with syntax reminiscent of Python but performance comparable to C.

**Strengths:**
- **Performance & Distribution:** Compiles to a single, lightning-fast binary. No runtime dependencies required in the `arch-builder` container.
- **Design-by-Contract (DbC) Native:** Nim’s AST macro system allows for literal DbC constructs. You can write robust `require:` (pre-condition) and `ensure:` (post-condition) blocks natively.
- **Type Safety:** Compile-time checking prevents entire classes of runtime errors regarding file paths and shell arguments.

**Weaknesses:**
- **Mocking Ecosystem:** Nim’s `unittest` module is solid, but its ecosystem for mocking dynamic interactions (like arbitrary shell subprocesses, filesystem mutations, or network requests) is significantly less mature than its competitors. Mocking often requires heavy boilerplate or compile-time variant objects.
- **Maintenance Pool:** The talent pool for maintaining Nim tooling is smaller, increasing the bus factor risk for the repository.

### 2.2 Python Evaluation
Python is a dynamically typed, interpreted language that serves as the de facto standard for infrastructure automation (e.g., Ansible, Portage utilities).

**Strengths:**
- **Dependency Injection & Interfaces:** Python 3.8+ introduced `typing.Protocol`, which acts exactly like a .NET `interface`. Coupled with IoC containers like the `dependency_injector` library, it allows for perfect structural typing and constructor injection.
- **Elite Testing Frameworks:** `pytest` is widely considered the best testing framework in any language. Specifically, `unittest.mock.patch` provides unmatched, surgical precision for mocking `subprocess.run`, `os.path`, and `urllib` calls.
- **DbC via Libraries:** Libraries like `icontract` provide powerful decorators (`@require`, `@ensure`, `@inv`) that enforce runtime contracts explicitly, failing fast if parameters violate business rules.

**Weaknesses:**
- **Runtime Overhead:** Python requires an interpreter and incurs startup overhead (milliseconds) compared to a compiled Nim binary.
- **Dynamic Nature:** Without strict enforcement of `mypy` (static analysis), type safety can be bypassed.

### 2.3 Decision: Python 3.11+
**Python is the chosen language for this refactoring.** 

*Justification:* The primary requirement for this architecture is **comprehensive testability and Dependency Injection**. Because 90% of these scripts orchestrate side-effects (running `makepkg`, `git`, `curl`), the ability to effortlessly mock these side-effects is the most critical feature. Python’s `pytest-mock` ecosystem vastly outperforms Nim in this specific domain, allowing us to simulate complex Arch Linux environments in milliseconds without writing custom shell wrappers for every single tool.

*Note:* Bash will remain *only* as thin glue layers (e.g., a 3-line `arch-builder.sh` that calls the Python tool) to bridge GitHub Actions to the CLI.

---

## 3. Architectural Blueprint (DI & DbC)

The new architecture will isolate the "Domain Logic" (the rules of package synchronization, identity protection, and changelog generation) from the "Infrastructure" (the file system, git, pacman).

### 3.1 Interfaces (The `.NET Protocol` Mapping)
We define explicit boundaries using `typing.Protocol`. All external interactions are abstracted.

```python
from typing import Protocol, List

class ICommandExecutor(Protocol):
    """Executes shell commands (makepkg, git, curl)."""
    def run(self, command: List[str], cwd: str) -> str: ...

class IFileSystem(Protocol):
    """Abstracts disk operations for mockability."""
    def read_file(self, path: str) -> str: ...
    def write_file(self, path: str, content: str) -> None: ...
    def merge_files(self, local: str, base: str, remote: str) -> bool: ...

class IPackageManager(Protocol):
    """Arch-specific tooling."""
    def generate_srcinfo(self, pkg_dir: str) -> str: ...
    def update_checksums(self, pkg_dir: str) -> None: ...
```

### 3.2 Constructor Injection
Classes must never instantiate their dependencies. They must be injected, allowing for pure, isolated unit testing.

```python
class SyncPackageUseCase:
    def __init__(
        self, 
        executor: ICommandExecutor, 
        fs: IFileSystem, 
        pacman: IPackageManager
    ):
        self._executor = executor
        self._fs = fs
        self._pacman = pacman
```

### 3.3 Design-by-Contract (DbC)
We use the `icontract` library to strictly define the boundaries of the `SyncPackageUseCase`.

- **Pre-Conditions (`@require`)**: What must be true before execution? (e.g., The target directory must contain a valid `PKGBUILD`).
- **Post-Conditions (`@ensure`)**: What must be guaranteed after execution? (e.g., The generated `.SRCINFO` must match the `PKGBUILD` checksum).
- **Invariants (`@inv`)**: What must remain unchanged? (e.g., The `pkgname` identity must be preserved across merges).

```python
import icontract

@icontract.require(lambda pkg_name: len(pkg_name) > 0)
@icontract.require(lambda new_ver: len(new_ver) > 0)
@icontract.ensure(lambda self, pkg_name: self._fs.read_file("PKGBUILD").startswith(f"pkgname={pkg_name}"))
def execute(self, pkg_name: str, new_ver: str) -> None:
    # Business logic here...
    pass
```

---

## 4. Comprehensive Testing Strategy (The Pyramid)

The testing suite will be partitioned into three distinct layers, balancing speed, determinism, and real-world confidence.

### Level 1: Unit Tests (Logic & Contracts)
- **Scope:** Testing the internal logic of the Python classes without touching the disk or invoking actual shell commands.
- **Strategy:** Provide mock implementations of `IFileSystem` and `ICommandExecutor` to the `SyncPackageUseCase`.
- **Target Metrics:** 100% path coverage for the core business logic.
- **Specific Scenarios:**
  - Verify that if `new_ver` is different from the current `pkgver`, `pkgrel` is reset to 1.
  - Verify that if an upstream merge alters the configuration but `pkgver` remains identical, `pkgrel` is incremented.
  - Ensure the identity snapshot mechanism correctly isolates the variant `pkgname` before triggering the `IFileSystem.merge_files` call.
- **Tooling:** `pytest`, `pytest-mock`.

### Level 2: Integration Tests (Adapter Verification)
- **Scope:** Testing the concrete implementations of our interfaces (the Adapters) against real files but mocked network/Arch environments.
- **Strategy:** Instead of mocking `IFileSystem`, we use `pytest`'s built-in `tmp_path` fixture to perform actual disk I/O. We continue to mock `ICommandExecutor` for commands that require an Arch environment (like `makepkg`).
- **Specific Scenarios:**
  - Write a raw `PKGBUILD` string to a temporary directory, invoke the `ArchPackageManager` adapter, and ensure it constructs the correct `makepkg --printsrcinfo` command line call.
  - Test the `GitIntegration` adapter by initializing a local temporary git repository and asserting that it commits files correctly.

### Level 3: End-to-End (E2E) Tests (The Sandbox)
- **Scope:** Verifying the full pipeline (from version discovery to built `.pkg.tar.zst` artifact) in a real Arch Linux environment.
- **Strategy:** These tests are executed exclusively inside the `arch-builder` Docker container via GitHub Actions.
- **Specific Scenarios:**
  - Run the CLI entrypoint of the Python tool against a dummy package in a `/tmp` workspace.
  - Assert that the tool successfully invokes the *real* `updpkgsums` and `makepkg`, handles the actual PGP key imports, and produces a valid compiled binary.
- **Tooling:** GitHub Actions `container` workflows executing high-level `pytest` markers (e.g., `@pytest.mark.e2e`).

---

## 5. Implementation Specifications

### 5.1 Project Structure
The `scripts/` directory will be restructured into a Python package module:

```text
scripts/
├── automation/
│   ├── __init__.py
│   ├── core/           # Domain logic (SyncPackageUseCase, ChangelogGenerator)
│   ├── ports/          # Interfaces (ICommandExecutor, IFileSystem)
│   ├── adapters/       # Concrete implementations (SubprocessExecutor, LocalFileSystem)
│   └── cli.py          # Entrypoint (Argparse/Click)
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── pyproject.toml      # Dependency & Pytest configuration
└── arch-builder.sh     # Thin Bash wrapper for CI compatibility
```

### 5.2 Dependency Injection Container Example
We will use a manual composition root (or a lightweight library) to wire the dependencies for the CLI:

```python
# cli.py
def main():
    # Concrete Implementations
    fs = LocalFileSystem()
    executor = SubprocessExecutor()
    pacman = ArchPackageManager(executor, fs)
    
    # Inject into the Domain
    sync_service = SyncPackageUseCase(executor, fs, pacman)
    
    # Execute
    sync_service.execute(args.pkg_name, args.version)
```

### 5.3 Unit Testing Example (Pytest)
Demonstrating how the DI architecture makes testing a 3-way merge scenario trivial:

```python
# tests/unit/test_sync_package.py
def test_identity_protection_during_merge(mocker):
    # Arrange
    mock_fs = mocker.Mock(spec=IFileSystem)
    mock_fs.read_file.return_value = "pkgname=gemini-cli-preview\npkgver=0.38.0"
    
    mock_executor = mocker.Mock(spec=ICommandExecutor)
    mock_pacman = mocker.Mock(spec=IPackageManager)
    
    sut = SyncPackageUseCase(mock_executor, mock_fs, mock_pacman)
    
    # Act
    sut.execute("gemini-cli-preview", "0.38.0")
    
    # Assert
    # Verify that merge_files was called, and that the file was subsequently 
    # patched back to 'gemini-cli-preview' to protect the identity.
    mock_fs.merge_files.assert_called_once()
    mock_fs.write_file.assert_any_call("PKGBUILD", mocker.ANY) # Asserts the restore
```

---

## 6. Assumptions & Risk Log

1. **Assumption: Python Execution Speed is Irrelevant.** 
   - *Reasoning:* The time taken by Python to interpret code is measured in milliseconds. The actual operations (`makepkg`, cloning git repos, compiling C++/Go/Node.js) take minutes. The "runtime tax" of Python is a non-issue for orchestration.
2. **Assumption: CI Environment Flexibility.**
   - *Reasoning:* I am assuming the GitHub Actions `arch-builder` image can have `python`, `python-pip`, and `pytest` installed via `pacman -S python pytest` without negatively impacting the build container's isolation.
3. **Assumption: Strict Typing is Maintained.**
   - *Reasoning:* Python's duck typing is a risk if not checked. I assume `mypy` will be integrated into the GitHub Actions CI pipeline to enforce the `Protocol` contracts at "compile time" before any script is executed.
4. **Risk: Maintainer Learning Curve.**
   - *Mitigation:* Replacing 100 lines of Bash with 400 lines of structured Python + 500 lines of tests increases the cognitive load for casual contributors. However, it completely eliminates the "hidden side-effect" bugs that plague Bash scripts, providing a net positive ROI for a sole maintainer or AI agent.
