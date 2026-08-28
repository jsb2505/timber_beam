# Review of `timber_beam` — EC5 accuracy and code quality

**Date:** 27 August 2026
**Scope:** all five Python modules, all five material data files and the demo notebook at commit `cd7a81d` (origin/main).
**Standards assumed:** BS EN 1995-1-1:2004 (+A1:2008, +A2:2014) with the UK National Annex; BS EN 1990:2002+A1:2005 with UK NA; BS EN 338:2016; BS EN 14080:2013. Nationally determined parameters are noted "UK NA".
**Method:** five independent review passes (EC5 factors; member checks and mechanics; vibration and joists; material data; code quality and API safety), every finding then adversarially re-verified against the code, followed by a completeness sweep. 70 findings survived verification; 1 was refuted.

> **Status of this document.** This review supports the engineer's own checking;
> it is not a Category 2 or 3 check, and the checking obligations remain with
> the engineer. Items marked **CHECK** assert something the review could not
> certify from the standard and must be closed against your copies of the
> standards. Items marked **CONFIRMED** are provable from the code/data alone
> or from standard values the review is certain of.
>
> **Fix status codes:** `[patched]` = fixed on branch `fix/review-findings` of
> this repo; `[timber-ec5]` = resolved structurally in the new `timber-ec5`
> package; `[engineer]` = needs your decision/verification; combinations apply.

---

## 1. Defects (wrong number or crash)

### D1. Effective length state corruption — CONFIRMED `[patched]` `[timber-ec5]`
`timber_beam.py:46-52`. The `effective_length` property returned
`_effective_length_factor`, and `_set_effective_length()` wrote
`length × factor` INTO the factor attribute; `_effective_length` was never
assigned. After one construction the value was right by accident; any re-set of
`.length` multiplied the new length by the old corrupted value (3000 mm beam
re-set to 4000 mm → l_ef = 12,000,000 mm), collapsing σ_m,crit (Eq 6.31) and
crushing every subsequent LTB result with no error. Patched to store
`_effective_length` separately. In `timber-ec5`, models are frozen so the bug
class cannot recur.

### D2. Strength grade normalisation discarded — CONFIRMED `[patched]` `[timber-ec5]`
`timber_material.py:45`. `strength_grade.strip().upper()` was evaluated and
thrown away, so `TimberMaterial("softwood", "c24", 1)` raised `ValueError`.
Patched to assign the result. (All grade keys in all five data files are
upper-case, so the fix is safe.)

### D3. Restrained-beam auto-sizing crashed / oversized — CONFIRMED `[patched]` `[timber-ec5]`
`timber_design.py:266, 272, 342`. With `is_restrained=True` (or breadth ≥
height) the LTB utilisation is legitimately `None`:
- line 266 evaluated `None > None` → `TypeError` as soon as the height search
  entered its loop — the height auto-sizer crashed for the most common case;
- lines 272/342 used `all(result is not None and result <= 1 ...)`, treating
  `None` as a failure, so the breadth search silently iterated to
  `max_breadth` and returned a grossly oversized section as the "design".
Patched with None-safe logic. In `timber-ec5`, NOT_APPLICABLE is a first-class
check status, eliminating the `None` sentinel entirely.

### D4. Exhausted search space returned a failing design silently — CONFIRMED `[patched]` `[timber-ec5]`
`timber_design.py:196-202` (and the max_height/max_breadth cap paths). When no
candidate passed, the routine returned the last candidate's dimensions and
utilisations in the same shape as a success (reproduced: a 693%-utilised
section returned with no flag). Patched: every auto-sizing result now carries
`"design_passes": bool`. In `timber-ec5`, sizing returns an explicit
termination reason and a full candidate audit trail.

### D5. Clamped-size results reported the wrong geometry's utilisations — CONFIRMED `[patched]` `[timber-ec5]`
`timber_design.py:247-250, 323-326`. On clamping to `max_height`/`max_breadth`
the loop broke WITHOUT recomputing, so the returned dict paired the clamped
dimension with utilisations computed at the previous, smaller size (reproduced:
reported h = 200 mm with the URs of h = 198 mm; a section passing at exactly the
cap could be reported as failing). Patched to recompute at the clamped size.

