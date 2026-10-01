# Adding Custom Estate Names

Estate names can be customized for various countries, regions and reforms. Follow these steps to add a custom estate name:

1. Add your estate to
    `mod/main_menu/localization/russian/ua_estate_l_russian_uk_ua_machine_translation.yml`
    ```yaml 
     # Cossacks, Ukraine: Starshyna
     nobles_estate_starshyna: "Старшина"
   ```
2. Add your estate to custom localization with appropriate triggers:
    `mod/in_game/common/customizable_localization/380_estates.txt`
    ```plaintext
      text = {
        localization_key = nobles_estate_starshyna
        trigger = {
          has_reform = government_reform:cossacks_reform
        }
      }
    ```
3. IF estate endings are not ordinary plural endings (NOT "вони" but other forms and genders like "знать", "духовенство", "простолюд"), then 
    1. Add appropriate endings to:
       `mod/main_menu/localization/russian/assets/ua_estates_ending_l_russian_uk_ua_machine_translation.yml`
    2. Don't forget to edit keys at the bottom: Estate_GetEnd_aei, Estate_GetEnd_yiaei 
4. Run automatic estate generation script:
 
    ```python -m eukrainersalis.utils.estate_ending_generator```