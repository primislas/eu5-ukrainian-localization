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
4. Oftentimes it's a good idea to set MAX_FILES_TO_TRANSLATE to a smaller value, like 4, 8, 20,
to process smaller manageable commits, and have an opportunity to edit ru_ua system instructions
along the way. Pick your value and repeatedly run "run_machine_translation.py",
until all files are exhausted.
5. Run "custom_loc_adaptation.py" to generate custom country and rank endings, custom culture ua scripts.
6. Run "ending_adaptionat.py" to adapt ru endings to Ukrainian ones.
7. Run "estate_ending_generator.py" to generate estate endings
8. Run "ending_patching.py" in a separate commit, to detect dangling cases of Russian endings and prepositions.

Various post-migration checks:
* Check correct 'GetAdjective' endings with a regex search `GetAdjective[^\]]*][^а-яіїє\[\$]`
