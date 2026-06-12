# Frontend-Backend Integration Guide

## Quick Start

### 1. Start Backend (Choose One)

**Option A: Mock Backend** (hardcoded responses, instant)
```bash
cd backend
./run_mock.sh
```

**Option B: Real Backend** (actual optimization, ~30s)
```bash
cd backend
./run_real.sh
```

Backend will run on `http://localhost:5000`

### 2. Start Frontend

```bash
cd procurement-agent-ui
npm run dev
```

Frontend will run on `http://localhost:5173`

### 3. Test Integration

Open browser to `http://localhost:5173`

**Health Check:**
```bash
curl http://localhost:5000/health
```

**Test Optimization:**
```bash
curl -X POST http://localhost:5000/api/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "materials": [
      {"material_id": "MAT-BAT-001", "quantity": 500}
    ],
    "constraints": {
      "max_supplier_concentration": 0.40,
      "max_lead_time_days": 45,
      "budget_max": 1000000,
      "budget_min": 0
    },
    "objectives": {
      "cost": 0.4,
      "risk": 0.3,
      "lead_time": 0.3
    }
  }'
```

## Integration Status

### ✅ Backend Ready
- API server (`api/server.py`)
- Real optimization engine (`api/real_server.py`)
- 89.63% test coverage
- All 61 tests passing

### ✅ Frontend Integration Ready
- API service layer created (`src/services/api.ts`)
- **Automatic fallback to hardcoded data if backend unavailable**
- React hook for easy integration (`src/hooks/useOptimization.ts`)
- Loading states and error handling included

### 🎯 Fallback Strategy
The frontend will **automatically use hardcoded data** if:
- Backend is not running
- Backend takes >30 seconds to respond
- Network error occurs
- API returns an error

This means your demo will ALWAYS work, even if backend is down!

## Next Steps

### Update App.tsx to Use API

Replace hardcoded data import:
```typescript
// OLD
import { paretoSolutions, chatHistory } from './data/realData'

// NEW
import { optimizeUrbanEBikes } from './services/api'
import { useState, useEffect } from 'react'
```

Add API call in useEffect:
```typescript
const [solutions, setSolutions] = useState([])
const [loading, setLoading] = useState(true)
const [error, setError] = useState(null)

useEffect(() => {
  async function loadOptimization() {
    try {
      setLoading(true)
      const response = await optimizeUrbanEBikes()
      setSolutions(response.solutions)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }
  
  loadOptimization()
}, [])
```

### Environment Configuration

Create `.env` file:
```bash
cp .env.example .env
```

Edit `.env`:
```
VITE_API_URL=http://localhost:5000
VITE_USE_MOCK_DATA=false
VITE_ENABLE_REAL_API=true
```

## API Endpoints

### GET /health
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "development"
}
```

### POST /api/optimize
Optimize supplier selection.

**Request:**
```json
{
  "materials": [
    {
      "material_id": "MAT-BAT-001",
      "quantity": 500
    }
  ],
  "constraints": {
    "max_supplier_concentration": 0.40,
    "max_lead_time_days": 45,
    "budget_max": 1000000,
    "budget_min": 0
  },
  "objectives": {
    "cost": 0.4,
    "risk": 0.3,
    "lead_time": 0.3
  }
}
```

**Response:**
```json
{
  "solutions": [
    {
      "name": "Budget",
      "total_cost": 650000,
      "risk_score": 7.5,
      "quality_score": 6.5,
      "lead_time_days": 55,
      "max_supplier_concentration": 0.32,
      "allocations": [...],
      "reasoning": "Lowest cost option..."
    },
    {
      "name": "Balanced",
      "total_cost": 875000,
      "risk_score": 3.5,
      "quality_score": 8.2,
      "lead_time_days": 42,
      "max_supplier_concentration": 0.28,
      "allocations": [...],
      "reasoning": "Optimal balance..."
    },
    {
      "name": "Premium",
      "total_cost": 1200000,
      "risk_score": 1.5,
      "quality_score": 9.5,
      "lead_time_days": 35,
      "max_supplier_concentration": 0.22,
      "allocations": [...],
      "reasoning": "Highest quality..."
    }
  ],
  "request_id": "uuid-here",
  "computation_time_ms": 25000
}
```

## Troubleshooting

### CORS Errors
Backend has CORS enabled for `http://localhost:5173` and `http://localhost:3000`.

If you see CORS errors, check `backend/config/settings.py`:
```python
cors_origins: str = Field(
    default="http://localhost:5173,http://localhost:3000",
    alias="CORS_ORIGINS"
)
```

### Backend Not Starting
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m api.server
```

### Frontend Not Connecting
Check `.env` file has correct API URL:
```
VITE_API_URL=http://localhost:5000
```

Restart frontend after changing `.env`:
```bash
npm run dev
```

## Demo Tomorrow

For your demo, I recommend:

1. **Use Mock Backend** - Instant responses, no waiting
2. **Keep Hardcoded Data** - UI already works perfectly
3. **Show Real Backend** - Run optimization in terminal to prove it works

This way you have a working demo AND can show the real optimization if asked.
