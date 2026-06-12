"""
Unit tests for the demand forecasting module.
Tests data loading, time series preparation, mock forecast generation,
explainability stats, and the forecast API server endpoints.
"""

import os
import sys
import json
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from pathlib import Path
import urllib.request

# Add agent directory to path
AGENT_DIR = Path(__file__).parent.parent / 'agents'
sys.path.insert(0, str(AGENT_DIR))

from chronos_forecasting_agent import (
    load_csv,
    prepare_material_timeseries,
    generate_mock_forecast,
    BIKE_SALES_FILE,
    MAINTENANCE_FILE,
    BOM_FILE,
    MATERIALS_FILE,
)


class TestLoadCSV:
    """Tests for CSV loading utility."""

    def test_load_bike_sales(self):
        data = load_csv(BIKE_SALES_FILE)
        assert len(data) > 0
        assert 'transaction_id' in data[0]
        assert 'timestamp' in data[0]
        assert 'product_id' in data[0]
        assert 'quantity_sold' in data[0]

    def test_load_materials(self):
        data = load_csv(MATERIALS_FILE)
        assert len(data) > 0
        assert 'material_id' in data[0]
        assert 'name' in data[0]
        assert 'category' in data[0]

    def test_load_bom(self):
        data = load_csv(BOM_FILE)
        assert len(data) > 0
        assert 'product_id' in data[0]
        assert 'material_id' in data[0]
        assert 'quantity_required' in data[0]

    def test_load_maintenance(self):
        data = load_csv(MAINTENANCE_FILE)
        assert len(data) > 0
        assert 'material_id' in data[0]
        assert 'quantity' in data[0]
        assert 'maintenance_type' in data[0]


class TestPrepareMaterialTimeseries:
    """Tests for time series preparation from sales + maintenance data."""

    def test_valid_material(self):
        """MAT-BAT-001 should have demand from both sales and maintenance."""
        df = prepare_material_timeseries('MAT-BAT-001')
        assert not df.empty
        assert 'timestamp' in df.columns
        assert 'target' in df.columns
        assert len(df) > 30  # should span many days
        assert df['target'].sum() > 0

    def test_invalid_material_returns_empty(self):
        """Non-existent material should return empty DataFrame."""
        df = prepare_material_timeseries('FAKE-MAT-999')
        assert df.empty

    def test_product_id_filter(self):
        """Filtering by product_id should give <= demand vs ALL."""
        df_all = prepare_material_timeseries('MAT-BAT-001')
        df_urban = prepare_material_timeseries('MAT-BAT-001', product_id='URBAN-COMMUTER')
        # Filtered should have less or equal total demand
        assert df_urban['target'].sum() <= df_all['target'].sum()

    def test_no_missing_dates(self):
        """Time series should have no gaps (filled with 0)."""
        df = prepare_material_timeseries('MAT-BAT-001')
        if len(df) > 1:
            date_diff = df['timestamp'].diff().dropna()
            assert (date_diff == pd.Timedelta(days=1)).all(), "Time series has date gaps"


class TestGenerateMockForecast:
    """Tests for mock forecast generation."""

    @pytest.fixture
    def context_df(self):
        """Create a realistic context DataFrame for testing."""
        dates = pd.date_range('2024-01-01', periods=90, freq='D')
        np.random.seed(42)
        values = np.random.poisson(lam=10, size=90).astype(float)
        return pd.DataFrame({
            'timestamp': dates,
            'target': values,
            'id': 'MAT-BAT-001'
        })

    def test_output_shape(self, context_df):
        pred_length = 7
        result = generate_mock_forecast(context_df, pred_length, [0.1, 0.5, 0.9])
        assert len(result) == pred_length
        assert 'timestamp' in result.columns
        assert '0.1' in result.columns
        assert '0.5' in result.columns
        assert '0.9' in result.columns

    def test_quantile_ordering(self, context_df):
        """p10 <= p50 <= p90 for every row."""
        result = generate_mock_forecast(context_df, 14, [0.1, 0.5, 0.9])
        for _, row in result.iterrows():
            assert row['0.1'] <= row['0.5'] <= row['0.9']

    def test_non_negative(self, context_df):
        """All forecast values should be >= 0."""
        result = generate_mock_forecast(context_df, 14, [0.1, 0.5, 0.9])
        assert (result['0.1'] >= 0).all()
        assert (result['0.5'] >= 0).all()
        assert (result['0.9'] >= 0).all()

    def test_date_range(self, context_df):
        """Forecast dates should start from today."""
        result = generate_mock_forecast(context_df, 7, [0.1, 0.5, 0.9])
        from datetime import date
        today = pd.Timestamp(date.today())
        assert result['timestamp'].iloc[0] == today


