from abc import ABC, abstractmethod
from decimal import Decimal, ROUND_HALF_UP
from typing import Any, List

# ==========================================
# 1. CUSTOM EXCEPTION HIERARCHY
# ==========================================
class TaxError(Exception):
    """Base exception for all tax-related errors."""
    pass

class InvalidIncomeError(TaxError):
    """Raised when income or amount values are negative or invalid."""
    pass

class NoScheduleForDateError(TaxError):
    """Raised when a tax schedule is requested for an unsupported timeline."""
    pass

# ==========================================
# 2. MONEY VALUE OBJECT (UGX)
# ==========================================
class Money:
    """Immutable Value Object to handle UGX currency using Decimal."""
    
    def __init__(self, amount: Any) -> None:
        try:
            # Round immediately to whole numbers for UGX currency rules
            self._amount = Decimal(str(amount)).quantize(Decimal('1'), rounding=ROUND_HALF_UP)
        except Exception:
            raise InvalidIncomeError(f"Invalid monetary value: {amount}")
        
        if self._amount < 0:
            raise InvalidIncomeError("Monetary amounts cannot be negative.")

    @property
    def amount(self) -> Decimal:
        return self._amount

    def __add__(self, other: 'Money') -> 'Money':
        if not isinstance(other, Money):
            return NotImplemented
        return Money(self._amount + other.amount)

    def __sub__(self, other: 'Money') -> 'Money':
        if not isinstance(other, Money):
            return NotImplemented
        # Ensure we don't end up with negative currency values unexpectedly
        result = self._amount - other.amount
        if result < 0:
            return Money(0)
        return Money(result)

    def __mul__(self, factor: Any) -> 'Money':
        try:
            factor_dec = Decimal(str(factor))
            return Money(self._amount * factor_dec)
        except Exception:
            return NotImplemented

    def __lt__(self, other: 'Money') -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self._amount < other.amount

    def __eq__(self, other: Any) -> bool:
        if not isinstance(other, Money):
            return NotImplemented
        return self._amount == other.amount

    def __repr__(self) -> str:
        return f"UGX {int(self._amount):,}"

# ==========================================
# 3. ABSTRACTION & CONTEXT
# ==========================================
class TaxContext:
    """Holds configuration/state needed for calculations."""
    def __init__(self, residency_status: str = "resident") -> None:
        self.residency_status = residency_status.lower()

class TaxResult:
    """Encapsulates the output of a tax computation."""
    def __init__(self, tax_payable: Money, details: dict) -> None:
        self.tax_payable = tax_payable
        self.details = details

class Tax(ABC):
    """Abstract Base Class for all tax types."""
    
    @abstractmethod
    def calculate(self, ctx: TaxContext) -> TaxResult:
        """Execute tax calculation. Must never fail silently."""
        pass

# ==========================================
# 4. REQUIREMENT 1: PAYE CALCULATOR
# ==========================================
class PAYECalculator(Tax):
    """Calculates Pay As You Earn (PAYE) tax based on URA monthly brackets."""

    def __init__(self, gross_pay: Money, allowances: Money) -> None:
        self.taxable_income = gross_pay + allowances

    def calculate(self, ctx: TaxContext) -> TaxResult:
        income = self.taxable_income.amount
        tax = Decimal('0')
        details = {"taxable_income": Money(income)}

        if ctx.residency_status == "resident":
            if income <= Decimal('335000'):
                tax = Decimal('0')
            elif income <= Decimal('410000'):
                tax = (income - Decimal('335000')) * Decimal('0.20')
            elif income <= Decimal('10000000'):
                tax = Decimal('15000') + (income - Decimal('410000')) * Decimal('0.30')
            else:
                base_tax = Decimal('15000') + (Decimal('10000000') - Decimal('410000')) * Decimal('0.30')
                excess_10m = income - Decimal('10000000')
                tax = base_tax + (excess_10m * Decimal('0.30')) + (excess_10m * Decimal('0.10'))

        elif ctx.residency_status == "non-resident":
            if income <= Decimal('335000'):
                tax = income * Decimal('0.10')
            elif income <= Decimal('410000'):
                tax = Decimal('33500') + (income - Decimal('335000')) * Decimal('0.20')
            elif income <= Decimal('10000000'):
                tax = Decimal('48500') + (income - Decimal('410000')) * Decimal('0.30')
            else:
                base_tax = Decimal('48500') + (Decimal('10000000') - Decimal('410000')) * Decimal('0.30')
                excess_10m = income - Decimal('10000000')
                tax = base_tax + (excess_10m * Decimal('0.30')) + (excess_10m * Decimal('0.10'))
        else:
            raise TaxError(f"Unsupported residency status: {ctx.residency_status}")

        tax_payable = Money(tax)
        details["paye_tax"] = tax_payable
        details["residency"] = ctx.residency_status
        
        return TaxResult(tax_payable, details)


