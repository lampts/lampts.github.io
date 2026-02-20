"""
practical_finance.py — Lifecycle Portfolio Choice in ~200 lines
=============================================================
Implements Choi, Liu & Liu (2025) "Practical Finance" NBER W34166.
Approximates the Cocco-Gomes-Maenhout (2005) optimal stock/bond split
by treating future wages as an implicit risk-free bond, then adjusting
the Merton (1969) formula for human capital.

The key insight: your future wages ARE a bond portfolio. The only question
is what discount rate to use when valuing that bond. This script computes
those discount rates via regression coefficients fit to 5,103 parameter sets.

Usage:
    python practical_finance.py                    # run example
    python practical_finance.py --interactive      # input your own params

Karpathy-style: one file, no classes, no dependencies beyond stdlib + math.
Every line does work. Read top to bottom.

Reference: https://www.nber.org/papers/w34166
"""

import math
import argparse

# --- US mortality table (probability of dying before next age, ages 22-100) ---
# Source: NCHS life table for total US population (simplified)
# p_die[i] = probability of dying before reaching age 22+i+1, given alive at 22+i
# These are approximate; the paper uses exact NCHS tables
MORTALITY = [
    # ages 22-39: low mortality
    0.0006, 0.0007, 0.0007, 0.0008, 0.0008, 0.0009, 0.0009, 0.0010,
    0.0010, 0.0011, 0.0011, 0.0012, 0.0013, 0.0014, 0.0015, 0.0016,
    0.0017, 0.0018,
    # ages 40-59: rising mortality
    0.0020, 0.0022, 0.0025, 0.0028, 0.0031, 0.0035, 0.0039, 0.0044,
    0.0049, 0.0055, 0.0062, 0.0069, 0.0077, 0.0086, 0.0096, 0.0107,
    0.0119, 0.0132, 0.0147, 0.0163,
    # ages 60-79: accelerating
    0.0181, 0.0202, 0.0226, 0.0253, 0.0284, 0.0319, 0.0359, 0.0404,
    0.0455, 0.0512, 0.0577, 0.0649, 0.0730, 0.0820, 0.0921, 0.1033,
    0.1158, 0.1297, 0.1451, 0.1622,
    # ages 80-99: high mortality
    0.1812, 0.2022, 0.2253, 0.2508, 0.2789, 0.3097, 0.3434, 0.3802,
    0.4203, 0.4638, 0.5109, 0.5617, 0.6163, 0.6748, 0.7373, 0.8038,
    0.8745, 0.9494, 0.9800, 1.0000,
]

# --- CGM college graduate income profile (log income = f0 + f1*age + f2*age^2 + f3*age^3) ---
INCOME_PROFILES = {
    'college':    (-4.3148, 0.3194, -0.00577, 0.000033),
    'highschool': (-2.1700, 0.1682, -0.00323, 0.000020),
    'no_hs':      (-2.1361, 0.1684, -0.00353, 0.000023),
}

# --- Income shock standard deviations by education ---
INCOME_RISK = {
    #                sigma_perm, sigma_temp
    'college':    (0.130, 0.242),
    'highschool': (0.103, 0.272),
    'no_hs':      (0.102, 0.325),
}

# --- Stock market parameters ---
SIGMA_STOCK = 0.185  # annualized std dev of log stock returns (1926-2024)

# ---------------------------------------------------------------------------
# Core computation functions
# ---------------------------------------------------------------------------

def merton_share(gamma, log_equity_premium, log_rf, sigma_s=SIGMA_STOCK):
    """Merton (1969) optimal equity share with NO labor income.
    This is the asymptote — what you'd hold if you had zero human capital."""
    numerator = log_equity_premium + 0.5 * sigma_s**2
    denominator = gamma * sigma_s**2
    alpha_star = numerator / denominator
    return max(0.0, min(1.0, alpha_star))


def discount_rate_working(gamma, log_ep, log_rf, sigma_p, sigma_e, replacement, age):
    """One-period-ahead discount rate during working life (ages 22-65).
    From Table 1, Column 3 of the paper. R² = 0.886 across 224,532 obs."""
    r = (0.087 * (gamma / 10.0)
       - 0.267 * log_ep
       + 1.132 * log_rf
       + 4.332 * sigma_p**2
       + 0.028 * sigma_e**2
       + 0.010 * replacement
       - 0.149 * (age / 100.0)
       + 0.142 * (age / 100.0)**2
       - 0.020)
    return r