class TestExplainability:
    """Tests for explainability statistics computed in the server."""

    @pytest.fixture
    def context_df(self):
        dates = pd.date_range('2024-01-01', periods=180, freq='D')
        np.random.seed(42)
        # Create data with a slight upward trend
        values = np.random.poisson(lam=10, size=180).astype(float)
        values[90:] += 3  # bump second half
        return pd.DataFrame({'timestamp': dates, 'target': values})

    def test_trend_detection(self, context_df):
        """Second half is higher, so trend should be 'increasing'."""
        ts = context_df['target']
        half = len(ts) // 2
        first_avg = float(ts.iloc[:half].mean())
        second_avg = float(ts.iloc[half:].mean())
        trend_pct = round((second_avg - first_avg) / first_avg * 100, 1)
        assert trend_pct > 5, "Expected increasing trend"

    def test_cv_calculation(self, context_df):
        """Coefficient of variation should be positive and reasonable."""
        ts = context_df['target']
        cv = round(float(ts.std()) / float(ts.mean()), 2)
        assert cv > 0
        assert cv < 5  # shouldn't be absurdly high for Poisson data

    def test_seasonal_strength(self, context_df):
        """Seasonal strength should be non-negative."""
        df = context_df.copy()
        df['dow'] = df['timestamp'].dt.dayofweek
        dow_avg = df.groupby('dow')['target'].mean()
        hist_mean = float(df['target'].mean())
        seasonal_strength = round(float(dow_avg.std()) / hist_mean, 2) if hist_mean > 0 else 0
        assert seasonal_strength >= 0

    def test_momentum(self, context_df):
        """Recent momentum should reflect the bump in second half."""
        ts = context_df['target']
        hist_mean = float(ts.mean())
        recent_avg = float(ts.iloc[-30:].mean())
        momentum_pct = round((recent_avg - hist_mean) / hist_mean * 100, 1)
        # Second half has +3 bump, so recent should be above average
        assert momentum_pct > 0


class TestForecastAPI:
    """Integration tests against the running forecast server on port 8888."""

    BASE_URL = 'http://localhost:8888'

    def _get(self, path):
        req = urllib.request.Request(f'{self.BASE_URL}{path}')
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode())

    def _post(self, path, data):
        body = json.dumps(data).encode()
        req = urllib.request.Request(
            f'{self.BASE_URL}{path}',
            data=body,
            headers={'Content-Type': 'application/json'},
            method='POST',
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())

    def test_health(self):
        result = self._get('/api/health')
        assert result['status'] == 'healthy'
        assert 'seasonal-analysis' in result['agents']
        assert 'chronos-forecast' in result['agents']

    def test_forecast_valid_material(self):
        result = self._post('/api/forecast', {
            'material_id': 'MAT-BAT-001',
            'prediction_length': 7,
        })
        assert result['status'] == 'success'
        assert result['material_id'] == 'MAT-BAT-001'
        assert len(result['forecast']) == 7
        # Check forecast structure
        point = result['forecast'][0]
        assert 'date' in point
        assert 'p10' in point
        assert 'p50' in point
        assert 'p90' in point
        # Quantile ordering
        assert point['p10'] <= point['p50'] <= point['p90']
        # Explainability present
        assert 'explainability' in result
        assert 'trend_direction' in result['explainability']

    def test_forecast_missing_material_id(self):
        """POST without material_id should return 400."""
        try:
            self._post('/api/forecast', {'prediction_length': 7})
            assert False, "Expected HTTP error"
        except urllib.error.HTTPError as e:
            assert e.code == 400

    def test_forecast_invalid_material(self):
        """Non-existent material should return 404."""
        try:
            self._post('/api/forecast', {
                'material_id': 'FAKE-999',
                'prediction_length': 7,
            })
            assert False, "Expected HTTP error"
        except urllib.error.HTTPError as e:
            assert e.code == 404
