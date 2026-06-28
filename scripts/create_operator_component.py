#!/usr/bin/env python3
"""
Скрипт для создания стандартной структуры компонента системы Эксплуатант.
Использование: python create_operator_component.py <component_name>
"""

import os
import sys
import argparse
from pathlib import Path


def create_component_structure(component_name: str, base_path: str = "systems/operator/src") -> None:
    """
    Создает стандартную структуру компонента согласно спецификации.
    
    Args:
        component_name: Название компонента (например, fleet_manager)
        base_path: Базовый путь для создания компонента
    """
    # Определяем структуру директорий
    directories = [
        "",  # Корневая директория компонента
        "src",
        "tests",
        "tests/unit",
        "tests/module", 
        "tests/integration",
        "resources",
        "docker",
        "docs"
    ]
    
    # Создаем директории
    component_path = Path(base_path) / component_name
    for directory in directories:
        dir_path = component_path / directory
        dir_path.mkdir(parents=True, exist_ok=True)
        print(f"Created directory: {dir_path}")
        
        # Создаем __init__.py файлы где необходимо
        if directory and not directory.endswith(('resources', 'docker', 'docs')):
            init_file = dir_path / "__init__.py"
            if not init_file.exists():
                init_file.touch()
                print(f"Created file: {init_file}")
    
    # Создаем основные файлы компонента
    create_main_file(component_path, component_name)
    create_component_file(component_path, component_name)
    create_makefile(component_path, component_name)
    create_dockerfile(component_path, component_name)
    create_readme(component_path, component_name)
    create_security_goals(component_path, component_name)
    create_test_files(component_path, component_name)
    create_requirements_file(component_path)


def create_main_file(component_path: Path, component_name: str) -> None:
    """Создает __main__.py файл для компонента."""
    content = f'''#!/usr/bin/env python3
"""
Точка входа для компонента {component_name}.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

# Добавляем путь к SDK
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent.parent))

from src.{component_name} import {to_class_name(component_name)}


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Основная функция запуска компонента."""
    logger.info(f"Starting {component_name} component...")
    
    # Получаем конфигурацию из переменных окружения
    broker_type = os.getenv('BROKER_TYPE', 'mqtt')
    broker_host = os.getenv('BROKER_HOST', 'localhost')
    broker_port = int(os.getenv('BROKER_PORT', '1883'))
    
    # Создаем и запускаем компонент
    component = {to_class_name(component_name)}(
        broker_type=broker_type,
        broker_host=broker_host,
        broker_port=broker_port
    )
    
    try:
        await component.start()
        # Держим компонент запущенным
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await component.stop()


if __name__ == "__main__":
    asyncio.run(main())
'''
    
    file_path = component_path / "__main__.py"
    file_path.write_text(content)
    file_path.chmod(0o755)
    print(f"Created file: {file_path}")


def create_component_file(component_path: Path, component_name: str) -> None:
    """Создает основной файл компонента."""
    class_name = to_class_name(component_name)
    content = f'''"""
Компонент {class_name} системы Эксплуатант.
"""

import asyncio
import logging
from typing import Dict, Any, Optional

from sdk.base_component import BaseComponent
from sdk.messages import Message


logger = logging.getLogger(__name__)


class {class_name}(BaseComponent):
    """
    Компонент {component_name} системы Эксплуатант.
    
    Отвечает за: [ОПИСАНИЕ ФУНКЦИОНАЛЬНОСТИ]
    """
    
    def __init__(self, broker_type: str, broker_host: str, broker_port: int):
        """
        Инициализация компонента.
        
        Args:
            broker_type: Тип брокера сообщений (mqtt/kafka)
            broker_host: Хост брокера
            broker_port: Порт брокера
        """
        super().__init__(
            name="{component_name}",
            broker_type=broker_type,
            broker_host=broker_host,
            broker_port=broker_port
        )
        
        # Инициализация специфичных для компонента атрибутов
        self._state: Dict[str, Any] = {{}}
        
    async def start(self) -> None:
        """Запуск компонента."""
        logger.info(f"Starting {class_name}...")
        
        # Подписка на необходимые топики
        await self._subscribe_to_topics()
        
        # Запуск фоновых задач
        self._tasks.append(
            asyncio.create_task(self._health_check_loop())
        )
        
        logger.info(f"{class_name} started successfully")
        
    async def stop(self) -> None:
        """Остановка компонента."""
        logger.info(f"Stopping {class_name}...")
        
        # Отмена всех задач
        for task in self._tasks:
            task.cancel()
            
        # Ожидание завершения задач
        await asyncio.gather(*self._tasks, return_exceptions=True)
        
        # Отключение от брокера
        await self._disconnect()
        
        logger.info(f"{class_name} stopped")
        
    async def _subscribe_to_topics(self) -> None:
        """Подписка на необходимые топики."""
        # TODO: Добавить подписки на топики
        pass
        
    async def _handle_message(self, message: Message) -> None:
        """
        Обработка входящего сообщения.
        
        Args:
            message: Входящее сообщение
        """
        logger.debug(f"Received message: {{message}}")
        
        # TODO: Реализовать обработку сообщений
        
    async def _health_check_loop(self) -> None:
        """Цикл проверки состояния компонента."""
        while True:
            try:
                # TODO: Реализовать проверку состояния
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Health check error: {{e}}")
                
    def get_health_status(self) -> Dict[str, Any]:
        """
        Получение статуса здоровья компонента.
        
        Returns:
            Словарь с информацией о состоянии компонента
        """
        return {{
            "status": "healthy",
            "component": self.name,
            "state": self._state
        }}
'''
    
    file_path = component_path / "src" / f"{component_name}.py"
    file_path.write_text(content)
    print(f"Created file: {file_path}")


