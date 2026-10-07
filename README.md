# Uganda Tax Engine — Mini-Project 2

An extensible, testable tax evaluation framework modeled to follow the official Uganda Revenue Authority (URA) tax rules. Handles currency tracking using immutable high-precision integer decimal representations.

## Key System Features
* **PAYE Progressive Bands**: Fully implements the tiered brackets for both resident and non-resident categories.
* **Surcharge Handling**: Dynamically levies the 10% premium calculation on individual monthly values exceeding 10,000,000 UGX.
* **Payroll Execution Pipeline**: Systematically evaluates ordered items (NSSF deductions, Local Service Tax modifications, and net payout structures).

## Verification Strategy
Execute tests locally using:
```bash
pytest tests/
```

## Academic Integrity & AI Support Declaration
* **AI Tool Usage**: Assisted with constructing structural code blocks and formatting boilerplate test tables.
* **Refinement Method**: Enhanced core calculations manually to match the exact mathematical bounds required by the Uganda Revenue Authority guidelines.