def discount_rate_retirement(gamma, log_ep, log_rf, age):
    """One-period-ahead discount rate during retirement (ages 66-99).
    From Table 2, Column 3 of the paper. R² = 0.819 across 2,142 obs.
    Note: income risk params vanish because retirement income is risk-free."""
    r = (0.0003 * (gamma / 10.0)
       - 0.217 * log_ep
       + 0.893 * log_rf
       + 0.476 * (age / 100.0)
       - 0.295 * (age / 100.0)**2
       - 0.166)
    return r


def expected_income_path(current_age, current_wage, retirement_age, replacement_rate,
                         retirement_benefit=0.0, education='college'):
    """Build the expected real income at each future age through 100.

    Two modes:
    - If current_wage > 0 and working: impute future wages from CGM polynomial
    - Retirement income = replacement_rate × final working wage (or explicit benefit)

    Returns dict: {age: expected_real_income}
    """
    f0, f1, f2, f3 = INCOME_PROFILES[education]

    # deterministic log income at any working age
    def log_income_det(age):
        return f0 + f1 * age + f2 * age**2 + f3 * age**3

    # scale factor: match the polynomial to current actual wage
    if current_age <= retirement_age and current_wage > 0:
        log_scale = math.log(current_wage) - log_income_det(current_age)
    else:
        log_scale = 0.0

    income = {}
    final_working_wage = current_wage  # will be updated

    for age in range(current_age + 1, 101):
        if age <= retirement_age:
            # working life: deterministic path scaled to current wage
            wage = math.exp(log_income_det(age) + log_scale)
            income[age] = wage
            final_working_wage = wage
        else:
            # retirement: fixed fraction of final working wage
            if retirement_benefit > 0:
                income[age] = retirement_benefit
            else:
                income[age] = replacement_rate * final_working_wage

    return income


def human_capital(current_age, income_path, gamma, log_ep, log_rf,
                  sigma_p, sigma_e, replacement_rate, retirement_age=66):
    """Compute H = present value of all future income, using age-varying discount rates.

    This is the paper's key contribution: the discount rates that make
    α* × (1 + H/W) match the CGM dynamic programming solution.

    Returns (H, details) where details is list of (age, income, rate, discounted_income).
    """
    H = 0.0
    cumulative_gross = 1.0
    details = []

    for age in range(current_age + 1, 101):
        if age not in income_path:
            continue

        # pick the right discount rate regime
        # rate at age t-1 applied to income arriving at age t
        discount_age = age - 1  # the age at which we're "standing" to discount
        if age <= retirement_age:
            r = discount_rate_working(gamma, log_ep, log_rf, sigma_p, sigma_e,
                                      replacement_rate, discount_age)
        else:
            r = discount_rate_retirement(gamma, log_ep, log_rf, discount_age)

        cumulative_gross *= (1.0 + r)
        discounted = income_path[age] / cumulative_gross

        # NOTE: no explicit mortality adjustment here. The fitted discount rates
        # were estimated from the CGM model which handles mortality internally
        # via the value function. The paper's Table 3 shows H without mortality.
        H += discounted
        details.append((age, income_path[age], 1.0 + r, discounted))

    return H, details


def optimal_equity_share(gamma, log_ep, log_rf, investable_wealth,
                         current_age, current_wage, retirement_age=66,
                         replacement_rate=0.4, retirement_benefit=0.0,
                         education='college', beta_perm=0.0):
    """The main function. Returns optimal % in stocks.

    Parameters:
        gamma:              risk aversion (1-10)
        log_ep:             log equity premium (e.g. 0.02 for ~4% level premium)
        log_rf:             log real risk-free rate (e.g. 0.02)
        investable_wealth:  non-housing assets minus non-mortgage debt (after tax)
        current_age:        your age now
        current_wage:       current annual after-tax wage (inc. employer 401k match)
        retirement_age:     last working age (default 66)
        replacement_rate:   Social Security as fraction of final wage (default 0.4)
        retirement_benefit: explicit annual retirement benefit if already receiving
        education:          'college', 'highschool', or 'no_hs'
        beta_perm:          correlation of permanent income shocks with stock returns
                           (0 for most people, 0.1-0.3 for finance workers)

    Returns:
        dict with equity_share, alpha_star, human_capital_value, details
    """
    sigma_p, sigma_e = INCOME_RISK[education]

    # Step 1: Merton baseline (no human capital)
    alpha_star = merton_share(gamma, log_ep, log_rf)

    # Step 2: build expected income path
    income_path = expected_income_path(
        current_age, current_wage, retirement_age,
        replacement_rate, retirement_benefit, education
    )

    # Step 3: compute human capital
    H, details = human_capital(
        current_age, income_path, gamma, log_ep, log_rf,
        sigma_p, sigma_e, replacement_rate, retirement_age
    )

    # Step 4: optimal equity share with human capital adjustment
    W = max(investable_wealth, 1.0)  # avoid division by zero
    h_over_w = H / W

    # base formula: scale Merton share by (1 + H/W)
    alpha = alpha_star * (1.0 + h_over_w)

    # correlation adjustment: if income covaries with stocks,
    # human capital has equity-like risk, reducing desired stock allocation
    if beta_perm > 0:
        alpha -= beta_perm * h_over_w

    # clamp to [0, 1]
    alpha = max(0.0, min(1.0, alpha))

    # level equity premium for display (convert from log)
    level_ep = math.exp(log_ep + log_rf + 0.5 * SIGMA_STOCK**2) - math.exp(log_rf)

    return {
        'equity_share': alpha,
        'equity_share_pct': round(alpha * 100, 1),
        'alpha_star': alpha_star,
        'alpha_star_pct': round(alpha_star * 100, 1),
        'human_capital': round(H, 0),
        'investable_wealth': W,
        'h_over_w': round(h_over_w, 2),
        'level_equity_premium_pct': round(level_ep * 100, 2),
        'details': details,
    }