def create_makefile(component_path: Path, component_name: str) -> None:
    """Создает Makefile для компонента."""
    content = f'''.PHONY: test test-unit test-module test-integration build run clean

COMPONENT_NAME := {component_name}

test: test-unit test-module test-integration

test-unit:
	@echo "Running unit tests for $(COMPONENT_NAME)..."
	pipenv run pytest tests/unit -v

test-module:
	@echo "Running module tests for $(COMPONENT_NAME)..."
	pipenv run pytest tests/module -v

test-integration:
	@echo "Running integration tests for $(COMPONENT_NAME)..."
	pipenv run pytest tests/integration -v

build:
	@echo "Building Docker image for $(COMPONENT_NAME)..."
	docker build -t operator-$(COMPONENT_NAME):latest -f docker/Dockerfile .

run:
	@echo "Running $(COMPONENT_NAME)..."
	pipenv run python -m {component_name}

clean:
	@echo "Cleaning $(COMPONENT_NAME)..."
	find . -type d -name __pycache__ -exec rm -rf {{}} +
	find . -type f -name "*.pyc" -delete
'''
    
    file_path = component_path / "Makefile"
    file_path.write_text(content)
    print(f"Created file: {file_path}")


def create_dockerfile(component_path: Path, component_name: str) -> None:
    """Создает Dockerfile для компонента."""
    content = f'''FROM python:3.12.3-slim

# Установка рабочей директории
WORKDIR /app

# Копирование файлов зависимостей
COPY requirements.txt .

# Установка зависимостей
RUN pip install --no-cache-dir -r requirements.txt

# Копирование SDK
COPY ../../../../sdk /app/sdk

# Копирование кода компонента
COPY . /app/{component_name}

# Установка переменных окружения
ENV PYTHONPATH=/app
ENV COMPONENT_NAME={component_name}

# Healthcheck
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \\
    CMD python -c "import requests; requests.get('http://localhost:8080/health')" || exit 1

# Запуск компонента
CMD ["python", "-m", "{component_name}"]
'''
    
    file_path = component_path / "docker" / "Dockerfile"
    file_path.write_text(content)
    print(f"Created file: {file_path}")


def create_readme(component_path: Path, component_name: str) -> None:
    """Создает README.md для компонента."""
    class_name = to_class_name(component_name)
    content = f'''# {class_name}

## Описание

Компонент {class_name} системы Эксплуатант отвечает за [ОПИСАНИЕ ФУНКЦИОНАЛЬНОСТИ].

## Структура

```
{component_name}/
├── __init__.py
├── __main__.py          # Точка входа
├── Makefile            # Команды сборки и тестирования
├── requirements.txt    # Зависимости
├── src/
│   └── {component_name}.py  # Основная логика
├── tests/
│   ├── unit/          # Модульные тесты
│   ├── module/        # Тесты взаимодействия
│   └── integration/   # Интеграционные тесты
├── resources/         # Конфигурации и данные
├── docker/
│   └── Dockerfile
└── docs/
    ├── README.md
    └── security_goals.md
```

## Запуск

### Локальный запуск

```bash
make run
```

### Запуск в Docker

```bash
make build
docker run -e BROKER_HOST=broker operator-{component_name}:latest
```

## Тестирование

```bash
# Все тесты
make test

# Только unit тесты
make test-unit

# Только интеграционные тесты
make test-integration
```

## Конфигурация

Компонент настраивается через переменные окружения:

- `BROKER_TYPE` - тип брокера сообщений (mqtt/kafka)
- `BROKER_HOST` - хост брокера
- `BROKER_PORT` - порт брокера
- `LOG_LEVEL` - уровень логирования

## API

### Входящие сообщения

[ОПИСАНИЕ ОБРАБАТЫВАЕМЫХ СООБЩЕНИЙ]

### Исходящие сообщения

[ОПИСАНИЕ ОТПРАВЛЯЕМЫХ СООБЩЕНИЙ]

## Цели безопасности

См. [security_goals.md](docs/security_goals.md)
'''
    
    file_path = component_path / "docs" / "README.md"
    file_path.write_text(content)
    print(f"Created file: {file_path}")


