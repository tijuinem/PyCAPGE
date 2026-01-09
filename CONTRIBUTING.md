# Contributing to PyCAPGE

First off, thanks for taking the time to contribute! PyCAPGE (Python Classic Adventure Point-and-Click Game Engine) is an open-source project designed for education and digital preservation. We welcome contributions from developers, educators, and retro-gaming enthusiasts.

## How Can You Contribute?

### 1. Reporting Bugs
If you find a bug, please create a GitHub Issue. Be sure to include:
* A clear title and description.
* Steps to reproduce the error.
* The expected behavior vs. actual behavior.
* The content of the `debug_console` or terminal output if relevant.

### 2. Suggesting Enhancements
We want to keep the engine **simple and readable** for students. Feature requests should prioritize educational clarity over complex optimizations.
* Open an issue to discuss your idea before writing code.
* Explain why this feature helps students or game preservation.

### 3. Pull Requests (Code Contributions)
1.  **Fork** the repository.
2.  **Clone** your fork locally.
3.  **Create a branch** for your feature (`git checkout -b feature/amazing-feature`).
4.  **Install dependencies**:
    ```bash
    pip install pygame pyyaml
    ```
5.  **Make your changes**.
6.  **Run tests**: Please ensure existing tests pass (check the `/test` folder).
7.  **Commit** your changes with clear messages.
8.  **Push** to your fork and submit a **Pull Request**.

## Coding Guidelines

Since PyCAPGE is an educational tool, code readability is paramount.

* **Style**: Follow PEP 8 guidelines where possible.
* **Architecture**:
    * **Engine Core**: Keep core logic in `engine/classes.py`.
    * **Game Logic**: Specific game data (scenes, items) belongs in `scenes/` or external YAML files. Avoid hardcoding game-specific logic inside the engine core classes.
* **Comments**: Comment your code generously. Remember that students will read this code to learn how game engines work.
* **Variables**: Use descriptive variable names (e.g., `current_scene` instead of `cs`).

## Localization (Translations)
You can contribute by translating the engine messages and demo game:
1.  Look into the `languages/` folder.
2.  Duplicate `es.yaml` (or `en.yaml`) and rename it to your language code (e.g., `fr.yaml`).
3.  Translate the values (keep the keys unchanged).
4.  Test it by changing the language in the Game Title Menu.

## License
By contributing to PyCAPGE, you agree that your contributions will be licensed under its GNU General Public License v3.0 (GPLv3).