# 5. REQUIREMENT 2: PAYROLL PIPELINE

class PayrollPipeline:
    """Manages ordered deductions for employee payroll pipelines."""
    
    def __init__(self, gross_pay: Money, allowances: Money, local_service_tax: Money) -> None:
        self.gross_pay = gross_pay
        self.allowances = allowances
        self.lst = local_service_tax

    def process(self, ctx: TaxContext) -> dict:
        # NSSF Calculation (Employee: 5%, Employer: 10%)
        nssf_employee = self.gross_pay * Decimal('0.05')
        nssf_employer = self.gross_pay * Decimal('0.10')
        
        # Local Service Tax is subtracted from salary BEFORE calculating PAYE
        adjusted_gross = self.gross_pay - self.lst
        paye_calc = PAYECalculator(adjusted_gross, self.allowances)
        paye_result = paye_calc.calculate(ctx)
        paye_tax = paye_result.tax_payable
        
        # Net Pay = Gross + Allowances - NSSF Employee - Local Service Tax - PAYE
        total_deductions = nssf_employee + self.lst + paye_tax
        net_pay = (self.gross_pay + self.allowances) - total_deductions
        
        return {
            "gross_pay": self.gross_pay,
            "allowances": self.allowances,
            "nssf_employee": nssf_employee,
            "nssf_employer": nssf_employer,
            "local_service_tax": self.lst,
            "paye_tax": paye_tax,
            "net_pay": net_pay
        }

# ==========================================
# 6. REQUIREMENT 3: VAT MODULE
# ==========================================
class VATInvoice:
    """Models Value Added Tax processing for billing entries."""
    
    def __init__(self, amount: Money, category: str = "standard") -> None:
        self.amount = amount
        self.category = category.lower()

    def calculate_vat(self) -> Money:
        if self.category == "standard":
            return self.amount * Decimal('0.18')
        elif self.category in ["zero-rated", "exempt"]:
            return Money(0)
        else:
            raise TaxError(f"Unknown VAT category: {self.category}")

# ==========================================
# 7. REQUIREMENT 4: CORPORATE INCOME TAX
# ==========================================
class CorporateTaxCalculator(Tax):
    """Applies corporate taxation on business net profits."""
    
    def __init__(self, revenue: Money, allowable_deductions: Money) -> None:
        self.revenue = revenue
        self.deductions = allowable_deductions

    def calculate(self, ctx: TaxContext) -> TaxResult:
        # Chargeable Income = Revenue - Allowable Deductions
        chargeable_income = self.revenue - self.deductions
        
        if ctx.residency_status == "resident":
            rate = Decimal('0.30')  # 30% standard rate for residents
        else:
            rate = Decimal('0.30')  # Default standard corporate rate
            
        tax_payable = chargeable_income * rate
        details = {
            "revenue": self.revenue,
            "allowable_deductions": self.deductions,
            "chargeable_income": chargeable_income,
            "rate": rate
        }
        return TaxResult(tax_payable, details)
