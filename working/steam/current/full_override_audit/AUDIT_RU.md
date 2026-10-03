# Steam 0.7.9.16321 — полный аудит бинарных override-пакетов

Версия **0.7.9.16321** подтверждена по текущему `RPGInventory_GameInstance.uasset`: строка версии находится по смещению 313692; SHA-256 `756887fd7ef918293f74de69e5bec51f7a54c6dc43408a2e24599cfd9382e898`. Точный Steam BuildID не подтверждён: в источнике нет EXE, appmanifest или Build.version.

Проверены все 151 пакетов NoSteam FULL против текущих Steam-файлов и все 34 пакета предыдущего Steam v4.

- Старый Steam v4 содержал 34 пакета; NoSteam FULL — 151.
- Из 123 пакетов, отсутствовавших в Steam v4, **все 123 содержат значимые изменения русификатора**; доказательств, что они были лишними, нет.
- 98 из этих 123 имеют идентичную нормализованную Zen-схему, name map, порядок exports и export-reference поля — это статически совместимые кандидаты на перенос.
- 21 пакет имеет ту же export-схему, но изменённый name map — его надо портировать на текущий Steam-исходник, а не копировать NoSteam целиком.
- 4 пакета имеют изменения схемы/export mapping и требуют отдельного Steam-патча: `bp_quest_actor.uasset, WB_CheatMenuOption_Quests.uasset, WB_FormScreen.uasset, WB_HUD.uasset`.
- Из 34 старых Steam v4 пакетов 23 побайтно совпадают с текущим источником, а 11 изменились и должны быть пересобраны/проверены заново.
- `Game.locres` текущего источника побайтно совпадает с v4 Steam; текстовый каталог сам по себе обновления не требует.

## 11 изменившихся пакетов старого Steam v4
- `Content/DLG_Tree/dmap_system/widgets/w_03_map_icon.uasset`
- `Content/RPG_InventorySystem/UI/Character/WB_CharacterScreen.uasset`
- `Content/RPG_InventorySystem/UI/PlayerInventory/WB_Stats_Full.uasset`
- `Content/RPG_InventorySystem/UI/PlayerInventory/WB_Stats_Main.uasset`
- `Content/RPG_InventorySystem/UI/PlayerInventory/WB_Stats_Main_Slot.uasset`
- `Content/RPG_InventorySystem/UI/Quests/WB_QuestName.uasset`
- `Content/RPG_InventorySystem/UI/Quests/WB_QuestObjectiveDescription.uasset`
- `Content/RPG_InventorySystem/UI/Quests/WB_QuestObjectiveName.uasset`
- `Content/RPG_InventorySystem/UI/Quests/WB_QuestType.uasset`
- `Content/RPG_InventorySystem/UI/WorldMap/WB_MapLegend_Item.uasset`
- `Content/RPG_InventorySystem/UI/WorldMap/WB_WorldMapPopup.uasset`

## 4 пакета со сменой схемы
- `Content/DLG_Tree/dqst_system/blueprints/bp_quest_actor.uasset`
- `Content/RPG_InventorySystem/UI/Dev/WB_CheatMenuOption_Quests.uasset`
- `Content/RPG_InventorySystem/UI/Forms/WB_FormScreen.uasset`
- `Content/RPG_InventorySystem/UI/HUD/WB_HUD.uasset`

## Вывод
Steam v4 действительно был бинарно неполным относительно NoSteam FULL. Для полного Steam FULL целевая совокупность после аудита — **157 уникальных бинарных пакетов**: 151 функциональный набор NoSteam плюс 6 Steam-специфичных пакетов. Копировать все NoSteam-файлы вслепую нельзя: 25 из ранее отсутствовавших 123 требуют Steam-специфичного переноса, а 11 старых Steam-патчей затронуты текущим обновлением.

Runtime-проверка в игре не выполнялась.
