For a successful and complete migration, we need the following:
* new version - usually base game directory;
* old version - will serve as a reference for change detection;
* project dir, where migration changes are applied;

To perform migration do the following:
1. Move current project to a separate directory, which will serve as a migration old version reference.
2. Set up migration environment variables:
    ```
    MIGRATION_FROM=from-1.2.3
    MIGRATION_TO=to-dev-1.2.4
    MIGRATION_REFERENCE_DIR=/home/primislas/workspace/eu5-modding-prev-version
    ```
3. Move new version files to the project directory.
   ```python -m eukrainersalis.move_game_localization_to_project```
