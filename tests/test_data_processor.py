"""Tests DataProcessor class."""

import pytest

from payload.data_handling.data_processor import DataProcessor


@pytest.fixture
def data_processor():
    return DataProcessor()


class TestDataProcessor:
    """Tests the DataProcessor class"""
