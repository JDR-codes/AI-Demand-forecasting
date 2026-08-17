# fastapi_app/routes/mock_router.py
from fastapi import APIRouter
from datetime import datetime, timedelta
import random

router = APIRouter(prefix="/mock", tags=["Mock APIs"])

@router.get("/supplier")
def get_suppliers():
    """Mock supplier data"""
    suppliers = [
        {
            "supplier": "ABC Ltd",
            "sku": "SKU001",
            "lead_time": 5,
            "price": 120.00,
            "min_order": 10
        },
        {
            "supplier": "XYZ Ltd", 
            "sku": "SKU002",
            "lead_time": 7,
            "price": 90.00,
            "min_order": 20
        },
        {
            "supplier": "PQR Corp",
            "sku": "SKU003",
            "lead_time": 3,
            "price": 150.00,
            "min_order": 5
        },
        {
            "supplier": "LMN Industries",
            "sku": "SKU004",
            "lead_time": 10,
            "price": 75.00,
            "min_order": 50
        }
    ]
    return suppliers

@router.get("/products")
def get_products():
    """Mock product data"""
    products = [
        {"sku": "SKU001", "name": "Product A", "category": "Electronics", "price": 100.00},
        {"sku": "SKU002", "name": "Product B", "category": "Furniture", "price": 200.00},
        {"sku": "SKU003", "name": "Product C", "category": "Clothing", "price": 50.00},
        {"sku": "SKU004", "name": "Product D", "category": "Food", "price": 25.00},
    ]
    return products

@router.get("/sales")
def get_sales():
    """Mock sales data"""
    base_date = datetime(2026, 7, 1)
    sales = []
    for i in range(30):
        date = base_date + timedelta(days=i)
        sales.append({
            "Date": date.strftime("%Y-%m-%d"),
            "SKU": f"SKU{str(random.randint(1, 4)).zfill(3)}",
            "Demand": random.randint(50, 500),
            "Revenue": round(random.uniform(1000, 10000), 2),
            "Units": random.randint(10, 200)
        })
    return sales

@router.get("/inventory")
def get_inventory():
    """Mock inventory data"""
    inventories = []
    warehouses = ["WH001", "WH002", "WH003"]
    for warehouse in warehouses:
        for sku_num in range(1, 5):
            inventories.append({
                "warehouse": warehouse,
                "sku": f"SKU{str(sku_num).zfill(3)}",
                "stock": random.randint(100, 1000),
                "reorder_level": random.randint(50, 200),
                "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
    return inventories

@router.get("/weather")
def get_weather():
    """Mock weather data"""
    base_date = datetime(2026, 7, 1)
    weather_data = []
    locations = ["NYC", "LA", "CHI", "MIA"]
    
    for i in range(14):
        date = base_date + timedelta(days=i)
        for location in locations:
            weather_data.append({
                "Date": date.strftime("%Y-%m-%d"),
                "Location": location,
                "Temperature": round(random.uniform(15, 35), 1),
                "Humidity": random.randint(30, 90),
                "Precipitation": round(random.uniform(0, 10), 1),
                "WindSpeed": round(random.uniform(0, 20), 1)
            })
    return weather_data

@router.get("/orders")
def get_orders():
    """Mock order data"""
    orders = []
    statuses = ["pending", "processing", "shipped", "delivered", "cancelled"]
    
    for i in range(50):
        order_date = datetime.now() - timedelta(days=random.randint(0, 30))
        orders.append({
            "order_id": f"ORD{str(i+1).zfill(6)}",
            "customer_id": f"CUST{str(random.randint(1, 20)).zfill(4)}",
            "order_date": order_date.strftime("%Y-%m-%d"),
            "total_amount": round(random.uniform(50, 500), 2),
            "status": random.choice(statuses),
            "sku": f"SKU{str(random.randint(1, 4)).zfill(3)}",
            "quantity": random.randint(1, 10)
        })
    return orders

@router.get("/customers")
def get_customers():
    """Mock customer data"""
    customers = []
    for i in range(20):
        customers.append({
            "customer_id": f"CUST{str(i+1).zfill(4)}",
            "name": f"Customer {i+1}",
            "email": f"customer{i+1}@example.com",
            "phone": f"+1-555-{str(random.randint(1000, 9999))}",
            "city": random.choice(["New York", "Los Angeles", "Chicago", "Miami", "Austin"]),
            "join_date": (datetime.now() - timedelta(days=random.randint(1, 365))).strftime("%Y-%m-%d"),
            "total_spent": round(random.uniform(100, 10000), 2)
        })
    return customers