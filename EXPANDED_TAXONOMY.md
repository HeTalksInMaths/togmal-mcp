# Expanded Taxonomy of LLM Limitations

Generated 2026-07-07 from 13,000 benchmark questions (48 models). All figures are measured.

## Domain Risk Profiles (hardest first)

| Domain | Questions | Avg Success | % Risky | % Nearly Impossible | SOTA Lift |
|--------|-----------|-------------|---------|---------------------|-----------|
| Pandas | 291 | 36.9% | 100% | 0% | — |
| engineering | 937 | 37.5% | 82% | 28% | +19% |
| law | 1,101 | 37.5% | 79% | 29% | +17% |
| Pytorch | 68 | 40.1% | 100% | 0% | — |
| Tensorflow | 45 | 41.0% | 100% | 0% | — |
| Scipy | 106 | 42.3% | 100% | 0% | — |
| chemistry | 1,132 | 42.9% | 80% | 17% | +29% |
| Sklearn | 115 | 43.2% | 100% | 0% | — |
| Numpy | 220 | 43.6% | 100% | 0% | — |
| math | 1,351 | 47.5% | 67% | 14% | +25% |
| physics | 1,299 | 47.7% | 70% | 13% | +25% |
| history | 381 | 51.1% | 54% | 21% | +16% |
| philosophy | 499 | 51.2% | 57% | 18% | +16% |
| computer science | 410 | 52.8% | 59% | 12% | +21% |
| business | 789 | 52.9% | 57% | 11% | +23% |
| Matplotlib | 155 | 54.4% | 100% | 0% | — |
| health | 818 | 54.9% | 50% | 18% | +16% |
| other | 924 | 55.8% | 52% | 15% | +17% |
| economics | 844 | 61.2% | 42% | 11% | +17% |
| psychology | 798 | 64.9% | 36% | 12% | +13% |
| biology | 717 | 68.3% | 30% | 8% | +16% |

## Riskiest Subjects (≥5 questions)

| Subject | Questions | Avg Success |
|---------|-----------|-------------|
| TransportPhenomena | 133 | 25.9% |
| MachineDesign | 67 | 26.0% |
| HeatTransfer | 64 | 30.2% |
| scibench-class | 45 | 30.6% |
| scibench-matter | 47 | 31.9% |
| scibench-diff | 50 | 32.0% |
| scibench-quan | 32 | 32.8% |
| PhysicalChemistry | 216 | 32.9% |
| theoremQA-Math | 344 | 33.9% |
| scibench-thermo | 55 | 34.7% |
| Thermodynamics | 169 | 36.0% |
| professional_law | 1003 | 36.1% |
| Mechanics | 33 | 37.0% |
| high_school_european_history | 69 | 37.9% |
| theoremQA-Physics | 104 | 37.9% |
| Optics | 193 | 38.2% |
| college_chemistry | 63 | 38.9% |
| college_mathematics | 74 | 39.3% |
| ElectricCircuits | 66 | 39.4% |
| scibench-calculus | 40 | 39.6% |
| ElectricalMachines | 102 | 40.2% |
| econometrics | 85 | 40.3% |
| FluidMechanics | 65 | 41.1% |
| scibench-atkins | 101 | 41.1% |
| theoremQA-EECS | 76 | 41.5% |

## Universal Failures (78 questions all 48 models fail)

- **engineering**: Compute the diameter of a square link subjected to a compressive load of 27,000 lbs. Modulus of elasticity = 30 × 10^6 p…
- **health**: A 30-year-old woman, gravida 2, para 0, aborta 1, at 28 weeks' gestation comes to the office for a prenatal visit. She h…
- **health**: Proprioceptive nerve endings in synovial joints are located in…
- **health**: In which of the following positions does a patient lie face down?…
- **health**: A 28-year-old man comes to the office because he would like to quit smoking cigarettes. He says, "I cannot go more than …
- **health**: The Worldwide HIV/AIDS campaigns have made significant progress over the last years. The HIV infection rates in Europe
…
- **health**: If links between various diseases are found, then future older adults will probably…
- **health**: Antivirals can be used prophylactically or therapeutically in persons in which of the following circumstances?…
- **health**: What is the biggest risk factor for infection with Ebola?…
- **health**: An investigator is studying the incidence of the common cold among medical students at various time points during the sc…

## Semantic Danger Clusters (30 ML-discovered topic clusters of hard questions, hardest first)

| Cluster | Size | Avg Success | Top Domains |
|---------|------|-------------|-------------|
| refers, question, information, following information | 96 | 12.9% | history, philosophy |
| according, moral, theory, behavior | 46 | 14.4% | philosophy, other |
| state, court, federal, statute | 94 | 14.9% | law, other |
| following, likely, associated, greatest | 204 | 15.0% | other, psychology |
| temperature, ft, heat, air | 113 | 15.4% | engineering, physics |
| statements, following statements, true, following | 78 | 15.9% | health, economics |
| man, woman, car, defendant | 143 | 16.4% | law, health |
| claims, best, view, argues | 372 | 16.4% | philosophy, psychology |
| patient, year, old, year old | 79 | 16.9% | health, psychology |
| 000, property, contract, owner | 153 | 17.6% | law, other |
| defendant, trial, attorney, evidence | 107 | 17.9% | law, math |
| number, output, population, different | 89 | 18.1% | math, biology |
| diameter, ft, speed, lb | 111 | 18.3% | engineering, physics |
| 000, year, rate, income | 153 | 18.4% | business, other |
| reaction, mole, calculate, kcal | 97 | 18.6% | chemistry, engineering |
| ways, people, group, major | 135 | 19.2% | math, other |
| value, given, positive, equation | 499 | 19.2% | math, engineering |
| price, cost, market, product | 101 | 19.6% | economics, business |
| current, load, voltage, power | 69 | 19.8% | engineering, physics |
| mathrm, mathrm cm, mathrm mathrm, _2 | 128 | 20.1% | chemistry, physics |

## Chain-of-Thought Failure Modes

- **Complex unit conversion requirements**: 78 questions (avg 1.3 reasoning steps)

Contributing factors: Models struggle with multi-system unit conversions (78), Question involves 5 different unit types (18), Question involves 7 different unit types (14), Question involves 8 different unit types (9), Question involves 9 different unit types (8), Question involves 4 different unit types (8), Question involves 10 different unit types (6), Question involves 6 different unit types (6)

## Deceptive Questions (SOTA fails, field succeeds)

50 questions where strong models underperform weaker ones by ≥20 points — likely traps or misleading phrasing.

- **economics** (SOTA 16% vs field 83%): Is it possible for many firms to sell exactly the same product, and still be in monopolistic competition?…
- **psychology** (SOTA 26% vs field 90%): Define the motive to avoid success according to Horner. How did she go about studying this motive in women?…
- **economics** (SOTA 32% vs field 83%): If the economy is operating at full employment which of the following policies will create the most inflation in the sho…
- **other** (SOTA 26% vs field 76%): As of 2013, which of the following countries had the highest per capita rate of homelessness?…
- **other** (SOTA 26% vs field 72%): Walt Disney, Sony and Time Warner are examples of:…

## Top Risk Keywords (log-odds, risky vs safe questions)

**Prose (MMLU-Pro):** `rancher`, `dm`, `distributor`, `nephew`, `theta`, `cu`, `noise`, `quad`, `neutron`, `prosecuted`, `ch_4`, `heirs`, `tau`, `nh_3`, `burglary`, `eat`, `vertex`, `seated`, `der`, `channel`, `bid`, `gibbs`, `y_2`, `acetic`, `co_2`

**Code (DS-1000):** 