### D6. GL24H mean density physically impossible — CONFIRMED value `[patched]` `[timber-ec5]`; replacement value **user-confirmed 420**
`glulam_data.json`. GL24H had `density_mean: 240` below
`density_characteristic: 385` — impossible (the only such grade among all 39).
Selfweight was under-predicted by ~43%, unconservative in every ULS and SLS
combination. Corrected to 420 kg/m³ (EN 14080:2013 Table 5 value, confirmed by
the author). `timber-ec5` validates `density_mean >= density_characteristic`
at data load, so this error class cannot recur.

### D7. n₄₀ silently returned a COMPLEX number for f₁ > 40 Hz — CONFIRMED `[patched]` `[timber-ec5]`
`timber_joist.py` (`get_number_of_first_order_modes`). For f₁ > 40 Hz,
`((40/f1)² - 1)**0.25` evaluates to a complex number in Python with no
exception, which then propagated into the velocity response. There was also no
gate on the f₁ > 8 Hz applicability precondition of cl. 7.3.3 (see N7).
Patched with explicit guards raising `ValueError`.

### D8. Trimmer span fits silently returned negative spans — CONFIRMED `[patched]` `[timber-ec5]`
`timber_joist.py:195-220`. The linear fit terms change sign outside the
calibration range (e.g. trimmed-joist span > ~10,970 mm → negative "max span");
large sections extrapolate upwards without bound. Patched to raise `ValueError`
on a non-positive result; see also P6 (provenance).

### D9. Data files opened relative to the CWD — CONFIRMED, already fixed upstream
`timber_material.py`. Already resolved on origin/main (commit `98bb33d`); the
review confirmed the fix is sound. The local checkout was two commits behind —
now fast-forwarded. Sharper risk noted by the review: a stray same-named JSON
in the caller's CWD would previously have been loaded silently in place of the
vetted data. `timber-ec5` loads data via `importlib.resources`.

### D10. Softwood C14 G_mean transcription error — CONFIRMED `[patched]` `[timber-ec5]`
`softwood_data.json`. C14 `G_mean` was 400 MPa; every other C-grade follows
E_0,mean/16 exactly (EN 338 derivation), giving 7000/16 → 440 MPa (tabulated
0.44 kN/mm²). Corrected to 440. Effect was ~10% overestimate of C14 shear
deflection (conservative direction, but wrong data).

---

## 2. Non-conformities with EC5 / UK NA

### N1. k_h applied to dense hardwoods — CONFIRMED `[patched]` `[timber-ec5]`
`timber_material.py` (`get_k_h`). Cl. 3.2(3) permits the solid-timber depth
factor only for ρ_k ≤ 700 kg/m³. D65 (750), D70 (800), D75 (850) and D80
(900 kg/m³) received up to a 15% unentitled bending enhancement at h = 75 mm
(up to the 1.3 cap for smaller depths). Unconservative. Patched with a density
gate.

### N2. Green oak k_def — CONFIRMED in part; SC3 value **[engineer]**
The green-oak row [1.6, 1.8, 2.0] is from TRADA *Green Oak in Construction*
(source confirmed by the author). The review established that 1.6/1.8 are
exactly EC5 Table 3.2 (0.6/0.8) plus the cl. 3.2(4) increase of 1.0 for timber
installed at or near fibre saturation and likely to dry out under load — i.e.
EC5-derivable, not arbitrary. **Open question for the engineer:** for service
class 3 the code (and the TRADA value) uses 2.0, but a strict reading of
cl. 3.2(4) gives 2.0 + 1.0 = 3.0 if the member is still expected to dry under
load in its SC3 environment; the TRADA figure presumably reflects a member that
stays wet. The review's verifiers took the strict reading (3.0); the published
guidance says 2.0. Both this repo and `timber-ec5` retain the published TRADA
value — **confirm against your copy of Green Oak in Construction and decide,
particularly for sheltered-external members that will partially dry.**

