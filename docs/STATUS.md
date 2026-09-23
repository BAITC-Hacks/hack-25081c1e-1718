# Team status

After kickoff, add module/file ownership here. Each person edits only their own section.

## Dima

- Current: Опубликованы эксперименты a10e7b1, документированная поставка 9a1b3b1 и фиксация 97da837. 110 новых прогонов не подтвердили улучшение; baseline/template/fixed сохранён. На независимых 300–319 baseline median 674970.62 против adaptive 642092.75, оба 20/20 положительных.
- Ownership: agent.py, llm_advisor.py, server.py, report_assistant.py, scripts/ и общие контракты. Азим — web/DESIGN/DEMO/README; candidate_model.py/analysis и данные остаются замороженными.
- Next: Принять checkpoint Азима по диагностике UI, README и DEMO, проверить изменения и обновить архив. Координация через GitHub #1 и QUESTIONS/HANDOFF каждые 3 минуты; повторять серии качества только при новой причине.
- Blockers: Своя часть проверена: 69 Python / 7 analysis / 33 Node, чистая поставка, точное совпадение standalone и CSV. Пока нет нового checkpoint Азима; финальная загрузка организаторам не подтверждена. 100/100 или рост качества не обещаем.

## Azim

- Current: Диагностический UI по QUALITY_STAGE реализован поверх RU/KK: исследование/причины/расходы пилотов, собственные доказательства кампаний, эвристическая неопределённость, раздельные прогноз финальных кампаний и факт всей симуляции, новые refs. Старые report1.0 без полей показывают «нет данных». На реальном offline seed42 Edge проверены RU/KK, 375/768/1440, loading/error/empty, фокус и пилотные ссылки; шесть снимков в web/screenshots. README/DEMO обновлены по финальному отчёту Димы 300c198 с версией проверенной поставки 9a1b3b1.
- Ownership: web/**, docs/DESIGN.md, docs/DEMO.md, README.md, собственные LOG/HANDOFF и этот раздел STATUS. candidate_model.py/analysis и данные заморожены.
- Next: Выполнить 34 Node, verify.ps1 -Release и checkpoint со своей зоной; после чистого коммита проверить собранный ZIP и передать SHA Диме. Сверка GitHub каждые 3 минуты активной работы.
- Blockers: Экономический gate не пройден, production baseline сохранён. Проверка новой UI/README-ревизии и приёмка Димой ожидаются. Отправка организаторам не подтверждена.