def create_security_goals(component_path: Path, component_name: str) -> None:
    """Создает документ с целями безопасности."""
    class_name = to_class_name(component_name)
    content = f'''# Цели безопасности компонента {class_name}

## Общее описание

Компонент {class_name} является частью системы Эксплуатант и отвечает за [ОПИСАНИЕ].

## Домен безопасности

Компонент относится к домену: [D0_CRITICAL/D1_TRUSTED/D2_OPERATIONAL/D3_EXTERNAL]

## Цели безопасности (Security Goals)

### SG-{component_name.upper()}-001: [Название цели]

**Описание**: При любых обстоятельствах [описание цели безопасности]

**Категория ГОСТ Р ИСО/МЭК 15408**: [Категория]

**Механизм реализации**: [Описание механизма]

**Метрики проверки**:
- [Метрика 1]
- [Метрика 2]

## Предположения безопасности

### AS-{component_name.upper()}-001: [Название предположения]

[Описание предположения о среде функционирования]

## Угрозы (STRIDE)

### Spoofing (Подмена идентичности)
- T-{component_name.upper()}-S01: [Описание угрозы]

### Tampering (Нарушение целостности)
- T-{component_name.upper()}-T01: [Описание угрозы]

### Repudiation (Отказ от авторства)
- T-{component_name.upper()}-R01: [Описание угрозы]

### Information Disclosure (Раскрытие информации)
- T-{component_name.upper()}-I01: [Описание угрозы]

### Denial of Service (Отказ в обслуживании)
- T-{component_name.upper()}-D01: [Описание угрозы]

### Elevation of Privilege (Повышение привилегий)
- T-{component_name.upper()}-E01: [Описание угрозы]

## Контрмеры

| Угроза | Контрмера | Реализация |
|--------|-----------|------------|
| T-{component_name.upper()}-S01 | [Контрмера] | [Как реализовано] |

## Трассировка к целям безопасности системы

| ЦБ компонента | ЦБ системы | Обоснование |
|---------------|------------|-------------|
| SG-{component_name.upper()}-001 | ЦБ-OPS-X | [Обоснование связи] |

## Тестирование безопасности

### Покрытие тестами
- Целевое покрытие: [X]%
- Текущее покрытие: [Y]%

### Тестовые сценарии
1. [Сценарий 1]
2. [Сценарий 2]
'''
    
    # Создаем файл целей безопасности в docs
    file_path = component_path / "docs" / "security_goals.md"
    file_path.write_text(content)
    print(f"Created file: {file_path}")
    
    # Создаем YAML файл с целями безопасности в resources
    yaml_content = f'''# Цели безопасности компонента {component_name}
security_goals:
  - id: "SG-{component_name.upper()}-001"
    name: "[Название цели]"
    description: "При любых обстоятельствах [описание]"
    gost_72118_mapping:
      category: "[Категория]"
      level: "Высокий"
    implementation:
      mechanism: "[Механизм]"
      verification: "Автоматическая проверка"
    system_goal_mapping: "ЦБ-OPS-X"
'''
    
    yaml_path = component_path / "resources" / "security_goals.yaml"
    yaml_path.write_text(yaml_content)
    print(f"Created file: {yaml_path}")


