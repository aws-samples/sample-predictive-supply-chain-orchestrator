# Demand Forecasting Agent - Sample Data

This document describes the sample datasets created for the Demand Forecasting Agent.

## Generated Files (4 new datasets)

### 1. bike_sales_history.csv
**Purpose:** Master sales transaction log (product-level)

**Records:** 1,782 transactions over 24 months (Jan 2024 - Dec 2025)

**Schema:**
- `transaction_id` (VARCHAR): Unique transaction ID (format: TXN-YYYYMMDD-###)
- `timestamp` (DATETIME): Date and time of sale
- `product_id` (VARCHAR): E-bike model (EBIKE-URBAN-2024 or EBIKE-MOUNTAIN-2024)
- `quantity_sold` (INTEGER): Number of bikes sold in transaction

**Data Characteristics:**
- Urban bikes: ~60% of sales
- Mountain bikes: ~40% of sales
- Seasonal patterns:
  - Winter: 50% of baseline
  - Spring: 120% of baseline
  - Summer: 150% of baseline (peak season)
  - Fall: 100% of baseline
- Weekend boost: +30% sales
- Holiday boost: +50% sales
- Business hours: 9am - 7pm

**Sample:**
```csv
transaction_id,timestamp,product_id,quantity_sold
TXN-20240101-001,2024-01-01 13:15:00,EBIKE-URBAN-2024,2
TXN-20240102-002,2024-01-02 19:47:00,EBIKE-MOUNTAIN-2024,1
```

---

### 2. maintenance_demand_history.csv
**Purpose:** Direct material demand from repairs and maintenance (not from bike production)

**Records:** 1,207 maintenance events over 24 months

**Schema:**
- `maintenance_id` (VARCHAR): Unique maintenance ID (format: MAINT-####)
- `timestamp` (DATE): Date of maintenance demand
- `material_id` (VARCHAR): Component ID (FK to materials.csv)
- `quantity` (INTEGER): Quantity needed (realistic: 1-3 units)
- `maintenance_type` (VARCHAR): Type of maintenance
  - SCHEDULED_MAINTENANCE: Regular service intervals (500/1000/2000/3000 miles)
  - WEAR_REPLACEMENT: Normal wear items (brakes, tires, chains)
  - ACCIDENT_REPAIR: Crash damage repairs
  - WEATHER_DAMAGE: Extreme weather-related failures
  - WARRANTY_REPLACEMENT: Warranty claims (removed - now part of scheduled)
- `bike_age_months` (INTEGER): Age of bike being serviced (1-48 months)
- `mileage` (INTEGER): Bike mileage at time of service
- `notes` (TEXT): Description of maintenance activity

**Data Characteristics:**
- **Scheduled Maintenance (72.8%):** Most common - regular service intervals
  - 500 miles: Brake adjustment
  - 1000 miles: Brake or tire service
  - 2000+ miles: Major service (brakes, chain, tires)
- **Wear Replacement (23.2%):** Normal wear items
  - Brakes (MAT-STD-002): Most frequent - 465 times
  - Wheels/Tires (MAT-STD-001): 376 times
  - Gears/Chain (MAT-STD-003): 335 times
- **Accident Repair (2.8%):** Random crashes affecting multiple parts
- **Weather Damage (1.2%):** Seasonal patterns
  - Winter: Battery failures in cold weather
  - Rainy seasons: Brake and electronics issues
- **Realistic quantities:** 1-3 units per order (avg: 1.5)
- **Bike age:** 3-48 months (avg: 21 months)

**Sample:**
```csv
maintenance_id,timestamp,material_id,quantity,maintenance_type,bike_age_months,mileage,notes
MAINT-0002,2024-01-03,MAT-STD-002,2,SCHEDULED_MAINTENANCE,8,2000,Brake pad replacement at 2000 miles
MAINT-0011,2024-01-11,MAT-BAT-001,1,WEATHER_DAMAGE,24,1200,Cold weather battery failure
MAINT-0012,2024-01-12,MAT-STD-002,1,WEAR_REPLACEMENT,7,350,Normal wear replacement - 7 months old
```

---

### 3. holiday_calendar.csv
**Purpose:** Reference data for holiday enrichment

**Records:** 14 holidays (2024-2025)

**Schema:**
- `date` (DATE): Holiday date
- `holiday_name` (VARCHAR): Holiday name
- `country` (VARCHAR): Country code
- `is_major_holiday` (BOOLEAN): 1 = major holiday, 0 = shopping day

**Holidays Included:**
- New Year's Day
- Memorial Day
- Independence Day
- Labor Day
- Thanksgiving
- Black Friday
- Christmas Day

**Sample:**
```csv
date,holiday_name,country,is_major_holiday
2024-01-01,New Year's Day,US,1
2024-11-29,Black Friday,US,0
```

---

### 4. weather_seasonal_data.csv
**Purpose:** Seasonal weather patterns by region (for bike usage correlation)

**Records:** 24 records (4 seasons × 2 years × 3 regions)

**Schema:**
- `season` (VARCHAR): WINTER, SPRING, SUMMER, FALL
- `year` (INTEGER): Year
- `region` (VARCHAR): NORTHEAST, MIDWEST, WEST_COAST
- `avg_temperature` (DECIMAL): Average temperature (°F)
- `avg_precipitation` (DECIMAL): Average precipitation (inches)
- `avg_wind_speed` (DECIMAL): Average wind speed (mph)
- `avg_humidity` (DECIMAL): Average humidity (%)
- `extreme_weather_days` (INTEGER): Days with extreme weather
- `bike_usage_index` (DECIMAL): Seasonal bike usage factor (0.00-1.00)

**Regional Variations:**
- NORTHEAST: Baseline temperatures
- MIDWEST: -5°F colder, -0.5" less precipitation
- WEST_COAST: +10°F warmer, -1.0" less precipitation

**Bike Usage Index:**
- Winter: 0.45 (low usage)
- Spring: 0.85 (high usage)
- Summer: 0.95 (peak usage)
- Fall: 0.75 (moderate usage)

**Sample:**
```csv
season,year,region,avg_temperature,avg_precipitation,avg_wind_speed,avg_humidity,extreme_weather_days,bike_usage_index
WINTER,2024,NORTHEAST,32,2.5,15,65,12,0.45
SUMMER,2024,WEST_COAST,88,1.8,10,62,8,0.95
```

---

## Existing Files (Used by Agent)

These files already exist in `shared/data/` and are referenced by the demand forecasting agent:

### 5. materials.csv (18 materials)
Component catalog with material details (name, category, cost, criticality)

### 6. bom.csv (32 BOM entries)
Bill of Materials - defines which materials are needed for each bike model

### 7. production_schedule.csv (12 schedules)
Planned production schedules for Q1-Q2 2026

---

## Agent Data Flow

```
Input Data:
├── bike_sales_history.csv          ← Product-level sales (clean transactional data)
├── maintenance_demand_history.csv  ← Direct material demand (repairs/maintenance)
├── bom.csv                         ← Assembly recipes (existing)
└── materials.csv                   ← Component catalog (existing)

Reference Data (for enrichment):
├── holiday_calendar.csv            ← Holiday lookups
└── weather_seasonal_data.csv       ← Weather patterns by season/region

Agent Processing (User Story 1):
1. Load bike_sales_history.csv
2. Enrich with season, is_weekend, is_holiday (derived from timestamp)
3. Explode via BOM to get material demand from production
4. Load maintenance_demand_history.csv (direct material demand)
5. Combine production + maintenance demand
6. Perform seasonal analysis
7. Output: seasonal_analysis.csv (agent-generated)

Agent Processing (User Story 3):
1. Use combined material demand as input to Chronos-2
2. Include weather covariates from weather_seasonal_data.csv
3. Generate forecasts with confidence intervals
4. Output: demand_forecast.csv (agent-generated)
```

---

## Data Statistics

**Sales Summary:**
- Total transactions: 1,782
- Time period: 24 months (Jan 2024 - Dec 2025)
- Products: 2 E-bike models
- Average transactions per day: ~2.4

**Maintenance Summary:**
- Total maintenance events: 1,207
- Scheduled maintenance: 879 (72.8%) - Regular service intervals
- Wear replacements: 280 (23.2%) - Normal wear items
- Accident repairs: 34 (2.8%) - Crash damage
- Weather damage: 14 (1.2%) - Seasonal failures
- Realistic quantities: 1-3 units per order (avg: 1.5)
- Materials covered: Focus on high-wear items (brakes, tires, chains)

**Coverage:**
- All 18 materials covered through BOM explosion
- All 4 seasons represented
- 3 geographic regions
- 2 years of historical data

---

## Regenerating Data

To regenerate the sample data:

```bash
cd kiro-mcp/buildermadness#2/shared/data
python generate_all_data.py
```

This will overwrite the existing CSV files with new randomly generated data (using seed=42 for reproducibility).

---

## Next Steps

With this sample data in place, the Demand Forecasting Agent can:

1. **User Story 1:** Load and analyze historical data by season
2. **User Story 3:** Use Chronos-2 to generate material demand forecasts
3. **User Story 15:** Validate data quality and completeness

The data is ready for agent development and testing.