### N3. Green oak service class unrestricted — CHECK `[timber-ec5]` (documented)
Nothing stopped `TimberMaterial('green_oak', 'TH1', 1)` claiming SC1 k_mod
(0.80 medium-term vs 0.65 for SC3 — 23% unconservative on every strength
check). Note the counter-argument the verifier raised: cl. 2.3.1.3 defines
service classes by the ENVIRONMENT, so green oak drying towards a heated
interior is legitimately SC1 for that purpose, with the initial wetness handled
by the cl. 3.2(4) creep increase. **The strength-side question — whether k_mod
for green oak should be taken at SC3 while the member remains wet — is flagged
in `timber-ec5` docstrings for the engineer to settle against the TRADA
guidance.**

### N4. Enhanced k_c,90 without geometric conditions — CONFIRMED `[timber-ec5]` (documented) `[engineer]`
`get_k_c_90`. The values (1.25/1.5 continuous, 1.5/1.75 discrete;
softwood-based only) are correct per cl. 6.1.5 post-A1:2008, but the attached
conditions (l₁ ≥ 2h clear distance; bearing length ≤ 400 mm for the glulam
discrete value of 1.75) are neither taken as inputs nor checked — a 600 mm
glulam bearing could claim +75%. The beneficial 30 mm effective contact length
of cl. 6.1.5(1) is also unused (conservative). `timber-ec5` documents the
conditions on the enum and the check, and offers the effective contact length
as an explicit opt-in; verifying the geometry remains with the engineer.

### N5. Bearing check never ran — CONFIRMED `[timber-ec5]`
`get_bearing_stress`/`get_bearing_strength` were implemented, unit-correct, and
called by nothing; `_find_utilisation_results` assembled only bending, shear,
LTB and deflection, so every auto-designed section was issued without a
compression-perpendicular check — which routinely governs for heavily loaded
softwood on short bearings (C24 f_c,90,k = 2.5 MPa). In `timber-ec5` the
bearing check is part of the standard result set (NOT_APPLICABLE when no
bearing detail is supplied). The legacy patch does not rewire the design flow
(out of scope for a minimal patch) — **note the legacy auto-sizers still do not
check bearing.**

### N6. Notched shear machinery dead and incomplete — CONFIRMED `[timber-ec5]`
`get_k_v` transcribes Eq 6.62/6.63 correctly (verified symbol by symbol) but
was never called, and no path computed the shear stress on the effective depth
h_ef required by Eq 6.60 — a notched beam got an unconservative, un-warned
check. `timber-ec5` wires the full notched path: τ_d = 1.5V/(k_cr·b·h_ef) with
capacity k_v·f_v,d, notch geometry validated, and x measured from the line of
action of the reaction (mid-bearing). The legacy patch leaves `get_k_v`
unwired (rewiring is a design change); the defect-level guards (D8) were
patched.

### N7. No f₁ > 8 Hz gate on the vibration method — CONFIRMED `[patched]` `[timber-ec5]`
Cl. 7.3.3 applies the Eq 7.3/7.4 criteria to residential floors with f₁ > 8 Hz;
below that a special investigation is required. No method or caller enforced
this. Patched (raises with an explanatory message); `timber-ec5` reports the
frequency criterion as an explicit check result and marks the velocity
criterion NOT_APPLICABLE outside the method's range.

### N8. Hardwood D60–D80 f_c,90,k appear pre-2016 — CHECK `[engineer]`
`hardwood_data.json`. D18–D55 follow the EN 338:2016 pattern (≈0.010·ρ_k)
exactly; D60–D80 follow the superseded ≈0.015·ρ_k rule exactly (10.5, 11.3,
12.0, 12.8, 13.5 MPa). If EN 338:2016 gives ≈7.0/7.5/8.0/8.5/9.0 MPa (believed,
not certified), bearing strength for these grades is overstated ~50% —
unconservative. **Verify the D60–D80 f_c,90,k column (and D18 f_v,k = 3.5 vs a
possible 3.4) against EN 338:2016 and correct both data sets.** Values left
untouched pending your verification.

