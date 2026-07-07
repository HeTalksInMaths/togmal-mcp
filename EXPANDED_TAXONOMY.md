# Expanded Taxonomy of LLM Limitations

Generated 2026-07-07 from 13,000 benchmark questions (39 models). All figures are measured.

## Domain Risk Profiles (hardest first)

| Domain | Questions | Avg Success | % Risky | % Nearly Impossible | SOTA Lift |
|--------|-----------|-------------|---------|---------------------|-----------|
| engineering | 937 | 32.6% | 86% | 35% | +20% |
| law | 1,101 | 32.8% | 85% | 36% | +17% |
| chemistry | 1,132 | 35.8% | 87% | 25% | +32% |
| Pandas | 291 | 36.9% | 100% | 0% | — |
| Pytorch | 68 | 40.1% | 100% | 0% | — |
| Tensorflow | 45 | 41.0% | 100% | 0% | — |
| math | 1,351 | 41.1% | 76% | 22% | +28% |
| physics | 1,299 | 42.0% | 77% | 19% | +28% |
| Scipy | 106 | 42.3% | 100% | 0% | — |
| Sklearn | 115 | 43.2% | 100% | 0% | — |
| Numpy | 220 | 43.6% | 100% | 0% | — |
| business | 789 | 47.2% | 68% | 15% | +27% |
| philosophy | 499 | 47.3% | 64% | 23% | +18% |
| history | 381 | 47.4% | 62% | 23% | +18% |
| computer science | 410 | 47.8% | 69% | 17% | +23% |
| health | 818 | 50.9% | 58% | 20% | +17% |
| other | 924 | 51.6% | 58% | 19% | +18% |
| Matplotlib | 155 | 54.4% | 100% | 0% | — |
| economics | 844 | 56.9% | 50% | 14% | +19% |
| psychology | 798 | 61.7% | 42% | 13% | +15% |
| biology | 717 | 64.3% | 37% | 10% | +18% |

## Riskiest Subjects (≥5 questions)

| Subject | Questions | Avg Success |
|---------|-----------|-------------|
| MachineDesign | 67 | 22.6% |
| TransportPhenomena | 133 | 22.8% |
| scibench-matter | 47 | 25.1% |
| scibench-diff | 50 | 25.2% |
| scibench-class | 45 | 26.0% |
| PhysicalChemistry | 216 | 26.1% |
| scibench-quan | 32 | 26.3% |
| HeatTransfer | 64 | 26.8% |
| theoremQA-Math | 344 | 27.2% |
| scibench-thermo | 55 | 28.6% |
| Mechanics | 33 | 30.4% |
| professional_law | 1003 | 31.2% |
| Thermodynamics | 169 | 31.5% |
| Optics | 193 | 31.9% |
| theoremQA-Physics | 104 | 32.1% |
| scibench-calculus | 40 | 32.5% |
| college_mathematics | 74 | 32.9% |
| ElectricCircuits | 66 | 33.1% |
| scibench-atkins | 101 | 33.2% |
| ElectricalMachines | 102 | 33.7% |
| college_chemistry | 63 | 34.5% |
| high_school_european_history | 69 | 34.7% |
| theoremQA-EECS | 76 | 34.8% |
| FluidMechanics | 65 | 34.8% |
| econometrics | 85 | 35.2% |

## Universal Failures (168 questions all 39 models fail)

- **engineering**: A bare steel wire (k = 13 Btu/hr ft°F) is carrying a current of 1000 amp. The diameter of the wire is 0.75 in. The air t…
- **engineering**: In a bridge hand of 13 cards, what is the probability of (a) having neither an ace nor a king, (b) having no ace or one …
- **engineering**: Compute the diameter of a square link subjected to a compressive load of 27,000 lbs. Modulus of elasticity = 30 × 10^6 p…
- **health**: With respect to job training, younger workers…
- **health**: A 30-year-old woman, gravida 2, para 0, aborta 1, at 28 weeks' gestation comes to the office for a prenatal visit. She h…
- **health**: Proprioceptive nerve endings in synovial joints are located in…
- **health**: A placebo-controlled clinical trial is conducted to assess whether a new antihypertensive drug is more effective than st…
- **health**: A difference between the social networks of older and younger adults is that older adults have…
- **health**: In which of the following positions does a patient lie face down?…
- **health**: A 28-year-old man comes to the office because he would like to quit smoking cigarettes. He says, "I cannot go more than …

