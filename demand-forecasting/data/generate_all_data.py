import csv
from datetime import datetime, timedelta
import random

# Set seed for reproducibility
random.seed(42)

print('Generating demand forecasting sample data...\n')

# ============================================================================
# 1. Generate bike_sales_history.csv
# ============================================================================
print('1. Generating bike_sales_history.csv...')

start_date = datetime(2024, 1, 1)
end_date = datetime(2025, 12, 31)
products = ['EBIKE-URBAN-2024', 'EBIKE-MOUNTAIN-2024']

def get_season_mult(date):
    month = date.month
    if month in [12, 1, 2]: return 'WINTER', 0.5
    elif month in [3, 4, 5]: return 'SPRING', 1.2
    elif month in [6, 7, 8]: return 'SUMMER', 1.5
    else: return 'FALL', 1.0

holidays = [
    datetime(2024, 1, 1), datetime(2024, 7, 4), datetime(2024, 11, 28),
    datetime(2024, 12, 25), datetime(2025, 1, 1), datetime(2025, 7, 4),
    datetime(2025, 11, 27), datetime(2025, 12, 25)
]

sales_data = []
txn_counter = 1

current_date = start_date
while current_date <= end_date:
    season, season_mult = get_season_mult(current_date)
    is_weekend = current_date.weekday() >= 5
    is_holiday = current_date.date() in [h.date() for h in holidays]
    
    base_sales = 2.5
    daily_sales = base_sales * season_mult
    if is_weekend: daily_sales *= 1.3
    if is_holiday: daily_sales *= 1.5
    
    num_transactions = max(1, int(random.gauss(daily_sales, 1)))
    
    for _ in range(num_transactions):
        hour = random.randint(9, 19)
        minute = random.randint(0, 59)
        timestamp = current_date.replace(hour=hour, minute=minute)
        
        product_id = random.choices(products, weights=[0.6, 0.4])[0]
        quantity = random.choices([1, 2, 3], weights=[0.7, 0.2, 0.1])[0]
        
        sales_data.append([
            f'TXN-{current_date.strftime("%Y%m%d")}-{txn_counter:03d}',
            timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            product_id,
            quantity
        ])
        txn_counter += 1
    
    current_date += timedelta(days=1)

