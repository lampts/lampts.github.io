"""
euler_finance.py — Personal Finance in 5 Axioms
================================================
e^(iπ) + 1 = 0 connects 5 constants with zero redundancy.
This model connects 5 rules with the same elegance:

    W(t) = Σ (I(t) - C) × (1+r)^(T-t)

    where I(t) grows, C is FIXED, and (I-C) accelerates over time.

The 5 axioms:
    1. Save  ≥ 20% of income
    2. Invest ≥ 20% of income
    3. Spend  ≤ 40% of income (or fix C = $40K/year)
    4. Compound: r ≈ 7-10% nominal, 5-7% real
    5. Optimize: reduce fees, rebalance, tax-harvest

The hidden gem: with FIXED spending and GROWING income,
your savings rate increases every year automatically.
Year 1: earn $100K, spend $40K → save 60%
Year 10: earn $150K, spend $40K → save 73%
Year 20: earn $220K, spend $40K → save 82%

This is the real alpha. Not portfolio optimization.
Not discount rates. Not regression coefficients.
Just: fix C, let I grow, compound the gap.

Usage:
    python euler_finance.py
    python euler_finance.py --income 120000 --spend 40000 --years 25

No dependencies. Reads top to bottom. Every line does work.
"""

import math
import argparse

# ---------------------------------------------------------------------------
# The 5 axioms as constraints
# ---------------------------------------------------------------------------

def validate_axioms(income, spending, save_rate, invest_rate):
    """Check the 5 axioms hold. Return violations."""
    violations = []
    actual_save = (income - spending) / income

    if save_rate < 0.20:
        violations.append(f"Axiom 1 violated: save rate {save_rate:.0%} < 20%")
    if invest_rate < 0.20:
        violations.append(f"Axiom 2 violated: invest rate {invest_rate:.0%} < 20%")
    if spending / income > 0.40:
        violations.append(f"Axiom 3 violated: spend ratio {spending/income:.0%} > 40%")
    if actual_save < 0.40:
        violations.append(f"Warning: total savings {actual_save:.0%} — good but room to grow")

    return violations


# ---------------------------------------------------------------------------
# Core wealth model
# ---------------------------------------------------------------------------

def simulate(income, spending, initial_wealth=0, years=30,
             income_growth=0.05, return_rate=0.07, fee=0.002,
             inflation=0.03):
    """Simulate wealth accumulation under the 5 axioms.

    The key equation each year:
        surplus = income - spending        (grows because C is fixed)
        wealth  = wealth × (1 + r - fee) + surplus

    Everything in REAL (inflation-adjusted) terms.

    Returns list of yearly snapshots.
    """
    real_return = return_rate - inflation  # ~4% real
    net_return = real_return - fee          # ~3.8% after fees
    real_income_growth = income_growth - inflation  # ~2% real

    W = initial_wealth
    I = income
    C = spending  # FIXED in real terms — this is the whole trick
    history = []

    for year in range(years + 1):
        surplus = I - C
        save_rate = surplus / I if I > 0 else 0
        invest_amount = surplus  # axiom: invest all surplus

        # record state
        history.append({
            'year': year,
            'income': I,
            'spending': C,
            'surplus': surplus,
            'save_rate': save_rate,
            'wealth': W,
            'passive_income': W * net_return,
            'fi_ratio': (W * net_return) / C if C > 0 else 0,  # financial independence ratio
        })

        # advance one year
        W = W * (1 + net_return) + surplus
        I = I * (1 + real_income_growth)  # income grows
        # C stays FIXED — this is the Euler identity of the model

    return history


def fi_year(history):
    """Find the year when passive income ≥ spending (financial independence)."""
    for h in history:
        if h['fi_ratio'] >= 1.0:
            return h['year']
    return None


# ---------------------------------------------------------------------------
# The closed-form approximation
# ---------------------------------------------------------------------------