### N9. GL36H/GL36C are not EN 14080:2013 classes — CONFIRMED `[engineer]`
GL classes in EN 14080:2013 end at GL32. GL36h/c are withdrawn BS EN 1194:1999
classes; GL36H's stiffness values (15000/12200 MPa) match no known table, and
the file applies EN 14080-style f_v,k/f_c,90,k to these legacy classes. A GL36
specification may be unprocurable as CE/UKCA-marked product. **Decide whether
to delete them or keep them explicitly marked legacy with cited sources.** Both
repos currently retain them; `timber-ec5`'s README flags them.

---

## 3. Provenance flags (non-EC5 content needing citation)

- **P1. G_0,05 derivation** — CONFIRMED non-normative. For softwood the code
  derives G_005 = E_005/((48+2/3)·β) from an Edinburgh Napier CWST blog post;
  the review independently re-derived the algebra and confirmed it is exactly
  the value that makes Eq 6.31 reproduce the simplified softwood expression
  Eq 6.32 (σ_m,crit = 0.78·b²·E_0,05/(h·l_ef)) — defensible, but it makes a
  "material" property depend on section aspect ratio, and a blog is not a
  design basis. Hardwood/green oak use E_005/16 (the EN 338 mean-ratio applied
  at the 5th percentile — an assumption). Glulam (540 MPa) and LVL (400 MPa)
  carry declared values consistent with EN 14080/manufacturer data.
  `timber-ec5` documents both derivations with CHECK notes. **[engineer]**
  accept or substitute a project convention.
- **P2. Green oak TH values** — BS 5756 visual grades with no property table of
  their own; the file's values carry EN 338:2003-era D-class fingerprints
  (f_c,90,k = 8.0/8.8 matching old D30/D40). Source confirmed by the author as
  TRADA *Green Oak in Construction* — **cite edition/table, and confirm TH2's
  E_0,05 = 6590 MPa against the source: at 98% of E_0,mean it is an implausible
  outlier (the other grades sit at 0.80–0.85; EN 384's hardwood ratio is
  0.84·E_0,mean ≈ 5640 MPa).**
- **P3. LVL data** — Kerto-type manufacturer declarations presented as generic
  grades. f_v,k = 5.7 MPa across S and Q grades matches no recalled Kerto
  edgewise figure (~4.1 S / ~4.5 Q — CHECK); a single f_c,90,k per grade hides
  the edgewise/flatwise distinction (roughly threefold); S44's E_0,mean 13500
  vs Kerto's 13800 may be a transcription slip; s = 0.12 needs the declaration
  cited. **Trace every LVL value to the current DoP/VTT certificate before
  relying on LVL output, especially shear.**
- **P4. k_strut = 0.97** — consistent with UK NA NA.2.7.2 (strutting present);
  CHECK against your NA copy. Now documented in `timber-ec5`.
- **P5. Torsion coefficient β fit** — the standard Roark/Timoshenko closed-form
  approximation (error < ~1%), correctly transcribed; cite a book source rather
  than roymech.org.
- **P6. Trimmer/trimming-joist span formulas** — uncited empirical curve fits
  (TRADA-style span tables presumed). No validity ranges, no embedded
  load/spacing assumptions stated, unexplained 1.075 C24 coefficient; the
  trimming-joist fit divides by `self.length`, whose intended meaning is
  undocumented. **Identify the source document and record the fitted ranges,
  or treat outputs as rough initial estimates only.** Both repos now guard
  against non-positive results; `timber-ec5` labels them EMPIRICAL, NON-EC5.
- **P7. Standard size lists** — merchant-availability conventions (BS EN 336
  adjacent), not normative; confirm availability with suppliers.

---

## 4. Code quality (selected; all 25 findings verified)

- **No package structure, no tests, no pyproject** — the gap that let D1–D5
  through. `timber-ec5`: src-layout package, pytest suite with worked-example
  pins and property-based tests, ruff, CI.
- **Auto-sizing mutates the shared instance** — the three routines leave the
  object at whatever size the search ended on; the demo notebook's third result
  silently inherits the second's height. `timber-ec5`: frozen models,
  `model_copy` per candidate, template untouched.
- **`TimberDesign(TimberBeam(TimberSection))` inheritance** — design
  orchestration is-a beam is-a section is a weak model; 6–10 untyped positional
  parameters per method invite transposed loads. `timber-ec5`: composition
  (beam HAS material and section; loading is its own object), full type hints,
  keyword construction.
