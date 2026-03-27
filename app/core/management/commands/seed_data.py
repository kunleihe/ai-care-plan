from django.core.management.base import BaseCommand
from core.models import Patient, Provider, Order, CarePlan


PATIENTS = [
    {"first_name": "James",   "last_name": "Wilson",   "mrn": "MRN-001234", "dob": "1965-03-15"},
    {"first_name": "Mary",    "last_name": "Johnson",  "mrn": "MRN-002345", "dob": "1978-11-22"},
    {"first_name": "Robert",  "last_name": "Davis",    "mrn": "MRN-003456", "dob": "1952-07-08"},
    {"first_name": "Linda",   "last_name": "Martinez", "mrn": "MRN-004567", "dob": "1989-02-14"},
    {"first_name": "Michael", "last_name": "Brown",    "mrn": "MRN-005678", "dob": "1943-09-30"},
]

PROVIDERS = [
    {"first_name": "Sarah",   "last_name": "Chen",    "npi": "1234567890"},
    {"first_name": "Michael", "last_name": "Torres",  "npi": "2345678901"},
    {"first_name": "Emily",   "last_name": "Park",    "npi": "3456789012"},
]

ORDERS = [
    {
        "patient_mrn": "MRN-001234",
        "provider_npi": "1234567890",
        "medication": "Rituximab 375 mg/m² IV",
        "diagnosis": "C83.39",
        "medical_notes": "Diffuse large B-cell lymphoma, cycle 3 of 6. Premedicate with acetaminophen and diphenhydramine.",
        "care_plan_status": "completed",
        "care_plan_content": """1. Problem List / Drug Therapy Problems (DTPs)
- Potential infusion-related reaction to Rituximab
- Risk of tumor lysis syndrome post-infusion
- Myelosuppression from concurrent CHOP regimen

2. Goals (SMART)
- Primary Goal: Complete 6 cycles of R-CHOP with CR confirmed by PET-CT within 6 months
- Safety Goal: No grade 3+ infusion reactions; manage mild reactions (fever, chills) with premedication
- Process Goal: Patient to attend all scheduled infusion appointments and labs

3. Pharmacist Interventions / Plan
- Dosing & Administration: Rituximab 375 mg/m² IV; initiate at 50 mg/hr, increase by 50 mg/hr every 30 min to max 400 mg/hr
- Premedication: Acetaminophen 650 mg PO + Diphenhydramine 25 mg IV 30 min before infusion
- Adverse Event Management: Hold infusion for grade ≥2 reactions; restart at 50% of previous rate once resolved

4. Monitoring Plan & Lab Schedule
- Before first dose: CBC with differential, CMP, uric acid, LDH, hepatitis B surface antigen
- During treatment: Vitals every 15 min × 1 hr, then every 30 min; CBC on day 14 of each cycle
- After treatment: PET-CT at cycle 3 and end of treatment; hepatitis B reactivation monitoring q3 months""",
    },
    {
        "patient_mrn": "MRN-001234",
        "provider_npi": "2345678901",
        "medication": "Methotrexate 15 mg PO weekly",
        "diagnosis": "M05.79",
        "medical_notes": "Seropositive rheumatoid arthritis, inadequate response to NSAIDs. Starting MTX therapy.",
        "care_plan_status": "completed",
        "care_plan_content": """1. Problem List / Drug Therapy Problems (DTPs)
- Active RA with joint inflammation and elevated CRP/ESR
- Risk of MTX hepatotoxicity with alcohol use history
- Folate deficiency risk associated with MTX

2. Goals (SMART)
- Primary Goal: Achieve DAS28 < 2.6 within 3 months of MTX initiation
- Safety Goal: Maintain LFTs within 2× ULN; no dose reduction needed due to hepatotoxicity
- Process Goal: Patient takes folic acid 1 mg daily on non-MTX days

3. Pharmacist Interventions / Plan
- Dosing & Administration: MTX 15 mg PO once weekly; take on the same day each week
- Premedication: Folic acid 1 mg PO daily (except MTX day) to reduce side effects
- Adverse Event Management: Hold MTX for LFTs > 3× ULN or WBC < 3,000; counsel on alcohol avoidance

4. Monitoring Plan & Lab Schedule
- Before first dose: CBC, CMP, hepatitis B/C serology, chest X-ray
- During treatment: CBC + CMP at 4 weeks, then every 8–12 weeks
- After treatment: Annual LFT review; reassess disease activity at 3 and 6 months""",
    },
    {
        "patient_mrn": "MRN-002345",
        "provider_npi": "1234567890",
        "medication": "Adalimumab 40 mg SC every 2 weeks",
        "diagnosis": "K50.10",
        "medical_notes": "Crohn's disease, moderate-to-severe. Failed conventional therapy. Starting biologic.",
        "care_plan_status": "completed",
        "care_plan_content": """1. Problem List / Drug Therapy Problems (DTPs)
- Active luminal Crohn's with elevated fecal calprotectin and CRP
- Latent TB risk prior to biologic initiation
- Injection site reaction potential with adalimumab

2. Goals (SMART)
- Primary Goal: Achieve clinical remission (CDAI < 150) within 12 weeks
- Safety Goal: No serious infections or reactivation of latent TB during therapy
- Process Goal: Patient demonstrates correct self-injection technique before discharge

3. Pharmacist Interventions / Plan
- Dosing & Administration: Adalimumab 160 mg SC at week 0, 80 mg at week 2, then 40 mg every 2 weeks
- Premedication: Allow pen to reach room temperature 15–30 min before injection
- Adverse Event Management: Counsel on infection signs; hold for active infection; report to provider within 24 hr

4. Monitoring Plan & Lab Schedule
- Before first dose: TB (IGRA), hepatitis B/C, CBC, CMP, ANA
- During treatment: CBC + CMP at 3 months, then every 6 months; CDAI assessment at weeks 4 and 12
- After treatment: Colonoscopy at 1 year to assess mucosal healing""",
    },
    {
        "patient_mrn": "MRN-002345",
        "provider_npi": "3456789012",
        "medication": "Insulin Glargine 20 units SC at bedtime",
        "diagnosis": "E11.65",
        "medical_notes": "Type 2 diabetes with hyperglycemia uncontrolled on oral agents alone. A1c 9.2%.",
        "care_plan_status": "processing",
        "care_plan_content": "",
    },
    {
        "patient_mrn": "MRN-003456",
        "provider_npi": "2345678901",
        "medication": "Carfilzomib 27 mg/m² IV",
        "diagnosis": "C90.01",
        "medical_notes": "Multiple myeloma, relapsed/refractory. Second-line therapy. Cycle 1 Day 1.",
        "care_plan_status": "completed",
        "care_plan_content": """1. Problem List / Drug Therapy Problems (DTPs)
- Relapsed myeloma with rising M-protein and bone pain
- Cardiovascular risk with carfilzomib (hypertension, cardiac failure)
- VTE prophylaxis required

2. Goals (SMART)
- Primary Goal: Achieve ≥ partial response (PR) by cycle 4 per IMWG criteria
- Safety Goal: Maintain BP < 140/90 throughout therapy; no cardiac events
- Process Goal: Patient adherent to daily dexamethasone and VTE prophylaxis

3. Pharmacist Interventions / Plan
- Dosing & Administration: Carfilzomib 20 mg/m² IV cycle 1 days 1 & 2, then 27 mg/m²; infuse over 10 min
- Premedication: Dexamethasone 4 mg IV 30 min before + IV hydration 250 mL NS before and after
- Adverse Event Management: Hold for grade 3 cardiac events; antihypertensives PRN for BP management

4. Monitoring Plan & Lab Schedule
- Before first dose: Echo or MUGA scan, BMP, CBC, serum protein electrophoresis (SPEP)
- During treatment: BP monitoring pre/post each dose; BMP on day 1 of each cycle
- After treatment: SPEP/SFLC every 2 cycles; echo at cycle 4""",
    },
    {
        "patient_mrn": "MRN-004567",
        "provider_npi": "3456789012",
        "medication": "Infliximab 5 mg/kg IV",
        "diagnosis": "L40.50",
        "medical_notes": "Psoriatic arthritis, moderate. Failed MTX. Starting infliximab induction.",
        "care_plan_status": "pending",
        "care_plan_content": "",
    },
    {
        "patient_mrn": "MRN-005678",
        "provider_npi": "1234567890",
        "medication": "Lenalidomide 25 mg PO days 1–21 of 28-day cycle",
        "diagnosis": "C90.00",
        "medical_notes": "Multiple myeloma, newly diagnosed. Part of VRd regimen. Cycle 1.",
        "care_plan_status": "failed",
        "care_plan_content": "",
    },
    {
        "patient_mrn": "MRN-004567",
        "provider_npi": "2345678901",
        "medication": "Dupilumab 300 mg SC every 2 weeks",
        "diagnosis": "L20.89",
        "medical_notes": "Atopic dermatitis, moderate-to-severe. Failed topical corticosteroids and cyclosporine.",
        "care_plan_status": "completed",
        "care_plan_content": """1. Problem List / Drug Therapy Problems (DTPs)
- Chronic moderate-to-severe AD with widespread eczema and pruritus
- Sleep disturbance secondary to itch
- Conjunctivitis risk associated with dupilumab

2. Goals (SMART)
- Primary Goal: Achieve IGA 0/1 and ≥75% improvement in EASI score (EASI-75) at week 16
- Safety Goal: No conjunctivitis requiring ophthalmology referral within first 6 months
- Process Goal: Patient performs correct SC self-injection and uses emollient moisturizer twice daily

3. Pharmacist Interventions / Plan
- Dosing & Administration: Dupilumab 600 mg SC (two 300 mg injections) at week 0, then 300 mg every 2 weeks
- Premedication: None required; allow syringe to warm to room temperature 45 min before injection
- Adverse Event Management: Lubricating eye drops for mild conjunctivitis; refer to ophthalmology if persistent

4. Monitoring Plan & Lab Schedule
- Before first dose: Skin swab if superinfection suspected; rule out active infection
- During treatment: EASI and IGA scoring at weeks 4, 8, and 16; assess for conjunctivitis at each visit
- After treatment: Reassess need for continuation at week 52 based on clinical response""",
    },
]


