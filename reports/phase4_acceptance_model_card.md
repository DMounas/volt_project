# Model & Assumption Card — Customer Flexibility Acceptance Model

## 1. Model Overview

| Field | Specification |
| :--- | :--- |
| **Model Identifier** | `VOLT-CUSTOMER-ACCEPTANCE-V1` |
| **Module Location** | `engine/customer/response_model.py` |
| **Model Family** | Bounded Parametric Logistic Regression / Discrete Choice Sigmoid |
| **Implementation** | Python 3.14 / NumPy |
| **Phase Introduced** | Phase 4 of 7 |
| **Provenance Classification** | **ASSUMED (Model Inputs) / SYNTHETIC (Output Distributions)** |

> [!IMPORTANT]
> **Epistemic Disclosure & Non-Observed Data Warning**  
> This customer response model is **not trained on observed customer behavioral telemetry, historical driver ride-hailing logs, or empirical price elasticity studies**. It is a transparent, configurable parametric model designed to demonstrate customer-service-aware scheduling and voluntary incentive economics. Never cite these acceptance rates as measured fleet behavior.

---

## 2. Mathematical Formulation

The customer acceptance probability $p_{\text{accept}} \in [0.0, 1.0]$ represents the probability that an opted-in EV driver or fleet manager accepts a proposed deferred charging or battery-swap window:

$$z = \beta_0 + \beta_1 \cdot S_{\text{incentive}} + \beta_2 \cdot T_{\text{notice}} + \beta_3 \cdot T_{\text{slack}} + \gamma_{\text{segment}}$$

$$p_{\text{accept}} = \text{clip}\left(\frac{1}{1 + e^{-z}}, 0.0, 1.0\right)$$

Where:
- $\beta_0$: Base willingness-to-defer intercept ($\beta_0 = -1.50$).
- $\beta_1$: Price/incentive sensitivity coefficient ($\beta_1 = 0.80$ per INR/kWh).
- $\beta_2$: Advance notice coefficient ($\beta_2 = 0.30$ per advance hour).
- $\beta_3$: Available schedule slack coefficient ($\beta_3 = 0.40$ per hour of buffer).
- $\gamma_{\text{segment}}$: Segment-specific utility adjustment.

---

## 3. Segment Calibration & Sensitivity Parameters

All parameters are configured in `configs/assumptions.yaml` under `customer_flexibility.acceptance_logistic_model`:

| Parameter | Unit | Base Value | Low Sensitivity | High Sensitivity | Provenance | Rationale |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| $\beta_0$ (Intercept) | dimensionless | -1.50 | -2.00 | -1.00 | ASSUMED | Reflects inherent driver reluctance to alter travel plans |
| $\beta_1$ (Incentive Elasticity) | $(\text{INR/kWh})^{-1}$ | 0.80 | 0.40 | 1.50 | ASSUMED | Elasticity of commercial fleets vs private commuters |
| $\beta_2$ (Advance Notice) | $\text{hour}^{-1}$ | 0.30 | 0.10 | 0.50 | ASSUMED | Notice allows drivers to plan breaks or driver changes |
| $\beta_3$ (Schedule Buffer) | $\text{hour}^{-1}$ | 0.40 | 0.20 | 0.60 | ASSUMED | Longer windows make deferral less risky for the driver |
| $\gamma_{\text{EMERGENCY}}$ | dimensionless | -999.0 | -999.0 | -999.0 | ASSUMED | Strict structural zero (never accepts deferral) |
| $\gamma_{\text{PRIORITY\_FLEET}}$ | dimensionless | -999.0 | -999.0 | -999.0 | ASSUMED | Strict structural zero (5% uncommitted reserve) |
| $\gamma_{\text{RIDE\_HAILING}}$ | dimensionless | 0.00 | -0.20 | +0.20 | ASSUMED | Neutral baseline commercial responsiveness |
| $\gamma_{\text{LOGISTICS\_FLEET}}$ | dimensionless | +0.50 | +0.20 | +0.80 | ASSUMED | High scheduling slack in overnight delivery depots |
| $\gamma_{\text{PRIVATE\_EV}}$ | dimensionless | -0.20 | -0.50 | +0.10 | ASSUMED | Individual commuters prioritize immediate readiness |

---

## 4. Hard Operating Safeguards

The model enforces four hard structural constraints:
1. **Emergency Exclusion:** Requests categorized as `EMERGENCY` (ambulances, police, emergency response) receive an unconditional $p_{\text{accept}} = 0.0$.
2. **Priority Fleet Protection:** Requests from `PRIORITY_FLEET` municipal and government transit vehicles receive $p_{\text{accept}} = 0.0$, safeguarding the 5% network-wide uncommitted reserve.
3. **Explicit Opt-In Required:** If `flexibility_opt_in == False`, the model returns $p_{\text{accept}} = 0.0$. Voluntary consent is never inferred from customer segment alone.
4. **Feasible Envelope Invariant:** If the proposed deferral violates the customer's departure deadline $T_{\text{deadline}}$ or max deferral window, $p_{\text{accept}} = 0.0$.

---

## 5. Execution Modes

The model provides dual output modes:
1. **Deterministic Expected Values:**
   $$\mathbb{E}[E_{\text{flex}}] = p_{\text{accept}} \times E_{\text{flexible}}$$
   Used as deterministic candidate schedules for future Phase 5 optimization.
2. **Seeded Stochastic Realizations:**
   $$Y_{\text{accept}} \sim \text{Bernoulli}(p_{\text{accept}})$$
   $$E_{\text{realized}} = Y_{\text{accept}} \times E_{\text{flexible}}$$
   Used for Monte Carlo risk simulations and stress testing.

---

## 6. Financial Decoupling

Retail energy tariff ($T_{\text{retail}}$) and flexibility incentive ($I_{\text{flex}}$) are strictly decoupled:
- **Retail Tariff Revenue:** Bounded to $[0.80 \times \bar{T}_{\text{prev}}, 1.20 \times \bar{T}_{\text{prev}}]$.
- **Flexibility Incentive:** Operating cost recorded as an operational expense.
- **Guardrail:** Never combine tariff discounts and cash incentives into a single blended rate. Double-counting savings is prohibited.

---

## 7. Model Limitations

- Does not capture vehicle-to-grid (V2G) power discharge back into chargers.
- Does not model individual battery state-of-health degradation in customer vehicles.
- Relies on assumed logistic coefficients; requires empirical recalibration if telemetry becomes available.