- **`TimberJoist` hard-codes service class 1 and inserts `floor_width` as the
  second positional argument** (a caller habituated to `TimberBeam`'s order
  silently corrupts every vibration result). `timber-ec5`: keyword-only frozen
  models.
- **Favourable defaults** — `is_restrained=True` (skips LTB silently) and
  `is_strutted=True` (claims the k_strut benefit silently). `timber-ec5`:
  restraint has no default (must be stated); strutting defaults False.
- **`print()` as a design warning; no machine-readable abort reason;
  input-validation gaps** (negative UDLs accepted; `deflection_limit=0`
  crashes; negative limit silently passes every check). All structural in
  `timber-ec5` (validated fields, explicit termination enums).
- **`data_to_json.ipynb` is stale** — regenerating it would write a misspelt
  key (`density_characterisitic`) over `softwood_data.json`, and it covers
  softwood only, so it is not a provenance record. Prefer deleting it or
  rebuilding it with cited sources.
- **Wrong type hint** (`strength_grade -> int`), missing docstrings on the
  design-effect methods (which assume simply supported single-span UDL —
  undocumented), mislabelled "Shear UR" print for deflection in the notebook.

---

## 5. Positive assurance (verified correct)

- γ_M (1.3 solid/green oak, 1.25 glulam, 1.2 LVL) matches UK NA Table NA.3.
- k_mod: all 15 values match Table 3.1; k_def (EC5 materials) matches Table 3.2.
- k_h thresholds/exponents/caps correct for all three material rules, including
  LVL's strength REDUCTION for h > 300 mm.
- k_sys = 1.1 (cl. 6.6) — applying it to shear as well as bending is permitted.
- k_cr (0.67 solid/glulam, 1.0 LVL) and its use as an effective width both
  correct; k_crit (Eq 6.34) exact and continuous at both branch points.
- k_c,90 base values and k_n (5.0/6.5/4.5) correct; Eq 6.62 transcription
  verified symbol by symbol.
- Shear, bending, LTB (Eq 6.30/6.31/6.33), deflection (incl. the kN/m ≡ N/mm
  unit identity and the Eq 2.3/2.4 creep combination), and the EN 1990 Eq 6.10
  ULS effects are all unit-consistent and correctly transcribed.
- Vibration Eq 7.5/7.6/7.7 orientation and unit conversions correct; Table NA.6
  a/b limits correct and continuous (b = 120 at a = 1 from both branches).
- Selfweight from mean density is normal practice (EN 1991-1-1 Annex A
  consistent) — now documented.
- All demo-notebook outputs were independently recomputed and match — they were
  produced with an uncorrupted l_ef by accident of construction order, so they
  remained valid regression anchors for the patch (and were re-verified after
  it).
- Refuted (1): a critic claim that the velocity constant b should be built from
  the floor's achieved 1 kN deflection rather than the Table NA.6 limit `a` —
  the NA pairs b with the prescribed limit; the code's reading is conventional.

---

## 6. Outstanding items for the engineer

> **Superseded in part — see §7 (resolution log, 28 August 2026)** for the
> items closed by the engineer's decisions and the EN 338:2016 verification.

1. EN 338:2016 D-class check: D60–D80 f_c,90,k (and D18 f_v,k) — N8.
2. GL36H/GL36C: delete or mark legacy with sources — N9.
3. Green oak: SC3 k_def 2.0 vs 3.0 (cl. 3.2(4) reading) and the k_mod service
   class question — N2/N3; TH2 E_0,05 outlier — P2.
4. LVL: trace f_v,k = 5.7, f_c,90,k orientation, E_0,mean 13500 and s = 0.12 to
   the current DoP — P3.
5. G_0,05 convention acceptance — P1.
6. Trimmer-fit provenance and validity ranges — P6.
7. k_c,90 geometry conditions on any enhanced bearing — N4.
8. UK NA edition strings for citations; modal damping ratio default (0.02 used,
   EC5 recommends 0.01 unless proven) — flagged in `timber-ec5` docstrings.