def wealth_formula(income, spending, r, g, years, W0=0):
    """Closed-form wealth after T years.

    W(T) = W0×(1+r)^T + (I-C)×[(1+r)^T - (1+g)^T] / (r-g)
                          ↑ initial compound    ↑ growing annuity (surplus grows because I grows, C fixed)

    When g=0 (no income growth), simplifies to:
    W(T) = W0×(1+r)^T + (I-C)×[(1+r)^T - 1] / r

    This IS the Euler identity of personal finance:
    5 variables (W0, I, C, r, T), one equation, zero waste.
    """
    surplus_0 = income - spending

    if abs(r - g) < 1e-10:
        # degenerate case: r ≈ g
        compound = (1 + r) ** years
        return W0 * compound + surplus_0 * years * (1 + r) ** (years - 1)

    compound_r = (1 + r) ** years
    compound_g = (1 + g) ** years

    # growing annuity: surplus starts at (I-C), grows at g (because I grows, C fixed)
    # but surplus growth rate is NOT g — it's I×g/(I-C) > g
    # for simplicity, use the simulation for exact numbers
    # this formula assumes surplus grows at rate g (lower bound)
    growing_annuity = surplus_0 * (compound_r - compound_g) / (r - g)

    return W0 * compound_r + growing_annuity


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def print_dashboard(history, show_all=False):
    """Print the wealth trajectory."""
    print("\n" + "=" * 75)
    print("EULER FINANCE — 5 AXIOMS WEALTH TRAJECTORY")
    print("=" * 75)
    h0 = history[0]
    print(f"  Starting income:   ${h0['income']:>12,.0f}")
    print(f"  Fixed spending:    ${h0['spending']:>12,.0f}")
    print(f"  Initial surplus:   ${h0['surplus']:>12,.0f}  ({h0['save_rate']:.0%} save rate)")
    print(f"  Initial wealth:    ${h0['wealth']:>12,.0f}")
    print("-" * 75)

    print(f"  {'Year':>4}  {'Income':>12}  {'Spending':>10}  {'Save%':>6}  "
          f"{'Wealth':>14}  {'Passive':>12}  {'FI%':>5}")

    milestones = {0, 1, 5, 10, 15, 20, 25, 30, 35, 40}
    fi_found = False

    for h in history:
        is_fi = h['fi_ratio'] >= 1.0 and not fi_found
        show = show_all or h['year'] in milestones or is_fi

        if show:
            marker = " ← FI!" if is_fi else ""
            print(f"  {h['year']:>4}  ${h['income']:>11,.0f}  "
                  f"${h['spending']:>9,.0f}  {h['save_rate']:>5.0%}  "
                  f"${h['wealth']:>13,.0f}  ${h['passive_income']:>11,.0f}  "
                  f"{h['fi_ratio']:>4.0%}{marker}")
            if is_fi:
                fi_found = True

    # final state
    hf = history[-1]
    fi = fi_year(history)

    print("-" * 75)
    print(f"  Final wealth:      ${hf['wealth']:>12,.0f}")
    print(f"  Final save rate:   {hf['save_rate']:>11.0%}  (started at {h0['save_rate']:.0%})")
    print(f"  Passive income:    ${hf['passive_income']:>12,.0f}/yr")
    if fi:
        print(f"  FI reached:        year {fi}")
    else:
        print(f"  FI reached:        not within simulation window")
    print("=" * 75)


def print_comparison(income, spending, years):
    """Compare the 5-axiom model vs common behaviors."""
    print("\n" + "=" * 75)
    print("SCENARIO COMPARISON — Same Income, Different Axioms")
    print("=" * 75)

    scenarios = [
        ("Average person (save 5%)",        income * 0.95, 0),
        ("Good saver (save 15%)",           income * 0.85, 0),
        ("Axiom follower (spend $40K)",     spending, 0),
        ("Axiom + $100K head start",        spending, 100_000),
        ("Axiom + $200K head start",        spending, 200_000),
    ]

    print(f"  {'Scenario':<35} {'Final Wealth':>14}  {'FI Year':>8}  {'Passive$/yr':>12}")
    print("  " + "-" * 72)

    for name, spend, w0 in scenarios:
        h = simulate(income, spend, initial_wealth=w0, years=years)
        fi = fi_year(h)
        hf = h[-1]
        fi_str = f"year {fi}" if fi else "never"
        print(f"  {name:<35} ${hf['wealth']:>13,.0f}  {fi_str:>8}  ${hf['passive_income']:>11,.0f}")

    print()