# ---------------------------------------------------------------------------
# Display
# ---------------------------------------------------------------------------

def print_result(r):
    """Print the result in a clean format."""
    print("\n" + "=" * 60)
    print("PRACTICAL FINANCE — OPTIMAL EQUITY ALLOCATION")
    print("=" * 60)
    print(f"  Merton share (no human capital):  {r['alpha_star_pct']}%")
    print(f"  Human capital value:              ${r['human_capital']:,.0f}")
    print(f"  Investable wealth:                ${r['investable_wealth']:,.0f}")
    print(f"  H/W ratio:                        {r['h_over_w']:.2f}x")
    print(f"  Level equity premium:             {r['level_equity_premium_pct']:.2f}%")
    print("-" * 60)
    print(f"  >>> OPTIMAL EQUITY SHARE:         {r['equity_share_pct']}% <<<")
    print("=" * 60)

    # show income discount table (abbreviated)
    if r['details']:
        print("\nDiscount table (first 5 + last 5 years):")
        print(f"  {'Age':>4}  {'Income':>12}  {'Gross Rate':>10}  {'PV Income':>12}")
        show = r['details'][:5] + [None] + r['details'][-5:]
        for row in show:
            if row is None:
                print(f"  {'...':>4}  {'...':>12}  {'...':>10}  {'...':>12}")
            else:
                age, inc, gr, pv = row
                print(f"  {age:>4}  ${inc:>11,.0f}  {gr:>10.4f}  ${pv:>11,.0f}")
    print()


# ---------------------------------------------------------------------------
# Paper's worked example (Section 3.3) — for validation
# ---------------------------------------------------------------------------

def run_paper_example():
    """Reproduce the paper's Section 3.3 example: 55yo, gamma=7, $100K wage, $1M portfolio."""
    print("\n>>> PAPER EXAMPLE (Section 3.3 validation)")
    print("    55yo, γ=7, r_f=2%, equity_premium=2%, λ=40%, college grad")
    print("    $100K/yr wage, $40K/yr retirement, $1M portfolio")

    # build a flat income path (paper uses $100K through 66, $40K after)
    income_path = {}
    for age in range(56, 101):
        income_path[age] = 100_000 if age <= 66 else 40_000

    sigma_p, sigma_e = INCOME_RISK['college']
    alpha_star = merton_share(7, 0.02, 0.02)

    H, details = human_capital(
        current_age=55, income_path=income_path,
        gamma=7, log_ep=0.02, log_rf=0.02,
        sigma_p=sigma_p, sigma_e=sigma_e,
        replacement_rate=0.4, retirement_age=66
    )

    # paper gets H=$924,805 (without mortality adjustment in the informational display)
    # and equity share = 30% vs CGM optimal of 33%
    alpha = alpha_star * (1.0 + H / 1_000_000)
    alpha = max(0.0, min(1.0, alpha))

    print(f"\n    α* (Merton):     {alpha_star*100:.1f}%")
    print(f"    H (human cap):   ${H:,.0f}")
    print(f"    1 + H/W:         {1 + H/1_000_000:.2f}x")
    print(f"    Equity share:    {alpha*100:.1f}%")
    print(f"    Paper says:      30% (CGM optimal: 33%)\n")


# ---------------------------------------------------------------------------
# Scenario sweep — how equity share changes with key parameters
# ---------------------------------------------------------------------------