---

## 7. Resolution log — 28 August 2026

Engineer decisions and verifications recorded against the findings above.

### Closed by verification against BS EN 338:2016 (engineer-supplied copy)

- **N8 — CLOSED, review suspicion REFUTED.** The full softwood and hardwood
  data sets in both repos were checked value-by-value against BS EN 338:2016
  Tables 1 and 3 (f_m,k, f_v,k, f_c,90,k, E_0,mean, E_0,05, G_mean, rho_k,
  rho_mean). The D60-D80 f_c,90,k values (10.5 / 11.3 / 12.0 / 12.8 /
  13.5 MPa) and D18 f_v,k = 3.5 MPa ARE the EN 338:2016 Table 3 values - the
  2016 edition genuinely retains the step-up at D60. No change; the review's
  "believed ~0.010 rho_k continuation" was wrong.
- **NEW (found in the same verification): C45 E_0,05 was 10 000 MPa** - the
  superseded EN 338:2009 value (2/3 x E_0,mean). EN 338:2016 Table 1 gives
  10.1 kN/mm2. Corrected to 10 100 MPa in `softwood_data.json` (this repo) and
  `timber-ec5` `softwood.json`, with a regression pin in the timber-ec5 test
  suite. Effect was ~0.5% conservative on C45 LTB via sigma_m,crit -
  negligible, but the wrong edition. Every other softwood value matches
  EN 338:2016 exactly.

### Closed by engineer decision

- **N9 (GL36H/GL36C) — RETAIN, marked legacy.** Suppliers still offer 36
  grade glulam. `timber-ec5` now emits `LegacyGradeWarning` on lookup
  (withdrawn BS EN 1194:1999 classes, not in BS EN 14080:2013; confirm
  procurement and declared properties with the supplier).
- **N5 (bearing in auto-sizing) — INFORMATIVE ONLY.** The support detail is
  more likely to be changed than the beam size, so a bearing failure must not
  drive the section search. Implemented in `timber-ec5`: sizing accepts on
  every applicable check except bearing; the bearing result is still evaluated
  and reported per candidate, and a failing bearing on the returned solution
  raises `SizingResult.bearing_advisory` directing the engineer to the support
  detail. (The legacy auto-sizers still do not check bearing at all - N5's
  legacy caveat stands.)
- **N3 (green oak service class for strength) — OPTIONAL FLAG.**
  `TimberBeam.green_oak_peak_load_while_wet` (timber-ec5, green oak only,
  validated): when True, strength checks (bending, shear, LTB, bearing) take
  k_mod at service class 3 - for peak ULS demand expected before the member
  dries below 20% moisture content - while the deflection check keeps the
  declared service class for k_def. Default False uses the declared service
  class throughout, per the cl. 2.3.1.3 environment reading.
- **P1 (G_0,05 derivations) — ACCEPTED** as the project convention
  (already addressed by the engineer).
- **P3 (LVL data) — PRELIMINARY DESIGN ONLY.** `timber-ec5` now emits
  `PreliminaryDataWarning` on every LVL grade lookup: the bundled values are
  of limited provenance and may be wrong or outdated; current supplier data
  (DoP/certificate) must be obtained before reliance, especially shear and
  compression perpendicular.
- **P6 (trimmer fits) — PROVENANCE IDENTIFIED.** Source confirmed by the
  engineer: *Manual for the Design of Timber Building Structures to
  Eurocode 5* (IStructE/TRADA), **section 8.4.4** (trimmer beam calculation).
  Cited in both repos' docstrings and `timber_ec5.codes.TIMBER_MANUAL`.
  Remaining: record the edition/year of the copy in use and transcribe the
  fitted validity ranges and embedded load/spacing assumptions from s. 8.4.4.

### Closed later on 28 August 2026 (second pass, engineer decisions)

- **N2 (green oak SC3 k_def) — CLOSED: 2.0 retained.** Engineer's rationale:
  an SC3 member cannot get wetter than its installed near-saturation state;
  the cl. 3.2(4) +1.0 addresses the drying that occurs under load towards
  drier environments, which does not apply in SC3. Documented in
  `timber_ec5.factors.k_def`.
