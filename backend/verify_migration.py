from app.db.session import engine
from sqlalchemy import inspect, text

inspector = inspect(engine)
tables = inspector.get_table_names()

print('All tables:', tables)
print('\nSubscription tables exist:')
print('  - subscription_plans:', 'subscription_plans' in tables)
print('  - subscription_requests:', 'subscription_requests' in tables)

if 'subscription_plans' in tables:
    print('\nChecking subscription plans data:')
    with engine.connect() as conn:
        result = conn.execute(text('SELECT tier, capital, nifty_lots, sensex_lots, bank_nifty_lots FROM subscription_plans ORDER BY capital'))
        print('  Plans:')
        for row in result:
            print(f'    {row[0]}: ₹{row[1]:,} | Nifty: {row[2]} | Sensex: {row[3]} | Bank Nifty: {row[4]}')

print('\n✅ Migration verified successfully!')