def run_sensitivity():
    """Show how the optimal equity share varies across key dimensions."""
    print("\n>>> SENSITIVITY ANALYSIS")
    print("    Base: 35yo, college, $80K wage, $200K portfolio, λ=0.4\n")

    base = dict(gamma=7, log_ep=0.02, log_rf=0.02, investable_wealth=200_000,
                current_age=35, current_wage=80_000, retirement_age=66,
                replacement_rate=0.4, education='college')

    # vary risk aversion
    print("  Risk aversion (γ) sweep:")
    for g in [3, 5, 7, 9, 10]:
        r = optimal_equity_share(**{**base, 'gamma': g})
        bar = "█" * int(r['equity_share_pct'] / 2)
        print(f"    γ={g:>2}  →  {r['equity_share_pct']:>5.1f}%  {bar}")

    # vary age
    print("\n  Age sweep (same wealth):")
    for a in [25, 35, 45, 55, 65]:
        r = optimal_equity_share(**{**base, 'current_age': a})
        bar = "█" * int(r['equity_share_pct'] / 2)
        print(f"    age={a}  →  {r['equity_share_pct']:>5.1f}%  {bar}")

    # vary wealth (H stays same, W changes → H/W changes)
    print("\n  Wealth sweep (same income):")
    for w in [50_000, 200_000, 500_000, 1_000_000, 5_000_000]:
        r = optimal_equity_share(**{**base, 'investable_wealth': w})
        bar = "█" * int(r['equity_share_pct'] / 2)
        print(f"    W=${w/1000:>6,.0f}K  →  {r['equity_share_pct']:>5.1f}%  {bar}")

    # vary equity premium
    print("\n  Equity premium sweep:")
    for ep in [0.01, 0.02, 0.03, 0.04, 0.05]:
        r = optimal_equity_share(**{**base, 'log_ep': ep})
        bar = "█" * int(r['equity_share_pct'] / 2)
        print(f"    log_ep={ep:.2f}  →  {r['equity_share_pct']:>5.1f}%  {bar}")

    # compare rules of thumb
    print("\n  >>> Rule comparison for this person:")
    r = optimal_equity_share(**base)
    age = base['current_age']
    print(f"    This model:        {r['equity_share_pct']:>5.1f}%")
    print(f"    (100 - age)%:      {100 - age:>5.1f}%")
    print(f"    Constant 60%:      60.0%")
    print(f"    Target date fund:  ~{85 - (age - 25) * 0.5:>4.0f}%  (approximate)")
    print()


# ---------------------------------------------------------------------------
# Interactive mode
# ---------------------------------------------------------------------------

def run_interactive():
    """Ask for inputs and compute."""
    print("\n>>> PRACTICAL FINANCE — INTERACTIVE MODE\n")

    def ask(prompt, default, cast=float):
        val = input(f"  {prompt} [{default}]: ").strip()
        return cast(val) if val else default

    gamma = ask("Risk aversion γ (1-10)", 7)
    age = ask("Current age", 35, int)
    wage = ask("Annual after-tax wage ($)", 80_000)
    wealth = ask("Investable net worth ($)", 200_000)
    ret_age = ask("Retirement age", 66, int)
    replacement = ask("SS replacement rate (0-1)", 0.4)
    log_rf = ask("Log real risk-free rate", 0.025)
    log_ep = ask("Log equity premium", 0.02)
    edu = input("  Education [college/highschool/no_hs] [college]: ").strip() or 'college'

    r = optimal_equity_share(
        gamma=gamma, log_ep=log_ep, log_rf=log_rf,
        investable_wealth=wealth, current_age=int(age),
        current_wage=wage, retirement_age=int(ret_age),
        replacement_rate=replacement, education=edu,
    )
    print_result(r)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Practical Finance: Lifecycle Portfolio Choice')
    parser.add_argument('--interactive', '-i', action='store_true', help='Interactive input mode')
    parser.add_argument('--example', '-e', action='store_true', help='Run paper validation example')
    args = parser.parse_args()

    if args.interactive:
        run_interactive()
    elif args.example:
        run_paper_example()
    else:
        # default: run everything
        run_paper_example()
        run_sensitivity()

        # a realistic personal example
        print(">>> PERSONAL EXAMPLE")
        print("    40yo, college, $120K wage, $500K portfolio\n")
        r = optimal_equity_share(
            gamma=6, log_ep=0.02, log_rf=0.025,
            investable_wealth=500_000, current_age=40,
            current_wage=120_000, retirement_age=66,
            replacement_rate=0.4, education='college',
        )
        print_result(r)