- **P2 (green oak TH values) — ACCEPTED and applied in both repos.**
  f_c,90,k realigned from the superseded EN 338:2003 D30/D40 values to
  EN 338:2016 Table 3: TH1/TH2/THB 8.0 → 5.3 MPa, THA 8.8 → 5.5 MPa (the wet
  condition is handled by k_mod - now the SC3 flag - not the characteristic
  value, which is referenced to 12% m.c.). TH2 E_0,05 6590 → 5640 MPa
  (0.84 x E_0,mean per the EN 384 hardwood ratio, the ratio every
  EN 338:2016 D-class row exhibits; the recorded 0.98 x E_0,mean was
  physically implausible). Basis: engineer-accepted derivations, not book
  citations - recorded in the timber-ec5 README provenance table and pinned
  in its test suite. Other TH values retained from the book (2003-era
  stiffnesses, conservative for deflection).
- **P6 (trimmer fits) — CLOSED.** Edition confirmed: IStructE/TRADA, 2007.
  Transcription of both fits verified against the engineer's copy of s. 8.4.4,
  including the previously unexplained 1.075 C24 coefficient (the Manual's
  "increase S_max by 7.5% for C24") and the legacy `self.length` divisor
  (d2 - the trimming joist's own trial span; the fit is implicit).
  Validity ranges and embedded loads now transcribed and ENFORCED in
  `timber_ec5.joist` (documented, not enforced, in this repo): trimmed joist
  span <= 6 m; 38 <= b <= 75 mm per member; 147 <= h <= 220 mm; supported
  trimmer span <= 3.0 m (Fig 8.1); assumes 0.5 kN/m2 floor dead + 1.5 kN/m2
  imposed and lightweight partitions <= 0.8 kN/m run. Residual micro-item:
  the Manual defines d1/d2/d3 by cross-reference to its Fig 4.3(b) - confirm
  the d2 = trimming-joist-span reading against that figure.
- **Modal damping ratio — CLOSED: UK NA default 0.02 retained** as the
  `TimberFloor.modal_damping_ratio` default, documented as user-overridable
  (EC5 cl. 7.3.1(2) recommends 0.01 unless proven - noted for non-UK use).
- **P4 (k_strut = 0.97) — CLOSED: confirmed** against the engineer's copy of
  the UK NA (NA.2.7.2).

### Final closures — 28 August 2026

- **UK NA edition strings — CLOSED**: confirmed correct by the engineer
  against the copies in use; the CHECK note in `timber_ec5.codes` is removed.
- **k_dist unit convention — CLOSED**: the NA defines (EI)_b as the floor
  flexural rigidity perpendicular to the joists in N.mm^2/m, matching the
  code's convention, so the expression as coded reproduces the NA value.
- **P6 d1/d2/d3 definitions — CLOSED**: confirmed by the engineer. d2 is the
  length of the double member trimming joist itself - the full-length floor
  joist that picks up the double member trimmer, which in turn trims
  (supports) the partial-length joists at the opening. This matches the
  code's reading (legacy `self.length`; `trimming_joist_span` in timber-ec5);
  the fit is implicit in the d1/d2 term.

**All review findings are now closed.** No open engineer actions remain.

### Standing per-use notes (not open actions)

These are inherent to how the values work, enforced or surfaced by the code
at the point of use - nothing to check now:

- **N4 (k_c,90)**: an enhanced bearing condition may only be claimed when the
  cl. 6.1.5(3)/(4) geometry of the SPECIFIC support being designed satisfies
  the clause (clear distance l_1 >= 2h; bearing length <= 400 mm for the
  glulam discrete value). By nature a per-use verification; the enum, check
  result notes and docstrings state the conditions whenever an enhanced value
  is selected.
- **P3 (LVL)**: preliminary design only; `PreliminaryDataWarning` fires on
  every LVL lookup, which is exactly when current supplier data (DoP or
  certificate) must be obtained.
- **Trimmer/trimming-joist fits**: initial sizing only, within the Manual's
  enforced ranges and stated loading assumptions; the chosen member must
  still be verified by calculation.