class Command(BaseCommand):
    help = "Seed the database with mock clinical data"

    def handle(self, *args, **options):
        self.stdout.write("Clearing existing data...")
        CarePlan.objects.all().delete()
        Order.objects.all().delete()
        Patient.objects.all().delete()
        Provider.objects.all().delete()

        self.stdout.write("Creating providers...")
        provider_map = {}
        for p in PROVIDERS:
            provider = Provider.objects.create(**p)
            provider_map[p["npi"]] = provider
            self.stdout.write(f"  Created: Dr. {p['first_name']} {p['last_name']}")

        self.stdout.write("Creating patients...")
        patient_map = {}
        for p in PATIENTS:
            patient = Patient.objects.create(**p)
            patient_map[p["mrn"]] = patient
            self.stdout.write(f"  Created: {p['first_name']} {p['last_name']} ({p['mrn']})")

        self.stdout.write("Creating orders and care plans...")
        for o in ORDERS:
            order = Order.objects.create(
                patient=patient_map[o["patient_mrn"]],
                provider=provider_map[o["provider_npi"]],
                medication=o["medication"],
                diagnosis=o["diagnosis"],
                medical_notes=o["medical_notes"],
            )
            CarePlan.objects.create(
                order=order,
                content=o["care_plan_content"],
                status=o["care_plan_status"],
            )
            self.stdout.write(f"  Order #{order.pk}: {o['medication']} [{o['care_plan_status']}]")

        self.stdout.write(self.style.SUCCESS(
            f"\nDone! Created {len(PROVIDERS)} providers, {len(PATIENTS)} patients, {len(ORDERS)} orders & care plans."
        ))
