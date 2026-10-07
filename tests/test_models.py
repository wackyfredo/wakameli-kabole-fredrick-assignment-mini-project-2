import pytest
from hypothesis import given, strategies as st
from decimal import Decimal
from src.models import Money, TaxContext, PAYECalculator, InvalidIncomeError

# ==========================================
# 1. BOUNDARY AND EDGE CASE TESTS
# ==========================================
@pytest.mark.parametrize("gross, allowances, status, expected_tax", [
    # --- RESIDENT BOUNDARIES ---
    # Under or exactly at nil bracket threshold (335,000 UGX)
    (335000, 0, "resident", 0),
    # Slightly above nil bracket threshold
    (335001, 0, "resident", 0), 
    # Exactly at upper limit of 20% bracket (410,000 UGX)
    (410000, 0, "resident", 15000), 
    # Right in the middle of the 30% bracket
    (500000, 0, "resident", 42000), 
    # Exactly at the 10,000,000 UGX surcharge boundary
    (10000000, 0, "resident", 2892000), 
    # Exceeding the 10,000,000 UGX boundary (triggers 40% combined marginal rate)
    (10000001, 0, "resident", 2892000),

    # --- NON-RESIDENT BOUNDARIES ---
    # First non-resident bracket (10%)
    (335000, 0, "non-resident", 33500),
    # Boundary cross to 20% bracket
    (410000, 0, "non-resident", 48500),
    # Boundary cross to 10,000,000 UGX surcharge
    (10000000, 0, "non-resident", 2925500),
])
def test_paye_boundaries(gross, allowances, status, expected_tax):
    """Verifies PAYE progressive bands at extreme regulatory thresholds."""
    ctx = TaxContext(residency_status=status)
    calc = PAYECalculator(Money(gross), Money(allowances))
    result = calc.calculate(ctx)
    assert result.tax_payable == Money(expected_tax)


# ==========================================
# 2. VALIDATION AND ERROR HANDLING TESTS
# ==========================================
def test_negative_income_raises_error():
    """Ensures input validation triggers explicit errors instead of silent failure."""
    with pytest.raises(InvalidIncomeError):
        Money(-1000)

def test_invalid_string_raises_error():
    """Ensures trash text inputs fail cleanly."""
    with pytest.raises(InvalidIncomeError):
        Money("not_a_number")


# ==========================================
# 3. PROPERTY-BASED PROPERTY TESTING
# ==========================================
@given(
    gross_val=st.integers(min_value=0, max_value=50_000_000),
    allowance_val=st.integers(min_value=0, max_value=10_000_000)
)
def test_paye_invariants_with_hypothesis(gross_val, allowance_val):
    """Property test validating system invariant rules for PAYE calculations."""
    ctx = TaxContext(residency_status="resident")
    gross = Money(gross_val)
    allowances = Money(allowance_val)
    
    calc = PAYECalculator(gross, allowances)
    result = calc.calculate(ctx)
    
    # Invariant 1: Tax payable can never be negative
    assert result.tax_payable.amount >= Decimal('0')
    
    # Invariant 2: Total tax payable can never strictly exceed total taxable income
    assert result.tax_payable.amount <= (gross + allowances).amount