def print_sensitivity(income, spending):
    """Show how return rate and years affect FI."""
    print("\n  FI Year Matrix (return rate × income growth):")
    print(f"  {'':>12}", end="")
    for g in [0.02, 0.03, 0.05, 0.07]:
        print(f"  g={g:.0%}  ", end="")
    print()
    print("  " + "-" * 50)

    for r in [0.04, 0.06, 0.08, 0.10]:
        print(f"  r={r:.0%}      ", end="")
        for g in [0.02, 0.03, 0.05, 0.07]:
            h = simulate(income, spending, years=40,
                        return_rate=r, income_growth=g, inflation=0.03)
            fi = fi_year(h)
            fi_str = f"  {fi:>3}   " if fi else "  40+  "
            print(fi_str, end="")
        print()
    print()


def print_the_formula():
    """Print the closed-form Euler identity of personal finance."""
    print("""
  ┌─────────────────────────────────────────────────────────┐
  │                                                         │
  │   The Euler Identity of Personal Finance:               │
  │                                                         │
  │                        T                                │
  │   W(T) = W₀(1+r)ᵀ +  Σ  (I(t) - C) × (1+r)ᵀ⁻ᵗ       │
  │                       t=1                               │
  │                                                         │
  │   where:                                                │
  │     W₀ = initial wealth          (what you start with)  │
  │     I(t) = income at time t      (grows ~5%/yr)         │
  │     C = FIXED spending           (the whole trick)      │
  │     r = real return after fees   (~4%/yr)               │
  │     T = time horizon             (patience)             │
  │                                                         │
  │   5 variables. 1 equation. Zero waste.                  │
  │                                                         │
  │   The insight: C is constant, I grows.                  │
  │   So (I - C) accelerates every year.                    │
  │   Compounding does the rest.                            │
  │                                                         │
  │   Axioms:                                               │
  │     1. Save  ≥ 20% of income                            │
  │     2. Invest ≥ 20% of income                           │
  │     3. Spend  ≤ 40% (or fix C)                          │
  │     4. Compound: r ≈ 4% real                            │
  │     5. Optimize: fees, taxes, rebalance                 │
  │                                                         │
  └─────────────────────────────────────────────────────────┘
""")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Euler Finance: 5 Axioms')
    parser.add_argument('--income', type=float, default=100_000, help='Annual income')
    parser.add_argument('--spend', type=float, default=40_000, help='Fixed annual spending')
    parser.add_argument('--wealth', type=float, default=0, help='Initial wealth')
    parser.add_argument('--years', type=int, default=30, help='Simulation years')
    parser.add_argument('--return-rate', type=float, default=0.07, help='Nominal return (default 7%%)')
    parser.add_argument('--income-growth', type=float, default=0.05, help='Income growth (default 5%%)')
    parser.add_argument('--inflation', type=float, default=0.03, help='Inflation rate (default 3%%)')
    parser.add_argument('--fee', type=float, default=0.002, help='Investment fee (default 0.2%%)')
    parser.add_argument('--all', action='store_true', help='Show all years')
    args = parser.parse_args()

    # the formula
    print_the_formula()

    # validate axioms
    violations = validate_axioms(
        args.income, args.spend,
        save_rate=0.20, invest_rate=0.20
    )
    if violations:
        print("  ⚠ Axiom check:")
        for v in violations:
            print(f"    {v}")
        print()

    # main simulation
    history = simulate(
        income=args.income,
        spending=args.spend,
        initial_wealth=args.wealth,
        years=args.years,
        income_growth=args.income_growth,
        return_rate=args.return_rate,
        inflation=args.inflation,
        fee=args.fee,
    )
    print_dashboard(history, show_all=args.all)

    # scenario comparison
    print_comparison(args.income, args.spend, args.years)

    # sensitivity matrix
    print_sensitivity(args.income, args.spend)

    # closed-form check
    real_r = args.return_rate - args.inflation - args.fee
    real_g = args.income_growth - args.inflation
    W_formula = wealth_formula(args.income, args.spend, real_r, real_g,
                               args.years, args.wealth)
    W_sim = history[-1]['wealth']
    print(f"  Closed-form W({args.years}):  ${W_formula:>12,.0f}")
    print(f"  Simulated W({args.years}):    ${W_sim:>12,.0f}")
    print(f"  Difference:          {abs(W_formula - W_sim) / max(W_sim, 1) * 100:.1f}%")
    print(f"  (gap from surplus growth rate approximation)\n")