def create_test_files(component_path: Path, component_name: str) -> None:
    """Создает базовые файлы тестов."""
    class_name = to_class_name(component_name)
    
    # Unit test
    unit_test_content = f'''"""
Unit тесты для компонента {class_name}.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from src.{component_name} import {class_name}


class Test{class_name}:
    """Тесты для класса {class_name}."""
    
    @pytest.fixture
    def component(self):
        """Фикстура для создания экземпляра компонента."""
        return {class_name}(
            broker_type="mqtt",
            broker_host="localhost",
            broker_port=1883
        )
    
    def test_initialization(self, component):
        """Тест инициализации компонента."""
        assert component.name == "{component_name}"
        assert component._state == {{}}
    
    def test_get_health_status(self, component):
        """Тест получения статуса здоровья."""
        status = component.get_health_status()
        assert status["status"] == "healthy"
        assert status["component"] == "{component_name}"
    
    @pytest.mark.asyncio
    async def test_start_stop(self, component):
        """Тест запуска и остановки компонента."""
        with patch.object(component, '_subscribe_to_topics', new_callable=AsyncMock):
            with patch.object(component, '_disconnect', new_callable=AsyncMock):
                await component.start()
                assert len(component._tasks) > 0
                
                await component.stop()
                assert all(task.cancelled() for task in component._tasks)
'''
    
    unit_test_path = component_path / "tests" / "unit" / f"test_{component_name}.py"
    unit_test_path.write_text(unit_test_content)
    print(f"Created file: {unit_test_path}")
    
    # Integration test
    integration_test_content = f'''"""
Интеграционные тесты для компонента {class_name}.
"""

import pytest
import asyncio
from unittest.mock import patch

from src.{component_name} import {class_name}


@pytest.mark.integration
class Test{class_name}Integration:
    """Интеграционные тесты для {class_name}."""
    
    @pytest.fixture
    async def component(self):
        """Фикстура для создания и запуска компонента."""
        component = {class_name}(
            broker_type="mqtt",
            broker_host="localhost",
            broker_port=1883
        )
        
        # Мокаем подключение к брокеру
        with patch.object(component, '_connect', new_callable=AsyncMock):
            with patch.object(component, '_disconnect', new_callable=AsyncMock):
                yield component
    
    @pytest.mark.asyncio
    async def test_component_lifecycle(self, component):
        """Тест полного жизненного цикла компонента."""
        # Запускаем компонент
        await component.start()
        
        # Даем компоненту поработать
        await asyncio.sleep(0.1)
        
        # Проверяем состояние
        health = component.get_health_status()
        assert health["status"] == "healthy"
        
        # Останавливаем компонент
        await component.stop()
'''
    
    integration_test_path = component_path / "tests" / "integration" / f"test_{component_name}_integration.py"
    integration_test_path.write_text(integration_test_content)
    print(f"Created file: {integration_test_path}")


def create_requirements_file(component_path: Path) -> None:
    """Создает requirements.txt для компонента."""
    content = '''# Зависимости компонента
pyyaml>=6.0
pydantic>=2.0
asyncio-mqtt>=0.16.0
aiohttp>=3.8.0

# Зависимости для тестирования
pytest>=7.0.0
pytest-asyncio>=0.21.0
pytest-cov>=4.0.0
'''
    
    file_path = component_path / "requirements.txt"
    file_path.write_text(content)
    print(f"Created file: {file_path}")


def to_class_name(component_name: str) -> str:
    """Преобразует имя компонента в имя класса."""
    return ''.join(word.capitalize() for word in component_name.split('_'))


def main():
    """Основная функция."""
    parser = argparse.ArgumentParser(
        description="Создает стандартную структуру компонента системы Эксплуатант"
    )
    parser.add_argument(
        "component_name",
        help="Имя компонента (например, fleet_manager)"
    )
    parser.add_argument(
        "--base-path",
        default="systems/operator/src",
        help="Базовый путь для создания компонента (по умолчанию: systems/operator/src)"
    )
    
    args = parser.parse_args()
    
    # Проверяем, что имя компонента валидно
    if not args.component_name.replace('_', '').isalnum():
        print(f"Ошибка: Имя компонента должно содержать только буквы, цифры и подчеркивания")
        sys.exit(1)
    
    print(f"Создание структуры компонента '{args.component_name}'...")
    
    try:
        create_component_structure(args.component_name, args.base_path)
        print(f"\nКомпонент '{args.component_name}' успешно создан!")
        print(f"Расположение: {args.base_path}/{args.component_name}")
        print("\nДальнейшие шаги:")
        print(f"1. Отредактируйте src/{args.component_name}.py для реализации логики")
        print(f"2. Обновите docs/security_goals.md с актуальными целями безопасности")
        print(f"3. Добавьте тесты в соответствующие директории")
        print(f"4. Запустите 'make test' для проверки")
    except Exception as e:
        print(f"Ошибка при создании компонента: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()