## Semantic Danger Clusters (30 ML-discovered topic clusters of hard questions, hardest first)

| Cluster | Size | Avg Success | Top Domains |
|---------|------|-------------|-------------|
| refers, information, question, following information | 110 | 12.8% | history, philosophy |
| state, court, statute, federal | 119 | 14.5% | law, other |
| according, moral, theory, principle | 60 | 14.6% | philosophy, psychology |
| defendant, trial, attorney, man | 139 | 15.2% | law, psychology |
| following, following true, best, true | 243 | 15.2% | health, other |
| statements, following statements, following, correct | 76 | 15.4% | economics, health |
| ft, temperature, heat, water | 174 | 15.5% | engineering, physics |
| likely, following, following likely, demand | 76 | 15.6% | economics, health |
| car, man, woman, likely | 157 | 15.8% | law, business |
| 000, contract, pay, woman | 111 | 16.4% | law, business |
| load, diameter, voltage, current | 130 | 16.9% | engineering, physics |
| claims, best, people, used | 768 | 16.9% | other, philosophy |
| does, does following, following, stand | 70 | 17.3% | math, other |
| mole, reaction, kcal, h_2o | 114 | 17.3% | chemistry, engineering |
| patient, year, old, year old | 96 | 17.4% | health, psychology |
| pressure, gas, volume, temperature | 191 | 18.1% | chemistry, engineering |
| property, deed, land, owner | 87 | 18.2% | law, other |
| 000, year, rate, income | 208 | 18.6% | business, other |
| number, random, probability, let | 196 | 18.7% | math, biology |
| value, let, function, suppose | 393 | 18.8% | math, engineering |

## Chain-of-Thought Failure Modes

- **Complex unit conversion requirements**: 166 questions (avg 1.4 reasoning steps)
- **Question may be truncated or ambiguous**: 2 questions (avg 3.0 reasoning steps)

Contributing factors: Models struggle with multi-system unit conversions (166), Question involves 7 different unit types (29), Question involves 5 different unit types (25), Question involves 6 different unit types (21), Question involves 8 different unit types (21), Question involves 4 different unit types (18), Question involves 10 different unit types (17), Question involves 9 different unit types (16)

## Deceptive Questions (SOTA fails, field succeeds)

50 questions where strong models underperform weaker ones by ≥20 points — likely traps or misleading phrasing.

- **economics** (SOTA 18% vs field 82%): Is it possible for many firms to sell exactly the same product, and still be in monopolistic competition?…
- **psychology** (SOTA 27% vs field 89%): Define the motive to avoid success according to Horner. How did she go about studying this motive in women?…
- **biology** (SOTA 9% vs field 68%): Describe the various land biomes that are usually encounteredby a traveler going from the equator to the arcticpolar ice…
- **psychology** (SOTA 9% vs field 64%): Studies into the etiology of Schizophrenia indicated a genetic predisposition to the condition but other factors are inv…
- **other** (SOTA 27% vs field 79%): As of 2013, which of the following countries had the highest per capita rate of homelessness?…

## Top Risk Keywords (log-odds, risky vs safe questions)

**Prose (MMLU-Pro):** `_2`, `rancher`, `x_1`, `heirs`, `builder`, `dm`, `acre`, `x_2`, `distributor`, `co_2`, `mathbf`, `nephew`, `theta`, `textbullet`, `cu`, `noise`, `dissociation`, `quad`, `conversation`, `neutron`, `trip`, `intersection`, `facility`, `mol`, `grantor`

**Code (DS-1000):** 