with open('bike_sales_history.csv', 'w', newline='', encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(['transaction_id', 'timestamp', 'product_id', 'quantity_sold'])
    writer.writerows(sales_data)

print(f'   ✅ Created {len(sales_data)} transactions')

# ============================================================================
# 2. Generate maintenance_demand_history.csv (REALISTIC)
# ============================================================================
print('2. Generating maintenance_demand_history.csv...')

# Material failure rates and maintenance patterns
material_patterns = {
    'MAT-BAT-001': {'type': 'battery', 'warranty_months': 24, 'failure_rate': 0.15, 'wear': False},
    'MAT-BAT-002': {'type': 'battery_bms', 'warranty_months': 24, 'failure_rate': 0.08, 'wear': False},
    'MAT-MOT-001': {'type': 'motor', 'warranty_months': 36, 'failure_rate': 0.05, 'wear': False},
    'MAT-MOT-002': {'type': 'motor', 'warranty_months': 36, 'failure_rate': 0.05, 'wear': False},
    'MAT-MOT-003': {'type': 'controller', 'warranty_months': 24, 'failure_rate': 0.10, 'wear': False},
    'MAT-STD-001': {'type': 'wheels', 'warranty_months': 12, 'failure_rate': 0.20, 'wear': True},
    'MAT-STD-002': {'type': 'brakes', 'warranty_months': 12, 'failure_rate': 0.25, 'wear': True},
    'MAT-STD-003': {'type': 'gears', 'warranty_months': 12, 'failure_rate': 0.15, 'wear': True},
    'MAT-ELC-001': {'type': 'display', 'warranty_months': 24, 'failure_rate': 0.12, 'wear': False},
    'MAT-ELC-002': {'type': 'wiring', 'warranty_months': 24, 'failure_rate': 0.08, 'wear': False},
}

maintenance_data = []
maint_counter = 1

# Calculate total bikes sold from sales data to estimate maintenance needs
# Assume average bike age distribution: 0-36 months
# Maintenance events are proportional to fleet size

current_date = start_date
while current_date <= end_date:
    # Daily maintenance events (random but realistic)
    
    # 1. SCHEDULED_MAINTENANCE (every 500/1000/2000 miles)
    # Assume 5-10 bikes per day need scheduled service
    if random.random() < 0.3:  # 30% chance per day
        num_bikes = random.randint(1, 3)
        for _ in range(num_bikes):
            # Scheduled maintenance typically needs multiple parts
            mileage = random.choice([500, 1000, 2000, 3000])
            
            # Parts needed based on mileage
            if mileage >= 2000:
                # Major service: brakes, chain, tires
                parts = [
                    ('MAT-STD-002', random.randint(1, 2), 'Brake pad replacement'),
                    ('MAT-STD-003', 1, 'Chain replacement'),
                    ('MAT-STD-001', random.randint(1, 2), 'Tire replacement')
                ]
            elif mileage >= 1000:
                # Medium service: brakes or tires
                parts = [
                    (random.choice(['MAT-STD-002', 'MAT-STD-001']), 
                     random.randint(1, 2), 
                     'Brake or tire service')
                ]
            else:
                # Light service: brake adjustment
                parts = [('MAT-STD-002', 1, 'Brake adjustment')]
            
            for material_id, qty, note in parts:
                bike_age = random.randint(3, 36)
                maintenance_data.append([
                    f'MAINT-{maint_counter:04d}',
                    current_date.strftime('%Y-%m-%d'),
                    material_id,
                    qty,
                    'SCHEDULED_MAINTENANCE',
                    bike_age,
                    mileage,
                    f'{note} at {mileage} miles'
                ])
                maint_counter += 1
    
    # 2. WARRANTY_REPLACEMENT (within warranty period)
    # Battery and motor failures within warranty
    if random.random() < 0.05:  # 5% chance per day
        for material_id, pattern in material_patterns.items():
            if pattern['warranty_months'] >= 24 and random.random() < pattern['failure_rate'] / 365:
                bike_age = random.randint(1, pattern['warranty_months'])
                qty = 1  # Warranty replacements are typically 1 unit
                mileage = bike_age * 50  # Rough estimate: 50 miles/month
                
                maintenance_data.append([
                    f'MAINT-{maint_counter:04d}',
                    current_date.strftime('%Y-%m-%d'),
                    material_id,
                    qty,
                    'WARRANTY_REPLACEMENT',
                    bike_age,
                    mileage,
                    f'{pattern["type"].title()} warranty claim - {bike_age} months old'
                ])
                maint_counter += 1
    
    # 3. WEAR_REPLACEMENT (normal wear items)
    # Brakes, tires, chains wear out regularly
    if random.random() < 0.4:  # 40% chance per day
        wear_materials = [m for m, p in material_patterns.items() if p['wear']]
        material_id = random.choice(wear_materials)
        qty = random.randint(1, 3)
        bike_age = random.randint(6, 48)
        mileage = bike_age * 50
        
        maintenance_data.append([
            f'MAINT-{maint_counter:04d}',
            current_date.strftime('%Y-%m-%d'),
            material_id,
            qty,
            'WEAR_REPLACEMENT',
            bike_age,
            mileage,
            f'Normal wear replacement - {bike_age} months old'
        ])
        maint_counter += 1
    
    # 4. ACCIDENT_REPAIR (random crashes)
    if random.random() < 0.02:  # 2% chance per day
        # Accidents typically damage multiple parts
        num_parts = random.randint(2, 4)
        accident_materials = random.sample(list(material_patterns.keys()), num_parts)
        bike_age = random.randint(1, 36)
        mileage = bike_age * 50
        
        for material_id in accident_materials:
            qty = random.randint(1, 2)
            maintenance_data.append([
                f'MAINT-{maint_counter:04d}',
                current_date.strftime('%Y-%m-%d'),
                material_id,
                qty,
                'ACCIDENT_REPAIR',
                bike_age,
                mileage,
                f'Accident damage repair'
            ])
            maint_counter += 1
    
    # 5. WEATHER_DAMAGE (extreme weather events)
    # More common in winter (battery) and rainy seasons (brakes/electronics)
    month = current_date.month
    if month in [12, 1, 2]:  # Winter - battery issues
        if random.random() < 0.03:
            qty = random.randint(1, 2)
            bike_age = random.randint(12, 36)
            mileage = bike_age * 50
            maintenance_data.append([
                f'MAINT-{maint_counter:04d}',
                current_date.strftime('%Y-%m-%d'),
                'MAT-BAT-001',
                qty,
                'WEATHER_DAMAGE',
                bike_age,
                mileage,
                'Cold weather battery failure'
            ])
            maint_counter += 1
    elif month in [3, 4, 10, 11]:  # Rainy seasons - brake/electronics issues
        if random.random() < 0.02:
            material_id = random.choice(['MAT-STD-002', 'MAT-ELC-001'])
            qty = random.randint(1, 2)
            bike_age = random.randint(6, 36)
            mileage = bike_age * 50
            maintenance_data.append([
                f'MAINT-{maint_counter:04d}',
                current_date.strftime('%Y-%m-%d'),
                material_id,
                qty,
                'WEATHER_DAMAGE',
                bike_age,
                mileage,
                'Water damage from heavy rain'
            ])
            maint_counter += 1
    
    current_date += timedelta(days=1)

with open('maintenance_demand_history.csv', 'w', newline='', encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(['maintenance_id', 'timestamp', 'material_id', 'quantity', 
                     'maintenance_type', 'bike_age_months', 'mileage', 'notes'])
    writer.writerows(maintenance_data)

print(f'   ✅ Created {len(maintenance_data)} maintenance records')

# ============================================================================
# 3. Generate holiday_calendar.csv
# ============================================================================
print('3. Generating holiday_calendar.csv...')

holiday_data = [
    ['2024-01-01', 'New Year\'s Day', 'US', 1],
    ['2024-05-27', 'Memorial Day', 'US', 1],
    ['2024-07-04', 'Independence Day', 'US', 1],
    ['2024-09-02', 'Labor Day', 'US', 1],
    ['2024-11-28', 'Thanksgiving', 'US', 1],
    ['2024-11-29', 'Black Friday', 'US', 0],
    ['2024-12-25', 'Christmas Day', 'US', 1],
    ['2025-01-01', 'New Year\'s Day', 'US', 1],
    ['2025-05-26', 'Memorial Day', 'US', 1],
    ['2025-07-04', 'Independence Day', 'US', 1],
    ['2025-09-01', 'Labor Day', 'US', 1],
    ['2025-11-27', 'Thanksgiving', 'US', 1],
    ['2025-11-28', 'Black Friday', 'US', 0],
    ['2025-12-25', 'Christmas Day', 'US', 1]
]

with open('holiday_calendar.csv', 'w', newline='', encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(['date', 'holiday_name', 'country', 'is_major_holiday'])
    writer.writerows(holiday_data)

print(f'   ✅ Created {len(holiday_data)} holiday records')

# ============================================================================
# 4. Generate weather_seasonal_data.csv
# ============================================================================
print('4. Generating weather_seasonal_data.csv...')

regions = ['NORTHEAST', 'MIDWEST', 'WEST_COAST']
weather_data = []

weather_patterns = {
    'WINTER': {'temp': 32, 'precip': 2.5, 'wind': 15, 'humidity': 65, 'extreme': 12, 'usage': 0.45},
    'SPRING': {'temp': 56, 'precip': 3.5, 'wind': 13, 'humidity': 58, 'extreme': 5, 'usage': 0.85},
    'SUMMER': {'temp': 78, 'precip': 2.8, 'wind': 10, 'humidity': 62, 'extreme': 8, 'usage': 0.95},
    'FALL': {'temp': 58, 'precip': 3.2, 'wind': 13, 'humidity': 60, 'extreme': 6, 'usage': 0.75}
}

for year in [2024, 2025]:
    for season in ['WINTER', 'SPRING', 'SUMMER', 'FALL']:
        for region in regions:
            pattern = weather_patterns[season]
            
            # Regional variations
            temp_adj = {'NORTHEAST': 0, 'MIDWEST': -5, 'WEST_COAST': 10}[region]
            precip_adj = {'NORTHEAST': 0, 'MIDWEST': -0.5, 'WEST_COAST': -1.0}[region]
            
            weather_data.append([
                season,
                year,
                region,
                round(pattern['temp'] + temp_adj, 1),
                round(pattern['precip'] + precip_adj, 1),
                round(pattern['wind'], 1),
                round(pattern['humidity'], 1),
                pattern['extreme'],
                round(pattern['usage'], 2)
            ])

with open('weather_seasonal_data.csv', 'w', newline='', encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(['season', 'year', 'region', 'avg_temperature', 'avg_precipitation',
                     'avg_wind_speed', 'avg_humidity', 'extreme_weather_days', 'bike_usage_index'])
    writer.writerows(weather_data)

print(f'   ✅ Created {len(weather_data)} weather records')

print('\n' + '='*60)
print('✅ All sample data files generated successfully!')
print('='*60)
print(f'\nFiles created in: kiro-mcp/buildermadness#2/shared/data/')
print(f'  - bike_sales_history.csv ({len(sales_data)} records)')
print(f'  - maintenance_demand_history.csv ({len(maintenance_data)} records)')
print(f'  - holiday_calendar.csv ({len(holiday_data)} records)')
print(f'  - weather_seasonal_data.csv ({len(weather_data)} records)')
