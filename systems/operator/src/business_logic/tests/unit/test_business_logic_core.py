"""
Unit тесты для BusinessLogicCore
"""

import pytest
from systems.operator.src.business_logic.src.business_logic_core import BusinessLogicCore, MarginValidation


class TestBusinessLogicCore:
    """Тесты для критического ядра бизнес-логики"""

    @pytest.fixture
    def core(self):
        """Фикстура для создания экземпляра BusinessLogicCore"""
        return BusinessLogicCore()

    def test_init(self, core):
        """Тест инициализации"""
        assert core._MIN_MARGIN_PERCENT == 10.0
        assert core._MAX_DISCOUNT_PERCENT == 5.0

    def test_validate_margin_valid(self, core):
        """Тест валидации маржи - успешный случай"""
        # Цена 1100, себестоимость 1000 = маржа 10%
        result = core.validate_margin(price=1100, cost=1000)

        assert isinstance(result, MarginValidation)
        assert result.is_valid is True
        assert result.margin_percent == 9.09  # (100/1100)*100
        assert result.min_required == 10.0
        assert result.reason is not None  # Маржа ниже минимальной

    def test_validate_margin_high_margin(self, core):
        """Тест валидации маржи - высокая маржа"""
        # Цена 2000, себестоимость 1000 = маржа 50%
        result = core.validate_margin(price=2000, cost=1000)

        assert result.is_valid is True
        assert result.margin_percent == 50.0
        assert result.reason is None

    def test_validate_margin_low_margin(self, core):
        """Тест валидации маржи - низкая маржа"""
        # Цена 1050, себестоимость 1000 = маржа ~4.76%
        result = core.validate_margin(price=1050, cost=1000)

        assert result.is_valid is False
        assert result.margin_percent == 4.76
        assert result.reason is not None
        assert "ниже минимальной" in result.reason

    def test_validate_margin_zero_price(self, core):
        """Тест валидации маржи - нулевая цена"""
        result = core.validate_margin(price=0, cost=1000)

        assert result.is_valid is False
        assert result.margin_percent == 0.0
        assert result.reason == "Цена должна быть положительной"

    def test_validate_margin_negative_cost(self, core):
        """Тест валидации маржи - отрицательная себестоимость"""
        result = core.validate_margin(price=1000, cost=-100)

        assert result.is_valid is False
        assert result.reason == "Себестоимость не может быть отрицательной"

    def test_validate_discount_valid(self, core):
        """Тест валидации скидки - допустимая скидка"""
        result = core.validate_discount(original_price=1000, discounted_price=970)

        assert result["valid"] is True
        assert result["discount_percent"] == 3.0

    def test_validate_discount_too_high(self, core):
        """Тест валидации скидки - слишком большая скидка"""
        result = core.validate_discount(original_price=1000, discounted_price=900)

        assert result["valid"] is False
        assert result["discount_percent"] == 10.0
        assert result["max_allowed"] == 5.0
        assert "превышает максимальную" in result["reason"]

    def test_validate_discount_invalid_prices(self, core):
        """Тест валидации скидки - некорректные цены"""
        # Нулевая исходная цена
        result = core.validate_discount(original_price=0, discounted_price=100)
        assert result["valid"] is False
        assert result["reason"] == "Исходная цена должна быть положительной"

        # Нулевая цена со скидкой
        result = core.validate_discount(original_price=100, discounted_price=0)
        assert result["valid"] is False
        assert result["reason"] == "Цена со скидкой должна быть положительной"

    def test_calculate_min_price(self, core):
        """Тест расчета минимальной цены"""
        # При себестоимости 1000 и марже 10%, минимальная цена = 1111.11
        min_price = core.calculate_min_price(cost=1000)
        assert min_price == 1111.11

        # При себестоимости 0
        min_price = core.calculate_min_price(cost=0)
        assert min_price == 0.0

    def test_calculate_min_price_negative_cost(self, core):
        """Тест расчета минимальной цены - отрицательная себестоимость"""
        with pytest.raises(ValueError, match="Себестоимость не может быть отрицательной"):
            core.calculate_min_price(cost=-100)

    def test_validate_order_economics_valid(self, core):
        """Тест комплексной проверки экономики заказа - успешный случай"""
        order_data = {"price": 2000, "cost": 1000, "has_discount": False}

        result = core.validate_order_economics(order_data)

        assert result["valid"] is True
        assert len(result["validations"]) == 1
        assert result["validations"][0]["check"] == "margin"
        assert result["validations"][0]["passed"] is True
        assert result["min_price_required"] == 1111.11

    def test_validate_order_economics_with_discount(self, core):
        """Тест комплексной проверки экономики заказа - со скидкой"""
        order_data = {"price": 1900, "cost": 1000, "has_discount": True, "original_price": 2000}

        result = core.validate_order_economics(order_data)

        assert result["valid"] is True
        assert len(result["validations"]) == 2

        # Проверка маржи
        margin_check = result["validations"][0]
        assert margin_check["check"] == "margin"
        assert margin_check["passed"] is True

        # Проверка скидки
        discount_check = result["validations"][1]
        assert discount_check["check"] == "discount"
        assert discount_check["passed"] is True

    def test_validate_order_economics_invalid(self, core):
        """Тест комплексной проверки экономики заказа - неуспешный случай"""
        order_data = {"price": 1050, "cost": 1000, "has_discount": True, "original_price": 1200}

        result = core.validate_order_economics(order_data)

        assert result["valid"] is False

        # Маржа должна быть недостаточной
        margin_check = result["validations"][0]
        assert margin_check["check"] == "margin"
        assert margin_check["passed"] is False

        # Скидка слишком большая (12.5%)
        discount_check = result["validations"][1]
        assert discount_check["check"] == "discount"
        assert discount_check["passed"] is False

    def test_get_economic_limits(self, core):
        """Тест получения экономических ограничений"""
        limits = core.get_economic_limits()

        assert limits["min_margin_percent"] == 10.0
        assert limits["max_discount_percent"] == 5.0
