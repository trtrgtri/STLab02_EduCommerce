import pandas as pd
from ecommerce_app import fixture

def execute_case(row):
    if row['expected_value'] == 'BLOCKED':
        return {
            'case_id': row['case_id'], 'requirement_id': row['requirement_id'],
            'scenario_id': row['scenario_id'], 'expected_value': row['expected_value'],
            'actual_value': 'Pending BA confirmation', 'status': 'BLOCKED',
            'stock_before': '', 'stock_after': ''
        }
        
    app, user, cart = fixture(row['fixture'])
    op = row['operation']
    actual, actual_error = "", ""
    before_stock = {k: p.stock for k, p in app.catalog.products.items()}
    
    try:
        if op == 'add_zero': cart.add('A', 0); actual = "NO_ERROR"
        elif op == 'add_bool': cart.add('A', True); actual = "NO_ERROR"
        elif op == 'add_merge': cart.add('A', 1); cart.add('A', 3); actual = str(cart.lines[0].quantity)
        elif op == 'auth_failure': user.authenticated = False; app.place(user, cart); actual = "NO_ERROR"
        elif op == 'auth_failure_empty': user.authenticated = False; cart.lines = []; app.place(user, cart); actual = "NO_ERROR"
        elif op == 'place_success': order = app.place(user, cart, method='ONLINE', approved=True); actual = order.status
        elif op == 'voucher_valid': order = app.place(user, cart, voucher=row['voucher']); actual = str(int(order.discount))
        elif op == 'voucher_used_twice': user.used_codes.add('SAVE10'); app.place(user, cart, voucher=row['voucher']); actual = "NO_ERROR"
        elif op == 'payment_fail_voucher':
            try: app.place(user, cart, voucher=row['voucher'], method='ONLINE', approved=False)
            except ValueError as e: actual_error = str(e)
            actual = 'CHANGED' if 'SAVE10' in user.used_codes else 'UNCHANGED'
        elif op == 'shipping_inner': actual = str(int(app.shipping.calculate(cart.subtotal(), 'inner')))
        elif op == 'shipping_outer': actual = str(int(app.shipping.calculate(cart.subtotal(), 'outer')))
        elif op == 'shipping_invalid_area': app.shipping.calculate(cart.subtotal(), 'moon'); actual = "NO_ERROR"
        elif op == 'place_stock_fail': app.catalog.products['A'].stock = 0; app.place(user, cart); actual = "NO_ERROR"
        elif op == 'place_stock_atomic':
            app.catalog.products['B'].stock = 0
            try: app.place(user, cart)
            except ValueError as e: actual_error = str(e)
        elif op == 'place_payment_fail':
            try: app.place(user, cart, method='ONLINE', approved=False)
            except ValueError as e: actual_error = str(e)
        elif op == 'place_wallet': app.place(user, cart, method='WALLET'); actual = "NO_ERROR"
        elif op == 'place_wallet_stock':
            try: app.place(user, cart, method='WALLET')
            except ValueError as e: actual_error = str(e)
    except ValueError as exc:
        actual_error = str(exc); actual = f"ERROR:{actual_error}"

    after_stock = {k: p.stock for k, p in app.catalog.products.items()}
    exp_val = row['expected_value']
    assertion = row['assertion']
    
    if assertion == 'equals': passed = actual == exp_val
    elif assertion == 'stock_unchanged':
        passed = (before_stock == after_stock) and (actual_error == row['expected_error'])
        actual = 'UNCHANGED' if before_stock == after_stock else 'CHANGED'
    elif assertion == 'voucher_state_unchanged':
        passed = (actual == 'UNCHANGED') and (actual_error == row['expected_error'])
    else: passed = False

    return {
        'case_id': row['case_id'], 'requirement_id': row['requirement_id'],
        'scenario_id': row['scenario_id'], 'expected_value': exp_val,
        'actual_value': actual if not actual_error else f"{actual} ({actual_error})",
        'status': 'PASS' if passed else 'FAIL',
        'stock_before': str(before_stock), 'stock_after': str(after_stock)
    }

if __name__ == '__main__':
    df_cases = pd.read_csv('test_cases.csv')
    results = [execute_case(row) for _, row in df_cases.iterrows()]
    df_res = pd.DataFrame(results)
    pd.set_option('display.max_colwidth', None); pd.set_option('display.width', 1000)
    print(df_res[['case_id', 'requirement_id', 'status', 'expected_value', 'actual_value']])
    df_res.to_excel('test_report.xlsx', index=False)
    print("\n--- SUMMARY ---"); print(df_res['status'].value_counts())
